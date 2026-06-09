"""
Finteca AuditRep — Financial Statements
Income Statement | Cash Flow | Inventory Valuation
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
import os
from datetime import date, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DB_PATH = (st.session_state.get("active_db_path") or
    ("/tmp/reconciliation.db" if os.path.exists("/mount/src")
     else "data/reconciliation.db"))
if not os.path.exists("/mount/src"):
    Path("data").mkdir(exist_ok=True)

st.set_page_config(
    page_title="Financial Statements - Finteca AuditRep",
    page_icon="🏦", layout="wide"
)

st.markdown("""
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
    border-radius:20px; font-size:0.75em; display:inline-block; margin-top:8px;
}
.section-header {
    background:#f5f7ff; border-left:4px solid #1a237e; padding:10px 15px;
    border-radius:0 8px 8px 0; margin:15px 0; font-weight:600; color:#1a237e;
}
.is-header {
    background:#1a237e; color:white; padding:8px 15px;
    border-radius:6px; margin:4px 0; font-weight:700;
}
.is-section {
    background:#e8eaf6; padding:6px 15px;
    border-radius:4px; margin:2px 0; font-weight:600; color:#1a237e;
}
.is-line {
    padding:4px 20px; border-bottom:1px solid #f0f0f0;
    display:flex; justify-content:space-between;
}
.is-subtotal {
    background:#f5f7ff; padding:6px 15px;
    border-top:2px solid #1a237e; margin:4px 0;
    font-weight:600;
}
.is-total {
    background:#1a237e; color:white; padding:10px 15px;
    border-radius:6px; margin:8px 0; font-weight:700; font-size:1.1em;
}
.positive { color:#2e7d32; font-weight:600; }
.negative { color:#c62828; font-weight:600; }
.flag-green {
    background:#e8f5e9; border-left:4px solid #2e7d32;
    padding:10px 15px; border-radius:6px; margin:6px 0;
}
.flag-red {
    background:#ffebee; border-left:4px solid #c62828;
    padding:10px 15px; border-radius:6px; margin:6px 0;
}
.flag-blue {
    background:#e3f2fd; border-left:4px solid #1565c0;
    padding:10px 15px; border-radius:6px; margin:6px 0;
}
.finteca-footer {
    text-align:center; color:#999; font-size:0.8em;
    padding:20px; border-top:1px solid #eee; margin-top:30px;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="finteca-header">
    <h1>🏦 Finteca AuditRep</h1>
    <p>Income Statement · Cash Flow · Inventory Valuation</p>
    <span class="finteca-badge">Module 6 — Financial Statements</span>
</div>
""", unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────
def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def load(table):
    try:
        conn = get_conn()
        df   = pd.read_sql(f"SELECT * FROM {table}", conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

def to_num(s):
    return pd.to_numeric(s, errors="coerce").fillna(0)

def filter_dates(df, start, end, col="date"):
    if df.empty or col not in df.columns:
        return df.copy()
    df = df.copy()
    df[col] = pd.to_datetime(df[col], errors="coerce")
    return df[
        (df[col].dt.date >= start) & (df[col].dt.date <= end)
    ].reset_index(drop=True)

def fmt(val, prefix=""):
    """Format number for financial statement display"""
    if val < 0:
        return f"({prefix}{abs(val):,.2f})"
    return f"{prefix}{val:,.2f}"

def pct(val, base):
    if base == 0:
        return "0.0%"
    return f"{val/base*100:.1f}%"

# ── Date Range ────────────────────────────────────────────
st.markdown(
    '<div class="section-header">📅 Statement Period</div>',
    unsafe_allow_html=True
)
today = date.today()

col_p, col_d = st.columns([1, 2])
with col_p:
    presets = {
        "This Month":  (today.replace(day=1), today),
        "Last Month":  (
            (today.replace(day=1)-timedelta(days=1)).replace(day=1),
            today.replace(day=1)-timedelta(days=1)
        ),
        "This Quarter":(date(today.year,((today.month-1)//3)*3+1,1), today),
        "This Year":   (date(today.year,1,1), today),
        "Last Year":   (date(today.year-1,1,1), date(today.year-1,12,31)),
        "All Time":    (date(2000,1,1), today),
    }
    btn_cols = st.columns(3)
    for i,(label,(s,e)) in enumerate(presets.items()):
        with btn_cols[i%3]:
            if st.button(label, key=f"fs_{label}",
                         use_container_width=True):
                st.session_state.fs_start = s
                st.session_state.fs_end   = e
                st.rerun()

    if "fs_start" not in st.session_state:
        st.session_state.fs_start = date(today.year,1,1)
    if "fs_end" not in st.session_state:
        st.session_state.fs_end = today

with col_d:
    dc1,dc2 = st.columns(2)
    with dc1:
        start_date = st.date_input(
            "From", value=st.session_state.fs_start
        )
    with dc2:
        end_date = st.date_input(
            "To", value=st.session_state.fs_end
        )
    st.session_state.fs_start = start_date
    st.session_state.fs_end   = end_date
    st.markdown(
        f'<div class="flag-blue">📊 Period: '
        f'<b>{start_date.strftime("%d %b %Y")}</b> → '
        f'<b>{end_date.strftime("%d %b %Y")}</b></div>',
        unsafe_allow_html=True
    )

company_name = st.text_input(
    "Company Name (for reports):",
    value="Finteca AuditRep",
    key="company_name"
)

st.divider()

# ── Load filtered data ────────────────────────────────────
sales_df   = filter_dates(load("sales"),            start_date, end_date)
purch_df   = filter_dates(load("purchases"),        start_date, end_date)
sal_ret_df = filter_dates(load("sales_returns"),    start_date, end_date)
pur_ret_df = filter_dates(load("purchase_returns"), start_date, end_date)
exp_df     = filter_dates(load("expenses"),         start_date, end_date)
bank_df    = filter_dates(load("banking"),          start_date, end_date)
coll_df    = filter_dates(load("collections"),      start_date, end_date)
swap_df    = filter_dates(load("swap_deals"),       start_date, end_date)
inv_df     = load("inventory")

# ── Compute Core Figures ──────────────────────────────────

# Revenue
gross_sales     = to_num(sales_df.get("net_amount",   pd.Series(dtype=float))).sum()
sales_discounts = to_num(sales_df.get("discount",     pd.Series(dtype=float))).sum()
sales_returns   = to_num(sal_ret_df.get("return_amount", pd.Series(dtype=float))).sum()
net_revenue     = gross_sales - sales_returns

# Swap revenue
swap_revenue = to_num(swap_df.get("customer_paid", pd.Series(dtype=float))).sum()
total_revenue = net_revenue + swap_revenue

# COGS Calculation
# Opening Stock
opening_value = to_num(inv_df.get("opening_value", pd.Series(dtype=float))).sum()

# Purchases
purchases_cost   = to_num(purch_df.get("total_cost",  pd.Series(dtype=float))).sum()
purchase_returns = to_num(pur_ret_df.get("return_amount", pd.Series(dtype=float))).sum()
net_purchases    = purchases_cost - purchase_returns

# Goods available for sale
goods_available = opening_value + net_purchases

# Closing Stock from inventory
closing_value   = to_num(inv_df.get("closing_value",  pd.Series(dtype=float))).sum()

# COGS = Opening + Net Purchases - Closing
cogs_from_inventory = goods_available - closing_value

# COGS from sales records (direct)
cogs_from_sales = to_num(sales_df.get("cost_of_goods", pd.Series(dtype=float))).sum()
cogs_returns    = to_num(sal_ret_df.get("cogs_reversal", pd.Series(dtype=float))).sum()
net_cogs_sales  = cogs_from_sales - cogs_returns

# Use inventory method if available, else use sales COGS
if goods_available > 0:
    cogs = cogs_from_inventory
else:
    cogs = net_cogs_sales

gross_profit = total_revenue - cogs
gp_margin    = gross_profit / total_revenue * 100 if total_revenue else 0

# Cost of Sales expenses
cos_df  = exp_df[
    exp_df.get("category", pd.Series(dtype=str)) == "Cost of Sales"
] if not exp_df.empty and "category" in exp_df.columns else pd.DataFrame()
cos_exp = to_num(cos_df.get("net_amount", pd.Series(dtype=float))).sum() if not cos_df.empty else 0

total_cogs_all = cogs + cos_exp
adjusted_gp    = total_revenue - total_cogs_all

# Operating Expenses
def get_exp_cat(cat):
    if exp_df.empty or "category" not in exp_df.columns:
        return 0.0
    d = exp_df[exp_df["category"] == cat]
    return to_num(d.get("net_amount", pd.Series(dtype=float))).sum()

admin_exp   = get_exp_cat("Administrative")
selling_exp = get_exp_cat("Selling & Distribution")
finance_exp = get_exp_cat("Finance Costs")
other_exp   = get_exp_cat("Other Expenses")

total_opex = admin_exp + selling_exp + other_exp
ebit       = adjusted_gp - total_opex
pbt        = ebit - finance_exp
net_profit = pbt
npm        = net_profit / total_revenue * 100 if total_revenue else 0

# Cash Flow figures
cash_in   = to_num(bank_df.get("credit", pd.Series(dtype=float))).sum()
cash_out  = to_num(bank_df.get("debit",  pd.Series(dtype=float))).sum()
net_cash  = cash_in - cash_out
collected = to_num(coll_df.get("amount", pd.Series(dtype=float))).sum()

# ── TABS ──────────────────────────────────────────────────
tabs = st.tabs([
    "📊 Income Statement",
    "📦 COGS & Inventory",
    "💸 Expenses",
    "🌊 Cash Flow Statement",
    "📋 Summary Dashboard",
])

# ════════════════════════════════════════════════════════
# TAB 1 — INCOME STATEMENT
# ════════════════════════════════════════════════════════
with tabs[0]:
    st.markdown(
        '<div class="section-header">📊 Income Statement (Profit & Loss)</div>',
        unsafe_allow_html=True
    )

    col_is, col_chart = st.columns([2, 1])

    with col_is:
        # Header
        st.markdown(f"""
        <div style="text-align:center; padding:15px; background:#f5f7ff;
                    border-radius:10px; margin-bottom:15px">
            <h3 style="margin:0; color:#1a237e">{company_name}</h3>
            <h4 style="margin:5px 0; color:#666">Income Statement</h4>
            <p style="margin:0; color:#888">
                For the period: {start_date.strftime("%d %b %Y")} to
                {end_date.strftime("%d %b %Y")}
            </p>
        </div>
        """, unsafe_allow_html=True)

        def is_row(label, value, indent=0, bold=False, total=False,
                   section=False, color=None):
            """Render an income statement row"""
            pad = indent * 20
            if total:
                bg    = "#1a237e"
                fg    = "white"
                brd   = ""
                fw    = "700"
                sz    = "1.05em"
            elif section:
                bg    = "#e8eaf6"
                fg    = "#1a237e"
                brd   = ""
                fw    = "700"
                sz    = "0.95em"
            elif bold:
                bg    = "#f5f7ff"
                fg    = "#1a237e"
                brd   = "border-top:1px solid #1a237e;"
                fw    = "600"
                sz    = "0.9em"
            else:
                bg    = "white"
                fg    = "#333"
                brd   = "border-bottom:1px solid #f0f0f0;"
                fw    = "400"
                sz    = "0.88em"

            if color:
                val_color = color
            elif value < 0:
                val_color = "#c62828"
            elif total or bold:
                val_color = "white" if total else "#1a237e"
            else:
                val_color = "#333"

            val_str = fmt(value)

            st.markdown(f"""
            <div style="display:flex; justify-content:space-between;
                        align-items:center; padding:6px {pad+10}px;
                        background:{bg}; margin:1px 0;
                        border-radius:4px; {brd}">
                <span style="color:{fg}; font-weight:{fw};
                             font-size:{sz}">{label}</span>
                <span style="color:{val_color}; font-weight:{fw};
                             font-size:{sz}">{val_str}</span>
            </div>
            """, unsafe_allow_html=True)

        # ── REVENUE SECTION ───────────────────────────────
        is_row("REVENUE", 0, section=True)
        is_row("Gross Sales",        gross_sales,     indent=1)
        is_row("Less: Sales Returns",sales_returns,   indent=1)
        is_row("Less: Discounts",    sales_discounts, indent=1)
        is_row("Swap Deal Revenue",  swap_revenue,    indent=1)
        is_row("Net Revenue",        net_revenue,     bold=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── COST OF GOODS SOLD ────────────────────────────
        is_row("COST OF GOODS SOLD (COGS)", 0, section=True)
        is_row("Opening Stock",        opening_value,    indent=1)
        is_row("Add: Purchases",       purchases_cost,   indent=1)
        is_row("Less: Purchase Returns",purchase_returns,indent=1)
        is_row("Net Purchases",        net_purchases,    indent=1, bold=True)
        is_row("Goods Available for Sale", goods_available, indent=1, bold=True)
        is_row("Less: Closing Stock",  closing_value,    indent=1)
        if cos_exp > 0:
            is_row("Add: Cost of Sales Expenses", cos_exp, indent=1)
        is_row("Total COGS",          total_cogs_all,   bold=True)
        is_row("GROSS PROFIT",        adjusted_gp,
               total=True,
               color="#4caf50" if adjusted_gp >= 0 else "#f44336")

        st.markdown(f"""
        <div style="text-align:right; padding:4px 10px;
                    color:#666; font-size:0.8em">
            Gross Margin: {pct(adjusted_gp, total_revenue)}
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── OPERATING EXPENSES ────────────────────────────
        is_row("OPERATING EXPENSES", 0, section=True)
        is_row("Administrative Expenses",         admin_exp,   indent=1)
        is_row("Selling & Distribution Expenses", selling_exp, indent=1)
        is_row("Total Operating Expenses",        total_opex,  bold=True)

        st.markdown("<br>", unsafe_allow_html=True)

        is_row("OPERATING PROFIT (EBIT)", ebit,
               total=True,
               color="#4caf50" if ebit >= 0 else "#f44336")

        st.markdown("<br>", unsafe_allow_html=True)

        # ── FINANCE COSTS ─────────────────────────────────
        is_row("FINANCE COSTS", 0, section=True)
        is_row("Finance Costs", finance_exp, indent=1)

        st.markdown("<br>", unsafe_allow_html=True)

        is_row("PROFIT BEFORE TAX", pbt,
               total=True,
               color="#4caf50" if pbt >= 0 else "#f44336")

        if other_exp > 0:
            is_row("Less: Other Expenses", other_exp, indent=1)

        st.markdown("<br>", unsafe_allow_html=True)

        is_row("NET PROFIT / (LOSS)", net_profit,
               total=True,
               color="#4caf50" if net_profit >= 0 else "#f44336")

        st.markdown(f"""
        <div style="text-align:right; padding:4px 10px;
                    color:#666; font-size:0.8em">
            Net Profit Margin: {pct(net_profit, total_revenue)}
        </div>
        """, unsafe_allow_html=True)

    with col_chart:
        # Waterfall chart
        waterfall_data = [
            ("Revenue",       net_revenue,    "relative"),
            ("COGS",         -total_cogs_all, "relative"),
            ("Gross Profit",  adjusted_gp,    "total"),
            ("Admin Exp",    -admin_exp,      "relative"),
            ("Selling Exp",  -selling_exp,    "relative"),
            ("EBIT",          ebit,           "total"),
            ("Finance",      -finance_exp,    "relative"),
            ("Net Profit",    net_profit,     "total"),
        ]
        wf_labels = [x[0] for x in waterfall_data]
        wf_values = [x[1] for x in waterfall_data]
        wf_measures= [x[2] for x in waterfall_data]

        fig_wf = go.Figure(go.Waterfall(
            name="P&L",
            orientation="v",
            measure=wf_measures,
            x=wf_labels,
            y=wf_values,
            connector={"line":{"color":"#1a237e"}},
            increasing={"marker":{"color":"#2e7d32"}},
            decreasing={"marker":{"color":"#c62828"}},
            totals={"marker":{"color":"#1a237e"}},
            textposition="outside",
            text=[fmt(v) for v in wf_values],
        ))
        fig_wf.update_layout(
            title="P&L Waterfall",
            height=500,
            showlegend=False
        )
        st.plotly_chart(fig_wf, use_container_width=True)

        # KPI cards
        kpis = [
            ("Net Revenue",     net_revenue),
            ("Gross Profit",    adjusted_gp),
            ("EBIT",            ebit),
            ("Net Profit",      net_profit),
        ]
        for label, val in kpis:
            color = "#2e7d32" if val >= 0 else "#c62828"
            st.markdown(f"""
            <div style="background:white; padding:10px 15px;
                        border-radius:8px; border-left:4px solid {color};
                        margin:5px 0; box-shadow:0 1px 4px rgba(0,0,0,0.08)">
                <div style="font-size:0.75em; color:#888">{label}</div>
                <div style="font-size:1.2em; font-weight:700;
                            color:{color}">{fmt(val)}</div>
            </div>
            """, unsafe_allow_html=True)

    # Download Income Statement
    is_data = {
        "Line Item": [
            "REVENUE",
            "Gross Sales", "Less: Sales Returns", "Less: Discounts",
            "Swap Revenue", "NET REVENUE",
            "",
            "COST OF GOODS SOLD",
            "Opening Stock", "Add: Purchases", "Less: Purchase Returns",
            "Net Purchases", "Goods Available", "Less: Closing Stock",
            "TOTAL COGS", "GROSS PROFIT",
            "",
            "OPERATING EXPENSES",
            "Administrative", "Selling & Distribution",
            "Total OpEx", "EBIT",
            "",
            "Finance Costs", "PROFIT BEFORE TAX",
            "Other Expenses", "NET PROFIT/(LOSS)",
        ],
        "Amount": [
            "",
            gross_sales, -sales_returns, -sales_discounts,
            swap_revenue, net_revenue,
            "",
            "",
            opening_value, purchases_cost, -purchase_returns,
            net_purchases, goods_available, -closing_value,
            total_cogs_all, adjusted_gp,
            "",
            "",
            admin_exp, selling_exp,
            total_opex, ebit,
            "",
            finance_exp, pbt,
            other_exp, net_profit,
        ],
        "% of Revenue": [
            "",
            pct(gross_sales,    total_revenue),
            pct(sales_returns,  total_revenue),
            pct(sales_discounts,total_revenue),
            pct(swap_revenue,   total_revenue),
            pct(net_revenue,    total_revenue),
            "",
            "",
            "", "", "", "", "", "",
            pct(total_cogs_all, total_revenue),
            pct(adjusted_gp,    total_revenue),
            "",
            "",
            pct(admin_exp,   total_revenue),
            pct(selling_exp, total_revenue),
            pct(total_opex,  total_revenue),
            pct(ebit,        total_revenue),
            "",
            pct(finance_exp, total_revenue),
            pct(pbt,         total_revenue),
            "",
            pct(net_profit,  total_revenue),
        ]
    }
    is_df = pd.DataFrame(is_data)
    st.download_button(
        "📥 Download Income Statement (CSV)",
        is_df.to_csv(index=False),
        f"income_statement_{start_date}_{end_date}.csv",
        "text/csv"
    )

# ════════════════════════════════════════════════════════
# TAB 2 — COGS & INVENTORY
# ════════════════════════════════════════════════════════
with tabs[1]:
    st.markdown(
        '<div class="section-header">📦 COGS & Inventory Valuation</div>',
        unsafe_allow_html=True
    )

    if inv_df.empty:
        st.warning(
            "No inventory data. Upload your inventory file "
            "or add items via manual entry."
        )
    else:
        inv = inv_df.copy()

        # Numeric columns
        num_cols = [
            "unit_cost","selling_price","opening_qty","opening_value",
            "purchases_qty","purchases_value",
            "purchase_returns_qty","purchase_returns_value",
            "sales_qty","sales_value",
            "sales_returns_qty","sales_returns_value",
            "swap_out_qty","swap_in_qty","adjustments_qty",
            "closing_qty","closing_value","physical_count",
            "variance_qty","variance_value"
        ]
        for c in num_cols:
            if c in inv.columns:
                inv[c] = to_num(inv[c])
            else:
                inv[c] = 0.0

        # ── Pull period transactions ───────────────────────
        # Sales qty/value by item
        if not sales_df.empty and "item_description" in sales_df.columns:
            sales_df["quantity"]      = to_num(sales_df["quantity"])
            sales_df["cost_of_goods"] = to_num(sales_df["cost_of_goods"])
            sales_df["net_amount"]    = to_num(sales_df["net_amount"])
            s_agg = sales_df.groupby("item_description").agg(
                p_sales_qty=("quantity","sum"),
                p_sales_value=("cost_of_goods","sum"),
                p_sales_revenue=("net_amount","sum")
            ).reset_index().rename(
                columns={"item_description":"description"}
            )
            inv = inv.merge(s_agg, on="description", how="left")
        else:
            inv["p_sales_qty"]     = 0.0
            inv["p_sales_value"]   = 0.0
            inv["p_sales_revenue"] = 0.0

        # Purchases by item
        if not purch_df.empty and "item_description" in purch_df.columns:
            purch_df["quantity"]   = to_num(purch_df["quantity"])
            purch_df["total_cost"] = to_num(purch_df["total_cost"])
            p_agg = purch_df.groupby("item_description").agg(
                p_purch_qty=("quantity","sum"),
                p_purch_value=("total_cost","sum")
            ).reset_index().rename(
                columns={"item_description":"description"}
            )
            inv = inv.merge(p_agg, on="description", how="left")
        else:
            inv["p_purch_qty"]   = 0.0
            inv["p_purch_value"] = 0.0

        # Purchase returns by item
        if not pur_ret_df.empty and "item_description" in pur_ret_df.columns:
            pur_ret_df["quantity_returned"] = to_num(pur_ret_df["quantity_returned"])
            pur_ret_df["return_amount"]     = to_num(pur_ret_df["return_amount"])
            pr_agg = pur_ret_df.groupby("item_description").agg(
                p_pur_ret_qty=("quantity_returned","sum"),
                p_pur_ret_value=("return_amount","sum")
            ).reset_index().rename(
                columns={"item_description":"description"}
            )
            inv = inv.merge(pr_agg, on="description", how="left")
        else:
            inv["p_pur_ret_qty"]   = 0.0
            inv["p_pur_ret_value"] = 0.0

        # Sales returns by item
        if not sal_ret_df.empty and "item_description" in sal_ret_df.columns:
            sal_ret_df["quantity_returned"] = to_num(sal_ret_df["quantity_returned"])
            sal_ret_df["return_amount"]     = to_num(sal_ret_df["return_amount"])
            sr_agg = sal_ret_df.groupby("item_description").agg(
                p_sal_ret_qty=("quantity_returned","sum"),
                p_sal_ret_value=("return_amount","sum")
            ).reset_index().rename(
                columns={"item_description":"description"}
            )
            inv = inv.merge(sr_agg, on="description", how="left")
        else:
            inv["p_sal_ret_qty"]   = 0.0
            inv["p_sal_ret_value"] = 0.0

        # Fill NaN
        for c in inv.columns:
            if inv[c].dtype in [np.float64, np.int64]:
                inv[c] = inv[c].fillna(0)

        # ── Stock Movement Formula ─────────────────────────
        # Closing = Opening + Purchases - Purchase Returns
        #           - Sales + Sales Returns
        #           + Swap In - Swap Out + Adjustments
        inv["total_purch"]     = inv["purchases_qty"]   + inv["p_purch_qty"]
        inv["total_pur_ret"]   = inv["purchase_returns_qty"] + inv["p_pur_ret_qty"]
        inv["total_sales"]     = inv["sales_qty"]        + inv["p_sales_qty"]
        inv["total_sal_ret"]   = inv["sales_returns_qty"] + inv["p_sal_ret_qty"]
        inv["calc_closing"]    = (
            inv["opening_qty"]
            + inv["total_purch"]
            - inv["total_pur_ret"]
            - inv["total_sales"]
            + inv["total_sal_ret"]
            + inv["swap_in_qty"]
            - inv["swap_out_qty"]
            + inv["adjustments_qty"]
        )
        inv["calc_closing_value"] = inv["calc_closing"] * inv["unit_cost"]

        # Physical count default
        inv["physical_count"] = inv["physical_count"].replace(0, np.nan).fillna(
            inv["calc_closing"]
        )

        # Variance
        inv["qty_variance"]   = inv["physical_count"] - inv["calc_closing"]
        inv["value_variance"] = inv["qty_variance"] * inv["unit_cost"]
        inv["cogs_this_period"] = (
            inv["total_sales"] - inv["total_sal_ret"]
        ) * inv["unit_cost"]

        # Status
        def var_status(v):
            if abs(v) == 0:     return "✅ BALANCED"
            elif abs(v) <= 1:   return "🟡 MINOR"
            elif abs(v) <= 5:   return "🟠 MODERATE"
            elif abs(v) <= 20:  return "🔴 HIGH"
            else:               return "🆘 CRITICAL"
        inv["status"] = inv["qty_variance"].apply(var_status)

        # ── Summary Metrics ───────────────────────────────
        tot_open  = inv["opening_value"].sum()
        tot_purch = (inv["total_purch"] * inv["unit_cost"]).sum()
        tot_pur_r = (inv["total_pur_ret"] * inv["unit_cost"]).sum()
        tot_cogs  = inv["cogs_this_period"].sum()
        tot_close = inv["calc_closing_value"].sum()
        tot_phys  = (inv["physical_count"] * inv["unit_cost"]).sum()
        tot_var   = inv["value_variance"].sum()

        m = st.columns(5)
        m[0].metric("Opening Stock",      f"{tot_open:,.2f}")
        m[1].metric("+ Net Purchases",    f"{tot_purch-tot_pur_r:,.2f}")
        m[2].metric("- COGS",             f"{tot_cogs:,.2f}")
        m[3].metric("= Expected Closing", f"{tot_close:,.2f}")
        m[4].metric("Variance",           f"{tot_var:,.2f}",
                    delta_color="inverse")

        # COGS reconciliation box
        st.markdown(f"""
        <div style="background:#e8f5e9; border:2px solid #2e7d32;
                    border-radius:10px; padding:15px; margin:10px 0">
            <h4 style="margin:0 0 10px 0; color:#1b5e20">
                📦 COGS Calculation
            </h4>
            <div style="display:grid; grid-template-columns:1fr 1fr;
                        gap:10px; font-size:0.9em">
                <div>Opening Stock: <b>{tot_open:,.2f}</b></div>
                <div>+ Purchases: <b>{tot_purch:,.2f}</b></div>
                <div>- Purchase Returns: <b>({tot_pur_r:,.2f})</b></div>
                <div>= Goods Available: <b>{tot_open+tot_purch-tot_pur_r:,.2f}</b></div>
                <div>- Closing Stock: <b>({tot_phys:,.2f})</b></div>
                <div style="grid-column:1/-1; border-top:2px solid #2e7d32;
                            padding-top:8px; font-size:1.1em">
                    <b>= COST OF GOODS SOLD: {tot_open+tot_purch-tot_pur_r-tot_phys:,.2f}</b>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Movement chart
        top_items = inv.nlargest(15, "cogs_this_period")
        if not top_items.empty:
            fig_move = go.Figure()
            fig_move.add_trace(go.Bar(
                name="Opening", x=top_items["description"],
                y=top_items["opening_qty"], marker_color="#42a5f5"
            ))
            fig_move.add_trace(go.Bar(
                name="+ Purchases", x=top_items["description"],
                y=top_items["total_purch"], marker_color="#2e7d32"
            ))
            fig_move.add_trace(go.Bar(
                name="- Sales", x=top_items["description"],
                y=top_items["total_sales"], marker_color="#c62828"
            ))
            fig_move.add_trace(go.Bar(
                name="- Pur Returns", x=top_items["description"],
                y=top_items["total_pur_ret"], marker_color="#ff7043"
            ))
            fig_move.add_trace(go.Bar(
                name="+ Sal Returns", x=top_items["description"],
                y=top_items["total_sal_ret"], marker_color="#7e57c2"
            ))
            fig_move.add_trace(go.Scatter(
                name="Expected Closing",
                x=top_items["description"],
                y=top_items["calc_closing"],
                mode="markers+lines",
                marker=dict(size=10, color="#ff9800"),
                line=dict(color="#ff9800", dash="dot")
            ))
            fig_move.add_trace(go.Scatter(
                name="Physical Count",
                x=top_items["description"],
                y=top_items["physical_count"],
                mode="markers",
                marker=dict(size=14, color="#1a237e",
                            symbol="diamond")
            ))
            fig_move.update_layout(
                title="Stock Movement — Opening to Closing",
                barmode="group", height=420,
                xaxis_tickangle=-30
            )
            st.plotly_chart(fig_move, use_container_width=True)

        # Full inventory table
        display_cols = [
            "item_code","description","category",
            "opening_qty",
            "total_purch","total_pur_ret",
            "total_sales","total_sal_ret",
            "swap_out_qty","swap_in_qty","adjustments_qty",
            "calc_closing","physical_count",
            "qty_variance","unit_cost",
            "calc_closing_value",
            "cogs_this_period",
            "value_variance","status"
        ]
        avail = [c for c in display_cols if c in inv.columns]

        st.markdown("**Complete Stock Movement Report:**")
        st.dataframe(
            inv[avail].round(3),
            use_container_width=True, height=350
        )
        st.download_button(
            "📥 Download Inventory Report",
            inv[avail].round(3).to_csv(index=False),
            f"inventory_{start_date}_{end_date}.csv",
            "text/csv"
        )

# ════════════════════════════════════════════════════════
# TAB 3 — EXPENSES
# ════════════════════════════════════════════════════════
with tabs[2]:
    st.markdown(
        '<div class="section-header">💸 Expenses Analysis</div>',
        unsafe_allow_html=True
    )

    if exp_df.empty:
        st.info(
            "No expenses recorded for this period. "
            "Upload expenses via the Upload Documents page "
            "or use the Expenses module."
        )
    else:
        exp_df["net_amount"] = to_num(exp_df.get("net_amount", pd.Series(dtype=float)))
        exp_df["tax"]        = to_num(exp_df.get("tax",        pd.Series(dtype=float)))

        tot_exp = exp_df["net_amount"].sum()
        m = st.columns(4)
        m[0].metric("Total Expenses",  f"{tot_exp:,.2f}")
        m[1].metric("Transactions",    len(exp_df))
        m[2].metric("Avg Expense",     f"{exp_df['net_amount'].mean():,.2f}")
        m[3].metric("As % of Revenue",  pct(tot_exp, total_revenue))

        # By category
        if "category" in exp_df.columns:
            by_cat = exp_df.groupby("category").agg(
                Amount=("net_amount","sum"),
                Count=("net_amount","count")
            ).reset_index().sort_values("Amount", ascending=False)
            by_cat["% of Total"] = (
                by_cat["Amount"]/tot_exp*100
            ).round(1).astype(str) + "%"

            col_c, col_pie = st.columns([1,1])
            with col_c:
                st.markdown("**By Category:**")
                st.dataframe(by_cat, use_container_width=True, height=250)
            with col_pie:
                fig_cat = px.pie(
                    by_cat, names="category", values="Amount",
                    title="Expenses by Category",
                    color_discrete_sequence=px.colors.qualitative.Set2
                )
                st.plotly_chart(fig_cat, use_container_width=True)

        # By sub-category
        if "sub_category" in exp_df.columns:
            by_sub = exp_df.groupby(
                ["category","sub_category"]
            ).agg(
                Amount=("net_amount","sum"),
                Count=("net_amount","count")
            ).reset_index().sort_values("Amount", ascending=False)
            st.markdown("**By Sub-Category:**")
            st.dataframe(by_sub, use_container_width=True, height=250)

        # By period
        if "date" in exp_df.columns:
            exp_df["date"] = pd.to_datetime(exp_df["date"], errors="coerce")
            exp_df["month"] = exp_df["date"].dt.strftime("%Y-%m")
            by_month = exp_df.groupby("month").agg(
                Amount=("net_amount","sum")
            ).reset_index()
            fig_exp = px.bar(
                by_month, x="month", y="Amount",
                title="Expenses by Month",
                color_discrete_sequence=["#e53935"]
            )
            st.plotly_chart(fig_exp, use_container_width=True)

        st.markdown("**Full Expense Detail:**")
        st.dataframe(
            exp_df.sort_values("date").reset_index(drop=True),
            use_container_width=True, height=300
        )
        st.download_button(
            "📥 Download Expenses",
            exp_df.to_csv(index=False),
            f"expenses_{start_date}_{end_date}.csv",
            "text/csv"
        )

# ════════════════════════════════════════════════════════
# TAB 4 — CASH FLOW STATEMENT
# ════════════════════════════════════════════════════════
with tabs[3]:
    st.markdown(
        '<div class="section-header">🌊 Cash Flow Statement</div>',
        unsafe_allow_html=True
    )

    col_cf, col_cfc = st.columns([2,1])

    with col_cf:
        # Header
        st.markdown(f"""
        <div style="text-align:center; padding:15px; background:#f5f7ff;
                    border-radius:10px; margin-bottom:15px">
            <h3 style="margin:0; color:#1a237e">{company_name}</h3>
            <h4 style="margin:5px 0; color:#666">Cash Flow Statement</h4>
            <p style="margin:0; color:#888">
                {start_date.strftime("%d %b %Y")} to
                {end_date.strftime("%d %b %Y")}
            </p>
        </div>
        """, unsafe_allow_html=True)

        def cf_row(label, value, indent=0, total=False, section=False):
            pad = indent * 20
            if total:
                bg = "#1a237e"; fg = "white"; fw = "700"; sz = "1.05em"
            elif section:
                bg = "#e8eaf6"; fg = "#1a237e"; fw = "700"; sz = "0.95em"
            else:
                bg = "white";   fg = "#333";   fw = "400"; sz = "0.88em"

            val_color = (
                "white"    if total
                else "#2e7d32" if value >= 0
                else "#c62828"
            )
            val_str = fmt(value) if not section else ""

            st.markdown(f"""
            <div style="display:flex; justify-content:space-between;
                        align-items:center; padding:6px {pad+10}px;
                        background:{bg}; margin:1px 0; border-radius:4px;
                        border-bottom:1px solid #f0f0f0">
                <span style="color:{fg}; font-weight:{fw};
                             font-size:{sz}">{label}</span>
                <span style="color:{val_color}; font-weight:{fw};
                             font-size:{sz}">{val_str}</span>
            </div>
            """, unsafe_allow_html=True)

        # ── A: OPERATING ACTIVITIES ───────────────────────
        cf_row("A. CASH FROM OPERATING ACTIVITIES", 0, section=True)

        # Cash receipts
        cf_row("Cash Collected from Customers",   collected, indent=1)
        swap_collected = to_num(swap_df.get("customer_paid", pd.Series(dtype=float))).sum()
        cf_row("Cash from Swap Deals",            swap_collected, indent=1)
        total_receipts = collected + swap_collected

        # Cash payments
        cash_paid_suppliers = to_num(
            purch_df.get("total_cost", pd.Series(dtype=float))
        )[
            to_num(purch_df.get("payment_status", pd.Series(dtype=str)).apply(
                lambda x: 1 if str(x).lower() == "paid" else 0
            )) == 1
        ].sum() if not purch_df.empty else 0

        # Use bank debits as proxy for cash payments
        cash_payments_bank = to_num(bank_df.get("debit", pd.Series(dtype=float))).sum()

        # Expense payments
        exp_paid = to_num(exp_df.get("net_amount", pd.Series(dtype=float))).sum()

        cf_row("Less: Cash Paid to Suppliers",    cash_payments_bank, indent=1)
        cf_row("Less: Operating Expenses Paid",   exp_paid,           indent=1)

        net_operating = total_receipts - cash_payments_bank - exp_paid

        cf_row("NET CASH FROM OPERATIONS",        net_operating, total=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── B: INVESTING ACTIVITIES ───────────────────────
        cf_row("B. CASH FROM INVESTING ACTIVITIES", 0, section=True)
        # From banking credits that are not collections
        investing_in  = 0.0
        investing_out = 0.0
        cf_row("Capital Expenditure",      -investing_out, indent=1)
        cf_row("Proceeds from Asset Sales", investing_in,  indent=1)
        net_investing = investing_in - investing_out
        cf_row("NET CASH FROM INVESTING",   net_investing, total=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── C: FINANCING ACTIVITIES ───────────────────────
        cf_row("C. CASH FROM FINANCING ACTIVITIES", 0, section=True)
        fin_in  = 0.0
        fin_out = finance_exp
        cf_row("Loan Proceeds",           fin_in,  indent=1)
        cf_row("Finance Costs Paid",     -fin_out, indent=1)
        net_financing = fin_in - fin_out
        cf_row("NET CASH FROM FINANCING", net_financing, total=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Net Cash Movement ─────────────────────────────
        net_cash_total = net_operating + net_investing + net_financing

        # Opening and Closing bank balance
        bank_sorted = bank_df.sort_values("date") if not bank_df.empty else bank_df
        open_bal  = float(bank_sorted["balance"].iloc[0])  if not bank_sorted.empty and "balance" in bank_sorted.columns else 0.0
        close_bal = float(bank_sorted["balance"].iloc[-1]) if not bank_sorted.empty and "balance" in bank_sorted.columns else 0.0

        cf_row("Opening Cash Balance",   open_bal,        indent=1)
        cf_row("Net Cash Movement",      net_cash_total,  indent=1)
        cf_row("CLOSING CASH BALANCE",   close_bal,       total=True)

        # Cash Flow Summary Table
        cf_summary = pd.DataFrame({
            "Section": [
                "Operating Activities",
                "Investing Activities",
                "Financing Activities",
                "NET CASH MOVEMENT",
                "Opening Balance",
                "Closing Balance"
            ],
            "Amount": [
                net_operating,
                net_investing,
                net_financing,
                net_cash_total,
                open_bal,
                close_bal
            ]
        })
        st.download_button(
            "📥 Download Cash Flow Statement",
            cf_summary.to_csv(index=False),
            f"cashflow_{start_date}_{end_date}.csv",
            "text/csv"
        )

    with col_cfc:
        # Cash flow chart
        fig_cf = go.Figure(go.Waterfall(
            name="Cash Flow",
            orientation="v",
            measure=["relative","relative","relative","total"],
            x=["Operating","Investing","Financing","Net Movement"],
            y=[net_operating, net_investing, net_financing, net_cash_total],
            connector={"line":{"color":"#1a237e"}},
            increasing={"marker":{"color":"#2e7d32"}},
            decreasing={"marker":{"color":"#c62828"}},
            totals={"marker":{"color":"#1a237e"}},
            textposition="outside",
            text=[fmt(v) for v in [
                net_operating, net_investing,
                net_financing, net_cash_total
            ]],
        ))
        fig_cf.update_layout(
            title="Cash Flow Waterfall",
            height=400, showlegend=False
        )
        st.plotly_chart(fig_cf, use_container_width=True)

        # Bank balance trend
        if not bank_df.empty and "balance" in bank_df.columns:
            bk = bank_df.copy()
            bk["date"] = pd.to_datetime(bk["date"], errors="coerce")
            bk = bk.sort_values("date")
            bk["balance"] = to_num(bk["balance"])
            fig_bal = px.area(
                bk, x="date", y="balance",
                title="Bank Balance Trend",
                color_discrete_sequence=["#1a237e"]
            )
            fig_bal.add_hline(y=0, line_dash="dash", line_color="red")
            st.plotly_chart(fig_bal, use_container_width=True)

# ════════════════════════════════════════════════════════
# TAB 5 — SUMMARY DASHBOARD
# ════════════════════════════════════════════════════════
with tabs[4]:
    st.markdown(
        '<div class="section-header">📋 Financial Summary Dashboard</div>',
        unsafe_allow_html=True
    )

    # Key ratios
    ratios = [
        ("Gross Profit Margin",  pct(adjusted_gp,  total_revenue), "Revenue-COGS/Revenue"),
        ("Net Profit Margin",    pct(net_profit,   total_revenue), "Net Profit/Revenue"),
        ("EBIT Margin",          pct(ebit,         total_revenue), "EBIT/Revenue"),
        ("COGS %",               pct(total_cogs_all,total_revenue),"COGS/Revenue"),
        ("OpEx Ratio",           pct(total_opex,   total_revenue), "OpEx/Revenue"),
        ("Return Rate",          pct(sales_returns, gross_sales),  "Returns/Gross Sales"),
        ("Purch Return Rate",    pct(purchase_returns, purchases_cost),"Pur Returns/Purchases"),
        ("Collections Rate",     pct(collected,    net_revenue),  "Collections/Revenue"),
    ]

    rc = st.columns(4)
    for i,(name,val,note) in enumerate(ratios):
        with rc[i%4]:
            st.markdown(f"""
            <div style="background:white; padding:15px; border-radius:10px;
                        border-left:5px solid #1a237e;
                        box-shadow:0 2px 6px rgba(0,0,0,0.07);
                        margin-bottom:10px">
                <div style="font-size:0.72em; color:#888;
                             text-transform:uppercase">{name}</div>
                <div style="font-size:1.4em; font-weight:700;
                             color:#1a237e">{val}</div>
                <div style="font-size:0.7em; color:#aaa">{note}</div>
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    # Comparative P&L
    col_pl, col_tb = st.columns(2)

    with col_pl:
        pl_data = {
            "Item":   ["Revenue","COGS","Gross Profit",
                       "OpEx","EBIT","Finance","Net Profit"],
            "Amount": [total_revenue, total_cogs_all, adjusted_gp,
                       total_opex, ebit, finance_exp, net_profit],
        }
        pl_df = pd.DataFrame(pl_data)
        pl_df["Color"] = pl_df["Amount"].apply(
            lambda x: "#2e7d32" if x >= 0 else "#c62828"
        )
        fig_pl = px.bar(
            pl_df, x="Item", y="Amount",
            title="P&L Summary",
            color="Color",
            color_discrete_map="identity"
        )
        st.plotly_chart(fig_pl, use_container_width=True)

    with col_tb:
        # Summary table
        summary = pd.DataFrame({
            "Metric":  [
                "Gross Sales", "Sales Returns", "Purch Returns",
                "Net Revenue", "COGS", "Gross Profit",
                "Admin Exp", "Selling Exp", "Finance Exp",
                "Total Expenses", "Net Profit",
                "Cash Collected", "Bank Balance"
            ],
            "Amount": [
                gross_sales, sales_returns, purchase_returns,
                net_revenue, total_cogs_all, adjusted_gp,
                admin_exp, selling_exp, finance_exp,
                total_opex + finance_exp, net_profit,
                collected, close_bal
            ],
            "% Revenue": [
                pct(gross_sales,       total_revenue),
                pct(sales_returns,     total_revenue),
                pct(purchase_returns,  purchases_cost),
                pct(net_revenue,       total_revenue),
                pct(total_cogs_all,    total_revenue),
                pct(adjusted_gp,       total_revenue),
                pct(admin_exp,         total_revenue),
                pct(selling_exp,       total_revenue),
                pct(finance_exp,       total_revenue),
                pct(total_opex+finance_exp, total_revenue),
                pct(net_profit,        total_revenue),
                pct(collected,         net_revenue),
                "",
            ]
        })
        st.dataframe(summary, use_container_width=True, height=400)
        st.download_button(
            "📥 Download Full Summary",
            summary.to_csv(index=False),
            f"financial_summary_{start_date}_{end_date}.csv",
            "text/csv"
        )

st.markdown("""
<div class="finteca-footer">
    Finteca AuditRep v1.0.0 · Income Statement ·
    Cash Flow · Inventory COGS
</div>
""", unsafe_allow_html=True)
