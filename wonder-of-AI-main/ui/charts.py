from __future__ import annotations

import plotly.graph_objects as go


def entropy_chart(frame):
    fig = go.Figure()
    if not frame.empty:
        fig.add_trace(go.Scatter(x=frame["window"], y=frame["shannon"], name="Shannon", line={"color": "#5b8cff", "width": 3}))
        fig.add_trace(go.Scatter(x=frame["window"], y=frame["min_entropy"], name="Min entropy", line={"color": "#22c7a8", "width": 2}))
    fig.update_layout(template="plotly_dark", height=330, margin={"l": 20, "r": 20, "t": 35, "b": 20}, title="Entropy health timeline", yaxis_title="bits / bit", xaxis_title="window")
    return fig


def health_chart(frame):
    fig = go.Figure()
    if not frame.empty:
        fig.add_trace(go.Scatter(x=frame["window"], y=frame["health_score"], fill="tozeroy", name="Health score", line={"color": "#e6b85c", "width": 3}))
    fig.update_layout(template="plotly_dark", height=260, margin={"l": 20, "r": 20, "t": 35, "b": 20}, title="Window health score", yaxis={"range": [0, 100]})
    return fig
