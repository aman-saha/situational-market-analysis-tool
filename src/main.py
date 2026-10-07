import streamlit as st
import pandas as pd
import signals
import data_manager
import charts

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="Situational Analysis")

# --- CLEAN HIGH-CONTRAST CSS ---
st.markdown("""
    <style>
    /* 1. App Background */
    .stApp { background-color: #ffffff !important; }
    
    /* 2. Sidebar Styling */
    [data-testid="stSidebar"] { 
        background-color: #ffffff !important; 
        border-right: 1px solid #e0e0e0; 
    }

    /* 3. Force General Text to Black */
    h1, h2, h3, p, label, .stMarkdown p { 
        color: #000000 !important; 
        font-family: 'Inter', sans-serif;
    }

    /* 4. FIX: Dropdown Selected Value Visibility */
    div[data-baseweb="select"] div {
        color: #000000 !important;
    }
    
    .stSelectbox div[data-baseweb="select"] > div:first-child {
        color: #000000 !important;
    }

    /* 5. Dropdown Background & Border */
    div[data-baseweb="select"] > div {
        background-color: #f1f3f6 !important; 
        border: 1px solid #cccccc !important;
    }

    /* 6. Metrics visibility */
    [data-testid="stMetricValue"] { color: #000000 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR: PATTERN FILTERS ---
with st.sidebar:
    st.title("Situational")
    st.caption("Historical Pattern Explorer")
    st.divider()

    tf_ui = st.selectbox("Timeframe", ["1min", "5min", "15min"], index=1) # Defaulting to 5m
    if tf_ui == "1min":
        db_tf = "1min"
    elif tf_ui == "5min":
        db_tf = "5min"
    else:
        db_tf = "15min"
    
    day_val = st.selectbox("Day of Week", ["Any", "Mon", "Tue", "Wed", "Thu", "Fri"], index=0)

    st.divider()
    st.subheader("Market Context")
    gap_val = st.selectbox("Open vs Prev Close", ["Any", "Above Prev Close", "Below Prev Close"])
    open_loc = st.selectbox("Open vs Prev Range", ["Any", "Above Prev High", "Below Prev Low", "Within Prev Range"])

    st.divider()
    st.subheader("Advanced Range Filters")
    gap_pct_range = st.selectbox("Gap % Range", [
        "Any", 
        "> 2%", 
        "1% to 2%", 
        "0% to 1%",
        "Flat (0%)",
        "-1% to 0%",
        "-2% to -1%",
        "< -2%"
    ])

    st.divider()
    st.subheader("Candle Sequence")
    c1_val = st.selectbox("1st Candle Color", ["Any", "Green", "Red"])
    c2_val = st.selectbox("2nd Candle Color", ["Any", "Green", "Red"])
    
    inside_bar_val = st.selectbox("2nd Candle Inside Bar?", ["Any", "Yes", "No"])

# --- DATA PROCESSING ---
matches = signals.find_pattern_days(
    timeframe=db_tf, 
    first_color=c1_val, 
    second_color=c2_val, 
    gap_filter=gap_val,
    day_filter=day_val,
    open_loc=open_loc,
    gap_pct_range=gap_pct_range,
    is_inside_bar=inside_bar_val
)

if not matches.empty:
    matches['ticker_date'] = pd.to_datetime(matches['ticker_date'])
    
    with st.sidebar:
        st.divider()
        st.subheader("Results")
        
        display_df = matches.copy()
        display_df['Date'] = display_df['ticker_date'].dt.date
        display_df = display_df[['Date', 'day_name']].sort_values('Date', ascending=False)
        
        st.write(f"**{len(display_df)} Matches Found**")
        
        selection_event = st.dataframe(
            display_df,
            hide_index=True,
            use_container_width=True,
            on_select="rerun",
            selection_mode="single-row"
        )

        if selection_event.selection.rows:
            selected_row_index = selection_event.selection.rows[0]
            selected_date = display_df.iloc[selected_row_index]['Date']
        else:
            selected_date = display_df.iloc[0]['Date']

    # --- MAIN CHART AREA ---
    day_df = data_manager.get_day_data(str(selected_date), timeframe=db_tf)
    
    if not day_df.empty:
        # Split header into 3 parts: Title, Gap Metric, Session Metric
        col_title, col_gap, col_move = st.columns([2, 1, 1])
        day_name_str = pd.to_datetime(selected_date).strftime('%A')
        
        with col_title:
            st.title(f"{selected_date} | {day_name_str}")
            st.caption(f"Nifty 50 Index • {tf_ui} Intraday View")

        # Morning Gap Calculation & Display
        with col_gap:
            f_open = day_df['open'].iloc[0]
            if 'prev_day_close' in day_df.columns:
                p_close = day_df['prev_day_close'].iloc[0]
                gap_pts = round(f_open - p_close, 2)
                gap_pct = round((gap_pts / p_close) * 100, 2)
                # Showing % as the delta for more context
                st.metric("Morning Gap", f"{gap_pts} pts", delta=f"{gap_pct}%")
            else:
                st.metric("Morning Gap", "N/A")

        # Session Move Calculation & Display
        with col_move:
            l_close = day_df['close'].iloc[-1]
            diff = round(l_close - f_open, 2)
            st.metric("Session Move", f"{diff} pts", delta=diff)

        # Render Chart
        fig = charts.render_chart(day_df, selected_date)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.error(f"Data for {selected_date} is missing.")
else:
    st.sidebar.info("No matches found.")