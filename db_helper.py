"""
Finteca AuditRep — Database Helper
Complete schema with all financial modules
"""
import os
import sqlite3
from pathlib import Path

def get_db_path() -> str:
    if os.path.exists("/mount/src"):
        return "/tmp/reconciliation.db"
    else:
        Path("data").mkdir(exist_ok=True)
        return "data/reconciliation.db"

DB_PATH = get_db_path()

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_conn()
    conn.executescript("""

    -- ── PURCHASES ─────────────────────────────────────────
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

    -- ── PURCHASE RETURNS ──────────────────────────────────
    CREATE TABLE IF NOT EXISTS purchase_returns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        return_reference TEXT,
        original_purchase_ref TEXT,
        supplier TEXT,
        item_description TEXT,
        quantity_returned REAL DEFAULT 0,
        unit_cost REAL DEFAULT 0,
        return_amount REAL DEFAULT 0,
        reason TEXT,
        condition TEXT,
        approved_by TEXT,
        credit_received INTEGER DEFAULT 0,
        refund_method TEXT,
        notes TEXT,
        document_source TEXT,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- ── SALES ─────────────────────────────────────────────
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

    -- ── SALES RETURNS ─────────────────────────────────────
    CREATE TABLE IF NOT EXISTS sales_returns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT, return_reference TEXT,
        original_invoice TEXT, customer TEXT,
        item_description TEXT,
        quantity_returned REAL DEFAULT 0,
        unit_price REAL DEFAULT 0,
        unit_cost REAL DEFAULT 0,
        return_amount REAL DEFAULT 0,
        cogs_reversal REAL DEFAULT 0,
        reason TEXT, condition TEXT, approved_by TEXT,
        restocked INTEGER DEFAULT 0,
        credit_issued INTEGER DEFAULT 0,
        refund_method TEXT, notes TEXT,
        document_source TEXT,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- ── BANKING ───────────────────────────────────────────
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

    -- ── COLLECTIONS ───────────────────────────────────────
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

    -- ── EXPENSES ──────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        reference TEXT,
        category TEXT,
        sub_category TEXT,
        description TEXT,
        amount REAL DEFAULT 0,
        tax REAL DEFAULT 0,
        net_amount REAL DEFAULT 0,
        payment_method TEXT,
        payment_reference TEXT,
        paid_to TEXT,
        approved_by TEXT,
        expense_type TEXT DEFAULT 'operating',
        notes TEXT,
        document_source TEXT,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- ── INVENTORY ─────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_code TEXT UNIQUE,
        description TEXT,
        category TEXT,
        unit_of_measure TEXT,
        unit_cost REAL DEFAULT 0,
        selling_price REAL DEFAULT 0,
        opening_qty REAL DEFAULT 0,
        opening_value REAL DEFAULT 0,
        purchases_qty REAL DEFAULT 0,
        purchases_value REAL DEFAULT 0,
        purchase_returns_qty REAL DEFAULT 0,
        purchase_returns_value REAL DEFAULT 0,
        sales_qty REAL DEFAULT 0,
        sales_value REAL DEFAULT 0,
        sales_returns_qty REAL DEFAULT 0,
        sales_returns_value REAL DEFAULT 0,
        swap_out_qty REAL DEFAULT 0,
        swap_in_qty REAL DEFAULT 0,
        adjustments_qty REAL DEFAULT 0,
        closing_qty REAL DEFAULT 0,
        closing_value REAL DEFAULT 0,
        physical_count REAL,
        variance_qty REAL DEFAULT 0,
        variance_value REAL DEFAULT 0,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- ── SWAP DEALS ────────────────────────────────────────
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

    -- ── UPLOAD LOG ────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS upload_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT, file_type TEXT,
        document_type TEXT,
        rows_extracted INTEGER, rows_saved INTEGER,
        status TEXT,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    """)
    conn.commit()
    conn.close()

# Expense categories
EXPENSE_CATEGORIES = {
    "Cost of Sales": [
        "Direct Labour",
        "Factory Overhead",
        "Freight Inward",
        "Packaging",
        "Other Cost of Sales",
    ],
    "Administrative": [
        "Salaries & Wages",
        "Rent & Rates",
        "Utilities",
        "Office Supplies",
        "Telephone & Internet",
        "Insurance",
        "Depreciation",
        "Repairs & Maintenance",
        "Professional Fees",
        "Audit & Accounting",
        "Legal Fees",
        "Other Admin",
    ],
    "Selling & Distribution": [
        "Advertising & Marketing",
        "Sales Commission",
        "Delivery & Freight Out",
        "Trade Shows",
        "Customer Entertainment",
        "Other Selling",
    ],
    "Finance Costs": [
        "Bank Charges",
        "Interest Expense",
        "Loan Charges",
        "Foreign Exchange Loss",
        "Other Finance",
    ],
    "Other Expenses": [
        "Donations",
        "Fines & Penalties",
        "Miscellaneous",
        "Other",
    ],
}
