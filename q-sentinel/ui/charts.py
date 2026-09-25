import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# Matching wonder-of-AI color palette: blue, mint, gold, red, purple
COLORS = ['#5b8cff', '#22c7a8', '#e6b85c', '#ef6a6a', '#ae8cff']

def frame(result):
    return pd.DataFrame([{k: v for k, v in r.items() if k not in ['tests', 'signatures', 'components', 'z', 'forecast']} for r in result['windows']])

def style(fig, title=None):
    title_dict = dict(text=title, x=0.01, y=0.98, xanchor='left', yanchor='top') if title else None
    fig.update_layout(
        template='plotly_dark',
        title=title_dict,
        paper_bgcolor='#111925',
        plot_bgcolor='#111925',
        font=dict(family='Space Grotesk, sans-serif', color='#e7edf7'),
        colorway=COLORS,
        margin=dict(l=25, r=25, t=75, b=35),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1.0),
        hovermode='x unified'
    )
    return fig

def timeline(result, columns, title, limit=300):
    df = frame(result).tail(limit)
    fig = go.Figure()
    
    col_colors = {
        'health': '#e6b85c',
        'shannon': '#5b8cff',
        'min_entropy': '#22c7a8',
        'collision': '#ae8cff',
        'block_entropy': '#ff9e9e',
        'bias': '#ef6a6a',
        'autocorrelation': '#5b8cff',
        'change_score': '#ef6a6a',
        'nist_pass_rate': '#22c7a8'
    }
    
    for col in columns:
        if col in df:
            line_dict = dict(color=col_colors.get(col)) if col in col_colors else {}
            if col == 'health':
                line_dict['width'] = 2.5
            fig.add_trace(go.Scatter(x=df['window'], y=df[col], name=col.replace('_', ' ').title(), mode='lines', line=line_dict))
            
    first = next((e for e in result['events'] if e['state'] in ['Early Warning', 'Degraded', 'Critical']), None)
    if first:
        fig.add_vline(x=first['window'], line_dash='dash', line_color='#e6b85c', annotation_text='First detected degradation')
    changes = [e for e in result['events'] if e['kind'] == 'Change point']
    for event in changes[:8]:
        fig.add_vline(x=event['window'], line_dash='dot', line_color='#ae8cff')
    for event in [e for e in result['events'] if e['kind'] == 'Recovery'][:5]:
        fig.add_vline(x=event['window'], line_color='#22c7a8', annotation_text='Recovery')
    fig.update_xaxes(title='Window (1-based; exact bit offsets in forensics)')
    return style(fig, title)

def fingerprint(result, name='Current', fig=None):
    row = next((r for r in reversed(result['windows']) if r['components']), None)
    fig = fig or go.Figure()
    if row:
        labels = list(row['components'])
        vals = [row['components'][k] for k in labels]
        fig.add_trace(go.Scatterpolar(r=vals + [vals[0]], theta=labels + [labels[0]], fill='toself', name=name, line=dict(color='#5b8cff')))
    fig.update_layout(polar=dict(radialaxis=dict(range=[0, 100], visible=True)), height=390)
    return style(fig, 'Entropy fingerprint · normalized stability')

SIGNATURE_META = [
    ('Bit bias', 'Bias', '#ef6a6a'),
    ('Periodic pattern', 'Periodicity', '#22c7a8'),
    ('Serial correlation', 'Correlation', '#5b8cff'),
    ('Burst error', 'Bursts', '#e6b85c'),
    ('Repeated sequence', 'Repetition', '#ae8cff'),
    ('Sudden collapse', 'Collapse', '#ff7d99'),
    ('Gradual drift', 'Drift', '#ff9e64'),
]

