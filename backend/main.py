import logging
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List
import sqlite3
import os
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from fuzzywuzzy import process
import pandas as pd
import re
import google.generativeai as genai
import uuid
import json
from apscheduler.schedulers.background import BackgroundScheduler
import smtplib
from email.mime.text import MIMEText
import urllib.request

logging.basicConfig(level=logging.INFO)

from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    logging.warning("WARNING: Gemini API key not found. Please set the GEMINI_API_KEY environment variable.")
else:
    masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "INVALID_KEY"
    logging.info(f"Loaded Gemini API key from environment/env-file: {masked_key}")

genai.configure(api_key=api_key)

def get_gemini_response(prompt: str, system_instruction: str) -> str:
    model = genai.GenerativeModel("gemini-2.5-flash", system_instruction=system_instruction)
    response = model.generate_content(prompt)
    return response.text

app = FastAPI(title="Revenue Leakage & Surgery Audit API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = str(BASE_DIR / "db" / "hospital.db")
RAW_DIR = str(BASE_DIR / "data" / "raw")

# --- AUDIT COMPLIANCE SYSTEM INITIALIZATION ---
def init_audit_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                details TEXT NOT NULL,
                ip_address TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                session_id TEXT
            )
        """)
        conn.commit()
        conn.close()
        logging.info("Audit log database table checked/initialized successfully.")
    except Exception as e:
        logging.error(f"Failed to initialize audit database table: {e}")

init_audit_db()

def init_alerts_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                condition_type TEXT NOT NULL,
                threshold REAL NOT NULL,
                comparison_column TEXT,
                bot_type TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                email_recipient TEXT,
                webhook_url TEXT,
                created_by TEXT DEFAULT 'System',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alert_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id INTEGER NOT NULL,
                triggered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                value_detected REAL NOT NULL,
                status TEXT DEFAULT 'unread',
                FOREIGN KEY(alert_id) REFERENCES alerts(id) ON DELETE CASCADE
            )
        """)
        
        cursor.execute("SELECT COUNT(*) FROM alerts WHERE name = ?", ("Daily leakage exceeds ₹500,000",))
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO alerts (name, condition_type, threshold, comparison_column, bot_type, is_active, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, ("Daily leakage exceeds ₹500,000", "total_leakage_daily", 500000.0, None, "revenue", 1, "System"))
            conn.commit()
            logging.info("Sample alert 'Daily leakage exceeds ₹500,000' pre-configured successfully.")
            
        conn.close()
        logging.info("Alerts database tables checked/initialized successfully.")
    except Exception as e:
        logging.error(f"Failed to initialize alerts database table: {e}")

init_alerts_db()

def init_feedback_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bot_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                query TEXT,
                bot_response TEXT,
                feedback_type TEXT NOT NULL,
                comment TEXT,
                user_id TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
        logging.info("Bot feedback database table checked/initialized successfully.")
    except Exception as e:
        logging.error(f"Failed to initialize feedback database table: {e}")

init_feedback_db()


def log_audit(user_id: str, action_type: str, details: dict, ip_address: Optional[str], session_id: Optional[str] = None):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO audit_logs (user_id, action_type, details, ip_address, session_id) VALUES (?, ?, ?, ?, ?)",
            (user_id, action_type, json.dumps(details), ip_address, session_id)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Failed to log audit event: {e}")


# --- END COMPLIANCE INITIALIZATION ---

REVENUE_QUESTIONS = [
    "Which services or charges are most frequently missed in billing?",
    "Which floor or department has the highest or lowest revenue leakage?",
    "What is the current average revenue leakage?",
    "What is the average monthly leakage?",
    "Which staff members are linked to the most or fewest missed or unbilled charges?",
    "Which month or time period shows the highest or lowest revenue leakage trends?",
    "What are the top or bottom service-area combinations with billing discrepancies?",
    "Are there cases where services were recorded but not billed? How frequent?",
    "Which staff-service combinations show repeated patterns of underbilling or missed charges?",
    "Based on past data, where is revenue leakage most likely to occur in the future?",
    "What is the total estimated revenue loss due to missed charges and what are the key contributing factors?"
]

class LoginRequest(BaseModel):
    username: str
    password: str

class ChatRequest(BaseModel):
    query: str
    bot: str
    username: str
    session_id: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    location_filter: Optional[str] = None

class CompareFilter(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    location_filter: Optional[str] = None

class CompareRequest(BaseModel):
    query: str
    bot: str
    username: str
    session_id: Optional[str] = None
    period_a: CompareFilter
    period_b: CompareFilter

class FeedbackSubmitRequest(BaseModel):
    session_id: Optional[str] = None
    query: str
    bot_response: str
    feedback_type: str
    comment: Optional[str] = None
    user_id: Optional[str] = None

class AuditLogCreateRequest(BaseModel):
    user_id: str
    action_type: str
    details: dict
    session_id: Optional[str] = None

class AlertCreateRequest(BaseModel):
    name: str
    condition_type: str
    threshold: float
    comparison_column: Optional[str] = None
    bot_type: str
    email_recipient: Optional[str] = None
    webhook_url: Optional[str] = None
    created_by: Optional[str] = "System"

class AlertUpdateRequest(BaseModel):
    name: Optional[str] = None
    condition_type: Optional[str] = None
    threshold: Optional[float] = None
    comparison_column: Optional[str] = None
    bot_type: Optional[str] = None
    is_active: Optional[int] = None
    email_recipient: Optional[str] = None
    webhook_url: Optional[str] = None

class AlertCheckNowRequest(BaseModel):
    username: str


@app.post("/login")
def login(req: LoginRequest, request: Request):
    ip_address = request.client.host if request.client else None
    if req.username == "Admin" and req.password == "Admin":
        log_audit(req.username, "LOGIN", {"status": "success"}, ip_address)
        return {"username": req.username, "bots": ["revenue", "audit"]}
    elif req.username == "Admin1" and req.password == "Admin1":
        log_audit(req.username, "LOGIN", {"status": "success"}, ip_address)
        return {"username": req.username, "bots": ["revenue"]}
    elif req.username == "Admin2" and req.password == "Admin2":
        log_audit(req.username, "LOGIN", {"status": "success"}, ip_address)
        return {"username": req.username, "bots": ["audit"]}
    else:
        log_audit(req.username, "LOGIN_FAILED", {"status": "failed", "attempted_username": req.username}, ip_address)
        raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/sessions/{bot}")
def get_sessions(bot: str, username: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT session_id, title, created_at FROM chat_sessions WHERE username = ? AND bot = ? ORDER BY created_at DESC", (username, bot))
    sessions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"sessions": sessions}

@app.get("/history/{session_id}")
def get_history(session_id: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT role, text, chart_data, chart_type, chart_value_type FROM chat_messages WHERE session_id = ? ORDER BY timestamp ASC", (session_id,))
    messages = []
    for row in cursor.fetchall():
        msg = dict(row)
        if msg['chart_data']:
            msg['chart'] = json.loads(msg['chart_data'])
        else:
            msg['chart'] = None
        msg['chartType'] = msg['chart_type']
        msg['chartValueType'] = msg['chart_value_type']
        messages.append(msg)
    conn.close()
    return {"messages": messages}

@app.get("/locations")
def get_locations():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM locations")
        locs = [r[0] for r in cursor.fetchall()]
        conn.close()
        return {"locations": locs}
    except Exception as e:
        return {"locations": [], "error": str(e)}

@app.get("/autocomplete")
def autocomplete(q: str = "", bot: str = "revenue"):
    if bot != "revenue":
        return {"suggestions": ["What are the discrepancies in the latest audit?"]}
    
    static_matches = process.extract(q, REVENUE_QUESTIONS, limit=5)
    suggestions = [match[0] for match in static_matches if match[1] > 40]
    
    if not suggestions and not q:
        suggestions = REVENUE_QUESTIONS[:5]

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM locations")
        locs = [r[0] for r in cursor.fetchall()]
        conn.close()
        
        if "floor" in q.lower() or "department" in q.lower() or "ward" in q.lower():
            for loc in locs:
                suggestions.append(f"Which floor has the highest leakage - {loc}?")
    except:
        pass

    return {"suggestions": list(set(suggestions))[:8]}

@app.get("/transactions")
def get_transactions(
    bot: str,
    query: str,
    value: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    location_filter: Optional[str] = None
):
    # 1. Infer category based on query and bot
    category = "location"
    if bot == "revenue":
        if "service" in query.lower():
            category = "service"
        elif "staff" in query.lower():
            category = "staff"
        elif "month" in query.lower() or "trend" in query.lower():
            category = "month"
        else:
            category = "location"
    else: # audit
        if "surgeon" in query.lower() or "doctor" in query.lower():
            category = "surgeon"
        elif "month" in query.lower() or "trend" in query.lower():
            category = "month"
        else:
            category = "speciality"

    # 2. Query appropriate table
    conn = sqlite3.connect(DB_PATH)
    try:
        if bot == "revenue":
            df = pd.read_sql_query("SELECT * FROM revenue_4a", conn)
            df['location'] = df['location'].apply(normalize_location)
            df['leakage_amount'] = pd.to_numeric(df['leakage_amount'], errors='coerce').fillna(0)
            df['date_dt'] = pd.to_datetime(df['date'], format='mixed', errors='coerce')
            
            # Apply filters
            if location_filter:
                df = df[df['location'].str.contains(location_filter, case=False, na=False)]
            if start_date:
                df = df[df['date_dt'] >= pd.to_datetime(start_date)]
            if end_date:
                df = df[df['date_dt'] <= pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)]
                
            # Filter by clicked item value
            if category == "service":
                df_filtered = df[df['service_name'].astype(str).str.contains(value, case=False, na=False)]
            elif category == "staff":
                df_filtered = df[df['staff_name'].astype(str).str.contains(value, case=False, na=False)]
            elif category == "location":
                df_filtered = df[df['location'].astype(str).str.contains(value, case=False, na=False)]
            elif category == "month":
                df_filtered = df[(df['date'].astype(str).str.startswith(value)) & (df['location'] == 'Multiple Wards')]
            else:
                df_filtered = df
        else: # audit
            df = pd.read_sql_query("SELECT * FROM audit_4b_4d", conn)
            df['difference_amount'] = pd.to_numeric(df['difference_amount'], errors='coerce').fillna(0)
            df['date_dt'] = pd.to_datetime(df['date'], format='mixed', errors='coerce')
            
            # Apply filters
            if location_filter:
                if 'location' in df.columns:
                    df = df[df['location'].str.contains(location_filter, case=False, na=False)]
            if start_date:
                df = df[df['date_dt'] >= pd.to_datetime(start_date)]
            if end_date:
                df = df[df['date_dt'] <= pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)]
                
            # Filter by clicked item value
            if category == "surgeon":
                df_filtered = df[df['surgeon'].astype(str).str.contains(value, case=False, na=False)]
            elif category == "speciality":
                df_filtered = df[df['speciality'].astype(str).str.contains(value, case=False, na=False)]
            elif category == "month":
                df_filtered = df[df['date'].astype(str).str.startswith(value)]
            else:
                df_filtered = df
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    conn.close()

    if df_filtered.empty:
        return {
            "transactions": [],
            "by_staff": [],
            "monthly_trend": [],
            "summary": {
                "title": value,
                "total_leakage": 0,
                "count": 0,
                "category": category
            }
        }

    # Tab 1: Detailed Transactions List
    tx_list = []
    for _, row in df_filtered.iterrows():
        tx = {
            "date": str(row['date'])[:10],
            "patient_id": str(row['patient_id']),
            "leakage_amount": float(row['leakage_amount'] if bot == "revenue" else row['difference_amount']),
        }
        if bot == "revenue":
            tx["service_name"] = str(row['service_name'])
            tx["staff_name"] = str(row['staff_name'])
            tx["location"] = str(row['location'])
        else:
            tx["service_name"] = f"{row['actual_procedure']} (Billed: {row['billed_procedure']})"
            tx["staff_name"] = str(row['surgeon'])
            tx["location"] = str(row['speciality'])
        tx_list.append(tx)

    # Sort transactions by date descending, then leakage amount descending
    tx_list.sort(key=lambda x: (x['date'], x['leakage_amount']), reverse=True)

    # Tab 2: Breakdown By Staff (or Surgeon)
    staff_col = 'staff_name' if bot == "revenue" else 'surgeon'
    amt_col = 'leakage_amount' if bot == "revenue" else 'difference_amount'
    by_staff_df = df_filtered.groupby(staff_col)[amt_col].sum().sort_values(ascending=False).reset_index()
    by_staff = [
        {
            "staff_name": row[staff_col],
            "leakage_amount": float(row[amt_col])
        }
        for _, row in by_staff_df.iterrows()
    ]

    # Tab 3: Monthly chronological trend
    df_filtered = df_filtered.copy()
    df_filtered['month_str'] = df_filtered['date_dt'].dt.strftime('%Y-%m')
    monthly_df = df_filtered.groupby('month_str')[amt_col].sum().sort_index().reset_index()
    monthly_trend = [
        {
            "month": row['month_str'],
            "leakage_amount": float(row[amt_col])
        }
        for _, row in monthly_df.iterrows()
    ]

    total_leakage = float(df_filtered[amt_col].sum())
    count = int(len(df_filtered))

    return {
        "transactions": tx_list,
        "by_staff": by_staff,
        "monthly_trend": monthly_trend,
        "summary": {
            "title": value,
            "total_leakage": total_leakage,
            "count": count,
            "category": category
        }
    }



