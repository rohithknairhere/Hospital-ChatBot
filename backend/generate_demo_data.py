import os
import sys
import shutil
import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path

# Setup paths relative to this script
BACKEND_DIR = Path(__file__).resolve().parent
BASE_DIR = BACKEND_DIR.parent
DEMO_DIR = BASE_DIR / "data" / "demo"
RAW_DIR = BASE_DIR / "data" / "raw"
DB_DIR = BASE_DIR / "db"

def create_directories():
    """Ensure all required directories exist."""
    os.makedirs(str(DEMO_DIR), exist_ok=True)
    os.makedirs(str(RAW_DIR), exist_ok=True)
    os.makedirs(str(DB_DIR), exist_ok=True)
    print(f"Directories verified: {DEMO_DIR}, {RAW_DIR}, {DB_DIR}")

def generate_ward_list():
    """Generate mock ICU + Ward List Excel file."""
    ward_list_path = DEMO_DIR / "ICU + Ward List.xlsx"
    print(f"Generating {ward_list_path}...")
    
    wards = [
        "2F CCU", "2F CTVS ICU", "2F MICU", "2F NICU", "2F SICU",
        "3F HDU", "3F PED WARD", "WARD 3RD FLOOR", "4F HDU",
        "4F PED WARD", "FOURTH FLOOR", "5F HDU", "5F GYNAEC",
        "6F HDU", "6F OBG AND ANC", "WARD 6TH FLOOR", "DAY CARE",
        "ECONOMY - 4BED"
    ]
    
    df = pd.DataFrame({
        "Detail Work Area": wards,
        "Type": ["ICU" if "ICU" in w or "CCU" in w or "NICU" in w or "SICU" in w or "HDU" in w else "Ward" for w in wards]
    })
    
    df.to_excel(str(ward_list_path), index=False)

def generate_soc_pdf():
    """Generate a valid minimal PDF for pdfplumber to parse."""
    pdf_path = DEMO_DIR / "Amrita Hospital SOC - 2022-23_03-01-2024..pdf"
    print(f"Generating {pdf_path}...")
    
    # Minimal valid PDF structure with 'Mock SOC PDF Data' text
    pdf_content = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /Resources << >> /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n"
        b"4 0 obj\n<< /Length 40 >>\nstream\nBT /F1 12 Tf 72 712 Td (Mock SOC PDF Data) Tj ET\nendstream\nendobj\n"
        b"xref\n0 5\n0000000000 65535 f\n0000000009 00000 n\n0000000056 00000 n\n0000000111 00000 n\n0000000212 00000 n\n"
        b"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n306\n%%EOF"
    )
    with open(str(pdf_path), 'wb') as f:
        f.write(pdf_content)

