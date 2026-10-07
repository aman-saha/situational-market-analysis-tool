import duckdb
import pandas as pd

def get_day_data(date_str, timeframe="5min"):
    db_table = f"nifty_{timeframe}"
    
    with duckdb.connect("nifty_data.duckdb", read_only=True) as con:
        # 1. Fetch current day data
        query = f"SELECT * FROM {db_table} WHERE CAST(date AS DATE) = '{date_str}' ORDER BY date ASC"
        df = con.execute(query).df()
        
        if df.empty:
            return df

        # 2. Calculate EMAs for the channel
        df['ema_low'] = df['low'].ewm(span=10, adjust=False).mean()
        df['ema_high'] = df['high'].ewm(span=10, adjust=False).mean()

        # 3. Fetch Previous Day Levels
        prev_query = f"""
            SELECT MAX(high) as ph, MIN(low) as pl, arg_max(close, date) as pc
            FROM {db_table} WHERE CAST(date AS DATE) < '{date_str}'
            GROUP BY CAST(date AS DATE) ORDER BY CAST(date AS DATE) DESC LIMIT 1
        """
        prev_levels = con.execute(prev_query).fetchone()
        
        if prev_levels:
            df['prev_day_high'] = prev_levels[0]
            df['prev_day_low'] = prev_levels[1]
            df['prev_day_close'] = prev_levels[2]
            
        return df