def local_extract_dates(query: str) -> dict:
    import calendar
    MONTHS = {
        'jan': 1, 'january': 1,
        'feb': 2, 'february': 2,
        'mar': 3, 'march': 3,
        'apr': 4, 'april': 4,
        'may': 5,
        'jun': 6, 'june': 6,
        'jul': 7, 'july': 7,
        'aug': 8, 'august': 8,
        'sep': 9, 'september': 9,
        'oct': 10, 'october': 10,
        'nov': 11, 'november': 11,
        'dec': 12, 'december': 12
    }
    query = query.lower()
    pattern = r'(?:(\d{1,2})\s+)?(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\s*(\d{4})'
    matches = list(re.finditer(pattern, query))
    if len(matches) >= 2:
        m1, m2 = matches[0], matches[1]
        day1 = int(m1.group(1)) if m1.group(1) else 1
        mon1 = MONTHS[m1.group(2)]
        yr1 = int(m1.group(3))
        mon2 = MONTHS[m2.group(2)]
        yr2 = int(m2.group(3))
        day2 = int(m2.group(1)) if m2.group(1) else calendar.monthrange(yr2, mon2)[1]
        return {
            "start_date": f"{yr1:04d}-{mon1:02d}-{day1:02d}",
            "end_date": f"{yr2:04d}-{mon2:02d}-{day2:02d}"
        }
    elif len(matches) == 1:
        m = matches[0]
        mon = MONTHS[m.group(2)]
        yr = int(m.group(3))
        if m.group(1):
            day = int(m.group(1))
            return {
                "start_date": f"{yr:04d}-{mon:02d}-{day:02d}",
                "end_date": f"{yr:04d}-{mon:02d}-{day:02d}"
            }
        else:
            last_day = calendar.monthrange(yr, mon)[1]
            return {
                "start_date": f"{yr:04d}-{mon:02d}-01",
                "end_date": f"{yr:04d}-{mon:02d}-{last_day:02d}"
            }
    return {"start_date": None, "end_date": None}

def extract_dates_from_query(query: str) -> dict:
    prompt = f"""
    Extract any start and end dates mentioned in the following user query: "{query}"
    Return ONLY a valid JSON object with the keys "start_date" and "end_date".
    Format the dates as "YYYY-MM-DD".
    If only a month and year are mentioned (e.g., "May 2022"), set "start_date" to the first day of that month ("2022-05-01") and "end_date" to the last day of that month ("2022-05-31").
    If the user mentions a range like "Jan 2023 to August 2023", set "start_date" to "2023-01-01" and "end_date" to "2023-08-31".
    If no dates are mentioned or it's just a general question, return {{"start_date": null, "end_date": null}}.
    Do not return any markdown formatting, just the raw JSON.
    """
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        res = json.loads(text.strip())
        if res.get("start_date") or res.get("end_date"):
            return res
        return local_extract_dates(query)
    except Exception as e:
        print("Date extraction failed:", e)
        return local_extract_dates(query)

from fastapi.responses import StreamingResponse
import asyncio

def parse_intent(query: str) -> int:
    return 0 # No longer needed, keeping for legacy structure compatibility

def normalize_location(loc: str) -> str:
    if not loc or pd.isna(loc):
        return "Unknown Location"
    loc_clean = str(loc).strip()
    loc_lower = loc_clean.lower()
    
    if loc_clean in ["Multiple Wards", "Ward", "System"]:
        return loc_clean

    # Direct room/bed mapping
    if re.match(r'^micu\d+', loc_lower) or loc_lower == 'micu':
        return "Second Floor MICU"
    if re.match(r'^3\d+', loc_lower): # e.g. 311-C
        return "Third Floor Ward"
    if re.match(r'^4\d+', loc_lower): # e.g. 408, 412--C
        return "Fourth Floor Ward"
        
    # Standard mappings
    mappings = {
        '2f ccu': 'Second Floor CCU',
        'ccu-hdu': 'Second Floor CCU',
        '2f ctvs icu': 'Second Floor CTVS ICU',
        'ctvs icu': 'Second Floor CTVS ICU',
        '2f micu': 'Second Floor MICU',
        '2f nicu': 'Second Floor NICU',
        'nicu': 'Second Floor NICU',
        '2f sicu': 'Second Floor SICU',
        '3f hdu': 'Third Floor HDU',
        '3f ped ward': 'Third Floor Pediatric Ward',
        'ward 3rd floor': 'Third Floor Ward',
        '4f hdu': 'Fourth Floor HDU',
        '4f ped ward': 'Fourth Floor Pediatric Ward',
        'fourth floor': 'Fourth Floor Ward',
        '5f hdu': 'Fifth Floor HDU',
        '5f gynaec': 'Fifth Floor Gynaecology Ward',
        '6f hdu': 'Sixth Floor HDU',
        '6f obg and anc': 'Sixth Floor OBG and ANC Ward',
        'ward 6th floor': 'Sixth Floor OBG and ANC Ward',
        'day care': 'Day Care',
        'economy - 4bed': 'Third Floor Economy Ward'
    }
    
    for key, val in mappings.items():
        if loc_lower == key or key in loc_lower or loc_lower in key:
            return val
            
    # Generic floor fallback
    if '2f' in loc_lower or 'second' in loc_lower:
        return f"Second Floor {loc_clean.replace('2F', '').replace('2f', '').strip()}"
    if '3f' in loc_lower or 'third' in loc_lower:
        return f"Third Floor {loc_clean.replace('3F', '').replace('3f', '').strip()}"
    if '4f' in loc_lower or 'fourth' in loc_lower:
        return f"Fourth Floor {loc_clean.replace('4F', '').replace('4f', '').strip()}"
    if '5f' in loc_lower or 'fifth' in loc_lower:
        return f"Fifth Floor {loc_clean.replace('5F', '').replace('5f', '').strip()}"
    if '6f' in loc_lower or 'sixth' in loc_lower:
        return f"Sixth Floor {loc_clean.replace('6F', '').replace('6f', '').strip()}"
        
    return loc_clean