def signature_trends(result, limit=300):
    """
    Intuitive multi-line evolution chart of degradation signatures across windows.
    Provides clear color-coded signal tracking, threshold indication at 30, and clean hover tooltips.
    """
    rows = result['windows'][-limit:]
    fig = go.Figure()
    
    if not rows:
        return style(fig, 'Degradation Signature Evolution')
        
    windows = [r['window'] for r in rows]
    
    # Operational alert threshold at 30
    fig.add_hline(
        y=30,
        line_dash='dash',
        line_color='#e6b85c',
        line_width=1.8,
        annotation_text='Alert Threshold (Match ≥ 30)',
        annotation_position='top right',
        annotation_font=dict(color='#e6b85c', size=11)
    )

    for key, label, color in SIGNATURE_META:
        scores = [r['signatures'].get(key, 0) for r in rows]
        fig.add_trace(go.Scatter(
            x=windows,
            y=scores,
            name=label,
            mode='lines',
            line=dict(color=color, width=2.2),
            hovertemplate=f'{label}: %{{y:.1f}} match<extra></extra>'
        ))

    # Mark first detected event if available
    first = next((e for e in result.get('events', []) if e.get('state') in ['Early Warning', 'Degraded', 'Critical']), None)
    if first:
        fig.add_vline(
            x=first['window'],
            line_dash='dash',
            line_color='#ef6a6a',
            line_width=1.5,
            annotation_text=f'Fault Event (Win {first["window"]})',
            annotation_position='top left',
            annotation_font=dict(color='#ef6a6a', size=11)
        )

    fig.update_xaxes(
        title=dict(text='Window Index', font=dict(size=12)),
        gridcolor='#1f2b3e',
        zerolinecolor='#26364b'
    )
    fig.update_yaxes(
        title=dict(text='Match Score (0 to 100)', font=dict(size=12)),
        range=[-2, 105],
        gridcolor='#1f2b3e',
        zerolinecolor='#26364b'
    )
    fig.update_layout(
        height=380,
        hovermode='x unified',
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.03,
            xanchor='left',
            x=0.0
        )
    )
    return style(fig, 'Degradation Signature Evolution · Continuous Match Tracking')

def signature_bars(result):
    """
    Horizontal bar chart showing peak signature match across all analyzed windows.
    Immediately highlights which failure mode dominated and whether it crossed the operational threshold.
    """
    rows = result['windows']
    fig = go.Figure()
    
    if not rows:
        return style(fig, 'Peak Degradation Match Severity')
        
    labels = []
    peak_scores = []
    bar_colors = []
    
    for key, label, _ in reversed(SIGNATURE_META):
        max_score = max((r['signatures'].get(key, 0) for r in rows), default=0)
        labels.append(label)
        peak_scores.append(max_score)
        if max_score >= 50:
            bar_colors.append('#ef6a6a')  # Critical fault match
        elif max_score >= 30:
            bar_colors.append('#e6b85c')  # Warning / alert match
        elif max_score > 5:
            bar_colors.append('#5b8cff')  # Low activity
        else:
            bar_colors.append('#22c7a8')  # Nominal clean
            
    fig.add_trace(go.Bar(
        x=peak_scores,
        y=labels,
        orientation='h',
        marker=dict(
            color=bar_colors,
            line=dict(color='#0b121d', width=1.5)
        ),
        text=[f'{s:.1f} / 100' for s in peak_scores],
        textposition='outside',
        textfont=dict(size=11, color='#e7edf7'),
        hovertemplate='Signature: %{y}<br>Peak Match: %{x:.1f}/100<extra></extra>'
    ))
    
    # Threshold line at 30
    fig.add_vline(
        x=30,
        line_dash='dash',
        line_color='#e6b85c',
        line_width=2,
        annotation_text='Trigger Threshold (30)',
        annotation_position='top right',
        annotation_font=dict(color='#e6b85c', size=11)
    )
    
    fig.update_xaxes(
        title=dict(text='Peak Observed Match Score (0 - 100)', font=dict(size=12)),
        range=[0, 115],
        gridcolor='#1f2b3e',
        zerolinecolor='#26364b'
    )
    fig.update_yaxes(
        gridcolor='#1f2b3e',
        zerolinecolor='#26364b'
    )
    fig.update_layout(
        height=320,
        margin=dict(l=90, r=40, t=75, b=35)
    )
    return style(fig, 'Peak Degradation Match Severity (Whole Stream)')

def heatmap(result):
    rows = result['windows'][-300:]
    z_data = [[r['signatures'].get(k, 0) for r in rows] for k, _, _ in SIGNATURE_META]
    labels = [l for _, l, _ in SIGNATURE_META]
    fig = go.Figure(go.Heatmap(
        z=z_data,
        x=[r['window'] for r in rows],
        y=labels,
        zmin=0,
        zmax=100,
        colorscale=[
            [0.0, '#0c1420'],
            [0.2, '#182d49'],
            [0.3, '#2a4d7d'],
            [0.6, '#e6b85c'],
            [1.0, '#ef6a6a']
        ],
        colorbar=dict(
            title=dict(text='Match', font=dict(color='#e7edf7', size=11)),
            tickfont=dict(color='#8ea3bf')
        ),
        hovertemplate='Window: %{x}<br>Signature: %{y}<br>Match: %{z:.1f}/100<extra></extra>'
    ))
    fig.update_xaxes(
        title=dict(text='Window Index', font=dict(size=12)),
        gridcolor='#1f2b3e'
    )
    fig.update_yaxes(
        gridcolor='#1f2b3e'
    )
    fig.update_layout(height=340)
    return style(fig, 'Degradation Signature Matrix Map')

