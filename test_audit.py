import sys
import sqlite3
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR / "backend"))

from main import extract_dates_from_query

DB_PATH = str(BASE_DIR / "db" / "hospital.db")

def test_query(q):
    print(f"--- Query: {q} ---")
    nlp_dates = extract_dates_from_query(q)
    print("Extracted Dates:", nlp_dates)
    
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM audit_4b_4d", conn)
    conn.close()
    
    df['date_dt'] = pd.to_datetime(df['date'], format='mixed', errors='coerce')
    print("Total rows:", len(df))
    
    query_start = nlp_dates.get("start_date")
    query_end = nlp_dates.get("end_date")
    
    if query_start:
        df = df[df['date_dt'] >= pd.to_datetime(query_start)]
    if query_end:
        df = df[df['date_dt'] <= pd.to_datetime(query_end) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)]
        
    print("Rows after filter:", len(df))
    if not df.empty:
        df['difference_amount'] = pd.to_numeric(df['difference_amount'], errors='coerce').fillna(0)
        discrepancies = df[df['difference_amount'] > 0]
        print(f"Discrepancies: {len(discrepancies)}, Total Loss: {discrepancies['difference_amount'].sum()}")
        print("Date range in filtered data:", df['date_dt'].min(), "to", df['date_dt'].max())
    print("\n")

test_query("surgery audit for may 2025")
test_query("from may 2025 to december 2025")

# Let's also check the raw data dates
conn = sqlite3.connect(DB_PATH)
df_all = pd.read_sql_query("SELECT date FROM audit_4b_4d", conn)
df_all['date_dt'] = pd.to_datetime(df_all['date'], format='mixed', errors='coerce')
print("--- DB Stats ---")
print("Min Date:", df_all['date_dt'].min())
print("Max Date:", df_all['date_dt'].max())
print("Rows in May 2025:", len(df_all[(df_all['date_dt'] >= '2025-05-01') & (df_all['date_dt'] <= '2025-05-31')]))
print("Rows in Jun-Dec 2025:", len(df_all[(df_all['date_dt'] >= '2025-06-01') & (df_all['date_dt'] <= '2025-12-31')]))