def generate_revenue_4a_excel():
    """Generate mock Revenue 4A Excel file."""
    excel_path = DEMO_DIR / "IH_4A_Bill_TR-01_ Revenue Leakage - April to Mar 26 (demo).xlsx"
    print(f"Generating {excel_path}...")
    
    # 1. Summary_Final Sheet
    services = [
        "Bed Charges", "ICU Charges", "Nursing Charges", 
        "Consultation Fees", "Pharmacy Charges"
    ]
    df_summary = pd.DataFrame({
        "Service Name": services,
        "Total Daily Leakage": [150000.0, 350000.0, 45000.0, 95000.0, 180000.0]
    })
    
    # 2. Billing staff leakage Sheet
    # Needs columns: Date, Staff Name (or duty/emp), Bed (or ward), Total Leakage (or amount), and Gap columns
    dates = pd.date_range(start="2025-01-01", end="2026-03-31", freq="W-WED").strftime("%Y-%m-%d").tolist()
    staff_members = ["Staff A", "Staff B", "Staff C", "Staff D"]
    wards = ["2F MICU", "WARD 3RD FLOOR", "FOURTH FLOOR", "ECONOMY - 4BED"]
    
    rows = []
    for i, date in enumerate(dates):
        staff = staff_members[i % len(staff_members)]
        ward = wards[i % len(wards)]
        # Add random gaps
        gap1 = 1500.0 if i % 2 == 0 else 0.0
        gap2 = 5000.0 if i % 3 == 0 else 0.0
        gap3 = 500.0 if i % 4 == 0 else 0.0
        gap4 = 800.0 if i % 5 == 0 else 0.0
        gap5 = 1200.0 if i % 6 == 0 else 0.0
        
        total_leakage = gap1 + gap2 + gap3 + gap4 + gap5
        if total_leakage == 0:
            total_leakage = 1000.0
            gap1 = 1000.0
            
        rows.append({
            "Date": date,
            "Staff Name": staff,
            "Bed": ward,
            "Total Leakage": total_leakage,
            "Gap 1 (Bed Charges)": gap1,
            "Gap 2 (ICU Charges)": gap2,
            "Gap 3 (Nursing Charges)": gap3,
            "Gap 4 (Consultation Fees)": gap4,
            "Gap 5 (Pharmacy Charges)": gap5
        })
        
    df_staff = pd.DataFrame(rows)
    
    # Write to Excel
    with pd.ExcelWriter(str(excel_path)) as writer:
        df_summary.to_excel(writer, sheet_name="Summary_Final", index=False)
        # Create empty rows to simulate non-zero header starting index (ingest.py searches for 'staff'/'duty')
        # We can write with header at row index 1
        df_empty_header = pd.DataFrame([[""] * len(df_staff.columns)], columns=df_staff.columns)
        df_empty_header.to_excel(writer, sheet_name="Billing staff leakage", index=False, startrow=0)
        df_staff.to_excel(writer, sheet_name="Billing staff leakage", index=False, startrow=1)

def generate_revenue_4a_csvs():
    """Generate mock CSV files for specific months."""
    months = [("May 2025", 5, 2025), ("Dec 2025", 12, 2025)]
    
    for label, month, year in months:
        csv_path = DEMO_DIR / f"Billing Audit - {label}.csv"
        print(f"Generating {csv_path}...")
        
        # Ingest.py parses CSV:
        # Row 1 (index 1) has days: e.g. column 4 is "1/May", col 5 is "2/May", etc.
        # Row 5 to 23 are services. Column 3 is service_name.
        # Row 42 to 61 are staff/locations. Col 0 is ward, Col 1 is staff, Col 2 is station, Col 3 is resp_col_val.
        
        # Build raw grid (e.g. 70 rows x 40 columns)
        grid = [["" for _ in range(40)] for _ in range(70)]
        
        # Day columns (say columns 4 to 34 represent days 1 to 31)
        grid[1][3] = "Service / Day"
        for day in range(1, 32):
            grid[1][3 + day] = f"{day}/{label[:3]}"
            
        # Services (rows 5 to 23)
        services = [
            "Bed Charges", "ICU Charges", "Nursing Charges", 
            "Consultation Fees", "Pharmacy Charges", "Lab Fees", "Radiology Fees"
        ]
        for idx, srv in enumerate(services):
            row_idx = 5 + idx
            grid[row_idx][3] = srv
            # Fill some leakage values
            for day in range(1, 32):
                if (day + idx) % 5 == 0:
                    grid[row_idx][3 + day] = str(1000 + (day * 100))
                    
        # Staff/Locations (rows 42 to 61)
        wards = ["2F CCU", "3F PED WARD", "FOURTH FLOOR", "DAY CARE"]
        staff = ["Staff A", "Staff B", "Staff C", "Staff D"]
        stations = ["CCU Station", "Ped Station", "Ward 4 Station", "DayCare Station"]
        
        for idx in range(10):
            row_idx = 42 + idx
            w = wards[idx % len(wards)]
            s = staff[idx % len(staff)]
            st = stations[idx % len(stations)]
            grid[row_idx][0] = w
            grid[row_idx][1] = s
            grid[row_idx][2] = st
            grid[row_idx][3] = "Assigned"
            
            # Fill staff leakage values
            for day in range(1, 32):
                if (day + idx) % 4 == 0:
                    grid[row_idx][3 + day] = str(500 + (day * 50))
                    
        df = pd.DataFrame(grid)
        df.to_csv(str(csv_path), header=False, index=False)

