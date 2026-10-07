import duckdb

def find_pattern_days(timeframe="5min", first_color="Any", second_color="Any", 
                      gap_filter="Any", day_filter="Any", open_loc="Any", gap_pct_range="Any", is_inside_bar="Any"):
    con = duckdb.connect("nifty_data.duckdb", read_only=True)
    
    # Matching your table naming convention (nifty_5min vs nifty_15min)
    table = "nifty_5min" if timeframe == "5min" else "nifty_15min"
    
    query = f"""
    WITH GapAnalysis AS (
        SELECT 
            ticker_date, 
            open as day_open,
            LAG(close) OVER (ORDER BY ticker_date ASC) as prev_close,
            LAG(high) OVER (ORDER BY ticker_date ASC) as prev_high,
            LAG(low) OVER (ORDER BY ticker_date ASC) as prev_low,
            ((open - LAG(close) OVER (ORDER BY ticker_date ASC)) / LAG(close) OVER (ORDER BY ticker_date ASC)) * 100 as gap_pct
        FROM nifty_daily
    ),
    Candle1 AS (
        SELECT ticker_date, open, close, high, low FROM {table} 
        WHERE (ticker_date, date) IN (SELECT ticker_date, MIN(date) FROM {table} GROUP BY 1)
    ),
    Candle2 AS (
        SELECT ticker_date, open, close, high, low FROM (
            SELECT ticker_date, open, close, high, low,
            ROW_NUMBER() OVER (PARTITION BY ticker_date ORDER BY date ASC) as rn
            FROM {table}
        ) sub WHERE rn = 2 -- Note: Added 'high' and 'low' to both SELECT levels
    )
    SELECT g.ticker_date, 
           strftime(g.ticker_date, '%a') as day_name
    FROM GapAnalysis g
    JOIN Candle1 c1 ON g.ticker_date = c1.ticker_date
    JOIN Candle2 c2 ON g.ticker_date = c2.ticker_date
    WHERE 1=1
    """
    
    # 1. Opening Location (vs Prev Day Close)
    if gap_filter == "Above Prev Close":
        query += " AND g.day_open > g.prev_close"
    elif gap_filter == "Below Prev Close":
        query += " AND g.day_open < g.prev_close"

    # 2. Opening Location (vs Prev Day Range)
    if open_loc == "Above Prev High":
        query += " AND g.day_open > g.prev_high"
    elif open_loc == "Below Prev Low":
        query += " AND g.day_open < g.prev_low"
    elif open_loc == "Within Prev Range":
        query += " AND g.day_open <= g.prev_high AND g.day_open >= g.prev_low"

    # 3. Gap Point Filters (Cleaned)
    # --- Refined Gap Point Filters ---
    if gap_pct_range == "> 2%":
        query += " AND g.gap_pct > 2.0"
    elif gap_pct_range == "1% to 2%":
        query += " AND g.gap_pct BETWEEN 1.0 AND 2.0"
    elif gap_pct_range == "0% to 1%":
        query += " AND g.gap_pct BETWEEN 0.0 AND 1.0"
    elif gap_pct_range == "Flat (0%)":
        query += " AND g.gap_pct BETWEEN -0.1 AND 0.1"
    elif gap_pct_range == "-1% to 0%":
        query += " AND g.gap_pct BETWEEN -1.0 AND 0.0"
    elif gap_pct_range == "-2% to -1%":
        query += " AND g.gap_pct BETWEEN -2.0 AND -1.0"
    elif gap_pct_range == "< -2%":
        query += " AND g.gap_pct < -2.0"

    # --- Inside Bar Filter ---
    if is_inside_bar == "Yes":
        query += " AND c2.high <= c1.high AND c2.low >= c1.low"
    elif is_inside_bar == "No":
        query += " AND (c2.high > c1.high OR c2.low < c1.low)"

    # 4. Candle Colors (Strict Inequality for cleaner stats)
    if first_color == "Red": query += " AND c1.close < c1.open"
    elif first_color == "Green": query += " AND c1.close > c1.open"
    
    if second_color == "Red": query += " AND c2.close < c2.open"
    elif second_color == "Green": query += " AND c2.close > c2.open"

    # 5. Day of Week
    if day_filter != "Any":
        query += f" AND strftime(g.ticker_date, '%a') = '{day_filter}'"
        
    query += " ORDER BY g.ticker_date DESC"
    
    df = con.execute(query).df()
    con.close()
    return df