def prepare_revenue_context(req: ChatRequest):
    """
    Shared helper to connect to database, parse date/location parameters, 
    filter records, and build a detailed analytical prompt context for the revenue bot.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT * FROM revenue_4a", conn)
        conn.close()
    except Exception as e:
        return {"error": "I could not load the database.", "prompt": None, "system_instruction": None, "freq_df": None, "leakage_by_loc": None, "staff_leakage": None, "monthly_sum": None}
        
    if df.empty:
        return {"error": "The database is currently empty. Please upload the data files.", "prompt": None, "system_instruction": None, "freq_df": None, "leakage_by_loc": None, "staff_leakage": None, "monthly_sum": None}

    df['location'] = df['location'].apply(normalize_location)

    # Extract dates from NLP query
    nlp_dates = extract_dates_from_query(req.query)
    query_start = req.start_date or nlp_dates.get("start_date")
    query_end = req.end_date or nlp_dates.get("end_date")

    df['date_dt'] = pd.to_datetime(df['date'], format='mixed', errors='coerce')

    # Validate dates
    if query_start or query_end:
        min_date = df['date_dt'].min()
        max_date = df['date_dt'].max()
        out_of_bounds = False
        
        if query_end:
            try:
                if pd.notnull(min_date) and pd.to_datetime(query_end) < min_date:
                    out_of_bounds = True
            except: pass
        if query_start:
            try:
                if pd.notnull(max_date) and pd.to_datetime(query_start) > max_date:
                    out_of_bounds = True
            except: pass
            
        if out_of_bounds:
            try:
                min_str = min_date.strftime('%B %Y')
                max_str = max_date.strftime('%B %Y')
            except:
                min_str = str(min_date)[:10]
                max_str = str(max_date)[:10]
            msg = f"I can only answer queries for the dates between {min_str} and {max_str} for this dataset. Your requested timeline falls completely outside this range."
            return {"error": msg, "prompt": None, "system_instruction": None, "freq_df": None, "leakage_by_loc": None, "staff_leakage": None, "monthly_sum": None}

    # Apply filters
    if req.location_filter:
        df = df[df['location'].str.contains(req.location_filter, case=False, na=False)]
    if query_start:
        df = df[df['date_dt'] >= pd.to_datetime(query_start)]
    if query_end:
        df = df[df['date_dt'] <= pd.to_datetime(query_end) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)]
        
    if df.empty:
        return {"error": "No data found for the selected filters.", "prompt": None, "system_instruction": None, "freq_df": None, "leakage_by_loc": None, "staff_leakage": None, "monthly_sum": None}

    # Ensure numeric columns
    df['leakage_amount'] = pd.to_numeric(df['leakage_amount'], errors='coerce').fillna(0)
    df['billed_qty'] = pd.to_numeric(df['billed_qty'], errors='coerce').fillna(0)

    # Filter for service summary rows to compute total leakage, unbilled frequency, and monthly growth trends
    df_service = df[df['location'] == 'Multiple Wards']

    total_loss = df_service['leakage_amount'].sum()
    
    freq_df = df_service[df_service['leakage_amount'] > 0].groupby('service_name').agg(
        count=('leakage_amount', 'count'),
        total_missed=('leakage_amount', 'sum')
    ).sort_values(by='count', ascending=False).head(5)
    freq_df['individual_price'] = freq_df['total_missed'] / freq_df['count']
    freq_context = freq_df.to_dict('index')
    
    leakage_by_loc = df[df['location'] != 'Multiple Wards'].groupby('location')['leakage_amount'].sum().sort_values(ascending=False).head(5).to_dict()
    staff_leakage = df[df['staff_name'] != 'System'].groupby('staff_name')['leakage_amount'].sum().sort_values(ascending=False).head(5).to_dict()
    
    df_service_copy = df_service.copy()
    df_service_copy['month'] = pd.to_datetime(df_service_copy['date'], errors='coerce').dt.to_period('M')
    monthly_sum = df_service_copy.groupby('month')['leakage_amount'].sum().tail(5)
    monthly_str = {str(k): float(v) for k, v in monthly_sum.items()}
    
    unbilled_cases = len(df_service[(df_service['leakage_amount'] > 0) & (df_service['billed_qty'] == 0)])
    
    context = f"""
    Revenue Leakage Database Metrics (Filtered for period: {query_start or 'Start'} to {query_end or 'End'}):
    - Total Revenue Leakage: ₹{total_loss:,.2f}
    - Unbilled Cases: {unbilled_cases}
    - Most Frequently Missed Services: {freq_context}
    - Top Leakage by Department/Location: {leakage_by_loc}
    - Top Leakage by Staff Member: {staff_leakage}
    - Recent Monthly Leakage Trends: {monthly_str}
    """
    
    prompt = f"Context Data:\n{context}\n\nUser Question: {req.query}\n\nThe user may have asked multiple questions at once. Please identify all distinct questions in the query and answer EACH of them directly and concisely based ONLY on the context data provided. Focus entirely on the statistics. Format numbers with commas and ₹ symbol. Do not include a chart placeholder."
    system_instruction = "You are an analytical Revenue Leakage Chatbot for a hospital."
    
    return {
        "error": None,
        "prompt": prompt,
        "system_instruction": system_instruction,
        "freq_df": freq_df,
        "leakage_by_loc": leakage_by_loc,
        "staff_leakage": staff_leakage,
        "monthly_sum": monthly_sum,
        "total_loss": total_loss,
        "unbilled_cases": unbilled_cases
    }

def prepare_audit_context(req: ChatRequest):
    """
    Shared helper to connect to database, parse date/location parameters, 
    filter records, and build a detailed analytical prompt context for the surgery audit bot.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT * FROM audit_4b_4d", conn)
        conn.close()
    except Exception as e:
        return {"error": "I could not load the audit database.", "prompt": None, "system_instruction": None, "surg_loss": None, "spec_loss": None, "monthly_sum": None}
        
    if df.empty:
        return {"error": "The audit database is currently empty. Please upload the data files.", "prompt": None, "system_instruction": None, "surg_loss": None, "spec_loss": None, "monthly_sum": None}

    # Extract dates from NLP query
    nlp_dates = extract_dates_from_query(req.query)
    query_start = req.start_date or nlp_dates.get("start_date")
    query_end = req.end_date or nlp_dates.get("end_date")

    df['date_dt'] = pd.to_datetime(df['date'], format='mixed', errors='coerce')

    # Validate dates
    if query_start or query_end:
        min_date = df['date_dt'].min()
        max_date = df['date_dt'].max()
        out_of_bounds = False
        
        if query_end:
            try:
                if pd.notnull(min_date) and pd.to_datetime(query_end) < min_date:
                    out_of_bounds = True
            except: pass
        if query_start:
            try:
                if pd.notnull(max_date) and pd.to_datetime(query_start) > max_date:
                    out_of_bounds = True
            except: pass
            
        if out_of_bounds:
            try:
                min_str = min_date.strftime('%B %Y')
                max_str = max_date.strftime('%B %Y')
            except:
                min_str = str(min_date)[:10]
                max_str = str(max_date)[:10]
            msg = f"I can only answer queries for the dates between {min_str} and {max_str} for this dataset. Your requested timeline falls completely outside this range."
            return {"error": msg, "prompt": None, "system_instruction": None, "surg_loss": None, "spec_loss": None, "monthly_sum": None}

    # Apply filters
    if req.location_filter:
        if 'location' in df.columns:
            df = df[df['location'].str.contains(req.location_filter, case=False, na=False)]
    if query_start:
        df = df[df['date_dt'] >= pd.to_datetime(query_start)]
    if query_end:
        df = df[df['date_dt'] <= pd.to_datetime(query_end) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)]

    if df.empty:
        return {"error": "No data found for the selected filters.", "prompt": None, "system_instruction": None, "surg_loss": None, "spec_loss": None, "monthly_sum": None}

    # Ensure numeric
    df['difference_amount'] = pd.to_numeric(df['difference_amount'], errors='coerce').fillna(0)
    
    discrepancies = df[df['difference_amount'] > 0]
    total_discrepancies = len(discrepancies)
    total_loss = discrepancies['difference_amount'].sum()
    
    if total_discrepancies == 0:
        return {
            "error": "Based on the recent surgery audit logs, there are no recorded financial discrepancies between billed procedures in HIS and the actual scheduled procedures.",
            "prompt": None, "system_instruction": None, "surg_loss": None, "spec_loss": None, "monthly_sum": None
        }

    # Top discrepancies by speciality
    spec_loss = discrepancies.groupby('speciality')['difference_amount'].sum().sort_values(ascending=False).head(5).to_dict()
    
    # Worst offender surgeon
    surg_loss = discrepancies.groupby('surgeon')['difference_amount'].sum().sort_values(ascending=False).head(5).to_dict()
    
    # Time trends
    discrepancies = discrepancies.copy()
    discrepancies['month'] = discrepancies['date_dt'].dt.to_period('M')
    monthly_sum = discrepancies.groupby('month')['difference_amount'].sum().tail(12)
    monthly_str = {str(k): float(v) for k, v in monthly_sum.items()}
    
    recent_days = discrepancies.groupby(discrepancies['date_dt'].dt.date)['difference_amount'].sum().tail(10)
    daily_str = {str(k): float(v) for k, v in recent_days.items()}
    
    context = f"""
    Surgery Audit Database Metrics (Filtered for period: {query_start or 'Start'} to {query_end or 'End'}):
    - Total Procedures with Discrepancies: {total_discrepancies}
    - Total Financial Loss: ₹{total_loss:,.2f}
    - Top Losses by Speciality: {spec_loss}
    - Top Losses by Surgeon: {surg_loss}
    - Monthly Loss Trends: {monthly_str}
    - Recent Daily Loss Trends: {daily_str}
    """
    
    prompt = f"Context Data:\n{context}\n\nUser Question: {req.query}\n\nThe user may have asked multiple questions at once. Please identify all distinct questions in the query and answer EACH of them directly and concisely based ONLY on the context data provided. Format numbers with commas and ₹ symbol. If the question isn't fully covered by the context, answer as best you can."
    system_instruction = "You are an analytical Surgery Audit Chatbot for a hospital."
    
    return {
        "error": None,
        "prompt": prompt,
        "system_instruction": system_instruction,
        "surg_loss": surg_loss,
        "spec_loss": spec_loss,
        "monthly_sum": monthly_sum,
        "total_loss": total_loss,
        "total_discrepancies": total_discrepancies
    }

