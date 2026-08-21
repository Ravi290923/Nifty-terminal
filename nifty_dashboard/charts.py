"""Builds the annotated candlestick chart — same visual language as the JS
dashboard (amber resistance, blue support, violet Fibonacci, translucent
FVG zones, amber SMC pivot labels) but rendered with Plotly.
"""

import plotly.graph_objects as go

from nifty_dashboard import analytics

BULL = "#34D8AE"
BEAR = "#F16B76"
AMBER = "#E8A63D"
VIOLET = "#A78BFA"
BLUE = "#5FA8F5"
GRID = "#232E3D"
TEXT = "#E8ECF2"


def build_chart(df, show_smc=True, show_fvg=True, show_fib=True, levels=None, height=520):
    x = df.index
    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=x, open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        increasing_line_color=BULL, decreasing_line_color=BEAR,
        increasing_fillcolor=BULL, decreasing_fillcolor=BEAR,
        name="Price", showlegend=False,
    ))

    if show_fvg:
        for f in analytics.find_fvgs(df):
            x0 = x[max(0, f["index"] - 2)]
            fig.add_shape(
                type="rect", x0=x0, x1=x[-1], y0=min(f["from"], f["to"]), y1=max(f["from"], f["to"]),
                fillcolor=BULL if f["type"] == "bull" else BEAR, opacity=0.13, line_width=0, layer="below",
            )

    if levels:
        fig.add_hline(y=levels["resistance"], line_dash="dash", line_color=AMBER, line_width=1.2,
                       annotation_text=f"Resistance {levels['resistance']:.2f}", annotation_position="top left",
                       annotation_font_color=AMBER, annotation_font_size=10.5)
        fig.add_hline(y=levels["support"], line_dash="dash", line_color=BLUE, line_width=1.2,
                       annotation_text=f"Support {levels['support']:.2f}", annotation_position="bottom left",
                       annotation_font_color=BLUE, annotation_font_size=10.5)

    if show_fib:
        fib = analytics.find_fib(df)
        for lvl in fib["levels"]:
            fig.add_hline(y=lvl["price"], line_dash="dot", line_color=VIOLET, line_width=1, opacity=0.85,
                           annotation_text=f"{lvl['r']:.3f} · {lvl['price']:.2f}", annotation_position="top right",
                           annotation_font_color=VIOLET, annotation_font_size=10)

    if show_smc:
        smc = analytics.analyze_smc(df)
        for p in smc["pivots"]:
            fig.add_annotation(
                x=x[p["index"]], y=p["price"], text=p["label"], showarrow=False,
                font=dict(color=AMBER, size=10), yshift=12 if p["type"] == "H" else -12,
            )
            fig.add_trace(go.Scatter(x=[x[p["index"]]], y=[p["price"]], mode="markers",
                                      marker=dict(color=AMBER, size=5), showlegend=False, hoverinfo="skip"))
        if smc["bos"]:
            bos = smc["bos"]
            color = BULL if bos["type"] == "bullish" else BEAR
            fig.add_hline(y=bos["level"], line_dash="dashdot", line_color=color, line_width=1.4,
                           annotation_text=bos["label"], annotation_position="top left",
                           annotation_font_color=color, annotation_font_size=10.5)

    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT, family="IBM Plex Mono, monospace", size=11),
        xaxis=dict(showgrid=False, rangeslider=dict(visible=False), color=TEXT),
        yaxis=dict(showgrid=True, gridcolor=GRID, color=TEXT, side="right"),
        hovermode="x unified",
    )
    return fig


def sparkline_figure(closes, tone="flat", height=40, width=110):
    color = BULL if tone == "bull" else BEAR if tone == "bear" else "#7C8B9E"
    fig = go.Figure(go.Scatter(y=list(closes), mode="lines", line=dict(color=color, width=1.6)))
    fig.update_layout(
        height=height, width=width, margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False), yaxis=dict(visible=False), showlegend=False,
    )
    return fig
