import streamlit as st
import pandas as pd
import duckdb
import plotly.express as px
import signals

# --- Page Config ---
st.set_page_config(layout="wide", page_title="Extreme Bar Statistics")

# --- UI Styling ---
st.markdown("""
    <style>
    .stApp { background-color: #ffffff !important; }
    [data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #f0f0f0; }
    h1, h2, h3, p, label { color: #000000 !important; font-family: 'Inter', sans-serif; }
    </style>
    """, unsafe_allow_html=True)

# --- Sidebar Filters ---
with st.sidebar:
    st.title("Stats Engine")
    tf_mode = st.selectbox("Timeframe", ["5min", "15min"], index=0)
    day_val = st.selectbox("Day of Week", ["Any", "Mon", "Tue", "Wed", "Thu", "Fri"])
    
    st.divider()
    st.subheader("Market Context")
    gap_val = st.selectbox("Gap Filter", ["Any", "Above Prev Close", "Below Prev Close"])
    open_loc = st.selectbox("Range Filter", ["Any", "Above Prev High", "Below Prev Low", "Within Prev Range"])
    
    st.divider()
    st.subheader("Candle Sequence")
    c1_val = st.selectbox("1st Candle", ["Any", "Green", "Red"])
    c2_val = st.selectbox("2nd Candle", ["Any", "Green", "Red"])

# --- Step 1: Find Matching Days ---
matches = signals.find_pattern_days(tf_mode, c1_val, c2_val, gap_val, day_val, open_loc)

if not matches.empty:
    matches['ticker_date'] = pd.to_datetime(matches['ticker_date'])
    date_list = matches['ticker_date'].dt.strftime('%Y-%m-%d').tolist()
    match_dates_sql = f"('{date_list[0]}')" if len(date_list) == 1 else str(tuple(date_list))

    # --- Step 2: Corrected DuckDB Analysis ---
    con = duckdb.connect("nifty_data.duckdb")
    
    query = f"""
    WITH DayBars AS (
        SELECT CAST(date AS DATE) as d_date, date as full_ts, open, close, high, low
        FROM nifty_{tf_mode}
        WHERE CAST(date AS DATE) IN {match_dates_sql}
    ),
    DailyMetrics AS (
        SELECT 
            d_date, 
            arg_min(open, full_ts) as d_open, 
            arg_max(close, full_ts) as d_close,
            MAX(high) as d_high, 
            MIN(low) as d_low
        FROM DayBars GROUP BY 1
    ),
    -- We create a standalone table of all daily H/L to join against
    AllDailyLevels AS (
        SELECT 
            CAST(date AS DATE) as l_date,
            MAX(high) as day_high,
            MIN(low) as day_low
        FROM nifty_5min 
        GROUP BY 1
    ),
    ContextualData AS (
        SELECT 
            m.*,
            prev.day_high as prev_high,
            prev.day_low as prev_low
        FROM DailyMetrics m
        -- Join with the record that has the largest date smaller than current date
        LEFT JOIN AllDailyLevels prev ON prev.l_date = (
            SELECT MAX(l_date) 
            FROM AllDailyLevels 
            WHERE l_date < m.d_date
        )
    ),
    Categorized AS (
        SELECT *,
            CASE 
                WHEN d_open > prev_high THEN 'Open Above Prev High'
                WHEN d_open < prev_low THEN 'Open Below Prev Low'
                ELSE 'Open Within Prev Range'
            END as open_context,
            CASE WHEN d_close > d_open THEN 'Positive Day' ELSE 'Negative Day' END as bias
        FROM ContextualData
    )
    SELECT c.*,
        CASE 
            WHEN c.bias = 'Positive Day' THEN (SELECT MIN(full_ts) FROM DayBars WHERE d_date = c.d_date AND low = c.d_low)
            ELSE (SELECT MIN(full_ts) FROM DayBars WHERE d_date = c.d_date AND high = c.d_high)
        END as extreme_ts
    FROM Categorized c
    """
    df_stats = con.execute(query).df()
    con.close()

    # --- Step 3: Calculate Bar Index ---
    tf_int = int(tf_mode.replace('min',''))
    df_stats['extreme_ts'] = pd.to_datetime(df_stats['extreme_ts'])
    df_stats['mins_from_open'] = (df_stats['extreme_ts'].dt.hour * 60 + df_stats['extreme_ts'].dt.minute) - (9 * 60 + 15)
    df_stats['bar_index'] = (df_stats['mins_from_open'] / tf_int).astype(int) + 1

    # --- Step 4: UI Segments ---
    st.title("Time of Extreme Analysis")
    
    # NEW: Opening Context Filter
    st.subheader("Filter by Opening Context")
    context_choice = st.radio(
        "Current Scenario:",
        ["All Matches", "Open Above Prev High", "Open Below Prev Low", "Open Within Prev Range"],
        horizontal=True
    )

    if context_choice != "All Matches":
        active_df = df_stats[df_stats['open_context'] == context_choice]
    else:
        active_df = df_stats

    st.write(f"Analyzing **{len(active_df)}** days for context: **{context_choice}**")

    # --- Step 5: Tables ---
    t_col1, t_col2 = st.columns(2)
    
    with t_col1:
        st.markdown("#### 🟢 Positive Days (Low of Day)")
        pos_df = active_df[active_df['bias'] == 'Positive Day']
        if not pos_df.empty:
            pos_counts = pos_df.groupby('bar_index').size().reset_index(name='Days')
            pos_counts.columns = ['Bar Number', 'Days with Low']
            pos_counts['% Probability'] = (pos_counts['Days with Low'] / len(pos_df) * 100).round(2)
            st.dataframe(pos_counts.sort_values('Bar Number'), hide_index=True, use_container_width=True)
        else:
            st.write("No data for this context.")

    with t_col2:
        st.markdown("#### 🔴 Negative Days (High of Day)")
        neg_df = active_df[active_df['bias'] == 'Negative Day']
        if not neg_df.empty:
            neg_counts = neg_df.groupby('bar_index').size().reset_index(name='Days')
            neg_counts.columns = ['Bar Number', 'Days with High']
            neg_counts['% Probability'] = (neg_counts['Days with High'] / len(neg_df) * 100).round(2)
            st.dataframe(neg_counts.sort_values('Bar Number'), hide_index=True, use_container_width=True)
        else:
            st.write("No data for this context.")

    # --- Step 6: Visuals ---
    st.divider()
    h_col1, h_col2 = st.columns(2)
    with h_col1:
        if not pos_df.empty:
            st.plotly_chart(px.histogram(pos_df, x="bar_index", color_discrete_sequence=['#2ecc71'], title="Positive Day LOD Distribution", template="plotly_white"), use_container_width=True)
    with h_col2:
        if not neg_df.empty:
            st.plotly_chart(px.histogram(neg_df, x="bar_index", color_discrete_sequence=['#e74c3c'], title="Negative Day HOD Distribution", template="plotly_white"), use_container_width=True)

else:
    st.warning("No matches found.")