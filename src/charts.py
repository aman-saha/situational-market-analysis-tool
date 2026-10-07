import plotly.graph_objects as go

def render_chart(df, selected_date):
    if df.empty:
        return None
    
    fig = go.Figure()

    # # 1. EMA Channel (Lower Line)
    # fig.add_trace(go.Scatter(
    #     x=df['date'], y=df['ema_low'],
    #     line=dict(color='rgba(100, 149, 237, 0.4)', width=1.5), 
    #     showlegend=False,
    #     name='EMA Low'
    # ))

    # # 2. EMA Channel (Upper Line + Fill)
    # fig.add_trace(go.Scatter(
    #     x=df['date'], y=df['ema_high'],
    #     line=dict(color='rgba(100, 149, 237, 0.4)', width=1.5),
    #     fill='tonexty', 
    #     fillcolor='rgba(100, 149, 237, 0.25)', 
    #     showlegend=False,
    #     name='10 EMA Channel'
    # ))

    # 3. Candlestick
    fig.add_trace(go.Candlestick(
        x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['close'],
        increasing_line_color='#1e1e1e', increasing_fillcolor='white',
        decreasing_line_color='#1e1e1e', decreasing_fillcolor='#1e1e1e',
        name="Price"
    ))

    # 4. Horizontal Lines (Previous Day Levels)
    if 'prev_day_high' in df.columns:
        fig.add_hline(y=df['prev_day_high'].iloc[0], line_dash="dot", 
                      line_color="#27ae60", opacity=0.5, annotation_text="P. High")
        fig.add_hline(y=df['prev_day_low'].iloc[0], line_dash="dot", 
                      line_color="#e74c3c", opacity=0.5, annotation_text="P. Low")
    
    if 'prev_day_close' in df.columns:
        fig.add_hline(y=df['prev_day_close'].iloc[0], line_dash="dash", 
                      line_color="#3498db", opacity=0.5, annotation_text="P. Close")
    
    
    # These provide visual anchors for your 11:30 AM exit strategy
    v_times = ["09:30:00", "10:30:00", "11:30:00", "12:30:00", "13:30:00", "14:30:00", "15:30:00"]
    for t_str in v_times:
        target_ts = f"{selected_date} {t_str}"
        fig.add_vline(
            x=target_ts, 
            line_width=1, 
            line_dash="dash", 
            line_color="#514F4F", # Very light grey
            opacity=0.6
        )

    # 5. Layout Formatting
    fig.update_layout(
        template="plotly_white",
        xaxis_rangeslider_visible=False,
        height=650,
        margin=dict(t=10, b=10, l=10, r=60), 
        hovermode="x unified",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        showlegend=False
    )

    fig.update_yaxes(tickformat="d", side="right", gridcolor="#f2f2f2", linecolor="#1e1e1e")
    fig.update_xaxes(gridcolor="#f2f2f2", linecolor="#1e1e1e")

    return fig