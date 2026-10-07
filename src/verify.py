import duckdb
con = duckdb.connect("nifty_data.duckdb")

print("--- Row Counts ---")
print("Daily Rows:", con.execute("SELECT count(*) FROM nifty_daily").fetchone()[0])
print("5-Min Rows:", con.execute("SELECT count(*) FROM nifty_5min").fetchone()[0])

print("\n--- Time Check ---")
print("Distinct Times in 5-min data (first 5):")
print(con.execute("SELECT DISTINCT CAST(date AS TIME) FROM nifty_5min LIMIT 5").df())

print("\n--- Join Check ---")
print("Number of overlapping dates:")
check_query = """
SELECT count(*) 
FROM (SELECT DISTINCT CAST(ticker_date AS DATE) as d FROM nifty_daily) daily
JOIN (SELECT DISTINCT CAST(date AS DATE) as d FROM nifty_5min) intra
ON daily.d = intra.d
"""
print(con.execute(check_query).fetchone()[0])