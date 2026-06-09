# pages/15_Bin_Cards.py
# Finteca AuditRep — Bin Card & Inventory Reconciliation

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
import os
from datetime import date, datetime
from pathlib import Path

# Import bin card engine
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from bin_card_engine import (
    compute_bin_cards,
    compute_daily_movements,
    get_bin_card_summary,
)

st.set_page_config(
    page_title="Bin Cards | Finteca AuditRep",
    page_icon="📦",
    layout="wide"
)

CSS = """
<style>
.finteca-header{
    background:linear-gradient(135deg,#1a237e 0%,#283593 50%,#42a5f5 100%);
    padding:25px 30px;border-radius:12px;color:white;margin-bottom:25px;}
.finteca-header h1{margin:0;font-size:2.2em;font-weight:800;}
.finteca-header p{margin:5px 0 0 0;opacity:0.85;}
.finteca-badge{background:rgba(255,255,255,0.2);padding:3px 10px;
    border-radius:20px;font-size:0.75em;display:inline-block;margin-top:8px;}
.metric-card{background:#f8f9ff;border:1px solid #e0e4ff;border-radius:10px;
    padding:15px;text-align:center;border-top:4px solid #1a237e;}
.metric-val{font-size:1.8em;font-weight:800;color:#1a237e;}
.metric-lbl{font-size:0.85em;color:#666;margin-top:4px;}
.section-hdr{background:#f5f7ff;border-left:4px solid #1a237e;
    padding:10px 15px;border-radius:0 8px 8px 0;margin:15px 0;
    font-weight:600;color:#1a237e;font-size:1.05em;}
.bin-formula{background:#e8f5e9;border:1px solid #a5d6a7;
    border-radius:8px;padding:15px;margin:10px 0;font-family:monospace;}
.low-stock{background:#ffebee;border-left:4px solid #c62828;
    padding:8px 12px;border-radius:0 5px 5px 0;margin:3px 0;}
.finteca-footer{text-align:center;color:#999;font-size:0.8em;
    padding:20px;border-top:1px solid #eee;margin-top:30px;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

st.markdown("""
<div class="finteca-header">
    <h1>📦 Bin Cards & Inventory Reconciliation</h1>
    <p>Real-time stock movement · Opening → Purchases → Sales → Returns → Closing</p>
    <span class="finteca-badge">Module 15 — Bin Cards</span>
</div>
""", unsafe_allow_html=True)

# ── DB Resolution ────────────────────────────────────────────
def get_db():
    if st.session_state.get("active_db_path"):
        return st.session_state.active_db_path
    if os.path.exists("/mount/src"):
        return "/tmp/reconciliation.db"
    Path("data").mkdir(exist_ok=True)
    return "data/reconciliation.db"

DB = get_db()

# ── Assignment Banner ────────────────────────────────────────
assign_name = st.session_state.get("active_assignment_name", "")
if assign_name:
    st.success(f"✅ Assignment: **{assign_name}**")
else:
    st.info("ℹ️ No assignment active — using default database.")

# ── Formula Display ──────────────────────────────────────────
st.markdown("""
<div class="bin-formula">
    <b>📐 Bin Card Formula (per SKU per period):</b><br><br>
    &nbsp;&nbsp;Closing Stock (Qty) =<br>
    &nbsp;&nbsp;&nbsp;&nbsp;Opening Stock<br>
    &nbsp;&nbsp;&nbsp;&nbsp;+ Purchases<br>
    &nbsp;&nbsp;&nbsp;&nbsp;− Purchase Returns<br>
    &nbsp;&nbsp;&nbsp;&nbsp;− Sales<br>
    &nbsp;&nbsp;&nbsp;&nbsp;+ Sales Returns<br><br>
    &nbsp;&nbsp;Closing Value = Closing Qty × Weighted Average Cost<br>
    &nbsp;&nbsp;Gross Profit  = Sales Revenue − Cost of Sales