def pvalues(result):
    """
    Renders a clear, structured histogram of windowed P-values with:
    - Distinct bar borders and subtle spacing
    - Rejection threshold reference (alpha = 0.01) in red
    - Expected uniform distribution level in gold
    - Clear x and y axis labels
    """
    values = [t['p_value'] for r in result['windows'] for t in r['tests'] if t['p_value'] is not None]
    fig = go.Figure()
    
    if values:
        nbins = 20
        fig.add_trace(go.Histogram(
            x=values,
            nbinsx=nbins,
            xbins=dict(start=0.0, end=1.0, size=0.05),
            marker=dict(
                color='#5b8cff',
                line=dict(color='#0b121d', width=1.5)
            ),
            name='Observed P-values',
            hovertemplate='P-value range: %{x}<br>Count: %{y} tests<extra></extra>'
        ))
        
        # Expected uniform count line
        expected_per_bin = len(values) / nbins
        fig.add_hline(
            y=expected_per_bin,
            line_dash='dot',
            line_color='#e6b85c',
            line_width=2,
            annotation_text=f'Expected Uniform Level ({expected_per_bin:.1f}/bin)',
            annotation_position='top right',
            annotation_font=dict(color='#e6b85c', size=11)
        )
        
        # Alpha = 0.01 Rejection Threshold
        fig.add_vline(
            x=0.01,
            line_dash='dash',
            line_color='#ef6a6a',
            line_width=2,
            annotation_text='α = 0.01 (Rejection Boundary)',
            annotation_position='top left',
            annotation_font=dict(color='#ef6a6a', size=11)
        )
        
    fig.update_xaxes(
        title=dict(text='P-Value (0.0 to 1.0 · Uniformly distributed under true randomness)', font=dict(size=12)),
        range=[-0.02, 1.02],
        gridcolor='#1f2b3e',
        zerolinecolor='#26364b'
    )
    fig.update_yaxes(
        title=dict(text='Test Count (Frequency across Windows)', font=dict(size=12)),
        gridcolor='#1f2b3e',
        zerolinecolor='#26364b'
    )
    fig.update_layout(
        height=380,
        bargap=0.06
    )
    return style(fig, 'P-Value Uniformity Distribution across Windows')

def nist_bars(result):
    """Horizontal bar chart showing P-values for each whole-stream NIST test family."""
    nist_tests = [t for t in result.get('nist', []) if t.get('p_value') is not None]
    fig = go.Figure()
    if nist_tests:
        names = [t['name'] for t in nist_tests]
        pvals = [t['p_value'] for t in nist_tests]
        statuses = [t.get('status', 'PASS') for t in nist_tests]
        bar_colors = ['#22c7a8' if s == 'PASS' else '#ef6a6a' for s in statuses]
        
        fig.add_trace(go.Bar(
            x=pvals,
            y=names,
            orientation='h',
            marker=dict(color=bar_colors, line=dict(color='#0b121d', width=1)),
            hovertemplate='Test: %{y}<br>P-value: %{x:.5f}<extra></extra>'
        ))
        
        fig.add_vline(
            x=0.01,
            line_dash='dash',
            line_color='#e6b85c',
            line_width=2,
            annotation_text='α = 0.01 Threshold',
            annotation_position='bottom right',
            annotation_font=dict(color='#e6b85c', size=11)
        )
        
    fig.update_xaxes(
        title=dict(text='P-Value (Values ≥ 0.01 PASS, < 0.01 FAIL)', font=dict(size=12)),
        range=[0, 1.02],
        gridcolor='#1f2b3e'
    )
    fig.update_yaxes(gridcolor='#1f2b3e')
    fig.update_layout(height=300)
    return style(fig, 'Whole-Stream NIST P-Values by Test Family')

