# pages/14_Templates_Upload.py
# Finteca AuditRep — Templates & Smart Upload Hub

import streamlit as st
import pandas as pd
import sqlite3
import os
import io
from datetime import datetime, date
from pathlib import Path

st.set_page_config(
    page_title="Templates & Upload | Finteca AuditRep",
    page_icon="📤",
    layout="wide"
)

CSS = """
<style>
.finteca-header{background:linear-gradient(135deg,#1a237e 0%,#283593 50%,#42a5f5 100%);
    padding:25px 30px;border-radius:12px;color:white;margin-bottom:25px;}
.finteca-header h1{margin:0;font-size:2.2em;font-weight:800;}
.finteca-header p{margin:5px 0 0 0;opacity:0.85;}
.finteca-badge{background:rgba(255,255,255,0.2);padding:3px 10px;
    border-radius:20px;font-size:0.75em;display:inline-block;margin-top:8px;}
.template-card{background:#f8f9ff;border:1px solid #e0e4ff;border-radius:10px;
    padding:15px;margin:8px 0;border-left:4px solid #1a237e;}
.section-hdr{background:#f5f7ff;border-left:4px solid #1a237e;
    padding:10px 15px;border-radius:0 8px 8px 0;margin:15px 0;
    font-weight:600;color:#1a237e;}
.success-box{background:#e8f5e9;border-left:4px solid #2e7d32;
    padding:12px;border-radius:5px;margin:8px 0;}
.finteca-footer{text-align:center;color:#999;font-size:0.8em;
    padding:20px;border-top:1px solid #eee;margin-top:30px;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)
st.markdown("""
<div class="finteca-header">
    <h1>📤 Templates & Smart Upload</h1>
    <p>Download Templates · Upload Data · Parse PDFs · Scan Handwriting</p>
    <span class="finteca-badge">Module 14 — Upload Hub</span>
</div>
""", unsafe_allow_html=True)

# ── DB helpers ───────────────────────────────────────────────
def get_db():
    if st.session_state.get("active_db_path"):
        return st.session_state.active_db_path
    if os.path.exists("/mount/src"):
        return "/tmp/reconciliation.db"
    Path("data").mkdir(exist_ok=True)
    return "data/reconciliation.db"

def get_conn():
    return sqlite3.connect(get_db(), check_same_thread=False)

def ensure_tables():
    conn = get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT, supplier_name TEXT, invoice_no TEXT,
        item_code TEXT, description TEXT,
        quantity REAL, rate REAL,
        amount REAL, vat_amount REAL,
        total_amount REAL, payment_method TEXT,
        status TEXT DEFAULT 'unpaid',
        notes TEXT, assignment_id INTEGER,
        uploaded_at TEXT, document_source TEXT
    );
    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT, customer_name TEXT, invoice_no TEXT,
        description TEXT, amount REAL, vat_amount REAL,
        total_amount REAL, payment_method TEXT,
        status TEXT DEFAULT 'unpaid',
        notes TEXT, assignment_id INTEGER,
        uploaded_at TEXT, document_source TEXT
    );
    CREATE TABLE IF NOT EXISTS purchase_returns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT, supplier_name TEXT, original_invoice_no TEXT,
        return_reference TEXT, description TEXT,
        return_amount REAL, reason TEXT, status TEXT,
        notes TEXT, assignment_id INTEGER,
        uploaded_at TEXT, document_source TEXT
    );
    CREATE TABLE IF NOT EXISTS sales_returns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT, customer_name TEXT, original_invoice_no TEXT,
        return_reference TEXT, description TEXT,
        return_amount REAL, reason TEXT, status TEXT,
        notes TEXT, assignment_id INTEGER,
        uploaded_at TEXT, document_source TEXT
    );
    CREATE TABLE IF NOT EXISTS collections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT, customer_name TEXT, amount_collected REAL,
        payment_method TEXT, reference_no TEXT,
        invoices_covered TEXT, collector_name TEXT,
        notes TEXT, assignment_id INTEGER,
        uploaded_at TEXT, document_source TEXT
    );
    CREATE TABLE IF NOT EXISTS banking (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT, description TEXT, reference_no TEXT,
        type TEXT, debit_amount REAL, credit_amount REAL,
        balance REAL, category TEXT, notes TEXT,
        assignment_id INTEGER,
        uploaded_at TEXT, document_source TEXT
    );
    CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sku TEXT, item_name TEXT, category TEXT,
        unit_of_measure TEXT, opening_stock REAL,
        unit_cost REAL, selling_price REAL,
        reorder_level REAL, supplier_name TEXT,
        notes TEXT, assignment_id INTEGER,
        uploaded_at TEXT, document_source TEXT
    );
    CREATE TABLE IF NOT EXISTS swap_deals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT, party_a_name TEXT, party_b_name TEXT,
        item_a_given TEXT, value_a REAL,
        item_b_received TEXT, value_b REAL,
        net_difference REAL, status TEXT,
        notes TEXT, assignment_id INTEGER,
        uploaded_at TEXT, document_source TEXT
    );
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT, category TEXT, description TEXT,
        amount REAL, payment_method TEXT,
        paid_to TEXT, receipt_no TEXT,
        approved_by TEXT, notes TEXT,
        assignment_id INTEGER,
        uploaded_at TEXT, document_source TEXT
    );
    CREATE TABLE IF NOT EXISTS upload_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT, table_name TEXT, rows_uploaded INTEGER,
        assignment_id INTEGER, uploaded_at TEXT, status TEXT
    );
    """)
    conn.commit()
    conn.close()