@app.post("/chat/revenue")
def chat_revenue(req: ChatRequest, request: Request):
    """
    Legacy non-streaming endpoint for Revenue Leakage bot. Keeps backward compatibility.
    """
    ip_address = request.client.host if request.client else None
    log_audit(req.username, "QUERY_SUBMITTED", {"query": req.query, "bot": "revenue"}, ip_address, req.session_id)

    session_id = req.session_id
    if not session_id:
        session_id = str(uuid.uuid4())
        title = req.query[:50] + "..." if len(req.query) > 50 else req.query
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute("INSERT INTO chat_sessions (session_id, username, bot, title) VALUES (?, ?, ?, ?)", (session_id, req.username, "revenue", title))
            conn.commit()
            conn.close()
        except:
            pass
            
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT INTO chat_messages (session_id, role, text) VALUES (?, ?, ?)", (session_id, "user", req.query))
        conn.commit()
        conn.close()
    except:
        pass

    ctx = prepare_revenue_context(req)
    if ctx["error"]:
        if "requested timeline falls completely outside" in ctx["error"] or "only answer queries for the dates" in ctx["error"]:
            return {"answer": ctx["error"], "chart_data": None, "chart_type": "bar", "chart_value_type": "currency", "session_id": session_id}
        return {"answer": ctx["error"], "chart_data": None}

    try:
        answer = get_gemini_response(ctx["prompt"], ctx["system_instruction"])
    except Exception as e:
        answer = f"Error generating AI response: {e}"

    freq_df = ctx["freq_df"]
    staff_leakage = ctx["staff_leakage"]
    monthly_sum = ctx["monthly_sum"]
    leakage_by_loc = ctx["leakage_by_loc"]

    # Chart generation based on queries
    if "service" in req.query.lower():
        chart_data = [{"name": str(idx)[:10], "leakage": float(row['count'])} for idx, row in freq_df.iterrows()]
        chart_value_type = "count"
    elif "staff" in req.query.lower():
        chart_data = [{"name": str(idx)[:10], "leakage": float(val)} for idx, val in staff_leakage.items()]
        chart_value_type = "currency"
    elif "month" in req.query.lower() or "trend" in req.query.lower():
        chart_data = [{"name": str(idx), "leakage": float(val)} for idx, val in monthly_sum.items()]
        chart_value_type = "currency"
    else:
        chart_data = [{"name": str(idx)[:10], "leakage": float(val)} for idx, val in leakage_by_loc.items()]
        chart_value_type = "currency"

    if chart_data and all(d['leakage'] == 0 for d in chart_data):
        chart_data = None

    try:
        conn = sqlite3.connect(DB_PATH)
        chart_data_str = json.dumps(chart_data) if chart_data else None
        conn.execute("INSERT INTO chat_messages (session_id, role, text, chart_data, chart_type, chart_value_type) VALUES (?, ?, ?, ?, ?, ?)", 
                     (session_id, "bot", answer, chart_data_str, "bar", chart_value_type))
        conn.commit()
        conn.close()
    except:
        pass

    return {"answer": answer, "chart_data": chart_data, "chart_type": "bar", "chart_value_type": chart_value_type, "session_id": session_id}

@app.post("/chat/audit")
def chat_audit(req: ChatRequest, request: Request):
    """
    Legacy non-streaming endpoint for Surgery Audit bot. Keeps backward compatibility.
    """
    ip_address = request.client.host if request.client else None
    log_audit(req.username, "QUERY_SUBMITTED", {"query": req.query, "bot": "audit"}, ip_address, req.session_id)

    session_id = req.session_id
    if not session_id:
        session_id = str(uuid.uuid4())
        title = req.query[:50] + "..." if len(req.query) > 50 else req.query
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute("INSERT INTO chat_sessions (session_id, username, bot, title) VALUES (?, ?, ?, ?)", (session_id, req.username, "audit", title))
            conn.commit()
            conn.close()
        except:
            pass
            
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT INTO chat_messages (session_id, role, text) VALUES (?, ?, ?)", (session_id, "user", req.query))
        conn.commit()
        conn.close()
    except:
        pass

    ctx = prepare_audit_context(req)
    if ctx["error"]:
        if "requested timeline falls completely outside" in ctx["error"] or "only answer queries for the dates" in ctx["error"]:
            return {"answer": ctx["error"], "chart_data": None, "chart_type": "bar", "chart_value_type": "currency", "session_id": session_id}
        return {"answer": ctx["error"], "chart_data": None}

    try:
        answer = get_gemini_response(ctx["prompt"], ctx["system_instruction"])
    except Exception as e:
        answer = f"Error generating AI response: {e}"

    surg_loss = ctx["surg_loss"]
    spec_loss = ctx["spec_loss"]
    monthly_sum = ctx["monthly_sum"]

    if "surgeon" in req.query.lower() or "doctor" in req.query.lower():
        chart_data = [{"name": str(idx)[:12], "leakage": float(val)} for idx, val in surg_loss.items()]
    else:
        chart_data = [{"name": str(idx)[:12], "leakage": float(val)} for idx, val in spec_loss.items()]
        
    if chart_data and all(d['leakage'] == 0 for d in chart_data):
        chart_data = None
    
    try:
        conn = sqlite3.connect(DB_PATH)
        chart_data_str = json.dumps(chart_data) if chart_data else None
        conn.execute("INSERT INTO chat_messages (session_id, role, text, chart_data, chart_type, chart_value_type) VALUES (?, ?, ?, ?, ?, ?)", 
                     (session_id, "bot", answer, chart_data_str, "bar", "currency"))
        conn.commit()
        conn.close()
    except:
        pass

    return {"answer": answer, "chart_data": chart_data, "chart_type": "bar", "chart_value_type": "currency", "session_id": session_id}

def get_follow_up_suggestions(bot_type: str, query: str):
    """
    Generate dynamic context-aware follow-up suggestion strings based on active bot.
    """
    if bot_type == "revenue":
        suggestions = [
            "Break down by department",
            "Show monthly trend",
            "Show missed billing by service",
            "Show unbilled charges"
        ]
    else:
        suggestions = [
            "Break down by surgeon",
            "Show monthly trend",
            "Show worst specialties",
            "Show total audit loss"
        ]
    # Rotate based on user inquiry queries
    q = query.lower()
    if "trend" in q or "month" in q:
        if bot_type == "revenue":
            suggestions[1] = "Identify top floor leakage"
        else:
            suggestions[1] = "Break down by surgeon"
    elif "surgeon" in q or "doctor" in q:
        suggestions[0] = "Show worst specialties"
    return suggestions

