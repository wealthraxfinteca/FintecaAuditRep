"""
Finteca AuditRep — Expense Management Module
Track, categorise and analyse all business expenses
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
import os
from datetime import datetime, date, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── DB Path ───────────────────────────────────────────────
DB_PATH = "/tmp/reconciliation.db" if os.path.exists("/mount/src") \
          else "data/reconciliation.db"
if not os.path.exists("/mount/src"):
    Path("data").mkdir(exist_ok=True)

st.set_page_config(
    page_title="Expenses - Finteca AuditRep",
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
    <p>Expense Management · Categorisation · Analysis</p>
    <span class="finteca-badge">Module 7 — Expenses</span>
</div>
""", unsafe_allow_html=True)

# ── Expense Categories ────────────────────────────────────
EXPENSE_CATEGORIES = {
    "Cost of Sales": [
        "Direct Materials", "Direct Labour",
        "Manufacturing Overhead", "Freight In",
        "Purchase Returns", "Other COGS",
    ],
    "Operating Expenses": [
        "Rent & Rates", "Electricity & Utilities",
        "Internet & Telephone", "Office Supplies",
        "Printing & Stationery", "Repairs & Maintenance",
        "Insurance", "Security", "Cleaning",
        "Other Operating",
    ],
    "Staff Costs": [
        "Salaries & Wages", "Bonuses & Commissions",
        "Staff Training", "Staff Welfare",
        "Pension & NSITF", "Other Staff",
    ],
    "Selling & Distribution": [
        "Advertising & Marketing", "Sales Commission",
        "Delivery & Freight Out", "Trade Shows",
        "Customer Entertainment", "Other Selling",
    ],
    "Finance Costs": [
        "Bank Charges", "Interest Expense",
        "Loan Charges", "Foreign Exchange Loss",
        "Other Finance",
    ],
    "Other Expenses": [
        "Donations", "Fines & Penalties",
        "Miscellaneous", "Other",
    ],
}

ALL_CATEGORIES = list(EXPENSE_CATEGORIES.keys())
ALL_SUBCATEGORIES = [
    sub for subs in EXPENSE_CATEGORIES.values() for sub in subs
]

# ── Database ──────────────────────────────────────────────
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            category TEXT NOT NULL,
            subcategory TEXT,
            description TEXT,
            amount REAL DEFAULT 0,
            vat REAL DEFAULT 0,
            total_amount REAL DEFAULT 0,
            payment_method TEXT,
            payment_reference TEXT,
            payee TEXT,
            approved_by TEXT,
            receipt_number TEXT,
            is_recurring INTEGER DEFAULT 0,
            notes TEXT,
            document_source TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    return conn