ensure_tables()

# ── Assignment info ──────────────────────────────────────────
assign_id   = st.session_state.get("active_assignment_id")
assign_name = st.session_state.get("active_assignment_name", "Default")

if assign_name and assign_name != "Default":
    st.success(f"✅ Active Assignment: **{assign_name}**")
else:
    st.warning("⚠️ No assignment selected — data saved to default DB.")

# ── Template definitions ─────────────────────────────────────
TEMPLATES = [
    ("01_Purchases_Template.xlsx",       "🛒", "Purchases",
     "purchases",       "Supplier invoices and purchase records"),
    ("02_Sales_Template.xlsx",           "💰", "Sales",
     "sales",           "Customer invoices and sales records"),
    ("03_Purchase_Returns_Template.xlsx","↩️", "Purchase Returns",
     "purchase_returns","Goods returned to suppliers"),
    ("04_Sales_Returns_Template.xlsx",   "🔄", "Sales Returns",
     "sales_returns",   "Goods returned by customers"),
    ("05_Collections_Template.xlsx",     "💵", "Collections",
     "collections",     "Cash and payment collections"),
    ("06_Bank_Statement_Template.xlsx",  "🏦", "Bank Statement",
     "banking",         "Bank transactions and reconciliation"),
    ("07_Inventory_Master_Template.xlsx","📦", "Inventory",
     "inventory",       "Stock and inventory master list"),
    ("08_Swap_Deals_Template.xlsx",      "🔁", "Swap Deals",
     "swap_deals",      "Barter and swap transactions"),
    ("09_Expenses_Template.xlsx",        "💳", "Expenses",
     "expenses",        "Business expense records"),
]