@app.post("/chat/stream/{bot_type}")
async def chat_stream(bot_type: str, req: ChatRequest, request: Request):
    """
    Streaming POST endpoint that yields Server-Sent Events (SSE).
    Uses Gemini stream=True capability.
    """
    if bot_type not in ["revenue", "audit"]:
        raise HTTPException(status_code=400, detail="Invalid bot type")

    ip_address = request.client.host if request.client else None
    log_audit(req.username, "QUERY_SUBMITTED", {"query": req.query, "bot": bot_type}, ip_address, req.session_id)

    session_id = req.session_id
    if not session_id:
        session_id = str(uuid.uuid4())
        title = req.query[:50] + "..." if len(req.query) > 50 else req.query
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute("INSERT INTO chat_sessions (session_id, username, bot, title) VALUES (?, ?, ?, ?)", (session_id, req.username, bot_type, title))
            conn.commit()
            conn.close()
        except:
            pass
            
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT INTO chat_messages (session_id, role, text) VALUES (?, ?, ?)", (session_id, "user", req.query))
        conn.commit()
        conn.close()
    except:
        pass

    async def event_generator():
        loop = asyncio.get_event_loop()
        
        # Connect to database, load context
        if bot_type == "revenue":
            ctx = await loop.run_in_executor(None, prepare_revenue_context, req)
        else:
            ctx = await loop.run_in_executor(None, prepare_audit_context, req)

        if ctx["error"]:
            err_msg = ctx["error"]
            # Yield as text so it prints the error message in the stream bubble
            yield f"data: {json.dumps({'text': err_msg, 'done': False})}\n\n"
            yield f"data: {json.dumps({'done': True, 'chart_data': None, 'chart_type': 'bar', 'chart_value_type': 'currency', 'session_id': session_id, 'follow_up_suggestions': []})}\n\n"
            return

        full_text = ""
        try:
            model = genai.GenerativeModel("gemini-2.5-flash", system_instruction=ctx["system_instruction"])
            
            # Run generative call with stream=True in threadpool
            def make_gemini_call():
                return model.generate_content(ctx["prompt"], stream=True)
                
            response = await loop.run_in_executor(None, make_gemini_call)
            
            for chunk in response:
                chunk_text = chunk.text
                full_text += chunk_text
                yield f"data: {json.dumps({'text': chunk_text, 'done': False})}\n\n"
                await asyncio.sleep(0.01) # Yield to event loop
        except Exception as e:
            err_msg = f"\nError generating streaming response: {e}"
            yield f"data: {json.dumps({'text': err_msg, 'done': False})}\n\n"
            yield f"data: {json.dumps({'done': True, 'chart_data': None, 'chart_type': 'bar', 'chart_value_type': 'currency', 'session_id': session_id, 'follow_up_suggestions': []})}\n\n"
            return

        # Prepare chart data
        chart_data = None
        chart_value_type = "currency"
        
        if bot_type == "revenue":
            freq_df = ctx["freq_df"]
            staff_leakage = ctx["staff_leakage"]
            monthly_sum = ctx["monthly_sum"]
            leakage_by_loc = ctx["leakage_by_loc"]

            if "service" in req.query.lower():
                chart_data = [{"name": str(idx)[:10], "leakage": float(row['count'])} for idx, row in freq_df.iterrows()]
                chart_value_type = "count"
            elif "staff" in req.query.lower():
                chart_data = [{"name": str(idx)[:10], "leakage": float(val)} for idx, val in staff_leakage.items()]
                chart_value_type = "currency"
            elif "month" in req.query.lower() or "trend" in req.query.lower():
                chart_data = [{"name": str(idx), "leakage": float(val)} for idx, val in monthly_sum.items()]
                chart_value_type = "currency"
            else:
                chart_data = [{"name": str(idx)[:10], "leakage": float(val)} for idx, val in leakage_by_loc.items()]
                chart_value_type = "currency"
        else:
            surg_loss = ctx["surg_loss"]
            spec_loss = ctx["spec_loss"]
            monthly_sum = ctx["monthly_sum"]

            if "surgeon" in req.query.lower() or "doctor" in req.query.lower():
                chart_data = [{"name": str(idx)[:12], "leakage": float(val)} for idx, val in surg_loss.items()]
            else:
                chart_data = [{"name": str(idx)[:12], "leakage": float(val)} for idx, val in spec_loss.items()]

        if chart_data and all(d['leakage'] == 0 for d in chart_data):
            chart_data = None

        # Persist full message and chart data to DB
        try:
            conn = sqlite3.connect(DB_PATH)
            chart_data_str = json.dumps(chart_data) if chart_data else None
            conn.execute("INSERT INTO chat_messages (session_id, role, text, chart_data, chart_type, chart_value_type) VALUES (?, ?, ?, ?, ?, ?)", 
                         (session_id, "bot", full_text, chart_data_str, "bar", chart_value_type))
            conn.commit()
            conn.close()
        except:
            pass

        # Yield completion metadata chunk
        suggestions = get_follow_up_suggestions(bot_type, req.query)
        yield f"data: {json.dumps({'done': True, 'chart_data': chart_data, 'chart_type': 'bar', 'chart_value_type': chart_value_type, 'session_id': session_id, 'follow_up_suggestions': suggestions})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/chat/stream/{bot_type}")
async def chat_stream_get(
    bot_type: str,
    query: str,
    username: str,
    request: Request,
    session_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    location_filter: Optional[str] = None
):
    """
    Fallback GET endpoint to allow native browser EventSource connections.
    """
    req = ChatRequest(
        query=query,
        bot=bot_type,
        username=username,
        session_id=session_id,
        start_date=start_date,
        end_date=end_date,
        location_filter=location_filter
    )
    return await chat_stream(bot_type, req, request)

@app.post("/chat/compare")
def chat_compare(req: CompareRequest, request: Request):
    ip_address = request.client.host if request.client else None
    log_audit(req.username, "QUERY_SUBMITTED", {"query": req.query, "bot": req.bot}, ip_address, req.session_id)

    session_id = req.session_id
    if not session_id:
        session_id = str(uuid.uuid4())
        title = "Comparison: " + (req.query[:40] + "..." if len(req.query) > 40 else req.query)
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute("INSERT INTO chat_sessions (session_id, username, bot, title) VALUES (?, ?, ?, ?)", (session_id, req.username, req.bot, title))
            conn.commit()
            conn.close()
        except:
            pass

    # Save user query to chat history
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT INTO chat_messages (session_id, role, text) VALUES (?, ?, ?)", (session_id, "user", req.query))
        conn.commit()
        conn.close()
    except:
        pass

    # Build individual ChatRequest mock objects for prepare functions
    req_a = ChatRequest(
        query=req.query,
        bot=req.bot,
        username=req.username,
        session_id=session_id,
        start_date=req.period_a.start_date,
        end_date=req.period_a.end_date,
        location_filter=req.period_a.location_filter
    )
    req_b = ChatRequest(
        query=req.query,
        bot=req.bot,
        username=req.username,
        session_id=session_id,
        start_date=req.period_b.start_date,
        end_date=req.period_b.end_date,
        location_filter=req.period_b.location_filter
    )

    if req.bot == "revenue":
        ctx_a = prepare_revenue_context(req_a)
        ctx_b = prepare_revenue_context(req_b)
    else:
        ctx_a = prepare_audit_context(req_a)
        ctx_b = prepare_audit_context(req_b)

    # Check for errors in context preparation
    if ctx_a["error"] or ctx_b["error"]:
        err_msg = ctx_a["error"] or ctx_b["error"]
        return {"error": err_msg}

    # Generate comparative answers via Gemini (Call 1 and Call 2)
    try:
        sys_inst_a = f"You are an analytical {req.bot.title()} Chatbot comparing Period A ({req.period_a.start_date or 'Start'} to {req.period_a.end_date or 'End'}) against Period B ({req.period_b.start_date or 'Start'} to {req.period_b.end_date or 'End'})."
        prompt_a = f"You are evaluating Period A.\n\nPeriod A Metrics & Context:\n{ctx_a['prompt']}\n\nPeriod B Contrast Reference:\n{ctx_b['prompt']}\n\nUser Query: {req.query}\n\nAnalyze Period A's metrics and answer the query, explicitly comparing it with Period B's baseline. Highlight trends, regressions, or improvements. Use precise numbers and delta indicators (e.g. green/red arrows or delta percentages) to describe findings."
        answer_a = get_gemini_response(prompt_a, sys_inst_a)
    except Exception as e:
        answer_a = f"Error evaluating Period A comparative response: {e}"

    try:
        sys_inst_b = f"You are an analytical {req.bot.title()} Chatbot comparing Period B ({req.period_b.start_date or 'Start'} to {req.period_b.end_date or 'End'}) against Period A ({req.period_a.start_date or 'Start'} to {req.period_a.end_date or 'End'})."
        prompt_b = f"You are evaluating Period B.\n\nPeriod B Metrics & Context:\n{ctx_b['prompt']}\n\nPeriod A Contrast Reference:\n{ctx_a['prompt']}\n\nUser Query: {req.query}\n\nAnalyze Period B's metrics and answer the query, explicitly comparing it with Period A's baseline. Highlight trends, regressions, or improvements. Use precise numbers and delta indicators (e.g. green/red arrows or delta percentages) to describe findings."
        answer_b = get_gemini_response(prompt_b, sys_inst_b)
    except Exception as e:
        answer_b = f"Error evaluating Period B comparative response: {e}"

    # Calculate Deltas
    def calculate_delta(a, b):
        if a == 0:
            return 0.0 if b == 0 else 100.0
        return round(((b - a) / a) * 100.0, 1)

    deltas = {}
    if req.bot == "revenue":
        loss_a = ctx_a.get("total_loss", 0.0)
        loss_b = ctx_b.get("total_loss", 0.0)
        cases_a = ctx_a.get("unbilled_cases", 0)
        cases_b = ctx_b.get("unbilled_cases", 0)
        sec_a = cases_a
        sec_b = cases_b
        
        deltas = {
            "total_loss": {
                "val_a": float(loss_a),
                "val_b": float(loss_b),
                "pct_change": calculate_delta(loss_a, loss_b)
            },
            "unbilled_cases": {
                "val_a": float(cases_a),
                "val_b": float(cases_b),
                "pct_change": calculate_delta(cases_a, cases_b)
            }
        }
    else:
        loss_a = ctx_a.get("total_loss", 0.0)
        loss_b = ctx_b.get("total_loss", 0.0)
        discr_a = ctx_a.get("total_discrepancies", 0)
        discr_b = ctx_b.get("total_discrepancies", 0)
        sec_a = discr_a
        sec_b = discr_b
        
        deltas = {
            "total_loss": {
                "val_a": float(loss_a),
                "val_b": float(loss_b),
                "pct_change": calculate_delta(loss_a, loss_b)
            },
            "total_discrepancies": {
                "val_a": float(discr_a),
                "val_b": float(discr_b),
                "pct_change": calculate_delta(discr_a, discr_b)
            }
        }

    # Generate merged overlapping chart data
    chart_data_a = None
    chart_data_b = None
    chart_value_type = "currency"

    if req.bot == "revenue":
        if "service" in req.query.lower():
            chart_data_a = [{"name": str(idx)[:10], "leakage": float(row['count'])} for idx, row in ctx_a["freq_df"].iterrows()]
            chart_data_b = [{"name": str(idx)[:10], "leakage": float(row['count'])} for idx, row in ctx_b["freq_df"].iterrows()]
            chart_value_type = "count"
        elif "staff" in req.query.lower():
            chart_data_a = [{"name": str(idx)[:10], "leakage": float(val)} for idx, val in ctx_a["staff_leakage"].items()]
            chart_data_b = [{"name": str(idx)[:10], "leakage": float(val)} for idx, val in ctx_b["staff_leakage"].items()]
        elif "month" in req.query.lower() or "trend" in req.query.lower():
            chart_data_a = [{"name": str(idx), "leakage": float(val)} for idx, val in ctx_a["monthly_sum"].items()]
            chart_data_b = [{"name": str(idx), "leakage": float(val)} for idx, val in ctx_b["monthly_sum"].items()]
        else:
            chart_data_a = [{"name": str(idx)[:10], "leakage": float(val)} for idx, val in ctx_a["leakage_by_loc"].items()]
            chart_data_b = [{"name": str(idx)[:10], "leakage": float(val)} for idx, val in ctx_b["leakage_by_loc"].items()]
    else:
        if "surgeon" in req.query.lower() or "doctor" in req.query.lower():
            chart_data_a = [{"name": str(idx)[:12], "leakage": float(val)} for idx, val in ctx_a["surg_loss"].items()]
            chart_data_b = [{"name": str(idx)[:12], "leakage": float(val)} for idx, val in ctx_b["surg_loss"].items()]
        else:
            chart_data_a = [{"name": str(idx)[:12], "leakage": float(val)} for idx, val in ctx_a["spec_loss"].items()]
            chart_data_b = [{"name": str(idx)[:12], "leakage": float(val)} for idx, val in ctx_b["spec_loss"].items()]

    # Collate both series into overlapping chart data
    dict_a = {item["name"]: item["leakage"] for item in chart_data_a} if chart_data_a else {}
    dict_b = {item["name"]: item["leakage"] for item in chart_data_b} if chart_data_b else {}
    
    all_keys = list(set(list(dict_a.keys()) + list(dict_b.keys())))
    merged_chart = []
    for k in all_keys:
        merged_chart.append({
            "name": k,
            "period_a": dict_a.get(k, 0.0),
            "period_b": dict_b.get(k, 0.0)
        })

    def try_sort_key(item):
        name = item["name"]
        if re.match(r"^\d{4}-\d{2}$", name):
            return name
        return -(item["period_a"] + item["period_b"])

    if merged_chart:
        merged_chart.sort(key=try_sort_key if any(re.match(r"^\d{4}-\d{2}$", x["name"]) for x in merged_chart) else lambda x: -(x["period_a"] + x["period_b"]))

    if merged_chart and all(d['period_a'] == 0 and d['period_b'] == 0 for d in merged_chart):
        merged_chart = None

    # Save to chat_messages (to preserve history)
    try:
        conn = sqlite3.connect(DB_PATH)
        chart_data_str = json.dumps(merged_chart) if merged_chart else None
        compare_msg_text = json.dumps({"text_a": answer_a, "text_b": answer_b, "deltas": deltas})
        conn.execute("INSERT INTO chat_messages (session_id, role, text, chart_data, chart_type, chart_value_type) VALUES (?, ?, ?, ?, ?, ?)", 
                     (session_id, "bot", compare_msg_text, chart_data_str, "bar_compare", chart_value_type))
        conn.commit()
        conn.close()
    except Exception as e:
        print("Failed to save comparative chat message:", e)

    return {
        "session_id": session_id,
        "period_a": {
            "answer": answer_a,
            "kpis": {
                "total_loss": loss_a,
                "secondary": sec_a
            }
        },
        "period_b": {
            "answer": answer_b,
            "kpis": {
                "total_loss": loss_b,
                "secondary": sec_b
            }
        },
        "deltas": deltas,
        "chart_data": merged_chart,
        "chart_type": "bar_compare",
        "chart_value_type": chart_value_type
    }

