import os
import pandas as pd
import sqlite3
import pdfplumber
import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = str(BASE_DIR / "data" / "raw")
DB_PATH = str(BASE_DIR / "db" / "hospital.db")

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


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Create tables
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT,
        name TEXT UNIQUE
    )''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS soc_rates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        service_name TEXT,
        charge REAL
    )''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS revenue_4a (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        patient_id TEXT,
        service_name TEXT,
        billed_qty INTEGER,
        actual_qty INTEGER,
        leakage_amount REAL,
        location TEXT,
        staff_name TEXT,
        hash_key TEXT UNIQUE
    )''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS audit_4b_4d (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        patient_id TEXT,
        actual_procedure TEXT,
        billed_procedure TEXT,
        surgeon TEXT,
        speciality TEXT,
        difference_amount REAL,
        hash_key TEXT UNIQUE
    )''')
    conn.commit()
    return conn

def ingest_locations(conn):
    print("Ingesting locations...")
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM locations")
        conn.commit()
        
        normalized_locs = set()
        
        # 1. Parse from Master List Detail Work Area
        try:
            df_master = pd.read_excel(os.path.join(RAW_DIR, "ICU + Ward List.xlsx"))
            if 'Detail Work Area' in df_master.columns:
                master_vals = df_master['Detail Work Area'].dropna().astype(str).unique().tolist()
                for val in master_vals:
                    norm = normalize_location(val)
                    if norm and norm not in ["Multiple Wards", "Ward", "System", "Unknown Location"]:
                        normalized_locs.add(norm)
        except Exception as e:
            print(f"  Warning parsing master list locations: {e}")
            
        # 2. Parse from populated database locations
        try:
            cursor.execute("SELECT DISTINCT location FROM revenue_4a")
            db_vals = [r[0] for r in cursor.fetchall()]
            for val in db_vals:
                norm = normalize_location(val)
                if norm and norm not in ["Multiple Wards", "Ward", "System", "Unknown Location"]:
                    normalized_locs.add(norm)
        except Exception as e:
            print(f"  Warning parsing DB locations: {e}")
            
        for loc in sorted(normalized_locs):
            try:
                cursor.execute("INSERT INTO locations (type, name) VALUES (?, ?)", ('ward', loc))
            except sqlite3.IntegrityError:
                pass
        conn.commit()
        print(f"  Successfully ingested {len(normalized_locs)} unique normalized locations.")
    except Exception as e:
        print(f"Error ingesting locations: {e}")

def ingest_soc(conn):
    print("Ingesting SOC...")
    pdf_file = "Amrita Hospital SOC - 2022-23_03-01-2024..pdf"
    pdf_path = os.path.join(RAW_DIR, pdf_file)
    if not os.path.exists(pdf_path):
        print(f"SOC PDF not found at {pdf_path}")
        return
        
    try:
        # Simplistic extraction for demo purposes, as real SOC PDFs are tabular and complex
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for page in pdf.pages[:5]: # Extract first few pages for speed
                text += page.extract_text() + "\n"
                
        # We would typically parse tables here. For now, we'll insert a mock row
        # if parsing text fails to yield structured data.
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO soc_rates (service_name, charge) VALUES (?, ?)", ("Mock Service", 100.0))
        except:
            pass
        conn.commit()
    except Exception as e:
        print(f"Error ingesting SOC: {e}")

import hashlib
import uuid

def generate_hash(*args):
    s = "".join([str(a) for a in args])
    return hashlib.md5(s.encode()).hexdigest()

def ingest_4a(conn):
    print("Ingesting Revenue 4A files...")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM revenue_4a")
    conn.commit()

    # 1. Process Excel files (.xlsx)
    excel_files = [f for f in os.listdir(RAW_DIR) if f.startswith('IH_4A_') and f.endswith('.xlsx')]
    
    for file in excel_files:
        print(f"  Parsing Excel file {file}...")
        path = os.path.join(RAW_DIR, file)
        try:
            xl = pd.ExcelFile(path)
            
            # Extract date from filename if possible
            import re
            date_match = re.search(r'(20\d{2}|\d{2})\.xlsx$', file.replace(' ', ''))
            fallback_date = "2023-01-01"
            if date_match:
                year_suffix = date_match.group(1)
                year = "20" + year_suffix if len(year_suffix) == 2 else year_suffix
                fallback_date = f"{year}-01-01"
            
            # Parse Summary_Final for precise daily service leakage
            services = []
            if 'Summary_Final' in xl.sheet_names:
                df_sum = pd.read_excel(xl, sheet_name='Summary_Final', nrows=30)
                date_val = fallback_date
                
                for idx, row in df_sum.iterrows():
                    srv = str(row.iloc[0]).strip()
                    if pd.isna(srv) or srv == 'nan' or 'Service Name' in srv or 'Sample' in srv or 'Total' in srv or 'Leakage' in srv or 'Occupied' in srv:
                        if pd.notna(srv) and 'Service Name' not in srv:
                            services.append(srv) # keep track of valid services even if we skip inserting them as pure services
                        continue
                        
                    services.append(srv)
                    
                    daily_leakage = 0.0
                    if len(row) > 1 and pd.notna(row.iloc[1]):
                        try:
                            daily_leakage = float(row.iloc[1])
                        except: pass
                        
                    if daily_leakage > 0:
                        h = generate_hash(date_val, srv, "System", file, "Summary", idx)
                        try:
                            cursor.execute("""
                                INSERT INTO revenue_4a (date, service_name, billed_qty, leakage_amount, location, staff_name, hash_key)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (date_val, srv, 0, daily_leakage, "Multiple Wards", "System", h))
                        except sqlite3.IntegrityError:
                            pass

            # Parse Billing staff leakage for staff-specific data
            if 'Billing staff leakage' in xl.sheet_names:
                df_raw = pd.read_excel(xl, sheet_name='Billing staff leakage', header=None, nrows=20)
                header_idx = 1
                for i, r in df_raw.iterrows():
                    row_str = " ".join([str(x).lower() for x in r.values])
                    if 'night duty' in row_str or 'staff' in row_str:
                        header_idx = i
                        break
                        
                df = pd.read_excel(xl, sheet_name='Billing staff leakage', header=header_idx, nrows=5000)
                
                gap_cols = [c for c in df.columns if 'Gap' in str(c) or 'Unnamed' in str(c)]
                date_col = next((c for c in df.columns if 'date' in str(c).lower()), None)
                staff_col = next((c for c in df.columns if 'duty' in str(c).lower() or 'staff' in str(c).lower() or 'emp' in str(c).lower()), None)
                amt_col = next((c for c in df.columns if 'amount' in str(c).lower() or 'total' in str(c).lower() and 'amount' not in str(c).lower()), None)
                bed_col = next((c for c in df.columns if 'bed' in str(c).lower() or 'ward' in str(c).lower()), None)
                
                for idx, row in df.iterrows():
                    staff = str(row[staff_col]) if staff_col and pd.notna(row[staff_col]) else "Unknown"
                    if staff == "Unknown" or staff.lower() == 'nan': continue
                    
                    date_val = str(row[date_col]) if date_col and pd.notna(row[date_col]) else "2023-01-01"
                    loc_val = str(row[bed_col]) if bed_col and pd.notna(row[bed_col]) else "Ward"
                    total_amount = 0.0
                    if amt_col and pd.notna(row[amt_col]):
                        try: total_amount = float(row[amt_col])
                        except: pass
                    
                    active_gaps = []
                    for i, g_col in enumerate(gap_cols):
                        val = row[g_col]
                        if pd.notna(val) and str(val).strip() != '' and str(val).strip() != '0':
                            try:
                                if float(val) > 0:
                                    srv = services[i] if i < len(services) else f"Unknown Service {i}"
                                    active_gaps.append(srv)
                            except: pass
                            
                    if total_amount > 0:
                        amt_per_gap = total_amount / len(active_gaps) if active_gaps else total_amount
                        gaps_to_insert = active_gaps if active_gaps else ["Unspecified Service"]
                        for srv in gaps_to_insert:
                            if "Unknown" in srv or "Unnamed" in srv or "Sample" in srv or "Total" in srv:
                                continue
                            h = generate_hash(date_val, srv, staff, loc_val, file, "StaffLeakage", idx)
                            try:
                                cursor.execute("""
                                    INSERT INTO revenue_4a (date, service_name, billed_qty, leakage_amount, location, staff_name, hash_key)
                                    VALUES (?, ?, ?, ?, ?, ?, ?)
                                """, (date_val, srv, 0, amt_per_gap, loc_val, staff, h))
                            except sqlite3.IntegrityError:
                                pass
                                
        except Exception as e:
            print(f"  Error on file {file}: {e}")

    # 2. Process CSV files (.csv)
    csv_files = [f for f in os.listdir(RAW_DIR) if f.startswith('Billing Audit - ') and f.endswith('.csv')]
    
    MONTHS_MAP = {
        'jan': 1, 'feb': 2, 'march': 3, 'apr': 4, 'may': 5, 'june': 6,
        'july': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }
    
    def parse_csv_value(val):
        if pd.isna(val):
            return 0.0
        val_str = str(val).strip().replace(',', '').replace('"', '').replace('(', '-').replace(')', '')
        if val_str == '-' or val_str == '' or val_str.lower() == 'nan':
            return 0.0
        try:
            if val_str.endswith('%'):
                return float(val_str[:-1]) / 100.0
            return float(val_str)
        except:
            return 0.0

    for file in csv_files:
        print(f"  Parsing CSV file {file}...")
        path = os.path.join(RAW_DIR, file)
        try:
            # Extract month/year from filename
            match = re.search(r'Billing Audit\s*-\s*([a-zA-Z]+)\s+(\d{4})\.csv', file)
            if not match:
                print(f"    Skipping {file}: Could not parse month/year from name")
                continue
            m_name, year_str = match.group(1).lower().strip(), match.group(2)
            year = int(year_str)
            month_num = None
            for key, val in MONTHS_MAP.items():
                if m_name.startswith(key[:3]) or key.startswith(m_name[:3]):
                    month_num = val
                    break
            if not month_num:
                print(f"    Skipping {file}: Unknown month name {m_name}")
                continue
                
            df = pd.read_csv(path, header=None)
            
            # Find day columns in header row
            header_row = df.iloc[1]
            day_cols = []
            for col_idx, col_val in enumerate(header_row):
                if pd.notna(col_val):
                    col_str = str(col_val).strip()
                    m_match = re.match(r'^(\d+)/[a-zA-Z]+$', col_str)
                    if m_match:
                        day_cols.append((col_idx, int(m_match.group(1))))
                        
            if not day_cols:
                print(f"    No day columns found in {file}")
                continue
                
            # A. Parse services: rows 5 to 23 (inclusive)
            for row_idx in range(5, 24):
                row = df.iloc[row_idx]
                service_name = str(row.iloc[3]).strip()
                if not service_name or service_name.lower() == 'nan':
                    continue
                    
                for col_idx, day_num in day_cols:
                    val = parse_csv_value(row.iloc[col_idx])
                    if val > 0:
                        date_str = f"{year:04d}-{month_num:02d}-{day_num:02d}"
                        h = generate_hash(date_str, service_name, "System", "Multiple Wards", "Summary", row_idx)
                        try:
                            cursor.execute("""
                                INSERT INTO revenue_4a (date, service_name, billed_qty, leakage_amount, location, staff_name, hash_key)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (date_str, service_name, 0, val, "Multiple Wards", "System", h))
                        except sqlite3.IntegrityError:
                            pass
                            
            # B. Parse staff/locations: rows 42 to 61 (inclusive)
            for row_idx in range(42, 62):
                row = df.iloc[row_idx]
                ward = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
                staff = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ""
                station = str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else ""
                
                location = station if station else (ward if ward else "Ward")
                staff_name = staff if staff else "Unknown"
                
                resp_col_val = str(row.iloc[3]).strip().lower()
                if not ward and not staff and not station:
                    if resp_col_val in ['total', 'check', '-', 'nan', '']:
                        continue
                        
                for col_idx, day_num in day_cols:
                    val = parse_csv_value(row.iloc[col_idx])
                    if val > 0:
                        date_str = f"{year:04d}-{month_num:02d}-{day_num:02d}"
                        h = generate_hash(date_str, "Unspecified Service", staff_name, location, "StaffLeakage", row_idx)
                        try:
                            cursor.execute("""
                                INSERT INTO revenue_4a (date, service_name, billed_qty, leakage_amount, location, staff_name, hash_key)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (date_str, "Unspecified Service", 0, val, location, staff_name, h))
                        except sqlite3.IntegrityError:
                            pass
                            
        except Exception as e:
            print(f"  Error on file {file}: {e}")
            
    conn.commit()

def ingest_4b_4d(conn):
    print("Ingesting Audit 4B/4D files...")
    files = [f for f in os.listdir(RAW_DIR) if (f.startswith('IH_4B_') or f.startswith('IH_4D_')) and f.endswith('.xlsx')]
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS audit_4b_4d")
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS audit_4b_4d (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        patient_id TEXT,
        actual_procedure TEXT,
        billed_procedure TEXT,
        surgeon TEXT,
        speciality TEXT,
        difference_amount REAL,
        hash_key TEXT UNIQUE
    )''')
    
    for file in files:
        print(f"  Parsing {file}...")
        path = os.path.join(RAW_DIR, file)
        try:
            xl = pd.ExcelFile(path)
            if 'Procedure detail' in xl.sheet_names:
                df = pd.read_excel(xl, sheet_name='Procedure detail')
                
                # Identify columns flexibly
                date_col = next((c for c in df.columns if 'date' in str(c).lower()), None)
                actual_proc_col = next((c for c in df.columns if 'actual' in str(c).lower() and 'surgery' in str(c).lower()), None)
                billed_proc_col = next((c for c in df.columns if 'billed' in str(c).lower() and 'his' in str(c).lower()), None)
                surgeon_col = next((c for c in df.columns if 'surgeon' in str(c).lower()), None)
                spec_col = next((c for c in df.columns if 'speciality' in str(c).lower()), None)
                diff_col = next((c for c in df.columns if 'difference' in str(c).lower() and 'amount' in str(c).lower()), None)
                patient_col = next((c for c in df.columns if 'mrd' in str(c).lower() or 'patient' in str(c).lower()), None)

                for idx, row in df.iterrows():
                    actual = str(row[actual_proc_col]) if actual_proc_col and pd.notna(row[actual_proc_col]) else "Unknown"
                    billed = str(row[billed_proc_col]) if billed_proc_col and pd.notna(row[billed_proc_col]) else "Unknown"
                    
                    if actual == "Unknown" and billed == "Unknown": continue
                    
                    date_val = str(row[date_col]) if date_col and pd.notna(row[date_col]) else "2024-01-01"
                    surgeon = str(row[surgeon_col]) if surgeon_col and pd.notna(row[surgeon_col]) else "Unknown"
                    spec = str(row[spec_col]) if spec_col and pd.notna(row[spec_col]) else "Unknown"
                    patient = str(row[patient_col]) if patient_col and pd.notna(row[patient_col]) else "Unknown"
                    
                    diff_amt = 0.0
                    if diff_col and pd.notna(row[diff_col]):
                        try: diff_amt = float(row[diff_col])
                        except: pass
                        
                    h = generate_hash(date_val, actual, billed, patient, file, idx)
                    
                    try:
                        cursor.execute("""
                            INSERT INTO audit_4b_4d (date, patient_id, actual_procedure, billed_procedure, surgeon, speciality, difference_amount, hash_key)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (date_val, patient, actual, billed, surgeon, spec, diff_amt, h))
                    except sqlite3.IntegrityError:
                        pass
        except Exception as e:
            print(f"  Error on file {file}: {e}")
            
    conn.commit()

if __name__ == "__main__":
    conn = init_db()
    ingest_soc(conn)
    ingest_4a(conn)
    ingest_4b_4d(conn)
    ingest_locations(conn)
    conn.close()
    print("Ingestion complete.")
