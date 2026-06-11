import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR / "backend"))

from main import extract_dates_from_query

queries = [
    "revenue leakage in May 2022",
    "revenue leakage from jan 2023 to august 2023",
    "surgery audit in june 2025",
    "surgery audit from june 2024 to october 2025",
    "what is the total revenue leakage?",
]

for q in queries:
    res = extract_dates_from_query(q)
    print(f"Query: '{q}'\nExtracted: {res}\n")