@app.post("/feedback/submit")
def submit_feedback(req: FeedbackSubmitRequest):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO bot_feedback (session_id, query, bot_response, feedback_type, comment, user_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (req.session_id, req.query, req.bot_response, req.feedback_type, req.comment, req.user_id))
        conn.commit()
        conn.close()
        
        # Log to compliance audit log
        log_audit(req.user_id or "Unknown", "FEEDBACK_SUBMITTED", {
            "session_id": req.session_id,
            "feedback_type": req.feedback_type,
            "comment": req.comment
        }, None)
        
        return {"status": "success", "message": "Feedback stored successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/feedback/export")
def export_feedback(username: str):
    if username != "Admin":
        raise HTTPException(status_code=403, detail="Unauthorized. Admin role required.")
        
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT * FROM bot_feedback ORDER BY timestamp DESC", conn)
        conn.close()
        
        # Log audit action
        log_audit(username, "FEEDBACK_EXPORTED", {}, None)
        
        return {"status": "success", "feedback": df.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/feedback/export/csv")
def export_feedback_csv(username: str):
    if username != "Admin":
        raise HTTPException(status_code=403, detail="Unauthorized. Admin role required.")
        
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT * FROM bot_feedback ORDER BY timestamp DESC", conn)
        conn.close()
        
        # Log audit action
        log_audit(username, "FEEDBACK_EXPORTED_CSV", {}, None)
        
        import io
        from fastapi.responses import StreamingResponse
        stream = io.StringIO()
        df.to_csv(stream, index=False)
        response = StreamingResponse(iter([stream.getvalue()]), media_type="text/csv")
        response.headers["Content-Disposition"] = "attachment; filename=bot_feedback_export.csv"
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload")
async def upload_file(request: Request, file: UploadFile = File(...)):
    import shutil
    username = request.query_params.get("username", "Unknown")
    ip_address = request.client.host if request.client else None
    log_audit(username, "FILE_UPLOAD", {"filename": file.filename}, ip_address)

    upload_path = os.path.join(RAW_DIR, file.filename)
    with open(upload_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"status": "success", "filename": file.filename, "message": "File uploaded and queued for ingestion."}

import time
from functools import lru_cache

@lru_cache(maxsize=16)
def get_kpi_data_cached(time_key: int):
    conn = sqlite3.connect(DB_PATH)
    try:
        rev_df = pd.read_sql_query("SELECT * FROM revenue_4a", conn)
        audit_df = pd.read_sql_query("SELECT * FROM audit_4b_4d", conn)
    except Exception as e:
        conn.close()
        raise e
    conn.close()

    rev_df['leakage_amount'] = pd.to_numeric(rev_df['leakage_amount'], errors='coerce').fillna(0)
    rev_df['billed_qty'] = pd.to_numeric(rev_df['billed_qty'], errors='coerce').fillna(0)
    audit_df['difference_amount'] = pd.to_numeric(audit_df['difference_amount'], errors='coerce').fillna(0)

    # 1. total_leakage
    total_leakage = float(rev_df['leakage_amount'].sum())

    # 2. unbilled_rate
    nil_billed_count = len(audit_df[audit_df['billed_procedure'].astype(str).str.upper().str.contains('NIL', na=False)])
    total_audit_count = len(audit_df)
    unbilled_rate = round((nil_billed_count / total_audit_count * 100), 1) if total_audit_count > 0 else 0.0

    # 3. top_offending_dept and top_offending_dept_amount
    dept_revenue = rev_df[rev_df['location'] != 'Multiple Wards'].groupby('location')['leakage_amount'].sum()
    dept_audit = audit_df.groupby('speciality')['difference_amount'].sum()

    max_rev_dept = dept_revenue.idxmax() if not dept_revenue.empty else None
    max_rev_amt = float(dept_revenue.max()) if not dept_revenue.empty else 0.0

    max_audit_dept = dept_audit.idxmax() if not dept_audit.empty else None
    max_audit_amt = float(dept_audit.max()) if not dept_audit.empty else 0.0

    if max_audit_amt >= max_rev_amt:
        top_offending_dept = max_audit_dept if max_audit_dept else "Cardiology"
        top_offending_dept_amount = max_audit_amt
    else:
        top_offending_dept = max_rev_dept if max_rev_dept else "Cardiology"
        top_offending_dept_amount = max_rev_amt

    # 4. surgery_audit_loss
    surgery_audit_loss = float(audit_df['difference_amount'].sum())

    # 5. monthly_trend
    rev_df['date_dt'] = pd.to_datetime(rev_df['date'], format='mixed', errors='coerce')
    rev_df_valid = rev_df.dropna(subset=['date_dt']).copy()
    rev_df_valid = rev_df_valid.sort_values('date_dt')
    rev_df_valid['month_name'] = rev_df_valid['date_dt'].dt.strftime('%b')
    
    monthly_trend_df = rev_df_valid.groupby('month_name', sort=False)['leakage_amount'].sum().reset_index()
    monthly_trend_df.columns = ['month', 'leakage']
    
    # Map months to their chronological order for presentation
    month_order = {m: i for i, m in enumerate(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])}
    monthly_trend_df['month_idx'] = monthly_trend_df['month'].map(month_order)
    monthly_trend_df = monthly_trend_df.sort_values('month_idx').drop(columns=['month_idx'])
    
    monthly_trend = [
        {"month": str(row['month']), "leakage": float(row['leakage'])}
        for _, row in monthly_trend_df.iterrows()
    ]

    return {
        "total_leakage": total_leakage,
        "unbilled_rate": unbilled_rate,
        "top_offending_dept": top_offending_dept,
        "top_offending_dept_amount": top_offending_dept_amount,
        "surgery_audit_loss": surgery_audit_loss,
        "monthly_trend": monthly_trend
    }