def generate_surgery_audit_excel():
    """Generate mock Surgery Audit Excel files (4B and 4D)."""
    files = [
        "IH_4B_Bill_02_Surgery Audit - April to Mar 26 (demo).xlsx",
        "IH_4D_Bill_03_Surgery Audit - April To  Dec 24 (demo).xlsx"
    ]
    
    procedures = [
        ("CABG", "Angioplasty", 120000.0, "Cardiology"),
        ("Total Knee Replacement", "Knee Arthroscopy", 85000.0, "Orthopedics"),
        ("Craniotomy", "Diagnostic CT Brain", 150000.0, "Neurology"),
        ("Laparoscopic Cholecystectomy", "Diagnostic Laparoscopy", 35000.0, "General Surgery"),
        ("Angioplasty with Stent", "Diagnostic Angiogram", 60000.0, "Cardiology"),
        ("Total Hip Replacement", "Hip X-ray", 95000.0, "Orthopedics")
    ]
    
    surgeons = ["Dr. Ramesh", "Dr. Suresh", "Dr. Priya", "Dr. Anita"]
    dates = pd.date_range(start="2025-01-01", end="2026-03-31", freq="W-MON").strftime("%Y-%m-%d").tolist()
    
    for filename in files:
        excel_path = DEMO_DIR / filename
        print(f"Generating {excel_path}...")
        
        rows = []
        for i, date in enumerate(dates):
            proc_actual, proc_billed, diff_amt, spec = procedures[i % len(procedures)]
            surgeon = surgeons[i % len(surgeons)]
            patient_id = f"MRD{10000 + i}"
            
            rows.append({
                "Date": date,
                "Patient MRD ID": patient_id,
                "Actual Surgery Procedure": proc_actual,
                "Billed HIS Procedure": proc_billed,
                "Primary Surgeon": surgeon,
                "Medical Speciality": spec,
                "Difference Amount": diff_amt
            })
            
        df = pd.DataFrame(rows)
        with pd.ExcelWriter(str(excel_path)) as writer:
            df.to_excel(writer, sheet_name="Procedure detail", index=False)

def run_ingest_and_optimize():
    """Run ingestion on the generated demo files to build db/hospital_demo.db."""
    print("Copying demo files to data/raw for ingestion...")
    for item in os.listdir(str(DEMO_DIR)):
        shutil.copy(str(DEMO_DIR / item), str(RAW_DIR / item))
        
    # We will temporarily override DB_PATH in ingest.py to write to db/hospital_demo.db
    demo_db_path = str(DB_DIR / "hospital_demo.db")
    if os.path.exists(demo_db_path):
        os.remove(demo_db_path)
        
    print("Importing and running ingestion pipeline...")
    sys.path.append(str(BACKEND_DIR))
    import ingest
    
    # Save original DB_PATH
    orig_db_path = ingest.DB_PATH
    # Override
    ingest.DB_PATH = demo_db_path
    
    # Execute ingestion steps
    conn = ingest.init_db()
    ingest.ingest_soc(conn)
    ingest.ingest_4a(conn)
    ingest.ingest_4b_4d(conn)
    ingest.ingest_locations(conn)
    conn.close()
    
    # Restore DB_PATH
    ingest.DB_PATH = orig_db_path
    print("Ingestion completed successfully for hospital_demo.db.")
    
    # Add indexes to db/hospital_demo.db using migrations script
    print("Running optimization migrations on hospital_demo.db...")
    from migrations import add_indexes
    success = add_indexes.run_migration(demo_db_path, dry_run=False)
    if success:
        print("Optimization index migrations completed successfully on hospital_demo.db.")
    else:
        print("Migration failed, check logs.")

def main():
    print("--- STARTING DEMO DATASET GENERATION ---")
    create_directories()
    generate_ward_list()
    generate_soc_pdf()
    generate_revenue_4a_excel()
    generate_revenue_4a_csvs()
    generate_surgery_audit_excel()
    run_ingest_and_optimize()
    print("--- DEMO DATASET GENERATION COMPLETED ---")

if __name__ == "__main__":
    main()
