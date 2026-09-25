import itertools
import numpy as np
import pandas as pd
import streamlit as st

from core.inconsistencies import get_short_explanation

def render(result, bits=None):
    st.subheader('Inconsistency Explorer')
    st.caption('Focused event-level and bit-level forensic view of detected anomalies.')
    
    inconsistencies = result.get('inconsistencies', [])
    summary = result.get('inconsistency_summary', {})
    w_size = result['config']['window_size']
    rows = result.get('windows', [])
    
    # 1. Summary Cards
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric('TOTAL EVENTS', str(summary.get('total_events', len(inconsistencies))))
    c2.metric('AFFECTED WINDOWS', str(summary.get('unique_affected_windows', 0)))
    c3.metric('FLAGGED RANGES', str(summary.get('flagged_ranges_count', 0)))
    c4.metric('FIRST DETECTED', str(summary.get('first_detected', 'None')))
    c5.metric('PRIMARY TYPE', str(summary.get('most_common_type', 'None')))
    c6.metric('HIGHEST SEVERITY', str(summary.get('highest_severity', 'Healthy')))
    
    st.divider()
    
    # 2. Inconsistency Events Table (if events exist)
    if inconsistencies:
        st.markdown('### Inconsistency Events')
        table_data = []
        for inc in inconsistencies:
            table_data.append({
                'ID': inc['id'],
                'Type': inc['type'],
                'Severity': inc['severity'],
                'First window': f"Window {inc['first_detected_window']}",
                'Affected windows': f"{inc['affected_windows_count']} ({inc['affected_windows'][0]}–{inc['affected_windows'][-1]})" if inc['affected_windows_count'] > 1 else f"Window {inc['affected_windows'][0]}",
                'Bit range': f"{inc['bit_start']:,} – {inc['bit_end']:,}",
                'Evidence strength': inc['evidence_strength'].split('(')[0].strip(),
                'Status': inc['status']
            })
        st.dataframe(pd.DataFrame(table_data), hide_index=True, width='stretch')
        st.divider()
    elif not rows:
        st.info('No complete windows available to inspect.')
        return

    # 3. Window Selection
    flagged_wins = [r['window'] for r in rows if r.get('state') in ['Early Warning', 'Degraded', 'Critical']]
    all_wins = [r['window'] for r in rows]
    
    default_win_idx = 0
    if flagged_wins:
        default_win_idx = all_wins.index(flagged_wins[0])
        
    col_win, col_page = st.columns([3, 1])
    with col_win:
        sel_win = st.selectbox(
            'Select window to inspect',
            all_wins,
            index=default_win_idx,
            format_func=lambda w: f"Window {w} ({'Flagged · ' + rows[w-1]['state'] if rows[w-1]['state'] in ['Early Warning', 'Degraded', 'Critical'] else 'Healthy'})"
        )
        
    win_row = rows[sel_win - 1]
    
    # Find matching inconsistency event (if any)
    inc_match = next((inc for inc in inconsistencies if sel_win in inc['affected_windows']), None)
    
    # Get localized flagged ranges for this window
    win_ranges = []
    if inc_match:
        win_ranges = [rg for rg in inc_match.get('flagged_ranges', []) if rg.get('window') == sel_win]
        
    # Bit page selection
    max_pages = max(0, (w_size - 1) // 512)
    default_page = 0
    if win_ranges:
        # Default to the page containing the flagged range
        default_page = min(max_pages, max(0, win_ranges[0]['local_start'] // 512))
        
    with col_page:
        bit_page = st.number_input(
            'Bit slice (512 bits)',
            min_value=0,
            max_value=max_pages,
            value=default_page,
            key=f'page_sel_{sel_win}'
        )
        
    slice_start = (sel_win - 1) * w_size + int(bit_page) * 512
    slice_end = min(slice_start + 512, sel_win * w_size)
    
    # 4. Clear Window Title
    st.markdown(f"### Window {sel_win} | Bits {slice_start:,}–{slice_end - 1:,}")
    
    # 5. Compact Evidence Row
    ev1, ev2, ev3, ev4 = st.columns(4)
    ev1.metric('Bias', f"{win_row.get('bias', 0.0):+.4f}")
    ev2.metric('Entropy', f"{win_row.get('shannon', 1.0):.3f}")
    runs_status = next((t['status'] for t in win_row.get('tests', []) if t.get('name') == 'Runs'), 'PASS')
    ev3.metric('Runs test', runs_status)
    thresh = result.get('calibration', {}).get('threshold', 0.0)
    ev4.metric('CUSUM', f"{win_row.get('change_score', 0.0):.3f} / threshold {thresh:.3f}")
    
    # 6. Small Legend
    st.markdown('''
    <div style="font-size: 13px; margin: 14px 0 6px 0;">
      <span style="color: #ff4d4f; font-weight: bold; background: rgba(255, 77, 79, 0.18); padding: 2px 6px; border-radius: 3px;">Red</span> = flagged inspection region &nbsp;&nbsp;|&nbsp;&nbsp;
      <span style="color: #cbd5e1; background: #1e293b; padding: 2px 6px; border-radius: 3px;">Normal color</span> = surrounding bits
    </div>
    ''', unsafe_allow_html=True)
    
    # 7. Binary Sequence in rows with bit positions & red highlight
    if bits is not None:
        slice_bits = bits[slice_start:slice_end]
        rows_html = []
        
        def is_flagged(pos):
            return any(rg['start'] <= pos <= rg['end'] for rg in win_ranges)
            
        for r_start in range(slice_start, slice_end, 64):
            r_end = min(r_start + 64, slice_end)
            sub_bits = bits[r_start:r_end]
            
            spans = []
            for flagged, grp in itertools.groupby(enumerate(sub_bits), key=lambda x: is_flagged(r_start + x[0])):
                chars = ''.join(str(item[1]) for item in grp)
                if flagged:
                    spans.append(f'<span style="color: #ff4d4f; font-weight: bold; background: rgba(255, 77, 79, 0.22); border-radius: 2px; padding: 0 1px;">{chars}</span>')
                else:
                    spans.append(f'<span style="color: #cbd5e1;">{chars}</span>')
            rows_html.append(f'<div style="margin: 2px 0;"><span style="color: #64748b; margin-right: 14px; user-select: none;">{r_start:010d}</span>{"".join(spans)}</div>')
            
        st.markdown(f'''
        <div style="font-family: 'Consolas', 'Courier New', monospace; background: #0b1120; border: 1px solid #1e293b; border-radius: 8px; padding: 12px 14px; font-size: 13px; line-height: 1.5; overflow-x: auto;">
          {''.join(rows_html)}
        </div>
        ''', unsafe_allow_html=True)
        
        # 8. Hexadecimal representation below binary sequence
        hex_str = np.packbits(slice_bits).tobytes().hex(' ')
        st.markdown(f'''
        <div style="font-family: 'Consolas', 'Courier New', monospace; background: #080d18; border: 1px solid #1e293b; border-radius: 6px; padding: 9px 14px; font-size: 13px; margin-top: 8px; color: #94a3b8; word-break: break-all;">
          <span style="color: #64748b; font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; display: block; margin-bottom: 3px;">Hexadecimal (MSB-first):</span>
          {hex_str}
        </div>
        ''', unsafe_allow_html=True)
    else:
        st.info('Raw bit retention was not enabled for this session. Aggregate window metrics and test results remain available.')
        
    # 9. Short Explanation Only
    short_exp = get_short_explanation(win_row, inc_match, result.get('baseline'), result.get('calibration'))
    st.markdown(f"""
    **Type:** {short_exp['type']}  
    **Evidence:** {short_exp['evidence']}  
    **Measured by:** {short_exp['measurement']}
    """)
    
    # 10. Accurate Scientific Discipline
    st.caption('Red highlights show a statistical inspection region from the window; individual bits are not asserted to be physically defective.')
