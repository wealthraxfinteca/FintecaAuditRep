import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sqlite3
import os
from pathlib import Path
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
load_dotenv()

st.set_page_config(
    page_title="Trial Balance - Finteca AuditRep",
    page_icon="🏦",
    layout="wide"
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
.section-header {
    background:#f5f7ff; border-left:4px solid #1a237e; padding:10px 15px;
    border-radius:0 8px 8px 0; margin:15px 0; font-weight:600; color:#1a237e;
}
.metric-card {
    background:white; padding:15px; border-radius:10px;
    border-left:5px solid #1a237e;
    box-shadow:0 2px 8px rgba(0,0,0,0.08); margin-bottom:8px;
    text-align:center;
}
.metric-card h3 { color:#666; font-size:0.75em; margin:0 0 4px 0; text-transform:uppercase; }
.metric-card h2 { color:#1a237e; font-size:1.4em; margin:0; font-weight:700; }
.metric-card small { color:#999; font-size:0.7em; }
.tb-positive { color:#2e7d32; font-weight:600; }
.tb-negative { color:#c62828; font-weight:600; }
.tb-neutral  { color:#1a237e; font-weight:600; }
.period-btn {
    background:#1a237e; color:white; border:none; padding:6px 14px;
    border-radius:20px; cursor:pointer; margin:2px; font-size:0.8em;
}
.alert-info {
    background:#e3f2fd; border-left:4px solid #1976d2;
    padding:10px 15px; border-radius:6px; margin:6px 0;
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
    <p>Extended Trial Balance · Transaction Ledger · Period Reports</p>
    <span class="finteca-badge">Module 4 — Trial Balance & Period Reports</span>
</div>
""", unsafe_allow_html=True)

DB_PATH = (st.session_state.get("active_db_path") or
    ("/tmp/reconciliation.db" if os.path.exists("/mount/src")
     else "data/reconciliation.db"))

# ── Database helpers ──────────────────────────────────────
def load(table):
    try:
        conn = sqlite3.connect(DB_PATH)
        df   = pd.read_sql(f"SELECT * FROM {table}", conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

def to_num(s):
    return pd.to_numeric(s, errors="coerce").fillna(0)

def parse_dates(df, col="date"):
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors="coerce")
    return df

def filter_by_date(df, start, end, col="date"):
    if df.empty or col not in df.columns:
        return df
    df = parse_dates(df, col)
    mask = (df[col].dt.date >= start) & (df[col].dt.date <= end)
    return df[mask].copy()

# ── Date Range Selector ───────────────────────────────────
st.markdown(
    '<div class="section-header">📅 Select Report Period</div>',
    unsafe_allow_html=True
)

col_period, col_dates = st.columns([1, 2])

with col_period:
    st.markdown("**Quick Select:**")
    period_cols = st.columns(3)

    today     = date.today()
    presets   = {
        "Today":     (today, today),
        "This Week": (today - timedelta(days=today.weekday()), today),
        "This Month":(today.replace(day=1), today),
        "Last Month":(
            (today.replace(day=1) - timedelta(days=1)).replace(day=1),
            today.replace(day=1) - timedelta(days=1)
        ),
        "This Qtr":  (
            date(today.year, ((today.month-1)//3)*3+1, 1),
            today
        ),
        "Last Qtr":  (
            date(
                today.year if ((today.month-1)//3)*3+1 > 3
                else today.year-1,
                (((today.month-1)//3)*3+1-3) % 12 or 12,
                1
            ),
            date(today.year, ((today.month-1)//3)*3+1, 1) - timedelta(days=1)
        ),
        "This Year": (date(today.year, 1, 1), today),
        "Last Year": (date(today.year-1, 1, 1), date(today.year-1, 12, 31)),
        "All Time":  (date(2000, 1, 1), today),
    }

    if "date_start" not in st.session_state:
        st.session_state.date_start = today.replace(day=1)
    if "date_end" not in st.session_state:
        st.session_state.date_end = today

    btn_cols = st.columns(3)
    preset_list = list(presets.items())
    for i, (label, (s, e)) in enumerate(preset_list):
        with btn_cols[i % 3]:
            if st.button(label, key=f"preset_{label}",
                         use_container_width=True):
                st.session_state.date_start = s
                st.session_state.date_end   = e

with col_dates:
    st.markdown("**Custom Date Range:**")
    dc1, dc2 = st.columns(2)
    with dc1:
        start_date = st.date_input(
            "From Date",
            value=st.session_state.date_start,
            key="start_date_input"
        )
    with dc2:
        end_date = st.date_input(
            "To Date",
            value=st.session_state.date_end,
            key="end_date_input"
        )
    st.session_state.date_start = start_date
    st.session_state.date_end   = end_date

    period_days = (end_date - start_date).days + 1
    st.markdown(
        f'<div class="alert-info">'
        f'📊 <b>Report Period:</b> {start_date.strftime("%d %b %Y")} → '
        f'{end_date.strftime("%d %b %Y")} '
        f'({period_days} days)</div>',
        unsafe_allow_html=True
    )

    group_by = st.selectbox(
        "Group Transactions By:",
        ["Daily", "Weekly", "Monthly", "Quarterly", "Yearly"],
        index=2
    )

st.divider()

# ── Load and filter all tables ────────────────────────────
sales_raw    = filter_by_date(load("sales"),         start_date, end_date)
purch_raw    = filter_by_date(load("purchases"),     start_date, end_date)
bank_raw     = filter_by_date(load("banking"),       start_date, end_date)
coll_raw     = filter_by_date(load("collections"),   start_date, end_date)
ret_raw      = filter_by_date(load("sales_returns"), start_date, end_date)
swap_raw     = filter_by_date(load("swap_deals"),    start_date, end_date)
inv_raw      = load("inventory")

# ── Period grouping function ──────────────────────────────
def get_period_key(df, col="date"):
    if df.empty or col not in df.columns:
        return df
    df = df.copy()
    df[col] = pd.to_datetime(df[col], errors="coerce")
    if group_by == "Daily":
        df["period"] = df[col].dt.strftime("%Y-%m-%d")
    elif group_by == "Weekly":
        df["period"] = df[col].dt.to_period("W").astype(str)
    elif group_by == "Monthly":
        df["period"] = df[col].dt.strftime("%Y-%m")
    elif group_by == "Quarterly":
        df["period"] = df[col].dt.to_period("Q").astype(str)
    else:
        df["period"] = df[col].dt.strftime("%Y")
    return df

# ── Tabs ─────────────────────────────────────────────────
tabs = st.tabs([
    "📋 Extended Trial Balance",
    "📊 Period Summary",
    "💰 Sales Ledger",
    "🛒 Purchase Ledger",
    "🏦 Bank Ledger",
    "💵 Collections Ledger",
    "📦 Inventory Movement",
    "↩️ Returns & Swaps",
    "⚖️ Debtors & Creditors",
    "📈 Charts & Trends",
])

# ════════════════════════════════════════════════════════
# TAB 1 — EXTENDED TRIAL BALANCE
# ════════════════════════════════════════════════════════
with tabs[0]:
    st.markdown(
        '<div class="section-header">'
        '📋 Extended Trial Balance — All Transactions Side by Side'
        '</div>',
        unsafe_allow_html=True
    )

    # Build unified transaction ledger
    all_entries = []

    # Sales entries
    for _, r in sales_raw.iterrows():
        amt = to_num(pd.Series([r.get("net_amount", 0)])).iloc[0]
        cog = to_num(pd.Series([r.get("cost_of_goods", 0)])).iloc[0]
        gp  = amt - cog
        all_entries.append({
            "date":        r.get("date"),
            "type":        "SALE",
            "reference":   str(r.get("invoice_number", "") or ""),
            "party":       str(r.get("customer", "") or ""),
            "description": str(r.get("item_description", "") or ""),
            "qty":         to_num(pd.Series([r.get("quantity", 0)])).iloc[0],
            "sales_dr":    0,
            "sales_cr":    amt,
            "cogs_dr":     cog,
            "cogs_cr":     0,
            "gross_profit":gp,
            "purchases_dr":0,
            "purchases_cr":0,
            "bank_dr":     0,
            "bank_cr":     0,
            "collection":  0,
            "returns":     0,
            "swap_value":  0,
            "discount":    to_num(pd.Series([r.get("discount", 0)])).iloc[0],
            "payment_method": str(r.get("payment_method", "") or ""),
            "salesperson": str(r.get("salesperson", "") or ""),
            "source":      "Sales",
        })

    # Purchase entries
    for _, r in purch_raw.iterrows():
        amt = to_num(pd.Series([r.get("total_cost", 0)])).iloc[0]
        all_entries.append({
            "date":        r.get("date"),
            "type":        "PURCHASE",
            "reference":   str(r.get("reference_number", "") or ""),
            "party":       str(r.get("supplier", "") or ""),
            "description": str(r.get("item_description", "") or ""),
            "qty":         to_num(pd.Series([r.get("quantity", 0)])).iloc[0],
            "sales_dr":    0,
            "sales_cr":    0,
            "cogs_dr":     0,
            "cogs_cr":     0,
            "gross_profit":0,
            "purchases_dr":amt,
            "purchases_cr":0,
            "bank_dr":     0,
            "bank_cr":     0,
            "collection":  0,
            "returns":     0,
            "swap_value":  0,
            "discount":    to_num(pd.Series([r.get("discount", 0)])).iloc[0],
            "payment_method": str(r.get("payment_method", "") or ""),
            "salesperson": "",
            "source":      "Purchases",
        })

    # Banking entries
    for _, r in bank_raw.iterrows():
        dr = to_num(pd.Series([r.get("debit", 0)])).iloc[0]
        cr = to_num(pd.Series([r.get("credit", 0)])).iloc[0]
        all_entries.append({
            "date":        r.get("date"),
            "type":        "BANKING",
            "reference":   str(r.get("reference", "") or ""),
            "party":       str(r.get("description", "") or ""),
            "description": str(r.get("description", "") or ""),
            "qty":         0,
            "sales_dr":    0,
            "sales_cr":    0,
            "cogs_dr":     0,
            "cogs_cr":     0,
            "gross_profit":0,
            "purchases_dr":0,
            "purchases_cr":0,
            "bank_dr":     dr,
            "bank_cr":     cr,
            "collection":  0,
            "returns":     0,
            "swap_value":  0,
            "discount":    0,
            "payment_method": str(r.get("transaction_type", "") or ""),
            "salesperson": "",
            "source":      "Banking",
        })

    # Collections entries
    for _, r in coll_raw.iterrows():
        amt = to_num(pd.Series([r.get("amount", 0)])).iloc[0]
        all_entries.append({
            "date":        r.get("date"),
            "type":        "COLLECTION",
            "reference":   str(r.get("invoice_reference", "") or ""),
            "party":       str(r.get("customer", "") or ""),
            "description": f"Collection from {r.get('customer','')}",
            "qty":         0,
            "sales_dr":    0,
            "sales_cr":    0,
            "cogs_dr":     0,
            "cogs_cr":     0,
            "gross_profit":0,
            "purchases_dr":0,
            "purchases_cr":0,
            "bank_dr":     0,
            "bank_cr":     0,
            "collection":  amt,
            "returns":     0,
            "swap_value":  0,
            "discount":    0,
            "payment_method": str(r.get("payment_method", "") or ""),
            "salesperson": str(r.get("received_by", "") or ""),
            "source":      "Collections",
        })

    # Returns entries
    for _, r in ret_raw.iterrows():
        amt = to_num(pd.Series([r.get("return_amount", 0)])).iloc[0]
        all_entries.append({
            "date":        r.get("date"),
            "type":        "RETURN",
            "reference":   str(r.get("return_reference", "") or ""),
            "party":       str(r.get("customer", "") or ""),
            "description": str(r.get("item_description", "") or ""),
            "qty":         to_num(pd.Series([r.get("quantity_returned", 0)])).iloc[0],
            "sales_dr":    amt,
            "sales_cr":    0,
            "cogs_dr":     0,
            "cogs_cr":     0,
            "gross_profit":-amt,
            "purchases_dr":0,
            "purchases_cr":0,
            "bank_dr":     0,
            "bank_cr":     0,
            "collection":  0,
            "returns":     amt,
            "swap_value":  0,
            "discount":    0,
            "payment_method": str(r.get("refund_method", "") or ""),
            "salesperson": str(r.get("approved_by", "") or ""),
            "source":      "Returns",
        })

    # Swap entries
    for _, r in swap_raw.iterrows():
        diff = to_num(pd.Series([r.get("difference_amount", 0)])).iloc[0]
        val  = to_num(pd.Series([r.get("value_given_out", 0)])).iloc[0]
        all_entries.append({
            "date":        r.get("date"),
            "type":        "SWAP",
            "reference":   str(r.get("deal_reference", "") or ""),
            "party":       str(r.get("customer", "") or ""),
            "description": (
                f"Swap: {r.get('item_given_out','')} → "
                f"{r.get('item_received','')}"
            ),
            "qty":         0,
            "sales_dr":    0,
            "sales_cr":    diff,
            "cogs_dr":     0,
            "cogs_cr":     0,
            "gross_profit":0,
            "purchases_dr":0,
            "purchases_cr":0,
            "bank_dr":     0,
            "bank_cr":     0,
            "collection":  diff,
            "returns":     0,
            "swap_value":  val,
            "discount":    0,
            "payment_method": str(r.get("payment_method", "") or ""),
            "salesperson": str(r.get("approved_by", "") or ""),
            "source":      "Swaps",
        })

    if not all_entries:
        st.warning(
            "No transactions found for the selected period. "
            "Upload documents or adjust the date range."
        )
    else:
        tb_df = pd.DataFrame(all_entries)
        tb_df["date"] = pd.to_datetime(tb_df["date"], errors="coerce")
        tb_df = tb_df.sort_values("date").reset_index(drop=True)
        tb_df["date_str"] = tb_df["date"].dt.strftime("%Y-%m-%d")

        # ── Summary Totals ────────────────────────────────
        st.markdown("**📊 Period Totals**")
        tc1,tc2,tc3,tc4,tc5,tc6,tc7,tc8 = st.columns(8)
        tc1.metric("💰 Sales",
                   f"{tb_df['sales_cr'].sum():,.0f}")
        tc2.metric("↩️ Returns",
                   f"{tb_df['returns'].sum():,.0f}")
        tc3.metric("📈 Net Revenue",
                   f"{tb_df['sales_cr'].sum()-tb_df['returns'].sum():,.0f}")
        tc4.metric("📦 Purchases",
                   f"{tb_df['purchases_dr'].sum():,.0f}")
        tc5.metric("💵 Collections",
                   f"{tb_df['collection'].sum():,.0f}")
        tc6.metric("🏦 Bank In",
                   f"{tb_df['bank_cr'].sum():,.0f}")
        tc7.metric("🏦 Bank Out",
                   f"{tb_df['bank_dr'].sum():,.0f}")
        tc8.metric("📊 Gross Profit",
                   f"{tb_df['gross_profit'].sum():,.0f}")

        st.divider()

        # ── Filter controls ───────────────────────────────
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            type_filter = st.multiselect(
                "Filter by Transaction Type:",
                options=tb_df["type"].unique().tolist(),
                default=tb_df["type"].unique().tolist(),
                key="tb_type_filter"
            )
        with fc2:
            party_search = st.text_input(
                "Search Party (Customer/Supplier):",
                placeholder="Type name to filter...",
                key="tb_party_search"
            )
        with fc3:
            min_amt = st.number_input(
                "Minimum Amount:",
                min_value=0.0,
                value=0.0,
                key="tb_min_amt"
            )

        # Apply filters
        filtered_tb = tb_df[tb_df["type"].isin(type_filter)]
        if party_search:
            filtered_tb = filtered_tb[
                filtered_tb["party"].str.contains(
                    party_search, case=False, na=False
                )
            ]
        if min_amt > 0:
            max_col = filtered_tb[[
                "sales_cr","purchases_dr","bank_cr",
                "bank_dr","collection","returns"
            ]].max(axis=1)
            filtered_tb = filtered_tb[max_col >= min_amt]

        # ── Display columns ───────────────────────────────
        display_cols = [
            "date_str", "type", "reference", "party",
            "description", "qty",
            "sales_cr", "returns", "purchases_dr",
            "collection", "bank_cr", "bank_dr",
            "gross_profit", "discount",
            "payment_method", "salesperson", "source"
        ]
        display_labels = {
            "date_str":       "Date",
            "type":           "Type",
            "reference":      "Reference",
            "party":          "Customer/Supplier",
            "description":    "Description",
            "qty":            "Qty",
            "sales_cr":       "Sales (CR)",
            "returns":        "Returns (DR)",
            "purchases_dr":   "Purchases (DR)",
            "collection":     "Cash Collected",
            "bank_cr":        "Bank In (CR)",
            "bank_dr":        "Bank Out (DR)",
            "gross_profit":   "Gross Profit",
            "discount":       "Discount",
            "payment_method": "Payment Method",
            "salesperson":    "Salesperson/By",
            "source":         "Source",
        }

        show_df = filtered_tb[display_cols].rename(
            columns=display_labels
        )

        # Color coding
        def color_tb_row(row):
            colors = {
                "SALE":       "background-color:#f1f8e9",
                "PURCHASE":   "background-color:#fff3e0",
                "BANKING":    "background-color:#e3f2fd",
                "COLLECTION": "background-color:#f3e5f5",
                "RETURN":     "background-color:#ffebee",
                "SWAP":       "background-color:#e8eaf6",
            }
            t = row.get("Type", "")
            color = colors.get(t, "")
            return [color] * len(row)

        st.dataframe(
            show_df.style.apply(color_tb_row, axis=1),
            use_container_width=True,
            height=500,
        )

        st.caption(
            f"Showing {len(show_df)} of {len(tb_df)} transactions"
        )

        # ── Edit / Modify row ─────────────────────────────
        with st.expander("✏️ Modify a Transaction", expanded=False):
            st.info(
                "Select a row number to edit. "
                "Changes update the display only — "
                "use manual entry to add corrected records."
            )
            row_idx = st.number_input(
                "Row number to inspect:",
                min_value=0,
                max_value=max(len(filtered_tb)-1, 0),
                value=0
            )
            if not filtered_tb.empty:
                sel_row = filtered_tb.iloc[row_idx]
                st.json({
                    k: str(v) for k, v in sel_row.items()
                    if k not in ["date"]
                })

        # ── Download ──────────────────────────────────────
        dc1, dc2, dc3 = st.columns(3)
        with dc1:
            st.download_button(
                "📥 Download Full Trial Balance (CSV)",
                show_df.to_csv(index=False),
                f"trial_balance_{start_date}_{end_date}.csv",
                "text/csv",
                use_container_width=True
            )
        with dc2:
            # Summary download
            summary = show_df.select_dtypes(include=[np.number]).sum()
            st.download_button(
                "📥 Download Summary (CSV)",
                summary.to_frame("Total").to_csv(),
                f"tb_summary_{start_date}_{end_date}.csv",
                "text/csv",
                use_container_width=True
            )
        with dc3:
            # Sales only
            sales_only = show_df[show_df["Type"] == "SALE"]
            if not sales_only.empty:
                st.download_button(
                    "📥 Download Sales Only (CSV)",
                    sales_only.to_csv(index=False),
                    f"sales_{start_date}_{end_date}.csv",
                    "text/csv",
                    use_container_width=True
                )

# ════════════════════════════════════════════════════════
# TAB 2 — PERIOD SUMMARY
# ════════════════════════════════════════════════════════
with tabs[1]:
    st.markdown(
        '<div class="section-header">📊 Period Summary Report</div>',
        unsafe_allow_html=True
    )

    if not all_entries:
        st.warning("No data for selected period.")
    else:
        tb_df2 = pd.DataFrame(all_entries)
        tb_df2["date"] = pd.to_datetime(tb_df2["date"], errors="coerce")
        tb_df2 = get_period_key(tb_df2)

        period_summary = tb_df2.groupby("period").agg(
            Sales=("sales_cr", "sum"),
            Returns=("returns", "sum"),
            Net_Revenue=("sales_cr", "sum"),
            COGS=("cogs_dr", "sum"),
            Gross_Profit=("gross_profit", "sum"),
            Purchases=("purchases_dr", "sum"),
            Collections=("collection", "sum"),
            Bank_In=("bank_cr", "sum"),
            Bank_Out=("bank_dr", "sum"),
            Discounts=("discount", "sum"),
            Swaps=("swap_value", "sum"),
            Transactions=("type", "count")
        ).reset_index()

        period_summary["Net_Revenue"] = (
            period_summary["Sales"] - period_summary["Returns"]
        )
        period_summary["Net_Cash"] = (
            period_summary["Bank_In"] - period_summary["Bank_Out"]
        )
        period_summary["Gross_Margin_%"] = (
            period_summary["Gross_Profit"]
            / period_summary["Net_Revenue"].clip(lower=0.01)
            * 100
        ).round(1)

        # Running totals
        num_cols = [
            "Sales","Returns","Net_Revenue","COGS",
            "Gross_Profit","Purchases","Collections",
            "Bank_In","Bank_Out","Net_Cash"
        ]
        for col in num_cols:
            period_summary[f"Running_{col}"] = (
                period_summary[col].cumsum()
            )

        # Display
        st.dataframe(
            period_summary.style.background_gradient(
                subset=["Net_Revenue","Gross_Profit","Net_Cash"],
                cmap="RdYlGn"
            ),
            use_container_width=True,
            height=400
        )

        # Period trend chart
        fig_period = make_subplots(
            rows=2, cols=2,
            subplot_titles=[
                "Sales vs Returns vs Net Revenue",
                "Gross Profit by Period",
                "Cash In vs Cash Out",
                "Purchases vs Collections"
            ]
        )

        fig_period.add_trace(
            go.Bar(name="Sales", x=period_summary["period"],
                   y=period_summary["Sales"], marker_color="#1a237e"),
            row=1, col=1
        )
        fig_period.add_trace(
            go.Bar(name="Returns", x=period_summary["period"],
                   y=period_summary["Returns"], marker_color="#c62828"),
            row=1, col=1
        )
        fig_period.add_trace(
            go.Scatter(name="Net Revenue", x=period_summary["period"],
                       y=period_summary["Net_Revenue"],
                       line=dict(color="#2e7d32", width=3)),
            row=1, col=1
        )
        fig_period.add_trace(
            go.Bar(name="Gross Profit", x=period_summary["period"],
                   y=period_summary["Gross_Profit"],
                   marker_color="#42a5f5"),
            row=1, col=2
        )
        fig_period.add_trace(
            go.Bar(name="Bank In", x=period_summary["period"],
                   y=period_summary["Bank_In"], marker_color="#2e7d32"),
            row=2, col=1
        )
        fig_period.add_trace(
            go.Bar(name="Bank Out", x=period_summary["period"],
                   y=period_summary["Bank_Out"], marker_color="#c62828"),
            row=2, col=1
        )
        fig_period.add_trace(
            go.Bar(name="Purchases", x=period_summary["period"],
                   y=period_summary["Purchases"], marker_color="#ff7043"),
            row=2, col=2
        )
        fig_period.add_trace(
            go.Bar(name="Collections", x=period_summary["period"],
                   y=period_summary["Collections"],
                   marker_color="#7e57c2"),
            row=2, col=2
        )

        fig_period.update_layout(
            height=600,
            title_text=f"Period Analysis — {group_by}",
            barmode="group"
        )
        st.plotly_chart(fig_period, use_container_width=True)

        st.download_button(
            "📥 Download Period Summary",
            period_summary.to_csv(index=False),
            f"period_summary_{start_date}_{end_date}.csv",
            "text/csv"
        )

# ════════════════════════════════════════════════════════
# TAB 3 — SALES LEDGER
# ════════════════════════════════════════════════════════
with tabs[2]:
    st.markdown(
        '<div class="section-header">💰 Sales Ledger</div>',
        unsafe_allow_html=True
    )

    if sales_raw.empty:
        st.warning("No sales data for selected period.")
    else:
        sales_raw["net_amount"]    = to_num(
            sales_raw.get("net_amount", pd.Series(dtype=float))
        )
        sales_raw["cost_of_goods"] = to_num(
            sales_raw.get("cost_of_goods", pd.Series(dtype=float))
        )
        sales_raw["discount"]      = to_num(
            sales_raw.get("discount", pd.Series(dtype=float))
        )
        sales_raw["gross_profit"]  = (
            sales_raw["net_amount"] - sales_raw["cost_of_goods"]
        )

        # Metrics
        m1,m2,m3,m4,m5,m6 = st.columns(6)
        m1.metric("Total Sales",     f"{sales_raw['net_amount'].sum():,.2f}")
        m2.metric("Transactions",    len(sales_raw))
        m3.metric("Avg Sale",
                  f"{sales_raw['net_amount'].mean():,.2f}")
        m4.metric("Gross Profit",
                  f"{sales_raw['gross_profit'].sum():,.2f}")
        m5.metric("Total Discounts",
                  f"{sales_raw['discount'].sum():,.2f}")
        m6.metric("Gross Margin",
                  f"{sales_raw['gross_profit'].sum()/sales_raw['net_amount'].sum()*100 if sales_raw['net_amount'].sum() else 0:.1f}%")

        # Group by period
        sales_period = get_period_key(sales_raw.copy())
        if "period" in sales_period.columns:
            by_period = sales_period.groupby("period").agg(
                Sales=("net_amount","sum"),
                COGS=("cost_of_goods","sum"),
                Profit=("gross_profit","sum"),
                Discounts=("discount","sum"),
                Transactions=("net_amount","count")
            ).reset_index()
            by_period["Margin_%"] = (
                by_period["Profit"]
                / by_period["Sales"].clip(lower=0.01)
                * 100
            ).round(1)
            by_period["Running_Sales"] = by_period["Sales"].cumsum()

            fig_sales = px.bar(
                by_period,
                x="period", y=["Sales","COGS","Profit"],
                title=f"Sales Analysis by {group_by}",
                barmode="group",
                color_discrete_sequence=["#1a237e","#e53935","#2e7d32"]
            )
            st.plotly_chart(fig_sales, use_container_width=True)
            st.dataframe(by_period, use_container_width=True, height=250)

        # By customer
        if "customer" in sales_raw.columns:
            by_cust = sales_raw.groupby("customer").agg(
                Sales=("net_amount","sum"),
                Transactions=("net_amount","count"),
                Avg_Sale=("net_amount","mean"),
                Profit=("gross_profit","sum")
            ).reset_index().sort_values("Sales", ascending=False)
            st.markdown("**Top Customers:**")
            st.dataframe(by_cust.head(20),
                         use_container_width=True, height=250)

        # By item
        if "item_description" in sales_raw.columns:
            by_item = sales_raw.groupby("item_description").agg(
                Sales=("net_amount","sum"),
                Qty=("quantity","sum"),
                Profit=("gross_profit","sum"),
                Transactions=("net_amount","count")
            ).reset_index().sort_values("Sales", ascending=False)
            st.markdown("**Sales by Item:**")
            fig_item = px.bar(
                by_item.head(15),
                x="item_description", y="Sales",
                color="Profit",
                color_continuous_scale="RdYlGn",
                title="Top Items by Sales Value"
            )
            st.plotly_chart(fig_item, use_container_width=True)

        # Detail table
        st.markdown("**Full Sales Detail:**")
        st.dataframe(
            sales_raw.sort_values("date").reset_index(drop=True),
            use_container_width=True, height=300
        )
        st.download_button(
            "📥 Download Sales Ledger",
            sales_raw.to_csv(index=False),
            f"sales_ledger_{start_date}_{end_date}.csv",
            "text/csv"
        )

# ════════════════════════════════════════════════════════
# TAB 4 — PURCHASE LEDGER
# ════════════════════════════════════════════════════════
with tabs[3]:
    st.markdown(
        '<div class="section-header">🛒 Purchase Ledger</div>',
        unsafe_allow_html=True
    )

    if purch_raw.empty:
        st.warning("No purchase data for selected period.")
    else:
        purch_raw["total_cost"] = to_num(
            purch_raw.get("total_cost", pd.Series(dtype=float))
        )
        purch_raw["quantity"]   = to_num(
            purch_raw.get("quantity", pd.Series(dtype=float))
        )

        m1,m2,m3,m4 = st.columns(4)
        m1.metric("Total Purchases",
                  f"{purch_raw['total_cost'].sum():,.2f}")
        m2.metric("Transactions", len(purch_raw))
        m3.metric("Avg Purchase",
                  f"{purch_raw['total_cost'].mean():,.2f}")
        m4.metric("Total Qty Purchased",
                  f"{purch_raw['quantity'].sum():,.0f}")

        purch_period = get_period_key(purch_raw.copy())
        if "period" in purch_period.columns:
            by_pp = purch_period.groupby("period").agg(
                Purchases=("total_cost","sum"),
                Transactions=("total_cost","count"),
                Qty=("quantity","sum")
            ).reset_index()
            by_pp["Running_Purchases"] = by_pp["Purchases"].cumsum()
            fig_p = px.bar(
                by_pp, x="period", y="Purchases",
                title=f"Purchases by {group_by}",
                color_discrete_sequence=["#ff7043"]
            )
            st.plotly_chart(fig_p, use_container_width=True)
            st.dataframe(by_pp, use_container_width=True, height=200)

        if "supplier" in purch_raw.columns:
            by_sup = purch_raw.groupby("supplier").agg(
                Total=("total_cost","sum"),
                Transactions=("total_cost","count"),
                Avg=("total_cost","mean")
            ).reset_index().sort_values("Total", ascending=False)
            st.markdown("**By Supplier:**")
            st.dataframe(by_sup, use_container_width=True, height=200)

        st.markdown("**Full Purchase Detail:**")
        st.dataframe(
            purch_raw.sort_values("date").reset_index(drop=True),
            use_container_width=True, height=300
        )
        st.download_button(
            "📥 Download Purchase Ledger",
            purch_raw.to_csv(index=False),
            f"purchase_ledger_{start_date}_{end_date}.csv",
            "text/csv"
        )

# ════════════════════════════════════════════════════════
# TAB 5 — BANK LEDGER
# ════════════════════════════════════════════════════════
with tabs[4]:
    st.markdown(
        '<div class="section-header">🏦 Bank Ledger</div>',
        unsafe_allow_html=True
    )

    if bank_raw.empty:
        st.warning("No banking data for selected period.")
    else:
        bank_raw["credit"]  = to_num(bank_raw.get("credit",  pd.Series(dtype=float)))
        bank_raw["debit"]   = to_num(bank_raw.get("debit",   pd.Series(dtype=float)))
        bank_raw["balance"] = to_num(bank_raw.get("balance", pd.Series(dtype=float)))
        bank_raw["net"]     = bank_raw["credit"] - bank_raw["debit"]

        total_in  = bank_raw["credit"].sum()
        total_out = bank_raw["debit"].sum()
        net_pos   = total_in - total_out
        open_bal  = bank_raw["balance"].iloc[0] if not bank_raw.empty else 0
        close_bal = bank_raw["balance"].iloc[-1] if not bank_raw.empty else 0

        m1,m2,m3,m4,m5 = st.columns(5)
        m1.metric("Total In (CR)",   f"{total_in:,.2f}")
        m2.metric("Total Out (DR)",  f"{total_out:,.2f}")
        m3.metric("Net Movement",    f"{net_pos:,.2f}")
        m4.metric("Opening Balance", f"{open_bal:,.2f}")
        m5.metric("Closing Balance", f"{close_bal:,.2f}")

        # Running balance chart
        bank_sorted = bank_raw.sort_values("date")
        if bank_sorted["balance"].sum() > 0:
            fig_bal = px.line(
                bank_sorted,
                x="date", y="balance",
                title="Running Bank Balance",
                color_discrete_sequence=["#1a237e"]
            )
            fig_bal.add_hline(y=0, line_dash="dash", line_color="red")
            st.plotly_chart(fig_bal, use_container_width=True)

        # Period summary
        bank_period = get_period_key(bank_raw.copy())
        if "period" in bank_period.columns:
            by_bp = bank_period.groupby("period").agg(
                Credits=("credit","sum"),
                Debits=("debit","sum"),
                Transactions=("credit","count")
            ).reset_index()
            by_bp["Net"] = by_bp["Credits"] - by_bp["Debits"]
            by_bp["Running_Net"] = by_bp["Net"].cumsum()
            fig_bk = px.bar(
                by_bp, x="period",
                y=["Credits","Debits"],
                title=f"Bank Movement by {group_by}",
                barmode="group",
                color_discrete_sequence=["#2e7d32","#c62828"]
            )
            st.plotly_chart(fig_bk, use_container_width=True)
            st.dataframe(by_bp, use_container_width=True, height=200)

        st.markdown("**Full Bank Statement:**")
        st.dataframe(
            bank_raw.sort_values("date").reset_index(drop=True),
            use_container_width=True, height=350
        )
        st.download_button(
            "📥 Download Bank Ledger",
            bank_raw.to_csv(index=False),
            f"bank_ledger_{start_date}_{end_date}.csv",
            "text/csv"
        )

# ════════════════════════════════════════════════════════
# TAB 6 — COLLECTIONS LEDGER
# ════════════════════════════════════════════════════════
with tabs[5]:
    st.markdown(
        '<div class="section-header">💵 Collections Ledger</div>',
        unsafe_allow_html=True
    )

    if coll_raw.empty:
        st.warning("No collections data for selected period.")
    else:
        coll_raw["amount"] = to_num(
            coll_raw.get("amount", pd.Series(dtype=float))
        )

        total_coll   = coll_raw["amount"].sum()
        banked_coll  = coll_raw[
            coll_raw.get("reconciled", pd.Series([0]*len(coll_raw))) == 1
        ]["amount"].sum() if "reconciled" in coll_raw.columns else 0

        m1,m2,m3,m4 = st.columns(4)
        m1.metric("Total Collected",   f"{total_coll:,.2f}")
        m2.metric("Transactions",      len(coll_raw))
        m3.metric("Avg Collection",    f"{coll_raw['amount'].mean():,.2f}")
        m4.metric("Confirmed Banked",  f"{banked_coll:,.2f}")

        coll_period = get_period_key(coll_raw.copy())
        if "period" in coll_period.columns:
            by_cp = coll_period.groupby("period").agg(
                Collections=("amount","sum"),
                Count=("amount","count"),
                Avg=("amount","mean")
            ).reset_index()
            by_cp["Running_Collections"] = by_cp["Collections"].cumsum()
            fig_c = px.bar(
                by_cp, x="period", y="Collections",
                title=f"Collections by {group_by}",
                color_discrete_sequence=["#7e57c2"]
            )
            st.plotly_chart(fig_c, use_container_width=True)
            st.dataframe(by_cp, use_container_width=True, height=200)

        if "customer" in coll_raw.columns:
            by_cust_c = coll_raw.groupby("customer").agg(
                Total=("amount","sum"),
                Count=("amount","count")
            ).reset_index().sort_values("Total", ascending=False)
            st.markdown("**Collections by Customer:**")
            st.dataframe(by_cust_c.head(20),
                         use_container_width=True, height=200)

        if "payment_method" in coll_raw.columns:
            by_method = coll_raw.groupby("payment_method").agg(
                Total=("amount","sum"),
                Count=("amount","count")
            ).reset_index()
            fig_m = px.pie(
                by_method, names="payment_method",
                values="Total",
                title="Collections by Payment Method"
            )
            st.plotly_chart(fig_m, use_container_width=True)

        st.markdown("**Full Collections Detail:**")
        st.dataframe(
            coll_raw.sort_values("date").reset_index(drop=True),
            use_container_width=True, height=300
        )
        st.download_button(
            "📥 Download Collections Ledger",
            coll_raw.to_csv(index=False),
            f"collections_ledger_{start_date}_{end_date}.csv",
            "text/csv"
        )

# ════════════════════════════════════════════════════════
# TAB 7 — INVENTORY MOVEMENT
# ════════════════════════════════════════════════════════
with tabs[6]:
    st.markdown(
        '<div class="section-header">📦 Inventory Movement</div>',
        unsafe_allow_html=True
    )

    if inv_raw.empty:
        st.warning("No inventory data available.")
    else:
        # Calculate movement for period
        inv_raw["opening_qty"]   = to_num(inv_raw.get("opening_qty",   pd.Series(dtype=float)))
        inv_raw["purchases_qty"] = to_num(inv_raw.get("purchases_qty", pd.Series(dtype=float)))
        inv_raw["sales_qty"]     = to_num(inv_raw.get("sales_qty",     pd.Series(dtype=float)))
        inv_raw["returns_in_qty"]= to_num(inv_raw.get("returns_in_qty",pd.Series(dtype=float)))
        inv_raw["swap_out_qty"]  = to_num(inv_raw.get("swap_out_qty",  pd.Series(dtype=float)))
        inv_raw["swap_in_qty"]   = to_num(inv_raw.get("swap_in_qty",   pd.Series(dtype=float)))
        inv_raw["closing_qty"]   = to_num(inv_raw.get("closing_qty",   pd.Series(dtype=float)))
        inv_raw["physical_count"]= to_num(inv_raw.get("physical_count",inv_raw["closing_qty"]))
        inv_raw["unit_cost"]     = to_num(inv_raw.get("unit_cost",     pd.Series(dtype=float)))
        inv_raw["selling_price"] = to_num(inv_raw.get("selling_price", pd.Series(dtype=float)))

        # Add transaction-period sales
        if not sales_raw.empty and "item_description" in sales_raw.columns:
            period_sales_qty = sales_raw.groupby("item_description")[
                "quantity"
            ].sum().reset_index()
            period_sales_qty.columns = ["description", "period_sales_qty"]
            inv_display = inv_raw.merge(
                period_sales_qty, on="description", how="left"
            )
            inv_display["period_sales_qty"] = to_num(
                inv_display.get("period_sales_qty", pd.Series(dtype=float))
            )
        else:
            inv_display = inv_raw.copy()
            inv_display["period_sales_qty"] = 0

        inv_display["expected_closing"] = (
            inv_display["opening_qty"]
            + inv_display["purchases_qty"]
            - inv_display["sales_qty"]
            + inv_display["returns_in_qty"]
            - inv_display["swap_out_qty"]
            + inv_display["swap_in_qty"]
        )
        inv_display["variance"]       = (
            inv_display["physical_count"] - inv_display["expected_closing"]
        )
        inv_display["variance_value"] = (
            inv_display["variance"] * inv_display["unit_cost"]
        )
        inv_display["closing_value"]  = (
            inv_display["closing_qty"] * inv_display["unit_cost"]
        )
        inv_display["retail_value"]   = (
            inv_display["closing_qty"] * inv_display["selling_price"]
        )
        inv_display["potential_profit"]=(
            inv_display["retail_value"] - inv_display["closing_value"]
        )

        # Summary
        total_cost_val   = inv_display["closing_value"].sum()
        total_retail_val = inv_display["retail_value"].sum()
        total_variance   = inv_display["variance_value"].sum()
        items_with_var   = len(inv_display[inv_display["variance"] != 0])

        m1,m2,m3,m4,m5 = st.columns(5)
        m1.metric("Total Items",      len(inv_display))
        m2.metric("Inventory at Cost",f"{total_cost_val:,.2f}")
        m3.metric("Retail Value",     f"{total_retail_val:,.2f}")
        m4.metric("Potential Profit", f"{total_retail_val-total_cost_val:,.2f}")
        m5.metric("Variance Value",   f"{total_variance:,.2f}",
                  delta_color="inverse")

        # Movement chart
        fig_inv = px.bar(
            inv_display.head(20),
            x="description",
            y=["opening_qty","purchases_qty","sales_qty","closing_qty"],
            title="Inventory Movement by Item",
            barmode="group",
            color_discrete_sequence=[
                "#1a237e","#2e7d32","#c62828","#42a5f5"
            ]
        )
        st.plotly_chart(fig_inv, use_container_width=True)

        # Variance chart
        var_items = inv_display[inv_display["variance"] != 0]
        if not var_items.empty:
            fig_var = px.bar(
                var_items,
                x="description",
                y="variance_value",
                color="variance",
                color_continuous_scale="RdYlGn",
                color_continuous_midpoint=0,
                title="Inventory Variance by Item (Value)"
            )
            fig_var.add_hline(y=0, line_dash="dash")
            st.plotly_chart(fig_var, use_container_width=True)

        # Detail table
        display_inv_cols = [
            "item_code","description","category",
            "opening_qty","purchases_qty","sales_qty",
            "returns_in_qty","swap_out_qty","swap_in_qty",
            "expected_closing","physical_count","variance",
            "unit_cost","closing_value","selling_price",
            "retail_value","potential_profit","variance_value"
        ]
        avail = [c for c in display_inv_cols if c in inv_display.columns]
        st.dataframe(
            inv_display[avail],
            use_container_width=True, height=350
        )

        st.download_button(
            "📥 Download Inventory Report",
            inv_display[avail].to_csv(index=False),
            f"inventory_{start_date}_{end_date}.csv",
            "text/csv"
        )

# ════════════════════════════════════════════════════════
# TAB 8 — RETURNS & SWAPS
# ════════════════════════════════════════════════════════
with tabs[7]:
    st.markdown(
        '<div class="section-header">↩️ Returns & Swap Deals</div>',
        unsafe_allow_html=True
    )

    col_ret, col_swap = st.columns(2)

    with col_ret:
        st.markdown("**Sales Returns:**")
        if ret_raw.empty:
            st.info("No returns in selected period.")
        else:
            ret_raw["return_amount"] = to_num(
                ret_raw.get("return_amount", pd.Series(dtype=float))
            )
            st.metric("Total Returns",
                      f"{ret_raw['return_amount'].sum():,.2f}")
            st.metric("Number of Returns", len(ret_raw))

            by_reason = ret_raw.groupby(
                ret_raw.get("reason", pd.Series(["Unknown"]*len(ret_raw)))
            )["return_amount"].sum().reset_index()
            if not by_reason.empty:
                fig_ret = px.pie(
                    by_reason, names="reason",
                    values="return_amount",
                    title="Returns by Reason"
                )
                st.plotly_chart(fig_ret, use_container_width=True)

            st.dataframe(
                ret_raw.sort_values("date").reset_index(drop=True),
                use_container_width=True, height=250
            )

    with col_swap:
        st.markdown("**Swap Deals:**")
        if swap_raw.empty:
            st.info("No swap deals in selected period.")
        else:
            swap_raw["difference_amount"] = to_num(
                swap_raw.get("difference_amount", pd.Series(dtype=float))
            )
            swap_raw["customer_paid"] = to_num(
                swap_raw.get("customer_paid", pd.Series(dtype=float))
            )
            swap_raw["value_given_out"] = to_num(
                swap_raw.get("value_given_out", pd.Series(dtype=float))
            )

            st.metric("Total Swaps",     len(swap_raw))
            st.metric("Total Value Out",
                      f"{swap_raw['value_given_out'].sum():,.2f}")
            st.metric("Total Collected",
                      f"{swap_raw['customer_paid'].sum():,.2f}")
            st.metric("Total Difference",
                      f"{swap_raw['difference_amount'].sum():,.2f}")

            st.dataframe(
                swap_raw.sort_values("date").reset_index(drop=True),
                use_container_width=True, height=250
            )

    # Combined download
    combined_rs = pd.concat([
        ret_raw.assign(type="Return"),
        swap_raw.assign(type="Swap")
    ], ignore_index=True) if not ret_raw.empty or not swap_raw.empty else pd.DataFrame()

    if not combined_rs.empty:
        st.download_button(
            "📥 Download Returns & Swaps",
            combined_rs.to_csv(index=False),
            f"returns_swaps_{start_date}_{end_date}.csv",
            "text/csv"
        )

# ════════════════════════════════════════════════════════
# TAB 9 — DEBTORS & CREDITORS
# ════════════════════════════════════════════════════════
with tabs[8]:
    st.markdown(
        '<div class="section-header">⚖️ Debtors & Creditors Balances</div>',
        unsafe_allow_html=True
    )

    col_deb, col_cred = st.columns(2)

    with col_deb:
        st.markdown("### 👤 Debtors (Customers Owing)")

        all_sales = load("sales")
        all_coll  = load("collections")
        all_ret   = load("sales_returns")

        if not all_sales.empty and "customer" in all_sales.columns:
            all_sales["net_amount"] = to_num(
                all_sales.get("net_amount", pd.Series(dtype=float))
            )
            sales_by_cust = all_sales.groupby("customer").agg(
                Total_Invoiced=("net_amount","sum"),
                Invoices=("net_amount","count")
            ).reset_index()

            coll_by_cust = pd.DataFrame()
            if not all_coll.empty and "customer" in all_coll.columns:
                all_coll["amount"] = to_num(
                    all_coll.get("amount", pd.Series(dtype=float))
                )
                coll_by_cust = all_coll.groupby("customer").agg(
                    Total_Collected=("amount","sum")
                ).reset_index()

            ret_by_cust = pd.DataFrame()
            if not all_ret.empty and "customer" in all_ret.columns:
                all_ret["return_amount"] = to_num(
                    all_ret.get("return_amount", pd.Series(dtype=float))
                )
                ret_by_cust = all_ret.groupby("customer").agg(
                    Total_Returns=("return_amount","sum")
                ).reset_index()

            debtors = sales_by_cust.copy()
            if not coll_by_cust.empty:
                debtors = debtors.merge(
                    coll_by_cust, on="customer", how="left"
                )
            else:
                debtors["Total_Collected"] = 0

            if not ret_by_cust.empty:
                debtors = debtors.merge(
                    ret_by_cust, on="customer", how="left"
                )
            else:
                debtors["Total_Returns"] = 0

            debtors = debtors.fillna(0)
            debtors["Balance_Due"] = (
                debtors["Total_Invoiced"]
                - debtors["Total_Collected"]
                - debtors["Total_Returns"]
            )
            debtors = debtors.sort_values(
                "Balance_Due", ascending=False
            )

            total_debtors = debtors["Balance_Due"].sum()
            overdue = debtors[debtors["Balance_Due"] > 0]

            st.metric("Total Debtors Balance",
                      f"{total_debtors:,.2f}")
            st.metric("Customers with Balance",
                      len(overdue))

            # Aging buckets
            if "date" in all_sales.columns:
                all_sales["date"] = pd.to_datetime(
                    all_sales["date"], errors="coerce"
                )
                all_sales["days_old"] = (
                    pd.Timestamp.now() - all_sales["date"]
                ).dt.days

                aging_buckets = pd.cut(
                    all_sales["days_old"].fillna(0),
                    bins=[0, 30, 60, 90, 120, float("inf")],
                    labels=["0-30", "31-60", "61-90", "91-120", "120+"]
                )
                aging_df = all_sales.groupby(
                    aging_buckets, observed=True
                )["net_amount"].sum().reset_index()
                aging_df.columns = ["Age_Bucket","Amount"]

                fig_aging = px.bar(
                    aging_df,
                    x="Age_Bucket", y="Amount",
                    title="Debtor Aging",
                    color="Age_Bucket",
                    color_discrete_sequence=[
                        "#2e7d32","#f9a825",
                        "#e65100","#c62828","#7b1fa2"
                    ]
                )
                st.plotly_chart(fig_aging, use_container_width=True)

            st.dataframe(
                debtors,
                use_container_width=True,
                height=300
            )
            st.download_button(
                "📥 Download Debtors",
                debtors.to_csv(index=False),
                f"debtors_{start_date}_{end_date}.csv",
                "text/csv"
            )

    with col_cred:
        st.markdown("### 🏢 Creditors (Suppliers Owed)")

        all_purch = load("purchases")
        all_bank  = load("banking")

        if not all_purch.empty and "supplier" in all_purch.columns:
            all_purch["total_cost"] = to_num(
                all_purch.get("total_cost", pd.Series(dtype=float))
            )
            purch_by_sup = all_purch.groupby("supplier").agg(
                Total_Purchased=("total_cost","sum"),
                Invoices=("total_cost","count")
            ).reset_index()

            # Estimate payments from banking
            payments_by_sup = pd.DataFrame()
            if not all_bank.empty and "description" in all_bank.columns:
                all_bank["debit"] = to_num(
                    all_bank.get("debit", pd.Series(dtype=float))
                )
                bank_debits = all_bank[all_bank["debit"] > 0].copy()
                bank_debits["supplier"] = bank_debits[
                    "description"
                ].astype(str).str[:30]
                payments_by_sup = bank_debits.groupby("supplier").agg(
                    Total_Paid=("debit","sum")
                ).reset_index()

            creditors = purch_by_sup.copy()
            if not payments_by_sup.empty:
                creditors = creditors.merge(
                    payments_by_sup,
                    on="supplier",
                    how="left"
                )
            else:
                creditors["Total_Paid"] = 0

            creditors = creditors.fillna(0)
            creditors["Balance_Owed"] = (
                creditors["Total_Purchased"] - creditors["Total_Paid"]
            )
            creditors = creditors.sort_values(
                "Balance_Owed", ascending=False
            )

            total_creditors = creditors["Balance_Owed"].sum()

            st.metric("Total Creditors Balance",
                      f"{total_creditors:,.2f}")
            st.metric("Suppliers with Balance",
                      len(creditors[creditors["Balance_Owed"] > 0]))

            fig_cred = px.bar(
                creditors.head(15),
                x="supplier",
                y="Balance_Owed",
                title="Top Creditors",
                color_discrete_sequence=["#ff7043"]
            )
            st.plotly_chart(fig_cred, use_container_width=True)

            st.dataframe(
                creditors,
                use_container_width=True,
                height=300
            )
            st.download_button(
                "📥 Download Creditors",
                creditors.to_csv(index=False),
                f"creditors_{start_date}_{end_date}.csv",
                "text/csv"
            )

# ════════════════════════════════════════════════════════
# TAB 10 — CHARTS & TRENDS
# ════════════════════════════════════════════════════════
with tabs[9]:
    st.markdown(
        '<div class="section-header">📈 Charts & Trends</div>',
        unsafe_allow_html=True
    )

    if not all_entries:
        st.warning("No data for selected period.")
    else:
        tb_full = pd.DataFrame(all_entries)
        tb_full["date"] = pd.to_datetime(tb_full["date"], errors="coerce")
        tb_full = get_period_key(tb_full)

        if "period" in tb_full.columns:
            summary_chart = tb_full.groupby("period").agg(
                Sales=("sales_cr","sum"),
                Returns=("returns","sum"),
                Purchases=("purchases_dr","sum"),
                Collections=("collection","sum"),
                Bank_In=("bank_cr","sum"),
                Bank_Out=("bank_dr","sum"),
                Gross_Profit=("gross_profit","sum"),
            ).reset_index()
            summary_chart["Net_Revenue"] = (
                summary_chart["Sales"] - summary_chart["Returns"]
            )
            summary_chart["Net_Cash"] = (
                summary_chart["Bank_In"] - summary_chart["Bank_Out"]
            )

            # Chart 1: Revenue trend
            fig1 = px.area(
                summary_chart,
                x="period",
                y=["Sales","Net_Revenue","Gross_Profit"],
                title=f"Revenue Trend by {group_by}",
                color_discrete_sequence=["#1a237e","#2e7d32","#42a5f5"]
            )
            st.plotly_chart(fig1, use_container_width=True)

            # Chart 2: Cash flow
            fig2 = make_subplots(rows=1, cols=2,
                subplot_titles=["Cash Flow","Collections vs Sales"])
            fig2.add_trace(
                go.Bar(name="Bank In", x=summary_chart["period"],
                       y=summary_chart["Bank_In"],
                       marker_color="#2e7d32"), row=1, col=1
            )
            fig2.add_trace(
                go.Bar(name="Bank Out", x=summary_chart["period"],
                       y=summary_chart["Bank_Out"],
                       marker_color="#c62828"), row=1, col=1
            )
            fig2.add_trace(
                go.Scatter(name="Collections", x=summary_chart["period"],
                           y=summary_chart["Collections"],
                           line=dict(color="#7e57c2",width=3)),
                row=1, col=2
            )
            fig2.add_trace(
                go.Scatter(name="Sales", x=summary_chart["period"],
                           y=summary_chart["Sales"],
                           line=dict(color="#1a237e",width=3)),
                row=1, col=2
            )
            fig2.update_layout(height=400, barmode="group")
            st.plotly_chart(fig2, use_container_width=True)

            # Chart 3: Transaction mix
            type_mix = tb_full.groupby("type").agg(
                Count=("type","count"),
                Value=("sales_cr","sum")
            ).reset_index()
            type_mix["Value"] = (
                type_mix["Value"]
                + tb_full.groupby("type")["purchases_dr"].sum().values
                + tb_full.groupby("type")["collection"].sum().values
            )
            fig3 = px.pie(
                type_mix, names="type", values="Count",
                title="Transaction Mix by Count"
            )
            st.plotly_chart(fig3, use_container_width=True)

            # Chart 4: Cumulative revenue
            summary_chart["Cumulative_Sales"]  = (
                summary_chart["Sales"].cumsum()
            )
            summary_chart["Cumulative_Profit"] = (
                summary_chart["Gross_Profit"].cumsum()
            )
            fig4 = px.line(
                summary_chart,
                x="period",
                y=["Cumulative_Sales","Cumulative_Profit"],
                title="Cumulative Revenue & Profit",
                color_discrete_sequence=["#1a237e","#2e7d32"]
            )
            st.plotly_chart(fig4, use_container_width=True)

# ── Footer ────────────────────────────────────────────────
st.markdown(
    '<div class="finteca-footer">'
    'Finteca AuditRep v1.0.0 · Extended Trial Balance & Period Reports'
    '</div>',
    unsafe_allow_html=True
)