# ── Column mappings for smart upload ────────────────────────
COL_MAP = {
    "purchases": {
        "date":              ["date","invoice date","inv date","doc date","txn date"],
        "supplier_name":     ["supplier","supplier name","vendor","vendor name","party","creditor"],
        "invoice_no":        ["invoice no","invoice number","inv no","inv #","ref","reference"],
        "item_code":         ["item code","sku","item code (sku)","code","product code","part no"],
        "description":       ["description","desc","item","particulars","narration","details","product"],
        "quantity":          ["quantity","qty","units","no of units","pcs","pieces","no. of units"],
        "rate":              ["rate","unit price","price","unit cost","cost per unit","rate per unit"],
        "amount":            ["amount","net amount","subtotal","sub total","net","line total"],
        "vat_amount":        ["vat","vat amount","tax","tax amount"],
        "total_amount":      ["total","total amount","gross","gross amount","grand total","invoice total"],
        "payment_method":    ["payment method","method","mode","payment mode"],
        "status":            ["status","payment status"],
        "notes":             ["notes","remarks","comment","comments"],
    },
    "sales": {
        "date":              ["date","invoice date","inv date","sale date","txn date"],
        "customer_name":     ["customer","customer name","client","client name","buyer","debtor"],
        "invoice_no":        ["invoice no","invoice number","inv no","inv #","ref","reference"],
        "item_code":         ["item code","sku","item code (sku)","code","product code","part no"],
        "description":       ["description","desc","item","particulars","narration","product"],
        "quantity":          ["quantity","qty","units","no of units","pcs","pieces","no. of units"],
        "rate":              ["rate","unit price","price","selling price","rate per unit"],
        "amount":            ["amount","net amount","subtotal","sub total","net","line total"],
        "vat_amount":        ["vat","vat amount","tax","tax amount"],
        "total_amount":      ["total","total amount","gross","grand total","invoice total"],
        "payment_method":    ["payment method","method","mode"],
        "status":            ["status","payment status"],
        "notes":             ["notes","remarks","comments"],
    },
    "purchase_returns": {
        "date":              ["date","return date","doc date"],
        "supplier_name":     ["supplier","supplier name","vendor","creditor"],
        "original_invoice_no":["original invoice","original invoice no","inv no","invoice no","orig inv"],
        "return_reference":  ["return ref","return reference","credit note","cn no","debit note"],
        "item_code":         ["item code","sku","item code (sku)","code","product code","part no"],
        "description":       ["description","desc","particulars","product","item"],
        "quantity_returned": ["quantity returned","qty returned","qty","quantity","units returned"],
        "rate":              ["rate","unit price","price","unit cost","cost per unit"],
        "return_amount":     ["return amount","amount","credit amount","value","total"],
        "reason":            ["reason","return reason","cause","remarks"],
        "status":            ["status"],
        "notes":             ["notes","comments"],
    },
    "sales_returns": {
        "date":              ["date","return date","doc date"],
        "customer_name":     ["customer","customer name","client","debtor"],
        "original_invoice_no":["original invoice","original invoice no","invoice no","inv no"],
        "return_reference":  ["return ref","return reference","credit note","cn no"],
        "item_code":         ["item code","sku","item code (sku)","code","product code"],
        "description":       ["description","desc","particulars","product","item"],
        "quantity_returned": ["quantity returned","qty returned","qty","quantity","units returned"],
        "rate":              ["rate","unit price","price","selling price"],
        "return_amount":     ["return amount","amount","credit amount","value","total"],
        "reason":            ["reason","return reason","cause"],
        "status":            ["status"],
        "notes":             ["notes","remarks"],
    },
    "collections": {
        "date":              ["date","collection date","payment date","receipt date"],
        "customer_name":     ["customer","customer name","client","payer","received from"],
        "amount_collected":  ["amount","amount collected","payment amount","collected","receipt amount"],
        "payment_method":    ["method","payment method","mode","payment mode"],
        "reference_no":      ["reference","ref","ref no","reference no","receipt no","cheque no"],
        "invoices_covered":  ["invoices","invoice covered","invoices covered","invoice no","covers"],
        "collector_name":    ["collector","collected by","received by","cashier"],
        "notes":             ["notes","remarks"],
    },
    "banking": {
        "date":              ["date","value date","transaction date","txn date","posting date"],
        "description":       ["description","narration","particulars","details","remarks","memo"],
        "reference_no":      ["reference","ref","ref no","cheque no","chq no","txn ref","transaction ref"],
        "type":              ["type","dr/cr","debit/credit","txn type","transaction type","dr cr"],
        "debit_amount":      ["debit","debit amount","dr","withdrawal","dr amount","withdrawals"],
        "credit_amount":     ["credit","credit amount","cr","deposit","cr amount","deposits"],
        "balance":           ["balance","closing balance","running balance","ledger balance"],
        "category":          ["category","cat","classification"],
        "notes":             ["notes","remarks"],
    },
    "expenses": {
        "date":              ["date","expense date","doc date","payment date"],
        "category":          ["category","expense category","type","expense type","head"],
        "description":       ["description","desc","particulars","details","narration"],
        "amount":            ["amount","expense amount","value","cost","total"],
        "payment_method":    ["method","payment method","mode","payment mode"],
        "paid_to":           ["paid to","payee","vendor","supplier","beneficiary"],
        "receipt_no":        ["receipt","receipt no","ref","reference","voucher no"],
        "approved_by":       ["approved by","approver","authorized by","sanctioned by"],
        "notes":             ["notes","remarks"],
    },
    "inventory": {
        "sku":               ["sku","item code","product code","code","part no","item code (sku)"],
        "item_name":         ["item name","product","description","item","product name","name"],
        "category":          ["category","type","product type","product category"],
        "unit_of_measure":   ["unit","uom","unit of measure","measure","unit of measurement"],
        "opening_stock":     ["opening stock","opening","qty","quantity","stock","opening qty"],
        "unit_cost":         ["unit cost","cost","cost price","purchase price","buy price"],
        "selling_price":     ["selling price","price","sale price","retail price","sell price"],
        "reorder_level":     ["reorder","reorder level","minimum stock","min stock","min qty"],
        "supplier_name":     ["supplier","vendor","supplier name","creditor"],
        "notes":             ["notes","remarks"],
    },
    "swap_deals": {
        "date":              ["date","swap date","deal date","transaction date"],
        "party_a_name":      ["party a","party a name","giver","supplier","from"],
        "party_b_name":      ["party b","party b name","receiver","customer","to"],
        "item_a_given":      ["item a","item given","goods given","product given","description a"],
        "value_a":           ["value a","amount a","value given","cost a"],
        "item_b_received":   ["item b","item received","goods received","product received","description b"],
        "value_b":           ["value b","amount b","value received","cost b"],
        "net_difference":    ["net","net difference","difference","balance","net value"],
        "status":            ["status"],
        "notes":             ["notes","remarks"],
    },
}


