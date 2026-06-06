import streamlit as st
import sqlite3
import pandas as pd
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Database path — Cloud + Local compatible ──────────────
if os.path.exists("/mount/src"):
    DB_PATH = "/tmp/reconciliation.db"
else:
    Path("data").mkdir(exist_ok=True)
    DB_PATH = "data/reconciliation.db"

st.set_page_config(
    page_title="Finteca AuditRep",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

CSS = """
<style>
.finteca-header {
    background: linear-gradient(135deg, #1a237e 0%, #283593 50%, #42a5f5 100%);
    padding: 25px 30px; border-radius: 12px; color: white;
    margin-bottom: 25px; box-shadow: 0 4px 15px rgba(26,35,126,0.3);
}
.finteca-header h1 { margin:0; font-size:2.2em; font-weight:800; }
.finteca-header p  { margin:5px 0 0 0; opacity:0.85; }
.finteca-badge {
    background:rgba(255,255,255,0.2); padding:3px 10px;
    border-radius:20px; font-size:0.75em; display:inline-block; margin-top:8px;
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

st.markdown("""
<div class="finteca-header">
    <h1>🏦 Finteca AuditRep</h1>
    <p>Forensic Accounting · Fraud Detection · Reconciliation · Reporting</p>
    <span class="finteca-badge">v1.0.0</span>
</div>
""", unsafe_allow_html=True)

# ── Show environment ──────────────────────────────────────
is_cloud = os.path.exists("/mount/src")
if is_cloud:
    st.sidebar.info("☁️ Running on Streamlit Cloud")
else:
    st.sidebar.success("💻 Running Locally")

api_key = os.getenv("OPENAI_API_KEY", "")
if api_key and api_key.startswith("sk-"):
    st.sidebar.success("✅ AI Connected")
else:
    st.sidebar.warning("⚠️ Add OPENAI_API_KEY to secrets")

# ── Initialize database ───────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
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

try:
    init_db()
    db_ok = True
except Exception as e:
    db_ok = False
    st.error(f"Database error: {e}")

# ── Dashboard metrics ─────────────────────────────────────
TABLES = ["purchases","sales","banking","collections",
          "sales_returns","swap_deals","inventory"]
ICONS  = ["🛒","💰","🏦","💵","↩️","🔄","📦"]

def get_counts():
    counts = {}
    try:
        conn = sqlite3.connect(DB_PATH)
        for t in TABLES:
            try:
                r = pd.read_sql(f"SELECT COUNT(*) as c FROM {t}", conn)
                counts[t] = int(r["c"].iloc[0])
            except Exception:
                counts[t] = 0
        conn.close()
    except Exception:
        counts = {t: 0 for t in TABLES}
    return counts

if db_ok:
    counts = get_counts()
    total  = sum(counts.values())

    st.markdown("## 📊 Database Overview")
    st.metric("Total Records", total)

    cols = st.columns(7)
    for col, icon, table in zip(cols, ICONS, TABLES):
        with col:
            st.metric(
                f"{icon} {table.replace('_',' ').title()}",
                counts.get(table, 0)
            )

    st.divider()

    if is_cloud:
        st.markdown("""
        <div style="background:#e3f2fd;border-left:4px solid #1565c0;
                    padding:15px;border-radius:8px;margin:10px 0">
        ☁️ <b>Cloud Mode:</b> Data is stored temporarily.
        Upload your documents each session.
        For permanent storage, use the local version.
        </div>
        """, unsafe_allow_html=True)

st.markdown("### 🚀 Quick Start")
c1, c2, c3 = st.columns(3)
with c1:
    st.info(
        "**Step 1 — Upload**\n\n"
        "Go to Upload Documents.\n"
        "Upload Excel, PDF, Word or image files."
    )
with c2:
    st.info(
        "**Step 2 — Reconcile**\n\n"
        "Go to Reconciliation.\n"
        "Match collections to bank deposits."
    )
with c3:
    st.info(
        "**Step 3 — Report**\n\n"
        "Go to Reports.\n"
        "View fraud alerts and export reports."
    )

st.markdown("""
<div style="text-align:center;color:#999;margin-top:30px;font-size:0.8em">
Finteca AuditRep v1.0.0 · Powered by OpenAI GPT-4o ·
<a href="https://github.com/wealthraxfinteca/FintecaAuditRep"
   target="_blank">GitHub</a>
</div>
""", unsafe_allow_html=True)
