import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

COLORS=['#75a7ff','#ae8cff','#53dfc3','#ffc66e','#ff7d99']

def frame(result):
    return pd.DataFrame([{k:v for k,v in r.items() if k not in ['tests','signatures','components','z','forecast']} for r in result['windows']])

def style(fig,title=None):
    title_dict = dict(text=title, x=0.01, y=0.98, xanchor='left', yanchor='top') if title else None
    fig.update_layout(
        template='plotly_dark',
        title=title_dict,
        paper_bgcolor='#101625',
        plot_bgcolor='#101625',
        font=dict(family='Inter, Segoe UI, sans-serif',color='#e0e8fa'),
        colorway=COLORS,
        margin=dict(l=25,r=25,t=75,b=35),
        legend=dict(orientation='h',yanchor='bottom',y=1.02,xanchor='right',x=1.0),
        hovermode='x unified'
    )
    return fig

def timeline(result,columns,title,limit=300):
    df=frame(result).tail(limit); fig=go.Figure()
    for col in columns:
        if col in df: fig.add_trace(go.Scatter(x=df['window'],y=df[col],name=col.replace('_',' ').title(),mode='lines'))
    first=next((e for e in result['events'] if e['state'] in ['Early Warning','Degraded','Critical']),None)
    if first: fig.add_vline(x=first['window'],line_dash='dash',line_color='#ffc66e',annotation_text='First detected degradation')
    changes=[e for e in result['events'] if e['kind']=='Change point']
    for event in changes[:8]: fig.add_vline(x=event['window'],line_dash='dot',line_color='#ae8cff')
    for event in [e for e in result['events'] if e['kind']=='Recovery'][:5]:
        fig.add_vline(x=event['window'],line_color='#53dfc3',annotation_text='Recovery')
    fig.update_xaxes(title='Window (1-based; exact bit offsets in forensics)')
    return style(fig,title)

def fingerprint(result,name='Current',fig=None):
    row=next((r for r in reversed(result['windows']) if r['components']),None)
    fig=fig or go.Figure()
    if row:
        labels=list(row['components']); vals=[row['components'][k] for k in labels]
        # Unavailable components remain gaps, never invented perfect scores.
        fig.add_trace(go.Scatterpolar(r=vals+[vals[0]],theta=labels+[labels[0]],fill='toself',name=name))
    fig.update_layout(polar=dict(radialaxis=dict(range=[0,100],visible=True)),height=390)
    return style(fig,'Entropy fingerprint · normalized stability')

def heatmap(result):
    rows=result['windows'][-300:]
    fig=go.Figure(go.Heatmap(z=[[r['signatures'].get(k,0) for r in rows] for k in ['Bit bias','Periodic pattern','Serial correlation','Burst error','Repeated sequence','Sudden collapse','Gradual drift']],x=[r['window'] for r in rows],y=['Bias','Periodicity','Correlation','Bursts','Repetition','Collapse','Drift'],zmin=0,zmax=100,colorscale=[[0,'#141c32'],[.5,'#7561c9'],[1,'#ff7799']],colorbar=dict(title='Match')))
    return style(fig,'Degradation signature map · match scores, not probabilities')

def pvalues(result):
    values=[t['p_value'] for r in result['windows'] for t in r['tests'] if t['p_value'] is not None]
    return style(go.Figure(go.Histogram(x=values,nbinsx=20,marker_color=COLORS[0])),'P-value distribution · correlated tests pooled for inspection only')
