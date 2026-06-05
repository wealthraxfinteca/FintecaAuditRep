import sqlite3
import pandas as pd
from datetime import datetime
import re

DB_PATH = "data/reconciliation.db"

TABLES = [
    "purchases", "sales", "banking", "collections",
    "sales_returns", "swap_deals", "inventory"
]

TABLE_DISPLAY = {
    "purchases":    "🛒 Purchases",
    "sales":        "💰 Sales",
    "banking":      "🏦 Banking",
    "collections":  "💵 Collections",
    "sales_returns":"↩️ Sales Returns",
    "swap_deals":   "🔄 Swap Deals",
    "inventory":    "📦 Inventory",
}

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def get_table_cols(table):
    conn   = get_conn()
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cursor.fetchall()]
    conn.close()
    return cols

def read_table(table, date_from=None, date_to=None,
               search=None, limit=500):
    """Read records with optional date and search filters"""
    conn  = get_conn()
    query = f"SELECT * FROM {table} WHERE 1=1"
    params = []

    if date_from:
        query += " AND date >= ?"
        params.append(str(date_from))
    if date_to:
        query += " AND date <= ?"
        params.append(str(date_to))
    if search:
        cols = get_table_cols(table)
        text_cols = [
            c for c in cols
            if c not in ["id","uploaded_at","last_updated"]
        ]
        search_clauses = " OR ".join(
            f"CAST({c} AS TEXT) LIKE ?" for c in text_cols
        )
        query  += f" AND ({search_clauses})"
        params += [f"%{search}%"] * len(text_cols)

    query += f" ORDER BY date DESC, id DESC LIMIT {limit}"
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df

def read_record(table, record_id):
    """Read single record by ID"""
    conn = get_conn()
    df   = pd.read_sql(
        f"SELECT * FROM {table} WHERE id = ?",
        conn, params=[record_id]
    )
    conn.close()
    return df.iloc[0].to_dict() if not df.empty else {}

def update_record(table, record_id, updates: dict):
    """Update a single record"""
    try:
        conn       = get_conn()
        valid_cols = get_table_cols(table)
        clean_updates = {
            k: v for k, v in updates.items()
            if k in valid_cols and k != "id"
        }
        if not clean_updates:
            return {"success": False, "error": "No valid columns to update"}

        set_clause = ", ".join(f"{k} = ?" for k in clean_updates)
        values     = list(clean_updates.values()) + [record_id]
        conn.execute(
            f"UPDATE {table} SET {set_clause} WHERE id = ?",
            values
        )
        conn.commit()
        conn.close()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

def delete_record(table, record_id):
    """Delete a single record"""
    try:
        conn = get_conn()
        conn.execute(f"DELETE FROM {table} WHERE id = ?", [record_id])
        conn.commit()
        conn.close()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

def delete_multiple(table, record_ids: list):
    """Delete multiple records"""
    try:
        conn        = get_conn()
        placeholders = ",".join("?" * len(record_ids))
        conn.execute(
            f"DELETE FROM {table} WHERE id IN ({placeholders})",
            record_ids
        )
        conn.commit()
        conn.close()
        return {"success": True, "deleted": len(record_ids)}
    except Exception as e:
        return {"success": False, "error": str(e)}

def insert_record(table, data: dict):
    """Insert a new record"""
    try:
        conn       = get_conn()
        valid_cols = get_table_cols(table)
        clean_data = {
            k: v for k, v in data.items()
            if k in valid_cols and k != "id"
        }
        clean_data["uploaded_at"] = datetime.now().isoformat()
        cols   = ", ".join(clean_data.keys())
        marks  = ", ".join("?" * len(clean_data))
        values = list(clean_data.values())
        conn.execute(
            f"INSERT INTO {table} ({cols}) VALUES ({marks})",
            values
        )
        conn.commit()
        conn.close()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

def move_record(from_table, record_id, to_table):
    """Move a record from one table to another"""
    try:
        # Read the record
        record = read_record(from_table, record_id)
        if not record:
            return {"success": False, "error": "Record not found"}

        # Get valid columns in target table
        target_cols = get_table_cols(to_table)
        filtered    = {
            k: v for k, v in record.items()
            if k in target_cols and k != "id"
        }
        filtered["document_source"] = (
            f"moved_from_{from_table}_{record_id}"
        )

        # Insert into target table
        res = insert_record(to_table, filtered)
        if not res["success"]:
            return res

        # Delete from source table
        del_res = delete_record(from_table, record_id)
        if not del_res["success"]:
            return del_res

        return {
            "success": True,
            "message": (
                f"Record {record_id} moved from "
                f"{from_table} to {to_table}"
            )
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def move_multiple(from_table, record_ids, to_table):
    """Move multiple records"""
    results = []
    for rid in record_ids:
        res = move_record(from_table, rid, to_table)
        results.append(res)
    success_count = sum(1 for r in results if r["success"])
    return {
        "success": success_count > 0,
        "moved": success_count,
        "failed": len(record_ids) - success_count
    }

def duplicate_record(table, record_id):
    """Duplicate a record"""
    try:
        record = read_record(table, record_id)
        if not record:
            return {"success": False, "error": "Record not found"}
        record.pop("id", None)
        record["document_source"] = (
            f"duplicate_of_{record_id}"
        )
        return insert_record(table, record)
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_table_summary(table):
    """Get summary stats for a table"""
    conn = get_conn()
    try:
        df = pd.read_sql(f"SELECT * FROM {table}", conn)
        conn.close()
        if df.empty:
            return {"count": 0}

        summary = {"count": len(df)}

        # Find amount column
        for col in ["net_amount","total_cost","amount",
                    "credit","return_amount","difference_amount"]:
            if col in df.columns:
                vals = pd.to_numeric(df[col], errors="coerce")
                summary["total_amount"] = vals.sum()
                summary["amount_col"]   = col
                break

        # Date range
        if "date" in df.columns:
            dates = pd.to_datetime(df["date"], errors="coerce").dropna()
            if not dates.empty:
                summary["date_from"] = str(dates.min().date())
                summary["date_to"]   = str(dates.max().date())

        return summary
    except Exception as e:
        return {"count": 0, "error": str(e)}