def smart_map(df, table):
    mapping = COL_MAP.get(table, {})
    df.columns = [c.strip().lower() for c in df.columns]
    rename = {}
    for target, aliases in mapping.items():
        for col in df.columns:
            if col in aliases and target not in rename.values():
                rename[col] = target
                break
    if rename:
        df = df.rename(columns=rename)
    return df

def upload_df_to_db(df, table, source_name):
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute(f"PRAGMA table_info('{table}')")
    valid_cols = [r[1] for r in cur.fetchall()]
    df = df.copy()
    df["assignment_id"]   = assign_id
    df["uploaded_at"]     = datetime.now().isoformat()
    df["document_source"] = source_name
    use_cols = [c for c in df.columns if c in valid_cols]
    df[use_cols].to_sql(table, conn, if_exists="append", index=False)
    rows = len(df)
    try:
        conn.execute(
            "INSERT INTO upload_log "
            "(filename,table_name,rows_uploaded,assignment_id,uploaded_at,status)"
            " VALUES (?,?,?,?,?,?)",
            (source_name, table, rows, assign_id,
             datetime.now().isoformat(), "success")
        )
    except Exception:
        pass
    conn.commit()
    conn.close()
    return rows

def count_table(table):
    try:
        conn = get_conn()
        c = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        conn.close()
        return c
    except Exception:
        return 0

# ════════════════════════════════════════════════════════════
# TABS
# ════════════════════════════════════════════════════════════
tab1, tab2, tab3 = st.tabs([
    "📥 Download Templates",
    "📤 Smart Upload",
    "📊 Upload Status",
])