</div>
""", unsafe_allow_html=True)

st.divider()

# ── Controls ─────────────────────────────────────────────────
st.markdown('<div class="section-hdr">🔧 Filter Controls</div>',
            unsafe_allow_html=True)

ctrl1, ctrl2, ctrl3, ctrl4 = st.columns([2, 2, 2, 2])

with ctrl1:
    date_from = st.date_input(
        "📅 Period From:",
        value=date(2025, 5, 1),
        key="bc_widget_date_from"
    )
with ctrl2:
    date_to = st.date_input(
        "📅 Period To:",
        value=date(2026, 5, 31),
        key="bc_widget_date_to"
    )
with ctrl3:
    sku_filter = st.text_input(
        "🔍 Filter by SKU / Item Code:",
        placeholder="Leave blank for all",
        key="bc_widget_sku_filter"
    )
with ctrl4:
    st.markdown("<br>", unsafe_allow_html=True)
    run_btn = st.button(
        "📊 Compute Bin Cards",
        type="primary",
        use_container_width=True,
        key="bc_run"
    )

# ── Compute ──────────────────────────────────────────────────
if run_btn:
    if date_from > date_to:
        st.error("❌ Period From must be before Period To.")
        st.stop()

    with st.spinner("⏳ Computing bin cards..."):
        try:
            df_bins = compute_bin_cards(
                db_path    = DB,
                date_from  = date_from,
                date_to    = date_to,
                sku_filter = sku_filter.strip() if sku_filter else None,
            )
            # Store results with different keys from widgets
            st.session_state["bc_computed"]       = True
            st.session_state["bc_df"]             = df_bins
            st.session_state["bc_stored_from"]    = date_from
            st.session_state["bc_stored_to"]      = date_to
        except Exception as e:
            st.error(f"❌ Computation error: {e}")
            st.exception(e)
            st.stop()

if st.session_state.get("bc_computed"):
    df_bins   = st.session_state.get("bc_df", pd.DataFrame())
    date_from = st.session_state.get("bc_stored_from", date_from)
    date_to   = st.session_state.get("bc_stored_to",   date_to)

    if df_bins.empty:
        st.warning(
            "⚠️ No SKU data found for this period. "
            "Please upload Inventory Master, Purchases, and Sales data first."
        )
        st.markdown("""
        **To get started:**
        1. Go to **14 Templates Upload**
        2. Download and fill **Inventory Master** template
        3. Upload Purchases, Sales, Purchase Returns
        4. Come back here and click Compute Bin Cards
        """)
        st.stop()

    summary = get_bin_card_summary(df_bins)

    # ── Summary Metrics ──────────────────────────────────────
    st.markdown('<div class="section-hdr">📊 Portfolio Summary</div>',
                unsafe_allow_html=True)

    m1,m2,m3,m4,m5,m6 = st.columns(6)

    m1.markdown(f"""
    <div class="metric-card">
        <div class="metric-val">{int(summary.get('total_skus',0))}</div>
        <div class="metric-lbl">Total SKUs</div>
    </div>""", unsafe_allow_html=True)

    m2.markdown(f"""
    <div class="metric-card">
        <div class="metric-val">{summary.get('total_purchases_qty',0):,.0f}</div>
        <div class="metric-lbl">Total Purchased Qty</div>
    </div>""", unsafe_allow_html=True)

    m3.markdown(f"""
    <div class="metric-card">
        <div class="metric-val">{summary.get('total_sales_qty',0):,.0f}</div>
        <div class="metric-lbl">Total Sold Qty</div>
    </div>""", unsafe_allow_html=True)

    m4.markdown(f"""
    <div class="metric-card">
        <div class="metric-val">{summary.get('total_closing_qty',0):,.0f}</div>
        <div class="metric-lbl">Total Closing Qty</div>
    </div>""", unsafe_allow_html=True)

    m5.markdown(f"""
    <div class="metric-card">
        <div class="metric-val">
            {summary.get('total_closing_value',0):,.2f}
        </div>
        <div class="metric-lbl">Closing Stock Value</div>
    </div>""", unsafe_allow_html=True)

    m6.markdown(f"""
    <div class="metric-card">
        <div class="metric-val"
             style="color:{'#2e7d32' if summary.get('total_gross_profit',0)>=0 else '#c62828'}">
            {summary.get('total_gross_profit',0):,.2f}
        </div>
        <div class="metric-lbl">Gross Profit</div>
    </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Low Stock Alert ──────────────────────────────────────
    low_stock = df_bins[df_bins["closing_qty"] <= 0]
    if not low_stock.empty:
        st.markdown(
            f'<div class="low-stock">⚠️ <b>{len(low_stock)} SKU(s)</b> '
            f'have zero or negative closing stock — review immediately.</div>',
            unsafe_allow_html=True
        )

    st.divider()

    # ── TABS ─────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Bin Card Summary",
        "📈 Charts",
        "🔍 Detailed Movement",
        "⬇️ Export",
    ])

    # ── TAB 1: SUMMARY TABLE ─────────────────────────────────
    with tab1:
        st.markdown(
            f'<div class="section-hdr">📋 Bin Card Summary — '
            f'{date_from} to {date_to}</div>',
            unsafe_allow_html=True
        )

        # Format for display
        display_df = df_bins.copy()

        # Rename columns for clarity
        display_df.columns = [
            "SKU", "Item Name",
            "Opening Qty", "Opening Value",
            "Purchases Qty", "Purchases Value",
            "Purch Returns Qty", "Purch Returns Value",
            "Sales Qty", "Sales Revenue", "Sales Cost",
            "Sales Returns Qty", "Sales Returns Value",
            "Closing Qty", "Closing Value",
            "WAC", "Gross Profit", "Margin %"
        ]

        # Highlight low stock
        def highlight_closing(row):
            if row["Closing Qty"] <= 0:
                return ["background-color: #ffebee"] * len(row)
            elif row["Closing Qty"] < 10:
                return ["background-color: #fff9c4"] * len(row)
            return [""] * len(row)

        styled = display_df.style.apply(
            highlight_closing, axis=1
        ).format({
            "Opening Qty":       "{:,.2f}",
            "Opening Value":     "{:,.2f}",
            "Purchases Qty":     "{:,.2f}",
            "Purchases Value":   "{:,.2f}",
            "Purch Returns Qty": "{:,.2f}",
            "Purch Returns Value":"{:,.2f}",
            "Sales Qty":         "{:,.2f}",
            "Sales Revenue":     "{:,.2f}",
            "Sales Cost":        "{:,.2f}",
            "Sales Returns Qty": "{:,.2f}",
            "Sales Returns Value":"{:,.2f}",
            "Closing Qty":       "{:,.2f}",
            "Closing Value":     "{:,.2f}",
            "WAC":               "{:,.4f}",
            "Gross Profit":      "{:,.2f}",
            "Margin %":          "{:.1f}%",
        })

        st.dataframe(styled, use_container_width=True, height=500)

        # Reconciliation check
        st.markdown("---")
        st.markdown("**🧮 Reconciliation Check:**")

        rc1, rc2, rc3, rc4 = st.columns(4)
        rc1.metric(
            "Total Opening",
            f"{df_bins['opening_qty'].sum():,.2f}"
        )
        rc2.metric(
            "Net In (Purchases − Returns)",
            f"{(df_bins['purchases_qty'] - df_bins['purchase_returns_qty']).sum():,.2f}"
        )
        rc3.metric(
            "Net Out (Sales − Returns)",
            f"{(df_bins['sales_qty'] - df_bins['sales_returns_qty']).sum():,.2f}"
        )
        rc4.metric(
            "Total Closing",
            f"{df_bins['closing_qty'].sum():,.2f}"
        )

        # Formula verification
        expected = (
            df_bins["opening_qty"].sum()
            + df_bins["purchases_qty"].sum()
            - df_bins["purchase_returns_qty"].sum()
            - df_bins["sales_qty"].sum()
            + df_bins["sales_returns_qty"].sum()
        )
        actual = df_bins["closing_qty"].sum()
        diff   = abs(actual - expected)

        if diff < 0.01:
            st.success(
                f"✅ Reconciliation BALANCED — "
                f"Opening + Purchases − Purch Returns − Sales + Sales Returns "
                f"= Closing: **{actual:,.2f}**"
            )
        else:
            st.error(
                f"❌ Reconciliation DIFFERENCE: {diff:,.4f} — "
                f"Expected {expected:,.4f}, Got {actual:,.4f}"
            )

    # ── TAB 2: CHARTS ────────────────────────────────────────
    with tab2:
        st.markdown(
            '<div class="section-hdr">📈 Visual Analysis</div>',
            unsafe_allow_html=True
        )

        if len(df_bins) == 0:
            st.info("No data to chart.")
        else:
            ch1, ch2 = st.columns(2)

            with ch1:
                # Stock movement bar chart
                fig1 = go.Figure()
                fig1.add_trace(go.Bar(
                    name="Opening",
                    x=df_bins["sku"],
                    y=df_bins["opening_qty"],
                    marker_color="#1a237e"
                ))
                fig1.add_trace(go.Bar(
                    name="Purchases",
                    x=df_bins["sku"],
                    y=df_bins["purchases_qty"],
                    marker_color="#42a5f5"
                ))
                fig1.add_trace(go.Bar(
                    name="Sales",
                    x=df_bins["sku"],
                    y=-df_bins["sales_qty"],
                    marker_color="#ef5350"
                ))
                fig1.add_trace(go.Bar(
                    name="Closing",
                    x=df_bins["sku"],
                    y=df_bins["closing_qty"],
                    marker_color="#2e7d32"
                ))
                fig1.update_layout(
                    title="Stock Movement by SKU",
                    barmode="group",
                    xaxis_title="SKU",
                    yaxis_title="Quantity",
                    height=400,
                    legend=dict(orientation="h", y=-0.2)
                )
                st.plotly_chart(fig1, use_container_width=True)

            with ch2:
                # Gross profit by SKU
                colors = [
                    "#2e7d32" if v >= 0 else "#c62828"
                    for v in df_bins["gross_profit"]
                ]
                fig2 = go.Figure(go.Bar(
                    x=df_bins["sku"],
                    y=df_bins["gross_profit"],
                    marker_color=colors,
                    text=[f"{v:,.0f}" for v in df_bins["gross_profit"]],
                    textposition="outside"
                ))
                fig2.update_layout(
                    title="Gross Profit by SKU",
                    xaxis_title="SKU",
                    yaxis_title="Gross Profit",
                    height=400
                )
                st.plotly_chart(fig2, use_container_width=True)

            # Closing stock value pie
            if df_bins["closing_value"].sum() > 0:
                fig3 = px.pie(
                    df_bins[df_bins["closing_value"] > 0],
                    values="closing_value",
                    names="sku",
                    title="Closing Stock Value Distribution",
                    color_discrete_sequence=px.colors.sequential.Blues_r
                )
                fig3.update_traces(textinfo="percent+label")
                st.plotly_chart(fig3, use_container_width=True)

    # ── TAB 3: DETAILED MOVEMENT ─────────────────────────────
    with tab3:
        st.markdown(
            '<div class="section-hdr">🔍 Detailed Daily Movement</div>',
            unsafe_allow_html=True
        )

        sku_list = df_bins["sku"].tolist()

        if not sku_list:
            st.info("No SKUs available.")
        else:
            sel_sku = st.selectbox(
                "Select SKU for detailed view:",
                options=sku_list,
                key="bc_detail_sku"
            )

            if sel_sku:
                sku_row = df_bins[df_bins["sku"] == sel_sku].iloc[0]

                # SKU summary header
                d1,d2,d3,d4,d5 = st.columns(5)
                d1.metric("Opening Qty",  f"{sku_row['opening_qty']:,.2f}")
                d2.metric("Purchases",    f"{sku_row['purchases_qty']:,.2f}")
                d3.metric("Sales",        f"{sku_row['sales_qty']:,.2f}")
                d4.metric("Closing Qty",  f"{sku_row['closing_qty']:,.2f}")
                d5.metric("Closing Value",f"{sku_row['closing_value']:,.2f}")

                # Reconciliation line
                st.markdown(
                    f"**Formula:** "
                    f"{sku_row['opening_qty']:,.2f} (Opening) "
                    f"+ {sku_row['purchases_qty']:,.2f} (Purchases) "
                    f"− {sku_row['purchase_returns_qty']:,.2f} (Purch Returns) "
                    f"− {sku_row['sales_qty']:,.2f} (Sales) "
                    f"+ {sku_row['sales_returns_qty']:,.2f} (Sales Returns) "
                    f"= **{sku_row['closing_qty']:,.2f}** (Closing)"
                )

                st.markdown("---")

                # Load daily movements
                with st.spinner(f"Loading movements for {sel_sku}..."):
                    _d_from = st.session_state.get("bc_stored_from", date_from)
                    _d_to   = st.session_state.get("bc_stored_to",   date_to)
                    df_mov = compute_daily_movements(
                        db_path   = DB,
                        sku       = sel_sku,
                        date_from = _d_from,
                        date_to   = _d_to,
                    )

                if df_mov.empty:
                    st.info("No movement details available.")
                else:
                    # Format display
                    df_mov_display = df_mov.copy()
                    df_mov_display["date"] = (
                        df_mov_display["date"]
                        .dt.strftime("%Y-%m-%d")
                    )
                    df_mov_display.columns = [
                        "Date", "Type", "Reference", "Party",
                        "Qty In", "Qty Out", "Unit Cost",
                        "Value In", "Value Out",
                        "Balance Qty", "Balance Value"
                    ]

                    def color_movement(row):
                        if row["Type"] == "Opening Balance":
                            return ["background-color:#e3f2fd"] * len(row)
                        elif row["Type"] == "Purchase":
                            return ["background-color:#e8f5e9"] * len(row)
                        elif row["Type"] in ("Sale",):
                            return ["background-color:#fff3e0"] * len(row)
                        elif "Return" in str(row["Type"]):
                            return ["background-color:#fce4ec"] * len(row)
                        return [""] * len(row)

                    styled_mov = df_mov_display.style.apply(
                        color_movement, axis=1
                    ).format({
                        "Qty In":       "{:,.4f}",
                        "Qty Out":      "{:,.4f}",
                        "Unit Cost":    "{:,.4f}",
                        "Value In":     "{:,.2f}",
                        "Value Out":    "{:,.2f}",
                        "Balance Qty":  "{:,.4f}",
                        "Balance Value":"{:,.2f}",
                    })

                    st.dataframe(
                        styled_mov,
                        use_container_width=True,
                        height=450
                    )

                    # Running balance chart
                    fig_bal = go.Figure()
                    fig_bal.add_trace(go.Scatter(
                        x=df_mov["date"],
                        y=df_mov["balance_qty"],
                        mode="lines+markers",
                        name="Balance Qty",
                        line=dict(color="#1a237e", width=2),
                        fill="tozeroy",
                        fillcolor="rgba(26,35,126,0.1)"
                    ))
                    fig_bal.update_layout(
                        title=f"Running Stock Balance — {sel_sku}",
                        xaxis_title="Date",
                        yaxis_title="Quantity",
                        height=350
                    )
                    st.plotly_chart(fig_bal, use_container_width=True)

    # ── TAB 4: EXPORT ────────────────────────────────────────
    with tab4:
        st.markdown(
            '<div class="section-hdr">⬇️ Export Bin Cards</div>',
            unsafe_allow_html=True
        )

        if df_bins.empty:
            st.info("No data to export.")
        else:
            ts = datetime.now().strftime("%Y%m%d_%H%M")

            # Full bin card CSV
            csv_full = df_bins.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Download Full Bin Card (CSV)",
                data=csv_full,
                file_name=f"bin_cards_{ts}.csv",
                mime="text/csv",
                use_container_width=True,
                key="dl_bc_full"
            )

            st.markdown("---")

            # Per-SKU detailed movement
            st.markdown("**Download Detailed Movement for one SKU:**")
            sel_export_sku = st.selectbox(
                "Select SKU:",
                options=df_bins["sku"].tolist(),
                key="bc_export_sku"
            )

            if st.button("Generate Movement Report",
                         key="bc_gen_mov"):
                _d_from = st.session_state.get("bc_stored_from", date_from)
                _d_to   = st.session_state.get("bc_stored_to",   date_to)
                df_exp = compute_daily_movements(
                    db_path   = DB,
                    sku       = sel_export_sku,
                    date_from = _d_from,
                    date_to   = _d_to,
                )
                if not df_exp.empty:
                    csv_exp = df_exp.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        label=f"📥 Download {sel_export_sku} Movement",
                        data=csv_exp,
                        file_name=f"bin_card_{sel_export_sku}_{ts}.csv",
                        mime="text/csv",
                        use_container_width=True,
                        key="dl_bc_mov"
                    )
                else:
                    st.info("No movement data for this SKU.")

else:
    st.info(
        "👆 Set the date range and click **Compute Bin Cards** to begin."
    )
    st.markdown("""
    **How it works:**
    1. Set **Period From** and **Period To**
    2. Optionally filter by SKU
    3. Click **Compute Bin Cards**
    4. View summary, charts, and detailed movements

    **Data sources used:**
    - 📦 Inventory Master → Opening Stock
    - 🛒 Purchases → Stock IN
    - ↩️ Purchase Returns → Stock OUT
    - 💰 Sales → Stock OUT
    - 🔄 Sales Returns → Stock IN
    """)

st.markdown(
    '<div class="finteca-footer">'
    'Finteca AuditRep · Bin Cards · '
    'Opening + Purchases − Purch Returns − Sales + Sales Returns = Closing'
    '</div>',
    unsafe_allow_html=True
)