@app.get("/dashboard/kpis")
def get_dashboard_kpis():
    time_key = int(time.time() // 300)  # 5 minutes cache
    try:
         return get_kpi_data_cached(time_key)
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/search-suggestions")
def search_suggestions(q: str = "", username: Optional[str] = None):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 1. Fetch departments
        cursor.execute("SELECT DISTINCT name FROM locations WHERE name IS NOT NULL AND name != ''")
        departments = [r[0] for r in cursor.fetchall()]
        
        # 2. Fetch surgeons
        cursor.execute("SELECT DISTINCT surgeon FROM audit_4b_4d WHERE surgeon IS NOT NULL AND surgeon != ''")
        surgeons = [r[0] for r in cursor.fetchall()]
        
        # 3. Fetch sessions
        sessions = []
        if username:
            cursor.execute(
                "SELECT session_id, title, bot FROM chat_sessions WHERE username = ? AND title IS NOT NULL AND title != '' ORDER BY created_at DESC", 
                (username,)
            )
            sessions = [{"session_id": r[0], "title": r[1], "bot": r[2]} for r in cursor.fetchall()]
            
        conn.close()
        
        # Filter with query if provided (simple server-side search backup)
        if q:
            q_lower = q.lower()
            departments = [d for d in departments if q_lower in d.lower()]
            surgeons = [s for s in surgeons if q_lower in s.lower()]
            sessions = [s for s in sessions if q_lower in s["title"].lower()]
            
        return {
            "departments": departments,
            "surgeons": surgeons,
            "sessions": sessions
        }
    except Exception as e:
        logging.error(f"Error in search suggestions: {e}")
        return {"departments": [], "surgeons": [], "sessions": [], "error": str(e)}

# --- AUDIT LOGS ENDPOINTS ---

@app.post("/audit-logs/log")
def create_audit_log(req: AuditLogCreateRequest, request: Request):
    ip_address = request.client.host if request.client else None
    log_audit(req.user_id, req.action_type, req.details, ip_address, req.session_id)
    return {"status": "success"}

@app.get("/audit-logs")
def get_audit_logs(
    username: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user_filter: Optional[str] = None,
    action_filter: Optional[str] = None,
    search: Optional[str] = None
):
    if username != "Admin":
        raise HTTPException(status_code=403, detail="Unauthorized. Admin role required.")
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = "SELECT * FROM audit_logs WHERE 1=1"
    params = []
    
    if start_date:
        query += " AND timestamp >= ?"
        params.append(f"{start_date} 00:00:00")
    if end_date:
        query += " AND timestamp <= ?"
        params.append(f"{end_date} 23:59:59")
    if user_filter:
        query += " AND user_id = ?"
        params.append(user_filter)
    if action_filter:
        query += " AND action_type = ?"
        params.append(action_filter)
    if search:
        query += " AND (user_id LIKE ? OR action_type LIKE ? OR details LIKE ? OR ip_address LIKE ?)"
        like_search = f"%{search}%"
        params.extend([like_search, like_search, like_search, like_search])
        
    query += " ORDER BY timestamp DESC"
    
    cursor.execute(query, params)
    logs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"logs": logs}