def load_expenses():
    try:
        conn = get_conn()
        df = pd.read_sql("SELECT * FROM expenses ORDER BY date DESC", conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

def save_expense(data: dict) -> dict:
    try:
        conn = get_conn()
        cols = ", ".join(data.keys())
        vals = ", ".join(["?" for _ in data])
        conn.execute(
            f"INSERT INTO expenses ({cols}) VALUES ({vals})",
            list(data.values())
        )
        conn.commit()
        conn.close()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

def to_num(s):
    return pd.to_numeric(s, errors="coerce").fillna(0)

# ── Date filter ───────────────────────────────────────────
st.markdown(
    '<div class="section-header">📅 Date Range</div>',
    unsafe_allow_html=True
)
dc1, dc2 = st.columns(2)
today = date.today()
with dc1:
    start_date = st.date_input(
        "From", value=today.replace(day=1), key="exp_start"
    )
with dc2:
    end_date = st.date_input(
        "To", value=today, key="exp_end"
    )

# ── Tabs ──────────────────────────────────────────────────
tabs = st.tabs([
    "➕ Add Expense",
    "📊 Expense Dashboard",
    "📋 Expense Ledger",
    "📈 Analysis",
])

# ── TAB 1: Add Expense ────────────────────────────────────
with tabs[0]:
    st.markdown(
        '<div class="section-header">➕ Record New Expense</div>',
        unsafe_allow_html=True
    )

    col1, col2 = st.columns(2)

    with col1:
        with st.form("add_expense_form", clear_on_submit=True):
            e_date     = st.date_input("Date", value=today)
            e_category = st.selectbox(
                "Category", ALL_CATEGORIES
            )
            e_subcat   = st.selectbox(
                "Sub-Category",
                EXPENSE_CATEGORIES.get(e_category, ["Other"])
            )
            e_desc     = st.text_input(
                "Description",
                placeholder="What was this expense for?"
            )
            e_payee    = st.text_input(
                "Payee / Vendor",
                placeholder="Who was paid?"
            )
            e_amount   = st.number_input(
                "Amount (excl. VAT)",
                min_value=0.0, value=0.0, step=100.0
            )
            e_vat      = st.number_input(
                "VAT Amount",
                min_value=0.0, value=0.0, step=10.0
            )
            e_total    = e_amount + e_vat
            st.metric("Total Amount", f"{e_total:,.2f}")

            e_method   = st.selectbox(
                "Payment Method",
                ["Cash","Bank Transfer","Cheque",
                 "Card","Credit","Other"]
            )
            e_ref      = st.text_input("Payment Reference / Cheque No.")
            e_receipt  = st.text_input("Receipt Number")
            e_approved = st.text_input("Approved By")
            e_notes    = st.text_area("Notes", height=60)
            e_recurring= st.checkbox("Recurring Expense")

            if st.form_submit_button(
                "💾 Save Expense",
                type="primary",
                use_container_width=True
            ):
                if e_amount > 0 and e_category:
                    result = save_expense({
                        "date":             str(e_date),
                        "category":         e_category,
                        "subcategory":      e_subcat,
                        "description":      e_desc,
                        "amount":           e_amount,
                        "vat":              e_vat,
                        "total_amount":     e_total,
                        "payment_method":   e_method,
                        "payment_reference":e_ref,
                        "payee":            e_payee,
                        "approved_by":      e_approved,
                        "receipt_number":   e_receipt,
                        "is_recurring":     1 if e_recurring else 0,
                        "notes":            e_notes,
                    })
                    if result["success"]:
                        st.success(
                            f"✅ Expense saved: {e_category} — "
                            f"{e_total:,.2f}"
                        )
                        st.rerun()
                    else:
                        st.error(f"❌ {result.get('error')}")
                else:
                    st.error("Amount must be greater than 0")

    with col2:
        st.markdown("**Quick Reference — Expense Categories:**")
        for cat, subs in EXPENSE_CATEGORIES.items():
            with st.expander(f"📂 {cat}"):
                for sub in subs:
                    st.text(f"  • {sub}")

# ── TAB 2: Dashboard ─────────────────────────────────────
with tabs[1]:
    st.markdown(
        '<div class="section-header">📊 Expense Dashboard</div>',
        unsafe_allow_html=True
    )

    exp_df = load_expenses()

    if exp_df.empty:
        st.info(
            "No expenses recorded yet. "
            "Add expenses using the form on the left."
        )
    else:
        exp_df["date"]         = pd.to_datetime(
            exp_df["date"], errors="coerce"
        )
        exp_df["total_amount"] = to_num(exp_df["total_amount"])
        exp_df["amount"]       = to_num(exp_df["amount"])
        exp_df["vat"]          = to_num(exp_df["vat"])

        # Filter by date
        mask = (
            (pd.to_datetime(exp_df["date"], errors="coerce") >= pd.Timestamp(start_date)) &
            (pd.to_datetime(exp_df["date"], errors="coerce") <= pd.Timestamp(end_date))
        )
        filtered = exp_df[mask].copy()

        if filtered.empty:
            st.warning(
                "No expenses in selected date range. "
                "Adjust the date filter above."
            )
        else:
            tot_exp = filtered["total_amount"].sum()
            tot_vat = filtered["vat"].sum()
            tot_ex_vat = filtered["amount"].sum()
            count   = len(filtered)

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Expenses",     f"{tot_exp:,.2f}")
            m2.metric("Excl. VAT",          f"{tot_ex_vat:,.2f}")
            m3.metric("VAT Paid",           f"{tot_vat:,.2f}")
            m4.metric("Transactions",       count)

            col_a, col_b = st.columns(2)

            with col_a:
                by_cat = filtered.groupby("category").agg(
                    Total=("total_amount","sum"),
                    Count=("total_amount","count")
                ).reset_index().sort_values("Total", ascending=False)
                fig1 = px.pie(
                    by_cat, names="category", values="Total",
                    title="Expenses by Category",
                    color_discrete_sequence=px.colors.qualitative.Set2
                )
                st.plotly_chart(fig1, use_container_width=True)

            with col_b:
                by_method = filtered.groupby(
                    "payment_method"
                ).agg(
                    Total=("total_amount","sum"),
                    Count=("total_amount","count")
                ).reset_index()
                fig2 = px.bar(
                    by_method, x="payment_method",
                    y="Total",
                    title="Expenses by Payment Method",
                    color_discrete_sequence=["#1a237e"]
                )
                st.plotly_chart(fig2, use_container_width=True)

            # Trend
            filtered["month"] = filtered["date"].dt.strftime("%Y-%m")
            by_month = filtered.groupby("month").agg(
                Total=("total_amount","sum")
            ).reset_index()
            fig3 = px.bar(
                by_month, x="month", y="Total",
                title="Monthly Expense Trend",
                color_discrete_sequence=["#e53935"]
            )
            st.plotly_chart(fig3, use_container_width=True)

            # By subcategory
            by_sub = filtered.groupby("subcategory").agg(
                Total=("total_amount","sum"),
                Count=("total_amount","count")
            ).reset_index().sort_values("Total", ascending=False)
            st.markdown("**Top Expense Items:**")
            st.dataframe(
                by_sub.head(15),
                use_container_width=True, height=300
            )

# ── TAB 3: Ledger ─────────────────────────────────────────
with tabs[2]:
    st.markdown(
        '<div class="section-header">📋 Expense Ledger</div>',
        unsafe_allow_html=True
    )

    exp_df2 = load_expenses()
    if exp_df2.empty:
        st.info("No expenses recorded yet.")
    else:
        exp_df2["date"]         = pd.to_datetime(
            exp_df2["date"], errors="coerce"
        )
        exp_df2["total_amount"] = to_num(exp_df2["total_amount"])

        mask2 = (
            (pd.to_datetime(exp_df2["date"], errors="coerce") >= pd.Timestamp(start_date)) &
            (pd.to_datetime(exp_df2["date"], errors="coerce") <= pd.Timestamp(end_date))
        )
        filtered2 = exp_df2[mask2].copy()

        # Search
        search = st.text_input(
            "🔍 Search expenses:",
            placeholder="Category, payee, description..."
        )
        if search:
            filtered2 = filtered2[
                filtered2.apply(
                    lambda r: search.lower() in
                    " ".join(r.astype(str).values).lower(),
                    axis=1
                )
            ]

        st.dataframe(
            filtered2.sort_values("date", ascending=False),
            use_container_width=True, height=450
        )

        if not filtered2.empty:
            st.download_button(
                "📥 Download Expense Ledger",
                filtered2.to_csv(index=False),
                f"expenses_{start_date}_{end_date}.csv",
                "text/csv"
            )

# ── TAB 4: Analysis ───────────────────────────────────────
with tabs[3]:
    st.markdown(
        '<div class="section-header">📈 Expense Analysis</div>',
        unsafe_allow_html=True
    )

    exp_df3 = load_expenses()
    if exp_df3.empty:
        st.info("No data for analysis yet.")
    else:
        exp_df3["date"]         = pd.to_datetime(
            exp_df3["date"], errors="coerce"
        )
        exp_df3["total_amount"] = to_num(exp_df3["total_amount"])

        mask3 = (
            (pd.to_datetime(exp_df3["date"], errors="coerce") >= pd.Timestamp(start_date)) &
            (pd.to_datetime(exp_df3["date"], errors="coerce") <= pd.Timestamp(end_date))
        )
        f3 = exp_df3[mask3].copy()

        if not f3.empty:
            # Category breakdown table
            cat_summary = f3.groupby(
                ["category","subcategory"]
            ).agg(
                Total=("total_amount","sum"),
                Count=("total_amount","count"),
                Avg=("total_amount","mean"),
                Max=("total_amount","max"),
            ).reset_index().sort_values(
                ["category","Total"], ascending=[True,False]
            )
            st.markdown("**Full Category Breakdown:**")
            st.dataframe(
                cat_summary.round(2),
                use_container_width=True, height=400
            )

            # Payee analysis
            if "payee" in f3.columns:
                by_payee = f3.groupby("payee").agg(
                    Total=("total_amount","sum"),
                    Count=("total_amount","count"),
                ).reset_index().sort_values(
                    "Total", ascending=False
                )
                st.markdown("**Top Payees:**")
                fig_p = px.bar(
                    by_payee.head(10),
                    x="payee", y="Total",
                    title="Top 10 Payees by Amount",
                    color_discrete_sequence=["#7e57c2"]
                )
                st.plotly_chart(fig_p, use_container_width=True)
                st.dataframe(
                    by_payee,
                    use_container_width=True, height=250
                )

            st.download_button(
                "📥 Download Analysis",
                cat_summary.round(2).to_csv(index=False),
                f"expense_analysis_{start_date}_{end_date}.csv",
                "text/csv"
            )

st.markdown("""
<div class="finteca-footer">
    Finteca AuditRep v1.0.0 · Expense Management
</div>
""", unsafe_allow_html=True)
