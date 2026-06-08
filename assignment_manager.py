"""
Finteca AuditRep — Assignment/Job Manager
Each assignment has its own isolated database and files
"""
import os
import sqlite3
import shutil
import json
from pathlib import Path
from datetime import datetime

# ── Base paths ────────────────────────────────────────────
if os.path.exists("/mount/src"):
    BASE_DIR = Path("/tmp/finteca_assignments")
else:
    BASE_DIR = Path("assignments")

BASE_DIR.mkdir(exist_ok=True)

ASSIGNMENTS_INDEX = BASE_DIR / "assignments_index.json"

# ── Assignment Index ──────────────────────────────────────
def load_index() -> dict:
    """Load all assignments from index file"""
    if ASSIGNMENTS_INDEX.exists():
        try:
            return json.loads(ASSIGNMENTS_INDEX.read_text())
        except Exception:
            return {}
    return {}

def save_index(index: dict):
    """Save assignments index"""
    ASSIGNMENTS_INDEX.write_text(json.dumps(index, indent=2))

def get_assignment_path(assignment_id: str) -> Path:
    """Get the folder path for an assignment"""
    path = BASE_DIR / assignment_id
    path.mkdir(exist_ok=True)
    (path / "uploads").mkdir(exist_ok=True)
    (path / "reports").mkdir(exist_ok=True)
    return path

def get_assignment_db(assignment_id: str) -> str:
    """Get the database path for an assignment"""
    path = get_assignment_path(assignment_id)
    return str(path / "reconciliation.db")

# ── Assignment CRUD ───────────────────────────────────────
def create_assignment(
    name: str,
    client: str,
    description: str,
    assignment_type: str,
    period_from: str,
    period_to: str,
    created_by: str
) -> dict:
    """Create a new assignment/job"""
    try:
        index = load_index()

        # Generate unique ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(
            c if c.isalnum() else "_"
            for c in name.lower()
        )[:20]
        assignment_id = f"{safe_name}_{timestamp}"

        # Create folder structure
        path = get_assignment_path(assignment_id)

        # Initialize database
        db_path = get_assignment_db(assignment_id)
        init_assignment_db(db_path)

        # Save to index
        index[assignment_id] = {
            "id":              assignment_id,
            "name":            name,
            "client":          client,
            "description":     description,
            "type":            assignment_type,
            "period_from":     period_from,
            "period_to":       period_to,
            "created_by":      created_by,
            "created_at":      datetime.now().isoformat(),
            "updated_at":      datetime.now().isoformat(),
            "status":          "active",
            "path":            str(path),
            "db_path":         db_path,
        }
        save_index(index)

        return {"success": True, "id": assignment_id,
                "assignment": index[assignment_id]}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_assignment(assignment_id: str) -> dict:
    """Get assignment details"""
    index = load_index()
    return index.get(assignment_id, {})

def update_assignment(assignment_id: str, updates: dict) -> dict:
    """Update assignment details"""
    try:
        index = load_index()
        if assignment_id not in index:
            return {"success": False, "error": "Assignment not found"}
        index[assignment_id].update(updates)
        index[assignment_id]["updated_at"] = datetime.now().isoformat()
        save_index(index)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

def delete_assignment(assignment_id: str) -> dict:
    """Permanently delete an assignment and all its data"""
    try:
        index = load_index()
        if assignment_id not in index:
            return {"success": False, "error": "Assignment not found"}

        # Delete folder and all files
        path = get_assignment_path(assignment_id)
        if path.exists():
            shutil.rmtree(str(path))

        # Remove from index
        del index[assignment_id]
        save_index(index)

        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

def list_assignments(status: str = None) -> list:
    """List all assignments, optionally filtered by status"""
    index = load_index()
    assignments = list(index.values())
    if status:
        assignments = [a for a in assignments if a.get("status") == status]
    return sorted(assignments, key=lambda x: x.get("created_at",""), reverse=True)

def archive_assignment(assignment_id: str) -> dict:
    """Archive an assignment (keep data, mark inactive)"""
    return update_assignment(assignment_id, {"status": "archived"})