@app.get("/audit-logs/export")
def export_audit_logs(
    username: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user_filter: Optional[str] = None,
    action_filter: Optional[str] = None,
    search: Optional[str] = None
):
    if username != "Admin":
        raise HTTPException(status_code=403, detail="Unauthorized. Admin role required.")
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = "SELECT * FROM audit_logs WHERE 1=1"
    params = []
    
    if start_date:
        query += " AND timestamp >= ?"
        params.append(f"{start_date} 00:00:00")
    if end_date:
        query += " AND timestamp <= ?"
        params.append(f"{end_date} 23:59:59")
    if user_filter:
        query += " AND user_id = ?"
        params.append(user_filter)
    if action_filter:
        query += " AND action_type = ?"
        params.append(action_filter)
    if search:
        query += " AND (user_id LIKE ? OR action_type LIKE ? OR details LIKE ? OR ip_address LIKE ?)"
        like_search = f"%{search}%"
        params.extend([like_search, like_search, like_search, like_search])
        
    query += " ORDER BY timestamp DESC"
    
    cursor.execute(query, params)
    logs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    import csv
    from io import StringIO
    
    f = StringIO()
    writer = csv.writer(f)
    writer.writerow(["ID", "Timestamp", "User ID", "Action Type", "Details", "IP Address", "Session ID"])
    for log in logs:
        writer.writerow([
            log["id"],
            log["timestamp"],
            log["user_id"],
            log["action_type"],
            log["details"],
            log["ip_address"],
            log["session_id"]
        ])
        
    f.seek(0)
    response = StreamingResponse(iter([f.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=audit_logs.csv"
    return response

@app.post("/export/pdf")
def log_export_pdf(username: str, request: Request):
    ip_address = request.client.host if request.client else None
    log_audit(username, "EXPORT_PDF", {}, ip_address)
    return {"status": "success", "message": "PDF export logged successfully."}

@app.post("/export/excel")
def log_export_excel(username: str, request: Request):
    ip_address = request.client.host if request.client else None
    log_audit(username, "EXPORT_EXCEL", {}, ip_address)
    return {"status": "success", "message": "Excel export logged successfully."}

# --- END AUDIT LOGS ENDPOINTS ---

# --- ALERTS & NOTIFICATIONS ENGINE ---

def trigger_notifications(name, cond_type, threshold, comp_col, detected_value, target_date, email, webhook):
    subject = f"🚨 Amrita Guard Alert Triggered: {name}"
    comp_str = f" for '{comp_col}'" if comp_col else ""
    cond_desc = {
        "total_leakage_daily": "Daily Total Revenue Leakage exceeds",
        "unbilled_rate": "Unbilled Rate exceeds",
        "department_leakage": "Department/Location Leakage exceeds",
        "surgery_loss": "Surgery package Audit Loss exceeds"
    }.get(cond_type, cond_type)
    
    val_suffix = "%" if cond_type == "unbilled_rate" else ""
    val_prefix = "" if cond_type == "unbilled_rate" else "₹"
    
    body = f"""
================================================================
ALERT TRIGGERED: {name}
================================================================
Condition: {cond_desc} {val_prefix}{threshold:,.2f}{val_suffix}{comp_str}
Detected Value: {val_prefix}{detected_value:,.2f}{val_suffix}
Target Data Date: {target_date}
Triggered At (System Time): {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}
================================================================
    """
    
    # 1. Email (SMTP)
    if email:
        logging.info(f"Attempting to send email alert to {email}...")
        try:
            smtp_host = "localhost"
            smtp_port = 1025
            sender = "alerts@amritaguard.com"
            
            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = sender
            msg['To'] = email
            
            with smtplib.SMTP(smtp_host, smtp_port, timeout=3) as server:
                server.sendmail(sender, [email], msg.as_string())
            logging.info(f"Email sent successfully to {email}")
        except Exception as e:
            logging.warning(f"SMTP delivery failed (expected in local/mock environments): {e}. Printing email to console logs:\n{body}")
            
    # 2. Webhook (Slack / Teams)
    if webhook:
        logging.info(f"Attempting to send Webhook notification to {webhook}...")
        try:
            is_slack = "hooks.slack.com" in webhook
            if is_slack:
                payload = {
                    "text": f"🚨 *Alert Triggered: {name}*\n"
                            f"• *Condition:* {cond_desc} {val_prefix}{threshold:,.2f}{val_suffix}{comp_str}\n"
                            f"• *Detected Value:* {val_prefix}{detected_value:,.2f}{val_suffix}\n"
                            f"• *Target Date:* {target_date}"
                }
            else:
                payload = {
                    "title": f"🚨 Alert Triggered: {name}",
                    "text": f"**Condition:** {cond_desc} {val_prefix}{threshold:,.2f}{val_suffix}{comp_str}<br>"
                            f"**Detected Value:** {val_prefix}{detected_value:,.2f}{val_suffix}<br>"
                            f"**Target Date:** {target_date}"
                }
                
            req = urllib.request.Request(
                webhook,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=3) as response:
                response.read()
            logging.info("Webhook payload delivered successfully.")
        except Exception as e:
            logging.warning(f"Webhook delivery failed (expected if URLs are placeholders): {e}")

def check_active_alerts_job():
    logging.info("Starting background alert checking process...")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Fetch active alerts
        cursor.execute("SELECT id, name, condition_type, threshold, comparison_column, bot_type, email_recipient, webhook_url FROM alerts WHERE is_active = 1")
        active_alerts = cursor.fetchall()
        
        for alert_id, name, cond_type, threshold, comp_col, bot_type, email, webhook in active_alerts:
            # Check for triggers in the last 24 hours to prevent duplicates
            cursor.execute("""
                SELECT COUNT(*) FROM alert_notifications 
                WHERE alert_id = ? AND triggered_at >= datetime('now', '-24 hours')
            """, (alert_id,))
            if cursor.fetchone()[0] > 0:
                logging.info(f"Alert '{name}' was triggered in the last 24 hours. Skipping to prevent duplicates.")
                continue
                
            triggered = False
            detected_value = 0.0
            target_date = None
            
            if cond_type == "total_leakage_daily":
                cursor.execute("""
                    SELECT date, SUM(leakage_amount) as val 
                    FROM revenue_4a 
                    GROUP BY date 
                    ORDER BY date DESC 
                    LIMIT 1
                """)
                res = cursor.fetchone()
                if res and res[1] is not None:
                    target_date, detected_value = res[0], float(res[1])
                    if detected_value > threshold:
                        triggered = True
                        
            elif cond_type == "unbilled_rate":
                cursor.execute("""
                    SELECT date, 
                           (SUM(CASE WHEN UPPER(billed_procedure) LIKE '%NIL%' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) as val
                    FROM audit_4b_4d
                    GROUP BY date
                    ORDER BY date DESC
                    LIMIT 1
                """)
                res = cursor.fetchone()
                if res and res[1] is not None:
                    target_date, detected_value = res[0], float(res[1])
                    if detected_value > threshold:
                        triggered = True
                        
            elif cond_type == "department_leakage":
                if comp_col:
                    cursor.execute("""
                        SELECT date, SUM(leakage_amount) as val
                        FROM revenue_4a
                        WHERE UPPER(location) = UPPER(?)
                        GROUP BY date
                        ORDER BY date DESC
                        LIMIT 1
                    """, (comp_col,))
                    res = cursor.fetchone()
                    if res and res[1] is not None:
                        target_date, detected_value = res[0], float(res[1])
                        if detected_value > threshold:
                            triggered = True
                            
            elif cond_type == "surgery_loss":
                cursor.execute("""
                    SELECT date, SUM(difference_amount) as val
                    FROM audit_4b_4d
                    GROUP BY date
                    ORDER BY date DESC
                    LIMIT 1
                """)
                res = cursor.fetchone()
                if res and res[1] is not None:
                    target_date, detected_value = res[0], float(res[1])
                    if detected_value > threshold:
                        triggered = True
            
            if triggered:
                logging.info(f"🚨 Alert Triggered: '{name}'! Detected: {detected_value} on date {target_date}")
                
                # Format triggered_at as CURRENT_TIMESTAMP (SQLite default handles this, but we force datetime('now'))
                cursor.execute("""
                    INSERT INTO alert_notifications (alert_id, triggered_at, value_detected, status)
                    VALUES (?, datetime('now'), ?, 'unread')
                """, (alert_id, detected_value))
                conn.commit()
                
                # Send notifications asynchronously/non-blocking
                try:
                    trigger_notifications(name, cond_type, threshold, comp_col, detected_value, target_date, email, webhook)
                except Exception as n_err:
                    logging.error(f"Failed to dispatch notifications: {n_err}")
                
        conn.close()
    except Exception as e:
        logging.error(f"Error executing active alerts monitoring: {e}")

# --- API ENDPOINTS FOR ALERTS & NOTIFICATIONS ---

@app.get("/api/alerts")
def get_alerts(username: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM alerts ORDER BY created_at DESC")
    alerts = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"alerts": alerts}

@app.post("/api/alerts")
def create_alert(req: AlertCreateRequest, request: Request):
    ip_address = request.client.host if request.client else None
    log_audit(req.created_by, "ALERT_CREATED", {"name": req.name}, ip_address)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO alerts (name, condition_type, threshold, comparison_column, bot_type, email_recipient, webhook_url, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (req.name, req.condition_type, req.threshold, req.comparison_column, req.bot_type, req.email_recipient, req.webhook_url, req.created_by))
        conn.commit()
        alert_id = cursor.lastrowid
        conn.close()
        return {"status": "success", "id": alert_id, "message": "Alert created successfully."}
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/alerts/{alert_id}")
def update_alert(alert_id: int, req: AlertUpdateRequest, request: Request):
    username = "Admin"
    ip_address = request.client.host if request.client else None
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM alerts WHERE id = ?", (alert_id,))
    res = cursor.fetchone()
    if not res:
        conn.close()
        raise HTTPException(status_code=404, detail="Alert not found.")
    alert_name = res[0]
    
    log_audit(username, "ALERT_UPDATED", {"id": alert_id, "name": alert_name}, ip_address)
    
    updates = []
    params = []
    for k, v in req.dict(exclude_unset=True).items():
        updates.append(f"{k} = ?")
        params.append(v)
        
    if not updates:
        conn.close()
        return {"status": "success", "message": "No updates specified."}
        
    query = f"UPDATE alerts SET {', '.join(updates)} WHERE id = ?"
    params.append(alert_id)
    
    try:
        cursor.execute(query, params)
        conn.commit()
        conn.close()
        return {"status": "success", "message": "Alert updated successfully."}
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/alerts/{alert_id}")
def delete_alert(alert_id: int, username: str, request: Request):
    ip_address = request.client.host if request.client else None
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM alerts WHERE id = ?", (alert_id,))
    res = cursor.fetchone()
    if not res:
        conn.close()
        raise HTTPException(status_code=404, detail="Alert not found.")
    alert_name = res[0]
    
    log_audit(username, "ALERT_DELETED", {"id": alert_id, "name": alert_name}, ip_address)
    
    try:
        cursor.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))
        conn.commit()
        conn.close()
        return {"status": "success", "message": "Alert deleted successfully."}
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/alerts/check-now")
def trigger_alert_check_manually(req: AlertCheckNowRequest, request: Request):
    ip_address = request.client.host if request.client else None
    log_audit(req.username, "MANUAL_ALERT_CHECK", {}, ip_address)
    try:
        check_active_alerts_job()
        return {"status": "success", "message": "Manual alert checks executed successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/alerts/notifications")
def get_alert_notifications(username: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT n.id, n.alert_id, n.triggered_at, n.value_detected, n.status,
               a.name as alert_name, a.condition_type, a.threshold, a.comparison_column, a.bot_type
        FROM alert_notifications n
        JOIN alerts a ON n.alert_id = a.id
        ORDER BY n.triggered_at DESC
    """)
    notifications = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"notifications": notifications}

@app.post("/api/alerts/notifications/{notification_id}/read")
def mark_notification_as_read(notification_id: int, username: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE alert_notifications SET status = 'read' WHERE id = ?", (notification_id,))
        conn.commit()
        conn.close()
        return {"status": "success", "message": "Notification marked as read."}
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/alerts/notifications/unread-count")
def get_unread_notifications_count(username: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM alert_notifications WHERE status = 'unread'")
    count = cursor.fetchone()[0]
    conn.close()
    return {"unread_count": count}

class AlertTestRequest(BaseModel):
    condition_type: str
    threshold: float
    comparison_column: Optional[str] = None
    bot_type: str
    username: str

@app.post("/api/alerts/test")
def dry_run_alert(req: AlertTestRequest, request: Request):
    ip_address = request.client.host if request.client else None
    log_audit(req.username, "ALERT_DRY_RUN", {"condition_type": req.condition_type, "threshold": req.threshold}, ip_address)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    triggers = []
    try:
        if req.condition_type == "total_leakage_daily":
            cursor.execute("""
                SELECT date, SUM(leakage_amount) as value
                FROM revenue_4a
                GROUP BY date
                HAVING value > ?
                ORDER BY date DESC
            """, (req.threshold,))
            for row in cursor.fetchall():
                triggers.append({"date": row[0], "value": float(row[1])})
                
        elif req.condition_type == "unbilled_rate":
            cursor.execute("""
                SELECT date,
                       (SUM(CASE WHEN UPPER(billed_procedure) LIKE '%NIL%' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) as value
                FROM audit_4b_4d
                GROUP BY date
                HAVING value > ?
                ORDER BY date DESC
            """, (req.threshold,))
            for row in cursor.fetchall():
                triggers.append({"date": row[0], "value": float(row[1])})
                
        elif req.condition_type == "department_leakage":
            if req.comparison_column:
                cursor.execute("""
                    SELECT date, SUM(leakage_amount) as value
                    FROM revenue_4a
                    WHERE UPPER(location) = UPPER(?)
                    GROUP BY date
                    HAVING value > ?
                    ORDER BY date DESC
                """, (req.comparison_column, req.threshold))
                for row in cursor.fetchall():
                    triggers.append({"date": row[0], "value": float(row[1])})
                    
        elif req.condition_type == "surgery_loss":
            cursor.execute("""
                SELECT date, SUM(difference_amount) as value
                FROM audit_4b_4d
                GROUP BY date
                HAVING value > ?
                ORDER BY date DESC
            """, (req.threshold,))
            for row in cursor.fetchall():
                triggers.append({"date": row[0], "value": float(row[1])})
                
        conn.close()
        return {"status": "success", "triggers": triggers}
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))

# --- APSCHEDULER BACKGROUND WORKER ---
scheduler = BackgroundScheduler()

def send_weekly_feedback_summary_job():
    try:
        logging.info("Running weekly feedback summary background job...")
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("""
            SELECT session_id, query, bot_response, feedback_type, comment, user_id, timestamp 
            FROM bot_feedback 
            WHERE feedback_type != 'thumbs_up' 
              AND timestamp >= datetime('now', '-7 days')
            ORDER BY timestamp DESC
        """, conn)
        conn.close()
        
        if df.empty:
            logging.info("No low-rated responses found for the weekly summary.")
            return
            
        summary_text = "Weekly Low-Rated Bot Responses Summary:\n\n"
        for idx, row in df.iterrows():
            summary_text += f"[{idx + 1}] Timestamp: {row['timestamp']} | User: {row['user_id']}\n"
            summary_text += f"Query: {row['query']}\n"
            summary_text += f"Feedback Type: {row['feedback_type']}\n"
            summary_text += f"Comment: {row['comment'] or 'N/A'}\n"
            summary_text += f"Response: {row['bot_response'][:250]}...\n"
            summary_text += "-"*50 + "\n\n"
            
        logging.info(f"Weekly Summary Report generated ({len(df)} entries):\n{summary_text}")
        
        recipient = "admin@amritahospital.org"
        subject = f"Weekly Bot Feedback Summary - {len(df)} Issues Detected"
        sender = "amritaguard-system@amritaguard.com"
        
        msg = MIMEText(summary_text)
        msg['Subject'] = subject
        msg['From'] = sender
        msg['To'] = recipient
        
        try:
            smtp_host = "localhost"
            smtp_port = 1025
            with smtplib.SMTP(smtp_host, smtp_port, timeout=3) as server:
                server.sendmail(sender, [recipient], msg.as_string())
            logging.info("Weekly feedback summary email sent successfully.")
        except Exception as smtp_err:
            logging.warning(f"SMTP delivery failed for weekly feedback email summary (expected in mock sandbox): {smtp_err}")
            
    except Exception as e:
        logging.error(f"Error in weekly feedback summary job: {e}")

@app.on_event("startup")
def start_scheduler():
    if not scheduler.running:
        scheduler.add_job(check_active_alerts_job, "interval", hours=1, id="active_alerts_job")
        scheduler.add_job(send_weekly_feedback_summary_job, "cron", day_of_week="sun", hour=0, minute=0, id="weekly_feedback_job")
        scheduler.start()
        logging.info("APScheduler Background Scheduler started successfully.")
        
        # Trigger an initial check in background so we get demo data immediately!
        try:
            import threading
            threading.Thread(target=check_active_alerts_job, daemon=True).start()
            logging.info("Triggered initial alert check thread.")
        except Exception as e:
            logging.warning(f"Could not start initial check thread: {e}")

@app.on_event("shutdown")
def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logging.info("APScheduler Background Scheduler stopped successfully.")

# --- END AUDIT LOGS ENDPOINTS ---

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)


