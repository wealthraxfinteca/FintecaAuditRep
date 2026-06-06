"""
Finteca AuditRep — Database Helper
Works on both local machine and Streamlit Cloud
"""
import os
import sqlite3
from pathlib import Path

def get_db_path() -> str:
    """Return correct database path for environment"""
    if os.path.exists("/mount/src"):
        # Streamlit Cloud — use /tmp (writable)
        return "/tmp/reconciliation.db"
    else:
        # Local — use data/ folder
        Path("data").mkdir(exist_ok=True)
        return "data/reconciliation.db"

DB_PATH = get_db_path()

def get_conn():
    """Get database connection"""
    return sqlite3.connect(DB_PATH, check_same_thread=False)