# ── Database Initialization ───────────────────────────────
def init_assignment_db(db_path: str):
    """Initialize a fresh database for an assignment"""
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, reference_number TEXT, supplier TEXT,
            item_description TEXT, quantity REAL DEFAULT 0,
            unit_cost REAL DEFAULT 0, total_cost REAL DEFAULT 0,
            discount REAL DEFAULT 0, tax REAL DEFAULT 0,
            net_amount REAL DEFAULT 0, payment_method TEXT,
            payment_reference TEXT,
            payment_status TEXT DEFAULT 'unpaid',
            notes TEXT, document_source TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, invoice_number TEXT, customer TEXT,
            item_description TEXT, quantity REAL DEFAULT 0,
            unit_price REAL DEFAULT 0, unit_cost REAL DEFAULT 0,
            gross_amount REAL DEFAULT 0, discount REAL DEFAULT 0,
            tax REAL DEFAULT 0, net_amount REAL DEFAULT 0,
            cost_of_goods REAL DEFAULT 0,
            gross_profit REAL DEFAULT 0,
            payment_method TEXT, payment_reference TEXT,
            salesperson TEXT,
            payment_status TEXT DEFAULT 'unpaid',
            notes TEXT, document_source TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS banking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, value_date TEXT, description TEXT,
            reference TEXT, debit REAL DEFAULT 0,
            credit REAL DEFAULT 0, balance REAL DEFAULT 0,
            transaction_type TEXT, category TEXT,
            matched_to TEXT,
            match_status TEXT DEFAULT 'unmatched',
            document_source TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS collections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, customer TEXT, invoice_reference TEXT,
            amount REAL DEFAULT 0, payment_method TEXT,
            received_by TEXT, bank_deposit_date TEXT,
            bank_deposit_ref TEXT, bank_account TEXT,
            reconciled INTEGER DEFAULT 0,
            reconcile_variance REAL DEFAULT 0,
            notes TEXT, document_source TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS sales_returns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, return_reference TEXT,
            original_invoice TEXT, customer TEXT,
            item_description TEXT,
            quantity_returned REAL DEFAULT 0,
            unit_price REAL DEFAULT 0,
            return_amount REAL DEFAULT 0,
            reason TEXT, condition TEXT, approved_by TEXT,
            restocked INTEGER DEFAULT 0,
            credit_issued INTEGER DEFAULT 0,
            refund_method TEXT, notes TEXT,
            document_source TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS swap_deals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, deal_reference TEXT, customer TEXT,
            item_given_out TEXT, qty_given_out REAL DEFAULT 0,
            price_given_out REAL DEFAULT 0,
            value_given_out REAL DEFAULT 0,
            item_received TEXT, qty_received REAL DEFAULT 0,
            assessed_value_received REAL DEFAULT 0,
            difference_amount REAL DEFAULT 0,
            customer_paid REAL DEFAULT 0,
            payment_method TEXT, payment_reference TEXT,
            approved_by TEXT, notes TEXT,
            document_source TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_code TEXT, description TEXT, category TEXT,
            unit_of_measure TEXT, unit_cost REAL DEFAULT 0,
            selling_price REAL DEFAULT 0,
            opening_qty REAL DEFAULT 0,
            opening_value REAL DEFAULT 0,
            purchases_qty REAL DEFAULT 0,
            purchases_value REAL DEFAULT 0,
            sales_qty REAL DEFAULT 0,
            sales_value REAL DEFAULT 0,
            returns_in_qty REAL DEFAULT 0,
            swap_out_qty REAL DEFAULT 0,
            swap_in_qty REAL DEFAULT 0,
            closing_qty REAL DEFAULT 0,
            closing_value REAL DEFAULT 0,
            physical_count REAL,
            variance_qty REAL DEFAULT 0,
            variance_value REAL DEFAULT 0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL, category TEXT NOT NULL,
            subcategory TEXT, description TEXT,
            amount REAL DEFAULT 0, vat REAL DEFAULT 0,
            total_amount REAL DEFAULT 0, payment_method TEXT,
            payment_reference TEXT, payee TEXT,
            approved_by TEXT, receipt_number TEXT,
            is_recurring INTEGER DEFAULT 0,
            notes TEXT, document_source TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS purchase_returns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL, return_reference TEXT,
            original_po_number TEXT, supplier TEXT NOT NULL,
            item_description TEXT,
            quantity_returned REAL DEFAULT 0,
            unit_cost REAL DEFAULT 0,
            return_amount REAL DEFAULT 0,
            reason TEXT, condition TEXT,
            debit_note_number TEXT,
            credit_received INTEGER DEFAULT 0,
            credit_amount REAL DEFAULT 0,
            restocked INTEGER DEFAULT 0,
            approved_by TEXT, notes TEXT,
            document_source TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS upload_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT, file_type TEXT,
            document_type TEXT,
            rows_extracted INTEGER, rows_saved INTEGER,
            status TEXT, file_path TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()

# ── File Management ───────────────────────────────────────
def list_uploaded_files(assignment_id: str) -> list:
    """List all uploaded files for an assignment"""
    try:
        db_path = get_assignment_db(assignment_id)
        conn    = sqlite3.connect(db_path)
        import pandas as pd
        df = pd.read_sql(
            "SELECT * FROM upload_log ORDER BY uploaded_at DESC",
            conn
        )
        conn.close()
        return df.to_dict("records") if not df.empty else []
    except Exception:
        return []

def delete_uploaded_file_data(
    assignment_id: str,
    filename: str,
    tables: list = None
) -> dict:
    """Delete all data from a specific uploaded file"""
    try:
        db_path = get_assignment_db(assignment_id)
        conn    = sqlite3.connect(db_path)
        if tables is None:
            tables = [
                "purchases","sales","banking","collections",
                "sales_returns","swap_deals","inventory",
                "expenses","purchase_returns"
            ]
        total_deleted = 0
        for table in tables:
            try:
                cursor = conn.execute(
                    f"DELETE FROM {table} "
                    f"WHERE document_source=?",
                    (filename,)
                )
                total_deleted += cursor.rowcount
            except Exception:
                pass
        conn.execute(
            "DELETE FROM upload_log WHERE filename=?",
            (filename,)
        )
        conn.commit()
        conn.close()
        return {"success": True, "rows_deleted": total_deleted}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_assignment_stats(assignment_id: str) -> dict:
    """Get statistics for an assignment"""
    try:
        db_path = get_assignment_db(assignment_id)
        conn    = sqlite3.connect(db_path)
        tables  = [
            "purchases","sales","banking","collections",
            "sales_returns","swap_deals","inventory",
            "expenses","purchase_returns"
        ]
        stats = {}
        for table in tables:
            try:
                cursor = conn.execute(
                    f"SELECT COUNT(*) FROM {table}"
                )
                stats[table] = cursor.fetchone()[0]
            except Exception:
                stats[table] = 0
        conn.close()
        return stats
    except Exception:
        return {}
