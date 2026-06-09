#!/usr/bin/env python3
"""
clear_cloud_data.py
Run this on Streamlit Cloud to wipe all data.
Add to main_app.py startup OR run as one-time script.
"""
import sqlite3
import os

DB_PATH = "data/reconciliation.db"

def purge_all():
    if not os.path.exists(DB_PATH):
        print(f"❌ DB not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in cur.fetchall()]

    print(f"Found {len(tables)} tables")
    total_deleted = 0

    for t in tables:
        try:
            cur.execute(f"DELETE FROM '{t}'")
            n = cur.rowcount
            total_deleted += max(n, 0)
            try:
                cur.execute("DELETE FROM sqlite_sequence WHERE name=?", (t,))
            except:
                pass
            print(f"  ✅ {t}: {n} rows deleted")
        except Exception as e:
            print(f"  ❌ {t}: {e}")

    conn.commit()
    conn.close()
    print(f"\n✅ Total deleted: {total_deleted} rows")

if __name__ == "__main__":
    purge_all()