def projection_chart(f, recent_windows=None):
    """
    Renders an intuitive health projection chart.
    If a degradation trend is detected, displays the projected decline, confidence envelope, and crossing point.
    If nominal/stable, displays recent window health stability verifying healthy margin above threshold.
    """
    fig = go.Figure()
    threshold = f.get('threshold', 40.0)
    
    # Red operational threshold line
    fig.add_hline(
        y=threshold,
        line_dash='dash',
        line_color='#ef6a6a',
        line_width=2,
        annotation_text=f'Intervention Threshold ({threshold:.0f})',
        annotation_position='bottom right',
        annotation_font=dict(color='#ef6a6a', size=11)
    )

    if f.get('available'):
        # Project future windows
        crossing = f['windows_to_threshold']
        end = min(120, int(np.ceil(crossing)) + 8)
        x_proj = np.arange(end + 1)
        y_proj = np.clip(f['current'] + f['slope'] * x_proj, 0, 100)
        
        # Uncertainty corridor
        low_slope = f.get('slope_interval', [f['slope'], f['slope']])[0]
        high_slope = f.get('slope_interval', [f['slope'], f['slope']])[1]
        y_low = np.clip(f['current'] + low_slope * x_proj, 0, 100)
        y_high = np.clip(f['current'] + high_slope * x_proj, 0, 100)

        # Upper bound
        fig.add_trace(go.Scatter(
            x=x_proj,
            y=y_high,
            mode='lines',
            line=dict(width=0),
            showlegend=False,
            hoverinfo='skip'
        ))
        # Lower bound with fill
        fig.add_trace(go.Scatter(
            x=x_proj,
            y=y_low,
            mode='lines',
            line=dict(width=0),
            fill='tonexty',
            fillcolor='rgba(239, 106, 106, 0.15)',
            name='95% Trend Interval',
            hoverinfo='skip'
        ))
        # Main projection line
        fig.add_trace(go.Scatter(
            x=x_proj,
            y=y_proj,
            mode='lines+markers',
            name='Projected Health Trajectory',
            line=dict(color='#ef6a6a', width=2.5),
            marker=dict(size=4),
            hovertemplate='Future Window: +%{x}<br>Projected Health: %{y:.1f}<extra></extra>'
        ))
        
        # Mark threshold crossing point
        if 0 < crossing <= end:
            fig.add_trace(go.Scatter(
                x=[crossing],
                y=[threshold],
                mode='markers+text',
                name='Projected Crossing',
                marker=dict(color='#e6b85c', size=11, symbol='circle'),
                text=[f' ~{crossing:.1f} windows'],
                textposition='top right',
                textfont=dict(color='#e6b85c', size=12),
                hovertemplate=f'Threshold Crossing: in ~{crossing:.1f} windows<extra></extra>'
            ))
            
        fig.update_xaxes(
            title=dict(text='Future Windows from Current Observation Point', font=dict(size=12)),
            gridcolor='#1f2b3e',
            zerolinecolor='#26364b'
        )
        fig.update_yaxes(
            title=dict(text='Operational Health Score (0 - 100)', font=dict(size=12)),
            range=[-2, 105],
            gridcolor='#1f2b3e',
            zerolinecolor='#26364b'
        )
        fig.update_layout(height=350)
        return style(fig, f'Entropy Risk Projection · Critical Crossing in ~{crossing:.1f} Windows')

    else:
        # Display stability verification from recent observed windows
        if recent_windows:
            x_wins = [w['window'] for w in recent_windows]
            y_health = [w.get('health', 100.0) for w in recent_windows]
            
            fig.add_trace(go.Scatter(
                x=x_wins,
                y=y_health,
                mode='lines+markers',
                name='Observed Health',
                line=dict(color='#22c7a8', width=2.5),
                marker=dict(size=5, color='#22c7a8'),
                fill='tozeroy',
                fillcolor='rgba(34, 199, 168, 0.08)',
                hovertemplate='Window: %{x}<br>Health: %{y:.1f}/100<extra></extra>'
            ))
            fig.update_xaxes(
                title=dict(text='Evaluated Window Index', font=dict(size=12)),
                gridcolor='#1f2b3e',
                zerolinecolor='#26364b'
            )
        else:
            fig.add_annotation(
                text='Stable stream: No downward degradation trajectory detected.',
                xref='paper', yref='paper', x=0.5, y=0.5,
                showarrow=False, font=dict(color='#22c7a8', size=14)
            )
            
        fig.update_yaxes(
            title=dict(text='Operational Health Score (0 - 100)', font=dict(size=12)),
            range=[0, 105],
            gridcolor='#1f2b3e',
            zerolinecolor='#26364b'
        )
        fig.update_layout(height=320)
        return style(fig, 'Health Stability Verification · Nominal Trend (Above Intervention Threshold)')
