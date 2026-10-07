import duckdb

def setup_database(intrada1m_csv, intrada5m_csv, intrada15m_csv, daily_csv):
    con = duckdb.connect("nifty_data.duckdb")
    
    # 1. Load Intraday - Just cast the existing auto-detected timestamp
    con.execute(f"""
        CREATE OR REPLACE TABLE nifty_5min AS 
        SELECT 
            CAST(date AS TIMESTAMP) as date,
            CAST(date AS DATE) as ticker_date,
            open, high, low, close, volume
        FROM read_csv_auto('{intrada5m_csv}')
    """)
    
    # 2. Load Daily - Cast to DATE
    con.execute(f"""
        CREATE OR REPLACE TABLE nifty_daily AS 
        SELECT 
            CAST(date AS DATE) as ticker_date,
            open, high, low, close
        FROM read_csv_auto('{daily_csv}')
    """)

    con.execute(f"""
    CREATE OR REPLACE TABLE nifty_15min AS 
    SELECT 
        CAST(date AS TIMESTAMP) as date,
        CAST(date AS DATE) as ticker_date,
        open, high, low, close
    FROM read_csv_auto('{intrada15m_csv}')
    """)

    con.execute(f"""
    CREATE OR REPLACE TABLE nifty_1min AS 
    SELECT 
        CAST(date AS TIMESTAMP) as date,
        CAST(date AS DATE) as ticker_date,
        open, high, low, close
    FROM read_csv_auto('{intrada1m_csv}')
    """)
    
    con.execute("CREATE INDEX IF NOT EXISTS idx_5min_date ON nifty_5min (ticker_date)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_15min_date ON nifty_15min (ticker_date)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_daily_date ON nifty_daily (ticker_date)")
    
    print("Database built successfully!")

if __name__ == "__main__":
    setup_database("/Users/amansaha/workspace/situational_analysis_tool/sample_data/nifty_1min.csv","/Users/amansaha/workspace/situational_analysis_tool/sample_data/nifty_5min.csv", "/Users/amansaha/workspace/situational_analysis_tool/sample_data/nifty_15min.csv", "/Users/amansaha/workspace/situational_analysis_tool/sample_data/nifty_daily.csv")