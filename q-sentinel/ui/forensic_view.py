import numpy as np
import pandas as pd
import streamlit as st

def render(result,bits):
    rows=result['windows']
    if not rows: st.info('No complete windows to inspect.'); return
    flagged=[r['window'] for r in rows if r['state'] in ['Early Warning','Degraded','Critical']]
    st.caption('Flagged windows: '+(', '.join(map(str,flagged[:25])) or 'none'))
    number=st.selectbox('Inspect window',[r['window'] for r in rows],index=(flagged[0]-1 if flagged else len(rows)-1))
    row=rows[number-1]; size=result['config']['window_size']
    st.subheader(f"Window {number} · {row['state']}")
    st.write(f"Absolute bits {row['bit_offset']:,}–{row['bit_offset']+size-1:,} (zero-based).")
    st.dataframe(pd.DataFrame([dict(metric=k,value=row[k],baseline=result['baseline'].get('mean',{}).get(k),standardized_change=row['z'][i]) for i,k in enumerate(['bias','autocorrelation','spectral','block_entropy'])]),hide_index=True,width='stretch')
    st.write('CUSUM score:',round(row['change_score'],3),' · threshold:',round(result['calibration'].get('threshold',0),3))
    st.bar_chart(pd.Series(row['signatures'],name='Signature match / 100'))
    st.dataframe(pd.DataFrame(row['tests']).drop(columns=['parameters']),hide_index=True,width='stretch')
    if bits is None:
        st.info('Raw bits were not retained for this historical session. Metrics and evidence remain available.'); return
    page=st.number_input('Bit page (512 bits per page)',0,(size-1)//512,0)
    start=row['bit_offset']+int(page)*512; end=min(start+512,row['bit_offset']+size)
    st.code('\n'.join(f'{offset:010d}  '+''.join(map(str,bits[offset:min(offset+64,end)])) for offset in range(start,end,64)),language=None)
    st.code(np.packbits(bits[start:end]).tobytes().hex(' '),language=None)
    st.caption('Hex uses MSB-first packing; final byte is zero-padded if the displayed selection is not byte-aligned.')
