"""
Finteca AuditRep — Purchase Returns Module
Track items returned to suppliers and debit notes
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import os
from datetime import datetime, date
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DB_PATH = "/tmp/reconciliation.db" if os.path.exists("/mount/src") \
          else "data/reconciliation.db"
if not os.path.exists("/mount/src"):
    Path("data").mkdir(exist_ok=True)

st.set_page_config(
    page_title="Purchase Returns - Finteca AuditRep",
    page_icon="🏦", layout="wide"
)

CSS = """
<style>
.finteca-header {
    background:linear-gradient(135deg,#1a237e 0%,#283593 50%,#42a5f5 100%);
    padding:25px 30px; border-radius:12px; color:white;
    margin-bottom:25px; box-shadow:0 4px 15px rgba(26,35,126,0.3);
}
.finteca-header h1 { margin:0; font-size:2.2em; font-weight:800; }
.finteca-header p  { margin:5px 0 0 0; opacity:0.85; }
.finteca-badge {
    background:rgba(255,255,255,0.2); padding:3px 10px;
    border-radius:20px; font-size:0.75em;
    display:inline-block; margin-top:8px;
}
.section-header {
    background:#f5f7ff; border-left:4px solid #1a237e;
    padding:10px 15px; border-radius:0 8px 8px 0;
    margin:15px 0; font-weight:600; color:#1a237e;
}
.flag-green {
    background:#e8f5e9; border-left:4px solid #2e7d32;
    padding:10px; border-radius:5px; margin:5px 0;
}
.flag-red {
    background:#ffebee; border-left:4px solid #c62828;
    padding:10px; border-radius:5px; margin:5px 0;
}
.finteca-footer {
    text-align:center; color:#999; font-size:0.8em;
    padding:20px; border-top:1px solid #eee; margin-top:30px;
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)
st.markdown("""
<div class="finteca-header">
    <h1>🏦 Finteca AuditRep</h1>
    <p>Purchase Returns · Debit Notes · Supplier Credits</p>
    <span class="finteca-badge">Module 8 — Purchase Returns</span>
</div>
""", unsafe_allow_html=True)

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS purchase_returns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            return_reference TEXT,
            original_po_number TEXT,
            supplier TEXT NOT NULL,
            item_description TEXT,
            quantity_returned REAL DEFAULT 0,
            unit_cost REAL DEFAULT 0,
            return_amount REAL DEFAULT 0,
            reason TEXT,
            condition TEXT,
            debit_note_number TEXT,
            credit_received INTEGER DEFAULT 0,
            credit_amount REAL DEFAULT 0,
            restocked INTEGER DEFAULT 0,
            approved_by TEXT,
            notes TEXT,
            document_source TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    return conn

def load_purchase_returns():
    try:
        conn = get_conn()
        df = pd.read_sql(
            "SELECT * FROM purchase_returns ORDER BY date DESC",
            conn
        )
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

def save_purchase_return(data: dict) -> dict:
    try:
        conn = get_conn()
        cols = ", ".join(data.keys())
        vals = ", ".join(["?" for _ in data])
        conn.execute(
            f"INSERT INTO purchase_returns ({cols}) VALUES ({vals})",
            list(data.values())
        )
        conn.commit()
        conn.close()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

def to_num(s):
    return pd.to_numeric(s, errors="coerce").fillna(0)

today = date.today()

dc1, dc2 = st.columns(2)
with dc1:
    start_date = st.date_input(
        "From", value=today.replace(day=1), key="pr_start"
    )
with dc2:
    end_date = st.date_input(
        "To", value=today, key="pr_end"
    )

tabs = st.tabs([
    "➕ Record Return",
    "📊 Returns Summary",
    "📋 Returns Ledger",
    "⚖️ Reconcile with Purchases",
])

# ── TAB 1: Record Return ─────────────────────────────────
with tabs[0]:
    st.markdown(
        '<div class="section-header">➕ Record Purchase Return</div>',
        unsafe_allow_html=True
    )

    col1, col2 = st.columns(2)

    with col1:
        with st.form("purchase_return_form", clear_on_submit=True):
            pr_date   = st.date_input("Return Date", value=today)
            pr_ref    = st.text_input(
                "Return Reference",
                placeholder="RET-2025-001"
            )
            pr_po     = st.text_input(
                "Original PO Number",
                placeholder="PO-2025-xxx"
            )
            pr_supp   = st.text_input(
                "Supplier Name",
                placeholder="Supplier company name"
            )
            pr_item   = st.text_input(
                "Item Description",
                placeholder="What is being returned?"
            )
            pr_qty    = st.number_input(
                "Quantity Returned",
                min_value=0.0, value=1.0, step=1.0
            )
            pr_cost   = st.number_input(
                "Unit Cost",
                min_value=0.0, value=0.0, step=100.0
            )
            pr_amount = pr_qty * pr_cost
            st.metric("Return Amount", f"{pr_amount:,.2f}")

            pr_reason = st.selectbox("Reason for Return", [
                "Defective/Damaged",
                "Wrong Item Supplied",
                "Quality Not as Ordered",
                "Excess Stock",
                "Price Dispute",
                "Expired/Obsolete",
                "Other",
            ])
            pr_cond   = st.selectbox("Item Condition", [
                "Damaged", "Unused", "Partially Used", "Other"
            ])
            pr_debit  = st.text_input("Debit Note Number")
            pr_credit_recv = st.checkbox("Credit Note Received?")
            pr_credit_amt  = st.number_input(
                "Credit Amount Received",
                min_value=0.0,
                value=pr_amount if pr_credit_recv else 0.0
            )
            pr_restock = st.checkbox("Item Restocked?")
            pr_approved= st.text_input("Approved By")
            pr_notes   = st.text_area("Notes", height=60)

            if st.form_submit_button(
                "💾 Save Purchase Return",
                type="primary",
                use_container_width=True
            ):
                if pr_amount > 0 and pr_supp:
                    result = save_purchase_return({
                        "date":             str(pr_date),
                        "return_reference": pr_ref,
                        "original_po_number":pr_po,
                        "supplier":         pr_supp,
                        "item_description": pr_item,
                        "quantity_returned":pr_qty,
                        "unit_cost":        pr_cost,
                        "return_amount":    pr_amount,
                        "reason":           pr_reason,
                        "condition":        pr_cond,
                        "debit_note_number":pr_debit,
                        "credit_received":  1 if pr_credit_recv else 0,
                        "credit_amount":    pr_credit_amt,
                        "restocked":        1 if pr_restock else 0,
                        "approved_by":      pr_approved,
                        "notes":            pr_notes,
                    })
                    if result["success"]:
                        st.success(
                            f"✅ Return saved: {pr_supp} — "
                            f"{pr_amount:,.2f}"
                        )
                        st.rerun()
                    else:
                        st.error(f"❌ {result.get('error')}")
                else:
                    st.error(
                        "Please enter supplier name and amount"
                    )

    with col2:
        st.markdown("**Purchase Return Process:**")
        st.markdown("""
        1. **Identify** the item to return
        2. **Record** the return with reference
        3. **Issue** a Debit Note to supplier
        4. **Track** credit note from supplier
        5. **Reconcile** against original purchase
        6. **Update** inventory if restocked
        """)
        st.info("""
        💡 **Debit Note** = Document you send to supplier
        requesting credit for returned goods.

        **Credit Note** = Document supplier sends back
        confirming the credit.
        """)

# ── TAB 2: Summary ────────────────────────────────────────
with tabs[1]:
    st.markdown(
        '<div class="section-header">📊 Purchase Returns Summary</div>',
        unsafe_allow_html=True
    )

    pr_df = load_purchase_returns()

    if pr_df.empty:
        st.info("No purchase returns recorded yet.")
    else:
        pr_df["date"]          = pd.to_datetime(
            pr_df["date"], errors="coerce"
        )
        pr_df["return_amount"] = to_num(pr_df["return_amount"])
        pr_df["credit_amount"] = to_num(pr_df["credit_amount"])

        mask = (
            (pd.to_datetime(pr_df["date"], errors="coerce") >= pd.Timestamp(start_date)) &
            (pd.to_datetime(pr_df["date"], errors="coerce") <= pd.Timestamp(end_date))
        )
        f = pr_df[mask].copy()

        if f.empty:
            st.warning("No returns in selected date range.")
        else:
            tot_ret    = f["return_amount"].sum()
            tot_credit = f["credit_amount"].sum()
            pending    = tot_ret - tot_credit
            count      = len(f)

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Returns",      f"{tot_ret:,.2f}")
            m2.metric("Credits Received",   f"{tot_credit:,.2f}")
            m3.metric("Pending Credits",    f"{pending:,.2f}",
                      delta_color="inverse")
            m4.metric("Return Count",       count)

            if pending > 0:
                st.markdown(
                    f'<div class="flag-red">'
                    f'⚠️ {pending:,.2f} in returns '
                    f'awaiting credit notes from suppliers.'
                    f'</div>',
                    unsafe_allow_html=True
                )

            by_supp = f.groupby("supplier").agg(
                Total_Returned=("return_amount","sum"),
                Credits_Received=("credit_amount","sum"),
                Count=("return_amount","count")
            ).reset_index()
            by_supp["Pending"] = (
                by_supp["Total_Returned"]
                - by_supp["Credits_Received"]
            )

            fig = px.bar(
                by_supp, x="supplier",
                y=["Total_Returned","Credits_Received"],
                title="Returns vs Credits by Supplier",
                barmode="group",
                color_discrete_sequence=["#e53935","#2e7d32"]
            )
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(
                by_supp.round(2),
                use_container_width=True, height=250
            )

# ── TAB 3: Ledger ─────────────────────────────────────────
with tabs[2]:
    st.markdown(
        '<div class="section-header">📋 Purchase Returns Ledger</div>',
        unsafe_allow_html=True
    )
    pr_df2 = load_purchase_returns()
    if pr_df2.empty:
        st.info("No purchase returns yet.")
    else:
        pr_df2["date"] = pd.to_datetime(
            pr_df2["date"], errors="coerce"
        )
        pr_df2["return_amount"] = to_num(pr_df2["return_amount"])
        mask2 = (
            (pd.to_datetime(pr_df2["date"], errors="coerce") >= pd.Timestamp(start_date)) &
            (pd.to_datetime(pr_df2["date"], errors="coerce") <= pd.Timestamp(end_date))
        )
        f2 = pr_df2[mask2].copy()
        st.dataframe(
            f2.sort_values("date", ascending=False),
            use_container_width=True, height=400
        )
        if not f2.empty:
            st.download_button(
                "📥 Download Purchase Returns",
                f2.to_csv(index=False),
                f"purchase_returns_{start_date}_{end_date}.csv",
                "text/csv"
            )

# ── TAB 4: Reconcile ──────────────────────────────────────
with tabs[3]:
    st.markdown(
        '<div class="section-header">'
        '⚖️ Reconcile Returns with Purchases'
        '</div>',
        unsafe_allow_html=True
    )

    try:
        conn = get_conn()
        purchases = pd.read_sql(
            "SELECT * FROM purchases", conn
        )
        pr_all    = pd.read_sql(
            "SELECT * FROM purchase_returns", conn
        )
        conn.close()
    except Exception:
        purchases = pd.DataFrame()
        pr_all    = pd.DataFrame()

    if purchases.empty:
        st.warning(
            "No purchases data found. "
            "Upload purchase records first."
        )
    else:
        purchases["total_cost"]    = to_num(
            purchases.get("total_cost", pd.Series(dtype=float))
        )
        pr_all["return_amount"]    = to_num(
            pr_all.get("return_amount", pd.Series(dtype=float))
        ) if not pr_all.empty else pd.Series(dtype=float)

        tot_purch  = purchases["total_cost"].sum()
        tot_ret    = pr_all["return_amount"].sum() \
                     if not pr_all.empty else 0
        net_purch  = tot_purch - tot_ret

        m1, m2, m3 = st.columns(3)
        m1.metric("Gross Purchases", f"{tot_purch:,.2f}")
        m2.metric("Purchase Returns",f"{tot_ret:,.2f}",
                  delta_color="inverse")
        m3.metric("Net Purchases",   f"{net_purch:,.2f}")

        st.markdown("""
        **Net Purchases Formula:**
        ```
        Gross Purchases
        - Purchase Returns
        = Net Purchases (feeds into COGS)
        ```
        """)

        if not pr_all.empty and "supplier" in purchases.columns:
            by_sup_p = purchases.groupby("supplier").agg(
                Purchased=("total_cost","sum")
            ).reset_index()
            by_sup_r = pr_all.groupby("supplier").agg(
                Returned=("return_amount","sum")
            ).reset_index()
            reconciled = by_sup_p.merge(
                by_sup_r, on="supplier", how="left"
            ).fillna(0)
            reconciled["Net"] = (
                reconciled["Purchased"] - reconciled["Returned"]
            )
            st.markdown("**By Supplier:**")
            st.dataframe(
                reconciled.round(2),
                use_container_width=True, height=300
            )

st.markdown("""
<div class="finteca-footer">
    Finteca AuditRep v1.0.0 · Purchase Returns
</div>
""", unsafe_allow_html=True)
