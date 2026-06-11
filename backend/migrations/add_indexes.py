#!/usr/bin/env python3
"""
SQLite Query Optimization Migration Script
Adds indexes to revenue_4a and audit_4b_4d tables to optimize query speeds for large datasets (100k+ rows).
Can be run as a standalone script.
"""

import os
import sys
import sqlite3
import argparse
import logging
from pathlib import Path

# Configure elegant logging format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("migration")

# Constants
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = str(BASE_DIR / "db" / "hospital.db")

# Definitions of indexes to add
INDEXES_TO_CREATE = [
    # Table: revenue_4a
    {
        "table": "revenue_4a",
        "name": "idx_revenue_date",
        "columns": "date",
        "description": "Index on date for temporal filtering"
    },
    {
        "table": "revenue_4a",
        "name": "idx_revenue_location",
        "columns": "location",
        "description": "Index on location for department-wise leakage analysis"
    },
    {
        "table": "revenue_4a",
        "name": "idx_revenue_staff_name",
        "columns": "staff_name",
        "description": "Index on staff name to optimize staff leakage queries"
    },
    {
        "table": "revenue_4a",
        "name": "idx_revenue_service_name",
        "columns": "service_name",
        "description": "Index on service name to speed up missed services analysis"
    },
    {
        "table": "revenue_4a",
        "name": "idx_revenue_leakage_amount",
        "columns": "leakage_amount",
        "description": "Index on leakage amount for filtering unbilled/missed cases"
    },
    {
        "table": "revenue_4a",
        "name": "idx_revenue_date_location",
        "columns": "date, location",
        "description": "Composite index on (date, location) to optimize combined filters"
    },
    # Table: audit_4b_4d
    {
        "table": "audit_4b_4d",
        "name": "idx_audit_date",
        "columns": "date",
        "description": "Index on date for temporal audit queries"
    },
    {
        "table": "audit_4b_4d",
        "name": "idx_audit_surgeon",
        "columns": "surgeon",
        "description": "Index on surgeon to quickly filter worst-offending doctors"
    },
    {
        "table": "audit_4b_4d",
        "name": "idx_audit_speciality",
        "columns": "speciality",
        "description": "Index on speciality for department/speciality-wide audits"
    },
    {
        "table": "audit_4b_4d",
        "name": "idx_audit_difference_amount",
        "columns": "difference_amount",
        "description": "Index on difference amount to quickly isolate billing discrepancies"
    }
]

def find_db_path() -> str:
    """Finds the database path using absolute path fallback and relative paths."""
    # 1. Check if the default path exists
    if os.path.exists(DEFAULT_DB_PATH):
        return DEFAULT_DB_PATH
        
    # 2. Check relative to the script: ../../db/hospital.db
    script_dir = os.path.dirname(os.path.abspath(__file__))
    relative_path = os.path.abspath(os.path.join(script_dir, "..", "..", "db", "hospital.db"))
    if os.path.exists(relative_path):
        return relative_path

    # 3. Check current working directory relative path: db/hospital.db
    cwd_path = os.path.abspath(os.path.join(os.getcwd(), "db", "hospital.db"))
    if os.path.exists(cwd_path):
        return cwd_path

    # 4. Check sub-directory cwd path: RevenueLeakageProject/db/hospital.db
    sub_cwd_path = os.path.abspath(os.path.join(os.getcwd(), "RevenueLeakageProject", "db", "hospital.db"))
    if os.path.exists(sub_cwd_path):
        return sub_cwd_path

    # Fallback to the default path
    return DEFAULT_DB_PATH

def check_table_exists(cursor: sqlite3.Cursor, table_name: str) -> bool:
    """Checks if a given table exists in the database."""
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    return cursor.fetchone() is not None

def check_index_exists(cursor: sqlite3.Cursor, index_name: str) -> bool:
    """Checks if a given index exists in the database."""
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
        (index_name,)
    )
    return cursor.fetchone() is not None

def run_migration(db_path: str, dry_run: bool = False) -> bool:
    """Runs the database migrations to add indexes."""
    logger.info(f"Connecting to database at: {db_path}")
    
    if not os.path.exists(db_path):
        logger.error(f"Database file not found at: {db_path}")
        logger.error("Please run the ingestion script first or specify the correct DB path using --db-path.")
        return False

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
    except sqlite3.Error as e:
        logger.critical(f"Failed to connect to database: {e}")
        return False

    success = True
    created_count = 0
    skipped_count = 0
    failed_count = 0

    try:
        for idx in INDEXES_TO_CREATE:
            table = idx["table"]
            name = idx["name"]
            cols = idx["columns"]
            desc = idx["description"]

            # 1. Verify table exists
            if not check_table_exists(cursor, table):
                logger.warning(f"Table '{table}' does not exist. Skipping index '{name}'.")
                failed_count += 1
                continue

            # 2. Check if index already exists (Error Handling)
            if check_index_exists(cursor, name):
                logger.info(f"[-] Index '{name}' already exists on '{table}({cols})'. Skipping. ({desc})")
                skipped_count += 1
                continue

            # 3. Create index
            sql = f"CREATE INDEX {name} ON {table} ({cols})"
            logger.info(f"[+] Creating index '{name}' on '{table}({cols})'...")
            logger.debug(f"SQL: {sql}")
            
            if not dry_run:
                try:
                    cursor.execute(sql)
                    logger.info(f"    -> Successfully created index '{name}'. ({desc})")
                    created_count += 1
                except sqlite3.Error as e:
                    logger.error(f"    -> Error creating index '{name}': {e}")
                    failed_count += 1
                    success = False
            else:
                logger.info(f"    -> [DRY RUN] Would create index '{name}'. ({desc})")
                created_count += 1

        if not dry_run:
            conn.commit()
            logger.info("Migration transaction committed successfully.")

    except Exception as e:
        logger.exception(f"An unexpected error occurred during migration: {e}")
        if not dry_run:
            conn.rollback()
            logger.warning("Migration transaction rolled back.")
        success = False
    finally:
        conn.close()

    # Log summary
    logger.info("=" * 60)
    logger.info("MIGRATION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total Indexes Planned : {len(INDEXES_TO_CREATE)}")
    logger.info(f"Created/Pending       : {created_count}")
    logger.info(f"Skipped (Already Exists): {skipped_count}")
    logger.info(f"Failed/Skipped (Table): {failed_count}")
    logger.info("=" * 60)
    
    return success

def main():
    parser = argparse.ArgumentParser(description="Standalone SQLite Index Migration Tool for Revenue Leakage Project")
    parser.add_argument(
        "--db-path",
        type=str,
        help="Custom path to the SQLite database file (hospital.db)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what indexes would be created without making actual database changes"
    )
    
    args = parser.parse_args()
    
    # Resolve DB Path
    db_path = args.db_path or find_db_path()
    db_path = os.path.abspath(db_path)

    logger.info("Starting SQLite Optimization Migration...")
    
    if args.dry_run:
        logger.info("NOTE: Running in DRY-RUN mode. No changes will be applied.")

    success = run_migration(db_path, dry_run=args.dry_run)
    
    if success:
        logger.info("SQLite Optimization Migration completed successfully.")
        sys.exit(0)
    else:
        logger.error("SQLite Optimization Migration completed with errors.")
        sys.exit(1)

if __name__ == "__main__":
    main()