# ── TAB 1: DOWNLOAD TEMPLATES ────────────────────────────────
with tab1:
    st.markdown('<div class="section-hdr">📥 Download Excel Templates</div>',
                unsafe_allow_html=True)
    st.info(
        "Download a template, fill in your data from **Row 7**, "
        "then upload it in the Smart Upload tab."
    )

    templates_dir = "templates"
    templates_exist = os.path.isdir(templates_dir)

    if not templates_exist:
        st.error("❌ Templates folder not found. Contact administrator.")
    else:
        cols = st.columns(3)
        for i, (fname, icon, name, table, desc) in enumerate(TEMPLATES):
            fpath = os.path.join(templates_dir, fname)
            col   = cols[i % 3]
            with col:
                st.markdown(
                    f'<div class="template-card">'
                    f'<b>{icon} {name}</b><br>'
                    f'<small style="color:#666">{desc}</small>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                if os.path.exists(fpath):
                    with open(fpath, "rb") as f:
                        st.download_button(
                            label=f"⬇️ Download",
                            data=f.read(),
                            file_name=fname,
                            mime="application/vnd.openxmlformats-officedocument"
                                 ".spreadsheetml.sheet",
                            key=f"dl_{table}",
                            use_container_width=True
                        )
                else:
                    st.caption(f"⚠️ File missing: {fname}")

# ── TAB 2: SMART UPLOAD ──────────────────────────────────────
with tab2:
    st.markdown('<div class="section-hdr">📤 Smart Upload</div>',
                unsafe_allow_html=True)

    table_options = {
        f"{t[1]} {t[2]}": (t[3], t[2]) for t in TEMPLATES
    }
    selected_label = st.selectbox(
        "Select data type:", list(table_options.keys())
    )
    selected_table, selected_name = table_options[selected_label]

    uploaded_file = st.file_uploader(
        f"Upload {selected_name} file:",
        type=["xlsx","xls","csv"],
        key=f"uploader_{selected_table}"
    )

    if uploaded_file:
        try:
            if uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file)
            else:
                # Try reading from row 6 (header) first
                df = pd.read_excel(uploaded_file, header=5)
                # Drop rows where all values are NaN
                df = df.dropna(how="all")
                # Drop rows that look like instruction rows
                df = df[df.iloc[:,0].notna()]

            st.success(f"✅ File loaded: **{len(df)} rows**, "
                       f"**{len(df.columns)} columns**")

            # Preview raw
            with st.expander("👁️ Preview Raw Data (first 5 rows)"):
                st.dataframe(df.head(), use_container_width=True)

            # Smart map columns
            df_mapped = smart_map(df, selected_table)

            with st.expander("🔀 Column Mapping Preview"):
                mapping_info = COL_MAP.get(selected_table, {})
                for target in mapping_info:
                    if target in df_mapped.columns:
                        st.write(f"✅ **{target}** — mapped")
                    else:
                        st.write(f"⚠️ **{target}** — not found "
                                 f"(will be blank)")

            with st.expander("👁️ Preview Mapped Data (first 5 rows)"):
                st.dataframe(df_mapped.head(), use_container_width=True)

            st.markdown("---")
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("Rows to Upload", len(df_mapped))
            with col_b:
                st.metric("Current Records in DB",
                          count_table(selected_table))

            if st.button(f"🚀 Upload {len(df_mapped)} rows to "
                         f"**{selected_name}**",
                         type="primary",
                         use_container_width=True):
                with st.spinner("Uploading..."):
                    rows = upload_df_to_db(
                        df_mapped, selected_table, uploaded_file.name
                    )
                st.success(
                    f"✅ **{rows} rows** uploaded to `{selected_table}` "
                    f"successfully!"
                )
                st.balloons()
                st.rerun()

        except Exception as e:
            st.error(f"❌ Error reading file: {e}")
            st.exception(e)

# ── TAB 3: UPLOAD STATUS ─────────────────────────────────────
with tab3:
    st.markdown('<div class="section-hdr">📊 Upload Status</div>',
                unsafe_allow_html=True)

    st.markdown("**Records in each table:**")
    cols3 = st.columns(3)
    for i, (_, icon, name, table, _) in enumerate(TEMPLATES):
        c = count_table(table)
        cols3[i % 3].metric(f"{icon} {name}", f"{c:,} records")

    st.markdown("---")
    st.markdown("**Upload Log (last 20):**")
    try:
        conn = get_conn()
        log_df = pd.read_sql(
            "SELECT filename, table_name, rows_uploaded, "
            "uploaded_at, status "
            "FROM upload_log ORDER BY id DESC LIMIT 20",
            conn
        )
        conn.close()
        if log_df.empty:
            st.info("No uploads yet.")
        else:
            st.dataframe(log_df, use_container_width=True)
    except Exception as e:
        st.info(f"No upload log available: {e}")

    st.markdown("---")
    st.markdown("**DHUB Upload Progress:**")
    steps = [
        ("1","🛒","Purchases",      "purchases",
         "Use Smart Upload tab → Purchases"),
        ("2","💰","Sales",          "sales",
         "Use Smart Upload tab → Sales"),
        ("3","↩️","Purchase Returns","purchase_returns",
         "Use Smart Upload tab → Purchase Returns"),
        ("4","🏦","Bank Statement 01","banking",
         "Use Smart Upload tab → Bank Statement"),
        ("5","🏦","Bank Statement 02","banking",
         "PDF → use Data Converter page first"),
        ("6","💵","Collections",    "collections",
         "Handwritten → use Data Converter page first"),
    ]
    for step, icon, name, table, desc in steps:
        n = count_table(table)
        status = "✅" if n > 0 else "⏳"
        st.markdown(
            f"**{status} Step {step}:** {icon} {name} — "
            f"{desc} "
            f"({'**' + str(n) + ' records**' if n > 0 else 'pending'})"
        )

st.markdown(
    '<div class="finteca-footer">'
    'Finteca AuditRep · Templates & Smart Upload · '
    'Supports Excel, CSV, PDF parsing, Handwriting OCR'
    '</div>',
    unsafe_allow_html=True
)
