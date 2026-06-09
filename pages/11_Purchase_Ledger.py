"""
Finteca AuditRep v4.0 — Purchase Ledger & Bin Cards
Complete purchase tracking with SKU-level bin cards
Purchase returns fully integrated
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
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv()

try:
    from assignment_manager import (
        get_assignment_db, get_assignment,
        load_table as am_load
    )
    AM_OK = True
except Exception:
    AM_OK = False

st.set_page_config(
    page_title="Purchase Ledger - Finteca AuditRep",
    page_icon="🛒", layout="wide"
)

CSS = """<style>
.finteca-header{background:linear-gradient(135deg,#1a237e,#283593,#42a5f5);
    padding:25px 30px;border-radius:12px;color:white;margin-bottom:25px;}
.finteca-header h1{margin:0;font-size:2.2em;font-weight:800;}
.finteca-header p{margin:5px 0 0;opacity:0.85;}
.finteca-badge{background:rgba(255,255,255,0.2);padding:3px 10px;
    border-radius:20px;font-size:0.75em;display:inline-block;margin-top:8px;}
.section-header{background:#f5f7ff;border-left:4px solid #1a237e;
    padding:10px 15px;border-radius:0 8px 8px 0;margin:15px 0;
    font-weight:600;color:#1a237e;}
.bin-card{background:white;border:2px solid #1a237e;border-radius:12px;
    padding:20px;margin:10px 0;}
.flag-green{background:#e8f5e9;border-left:4px solid #2e7d32;
    padding:10px;border-radius:5px;margin:5px 0;}
.flag-red{background:#ffebee;border-left:4px solid #c62828;
    padding:10px;border-radius:5px;margin:5px 0;}
.flag-orange{background:#fff3e0;border-left:4px solid #e65100;
    padding:10px;border-radius:5px;margin:5px 0;}
.finteca-footer{text-align:center;color:#999;font-size:0.8em;
    padding:20px;border-top:1px solid #eee;margin-top:30px;}
</style>"""
st.markdown(CSS, unsafe_allow_html=True)
st.markdown("""
<div class="finteca-header">
    <h1>🛒 Finteca AuditRep</h1>
    <p>Purchase Ledger · Bin Cards · SKU Tracking · Returns</p>
    <span class="finteca-badge">Module 11 — Purchase Ledger</span>
</div>
""", unsafe_allow_html=True)

# ── Get active assignment DB ──────────────────────────────
DB_PATH = (st.session_state.get("active_db_path") or
    ("/tmp/reconciliation.db" if os.path.exists("/mount/src")
     else "data/reconciliation.db"))

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def to_num(s):
    return pd.to_numeric(s, errors="coerce").fillna(0)

def load(table):
    try:
        conn = get_conn()
        df = pd.read_sql(f"SELECT * FROM {table}", conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

# Active assignment banner
if st.session_state.get("active_assignment_name"):
    st.markdown(
        f'<div class="flag-green">Assignment: <b>{st.session_state.active_assignment_name}</b></div>',
        unsafe_allow_html=True)
else:
    st.markdown('<div class="flag-orange">No assignment active.</div>',
                unsafe_allow_html=True)

# Date filter
today = date.today()
dc1, dc2, dc3 = st.columns([2,2,1])
with dc1:
    start_date = st.date_input("From", today.replace(day=1), key="pl_s")
with dc2:
    end_date = st.date_input("To", today, key="pl_e")
with dc3:
    group_by = st.selectbox("Group", ["Daily","Weekly","Monthly","Quarterly","Yearly"], index=2)

tabs = st.tabs([
    "📋 Purchase Ledger",
    "📇 Item Bin Cards",
    "↩️ Purchase Returns",
    "📊 Purchase Analysis",
    "⚖️ Reconcile Purchases",
    "📦 Inventory Month-End",
])

# ════════════════════════════════════════════════════════
# TAB 1 — PURCHASE LEDGER
# ════════════════════════════════════════════════════════
with tabs[0]:
    st.markdown('<div class="section-header">📋 Purchase Ledger</div>', unsafe_allow_html=True)
    purch = load("purchases")
    pr    = load("purchase_returns")

    if purch.empty:
        st.warning("No purchases found. Upload purchase documents first.")
    else:
        purch["date"]       = pd.to_datetime(purch["date"], errors="coerce")
        purch["total_cost"] = to_num(purch.get("total_cost", pd.Series(dtype=float)))
        purch["quantity"]   = to_num(purch.get("quantity",   pd.Series(dtype=float)))
        purch["unit_cost"]  = to_num(purch.get("unit_cost",  pd.Series(dtype=float)))
        purch["discount"]   = to_num(purch.get("discount",   pd.Series(dtype=float)))
        purch["tax"]        = to_num(purch.get("tax",         pd.Series(dtype=float)))

        # Fix: compare as full datetime to avoid dtype mismatch
        _start = pd.Timestamp(start_date)
        _end   = pd.Timestamp(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        purch["date"] = pd.to_datetime(purch["date"], errors="coerce")
        mask = (purch["date"] >= _start) & (purch["date"] <= _end)
        p = purch[mask].copy()

        # Purchase returns in period
        pr_total = 0
        if not pr.empty and "return_amount" in pr.columns:
            pr["date"] = pd.to_datetime(pr["date"], errors="coerce")
            pr["return_amount"] = to_num(pr["return_amount"])
            pr_mask = (pd.to_datetime(pr["date"], errors="coerce") >= pd.Timestamp(start_date)) & (pd.to_datetime(pr["date"], errors="coerce") <= pd.Timestamp(end_date))
            pr_period = pr[pr_mask]
            pr_total = pr_period["return_amount"].sum()

        gross_purch = p["total_cost"].sum()
        net_purch   = gross_purch - pr_total
        tot_qty     = p["quantity"].sum()
        tot_disc    = p["discount"].sum()
        tot_tax     = p["tax"].sum()
        n_suppliers = p["supplier"].nunique() if "supplier" in p.columns else 0

        m = st.columns(6)
        m[0].metric("Gross Purchases",   f"{gross_purch:,.2f}")
        m[1].metric("Purchase Returns",  f"{pr_total:,.2f}", delta_color="inverse")
        m[2].metric("Net Purchases",     f"{net_purch:,.2f}")
        m[3].metric("Total Units",       f"{tot_qty:,.0f}")
        m[4].metric("Discounts",         f"{tot_disc:,.2f}")
        m[5].metric("Suppliers",         n_suppliers)

        # Period grouping
        if not p.empty:
            if group_by == "Daily":    p["period"] = p["date"].dt.strftime("%Y-%m-%d")
            elif group_by == "Weekly": p["period"] = p["date"].dt.to_period("W").astype(str)
            elif group_by == "Monthly":p["period"] = p["date"].dt.strftime("%Y-%m")
            elif group_by == "Quarterly": p["period"] = p["date"].dt.to_period("Q").astype(str)
            else:                      p["period"] = p["date"].dt.strftime("%Y")

            by_period = p.groupby("period").agg(
                Purchases=("total_cost","sum"),
                Qty=("quantity","sum"),
                Transactions=("total_cost","count")
            ).reset_index()
            by_period["Running"] = by_period["Purchases"].cumsum()

            fig = px.bar(by_period, x="period", y="Purchases",
                         title=f"Purchases by {group_by}",
                         color_discrete_sequence=["#1a237e"])
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(by_period.round(2), use_container_width=True, height=200)

        # Full ledger table
        st.markdown("**Full Purchase Ledger:**")
        disp_cols = [c for c in ["id","date","reference_number","supplier",
            "item_code","item_description","quantity","unit_cost",
            "total_cost","discount","tax","net_amount",
            "payment_method","payment_reference","payment_status",
            "document_source"] if c in p.columns]
        st.dataframe(p[disp_cols].sort_values("date"), use_container_width=True, height=400)
        st.download_button("📥 Download Purchase Ledger",
            p[disp_cols].to_csv(index=False),
            f"purchase_ledger_{start_date}_{end_date}.csv","text/csv")

# ════════════════════════════════════════════════════════
# TAB 2 — BIN CARDS
# ════════════════════════════════════════════════════════
with tabs[1]:
    st.markdown('<div class="section-header">📇 Item Bin Cards (SKU Level)</div>', unsafe_allow_html=True)

    purch2  = load("purchases")
    sales2  = load("sales")
    pr2     = load("purchase_returns")
    sr2     = load("sales_returns")
    inv2    = load("inventory")

    for df in [purch2, sales2, pr2, sr2]:
        if not df.empty and "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # Build item master from inventory + purchases
    items = {}
    if not inv2.empty:
        for _, r in inv2.iterrows():
            code = str(r.get("item_code","") or r.get("description",""))
            if code:
                items[code] = {
                    "code": str(r.get("item_code","")),
                    "name": str(r.get("description","")),
                    "unit_cost": float(r.get("unit_cost",0) or 0),
                    "selling_price": float(r.get("selling_price",0) or 0),
                    "opening_qty": float(r.get("opening_qty",0) or 0),
                    "uom": str(r.get("unit_of_measure","Piece")),
                    "category": str(r.get("category","")),
                    "reorder_level": float(r.get("reorder_level",0) or 0),
                }

    # Add items from purchases if not in inventory
    if not purch2.empty:
        for _, r in purch2.iterrows():
            code = str(r.get("item_code","") or r.get("item_description",""))
            if code and code not in items:
                items[code] = {
                    "code": str(r.get("item_code","")),
                    "name": str(r.get("item_description","")),
                    "unit_cost": float(r.get("unit_cost",0) or 0),
                    "selling_price": 0,
                    "opening_qty": 0,
                    "uom": "Piece",
                    "category": "",
                    "reorder_level": 0,
                }

    if not items:
        st.warning("No items found. Upload inventory or purchase data with item codes.")
    else:
        item_list = sorted(items.keys())
        c1, c2 = st.columns([3,1])
        with c1:
            selected = st.selectbox("Select Item (by SKU/Code):", item_list,
                format_func=lambda x: f"{x} — {items[x]['name']}")
        with c2:
            show_all = st.checkbox("Show all movements", value=True)

        if selected:
            item = items[selected]
            name = item["name"]
            cost = item["unit_cost"]
            sell = item["selling_price"]
            opening = item["opening_qty"]
            uom    = item["uom"]

            # Display bin card header
            st.markdown(f"""
            <div class="bin-card">
                <h3>📇 BIN CARD</h3>
                <table style="width:100%;border-collapse:collapse">
                <tr style="background:#f5f7ff">
                    <td style="padding:8px"><b>Item Code/SKU:</b> {item["code"]}</td>
                    <td style="padding:8px"><b>Description:</b> {name}</td>
                    <td style="padding:8px"><b>Category:</b> {item["category"]}</td>
                    <td style="padding:8px"><b>UoM:</b> {uom}</td>
                </tr>
                <tr>
                    <td style="padding:8px"><b>Unit Cost:</b> {cost:,.2f}</td>
                    <td style="padding:8px"><b>Selling Price:</b> {sell:,.2f}</td>
                    <td style="padding:8px"><b>Margin:</b> {sell-cost:,.2f} ({(sell-cost)/max(sell,0.01)*100:.1f}%)</td>
                    <td style="padding:8px"><b>Reorder Level:</b> {item["reorder_level"]}</td>
                </tr>
                </table>
            </div>
            """, unsafe_allow_html=True)

            # Build bin card entries
            entries = []

            # Opening balance
            entries.append({
                "date": pd.Timestamp(start_date),
                "type": "OPENING",
                "reference": "Opening Balance",
                "party": "",
                "qty_in": opening,
                "qty_out": 0,
                "unit_cost": cost,
                "value_in": opening * cost,
                "value_out": 0,
            })

            # Purchases
            if not purch2.empty:
                for col in ["item_code","item_description"]:
                    if col in purch2.columns:
                        mask = purch2[col].astype(str).str.lower() == selected.lower()
                        ip = purch2[mask]
                        if show_all:
                            ip = ip
                        else:
                            ip = ip[(pd.to_datetime(ip["date"], errors="coerce") >= pd.Timestamp(start_date)) & (pd.to_datetime(ip["date"], errors="coerce") <= pd.Timestamp(end_date))]
                        for _, r in ip.iterrows():
                            qty = float(to_num(pd.Series([r.get("quantity",0)])).iloc[0])
                            uc  = float(to_num(pd.Series([r.get("unit_cost",cost)])).iloc[0]) or cost
                            entries.append({
                                "date": r.get("date"),
                                "type": "PURCHASE IN",
                                "reference": str(r.get("reference_number","") or ""),
                                "party": str(r.get("supplier","") or ""),
                                "qty_in": qty, "qty_out": 0,
                                "unit_cost": uc, "value_in": qty*uc, "value_out": 0,
                            })
                        break

            # Purchase returns
            if not pr2.empty:
                for col in ["item_code","item_description"]:
                    if col in pr2.columns:
                        mask = pr2[col].astype(str).str.lower() == selected.lower()
                        ipr = pr2[mask]
                        for _, r in ipr.iterrows():
                            qty = float(to_num(pd.Series([r.get("quantity_returned",0)])).iloc[0])
                            uc  = float(to_num(pd.Series([r.get("unit_cost",cost)])).iloc[0]) or cost
                            entries.append({
                                "date": r.get("date"),
                                "type": "PURCHASE RTN OUT",
                                "reference": str(r.get("return_reference","") or ""),
                                "party": str(r.get("supplier","") or ""),
                                "qty_in": 0, "qty_out": qty,
                                "unit_cost": uc, "value_in": 0, "value_out": qty*uc,
                            })
                        break

            # Sales
            if not sales2.empty:
                for col in ["item_code","item_description"]:
                    if col in sales2.columns:
                        mask = sales2[col].astype(str).str.lower() == selected.lower()
                        isl = sales2[mask]
                        if not show_all:
                            isl = isl[(pd.to_datetime(isl["date"], errors="coerce") >= pd.Timestamp(start_date)) & (pd.to_datetime(isl["date"], errors="coerce") <= pd.Timestamp(end_date))]
                        for _, r in isl.iterrows():
                            qty = float(to_num(pd.Series([r.get("quantity",0)])).iloc[0])
                            entries.append({
                                "date": r.get("date"),
                                "type": "SALE OUT",
                                "reference": str(r.get("invoice_number","") or ""),
                                "party": str(r.get("customer","") or ""),
                                "qty_in": 0, "qty_out": qty,
                                "unit_cost": cost, "value_in": 0, "value_out": qty*cost,
                            })
                        break

            # Sales returns
            if not sr2.empty:
                for col in ["item_code","item_description"]:
                    if col in sr2.columns:
                        mask = sr2[col].astype(str).str.lower() == selected.lower()
                        isr = sr2[mask]
                        for _, r in isr.iterrows():
                            qty = float(to_num(pd.Series([r.get("quantity_returned",0)])).iloc[0])
                            entries.append({
                                "date": r.get("date"),
                                "type": "SALE RTN IN",
                                "reference": str(r.get("return_reference","") or ""),
                                "party": str(r.get("customer","") or ""),
                                "qty_in": qty, "qty_out": 0,
                                "unit_cost": cost, "value_in": qty*cost, "value_out": 0,
                            })
                        break

            # Build dataframe
            if entries:
                bin_df = pd.DataFrame(entries)
                bin_df["date"] = pd.to_datetime(bin_df["date"], errors="coerce")
                bin_df = bin_df.sort_values("date").reset_index(drop=True)
                bin_df["net_qty"]       = bin_df["qty_in"] - bin_df["qty_out"]
                bin_df["balance_qty"]   = bin_df["net_qty"].cumsum()
                bin_df["balance_value"] = bin_df["balance_qty"] * bin_df["unit_cost"]
                bin_df["date_str"]      = bin_df["date"].dt.strftime("%Y-%m-%d")

                # Summary
                total_in  = bin_df["qty_in"].sum()
                total_out = bin_df["qty_out"].sum()
                final_bal = bin_df["balance_qty"].iloc[-1]
                final_val = final_bal * cost

                bm = st.columns(5)
                bm[0].metric("Opening", f"{opening:,.2f}")
                bm[1].metric("Total In",  f"{total_in - opening:,.2f}")
                bm[2].metric("Total Out", f"{total_out:,.2f}")
                bm[3].metric("Closing Qty", f"{final_bal:,.2f}")
                bm[4].metric("Closing Value", f"{final_val:,.2f}")

                # Status check
                if final_bal < 0:
                    st.markdown('<div class="flag-red">🚨 NEGATIVE STOCK — Data issue or unrecorded purchases!</div>',
                                unsafe_allow_html=True)
                elif final_bal == 0:
                    st.markdown('<div class="flag-orange">⚠️ Zero stock balance</div>',
                                unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="flag-green">✅ Stock balance: {final_bal:,.2f} units at cost {final_val:,.2f}</div>',
                                unsafe_allow_html=True)

                # Chart
                fig_bin = go.Figure()
                fig_bin.add_trace(go.Scatter(
                    x=bin_df["date"], y=bin_df["balance_qty"],
                    mode="lines+markers", name="Stock Balance",
                    line=dict(color="#1a237e", width=3),
                    fill="tozeroy", fillcolor="rgba(26,35,126,0.08)"
                ))
                fig_bin.add_hline(y=0, line_dash="dash", line_color="red")
                if item["reorder_level"] > 0:
                    fig_bin.add_hline(
                        y=item["reorder_level"],
                        line_dash="dot", line_color="orange",
                        annotation_text=f"Reorder: {item['reorder_level']}"
                    )
                fig_bin.update_layout(title=f"Stock Movement — {name} ({selected})",
                                      height=350)
                st.plotly_chart(fig_bin, use_container_width=True)

                # Bin card table
                display = bin_df[["date_str","type","reference","party",
                    "qty_in","qty_out","unit_cost","value_in","value_out",
                    "balance_qty","balance_value"]].rename(columns={
                    "date_str":"Date","type":"Movement","reference":"Reference",
                    "party":"Party","qty_in":"Qty In","qty_out":"Qty Out",
                    "unit_cost":"Unit Cost","value_in":"Value In",
                    "value_out":"Value Out","balance_qty":"Balance Qty",
                    "balance_value":"Balance Value"})
                st.dataframe(display.round(2), use_container_width=True, height=400)
                st.download_button(
                    f"📥 Download Bin Card — {selected}",
                    display.round(2).to_csv(index=False),
                    f"bin_card_{selected}_{start_date}_{end_date}.csv","text/csv"
                )

# ════════════════════════════════════════════════════════
# TAB 3 — PURCHASE RETURNS
# ════════════════════════════════════════════════════════
with tabs[2]:
    st.markdown('<div class="section-header">↩️ Purchase Returns</div>', unsafe_allow_html=True)

    pr3 = load("purchase_returns")
    p3  = load("purchases")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Record New Purchase Return:**")
        with st.form("pr_form", clear_on_submit=True):
            pr_date  = st.date_input("Return Date", today)
            pr_ref   = st.text_input("Return Reference", placeholder="RTN-2025-001")
            pr_po    = st.text_input("Original PO Number")
            pr_supp  = st.text_input("Supplier *")
            pr_code  = st.text_input("Item Code / SKU")
            pr_item  = st.text_input("Item Description")
            pr_qty   = st.number_input("Qty Returned", min_value=0.0, value=1.0)
            pr_cost  = st.number_input("Unit Cost", min_value=0.0, value=0.0)
            pr_amt   = pr_qty * pr_cost
            st.metric("Return Amount", f"{pr_amt:,.2f}")
            pr_reason = st.selectbox("Reason", [
                "Defective/Damaged","Wrong Item","Quality Issue",
                "Excess Stock","Price Dispute","Expired","Other"])
            pr_debit = st.text_input("Debit Note No.")
            pr_credit_recv = st.checkbox("Credit Note Received?")
            pr_credit_amt  = st.number_input("Credit Amount", min_value=0.0,
                value=pr_amt if pr_credit_recv else 0.0)
            pr_approved = st.text_input("Approved By")

            if st.form_submit_button("💾 Save Return", type="primary", use_container_width=True):
                if pr_supp and pr_qty > 0:
                    conn = get_conn()
                    conn.execute("""
                        INSERT INTO purchase_returns
                        (date,return_reference,original_po_number,supplier,
                         item_code,item_description,quantity_returned,unit_cost,
                         return_amount,reason,debit_note_number,
                         credit_received,credit_amount,approved_by)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """, (str(pr_date),pr_ref,pr_po,pr_supp,pr_code,pr_item,
                          pr_qty,pr_cost,pr_amt,pr_reason,pr_debit,
                          1 if pr_credit_recv else 0,pr_credit_amt,pr_approved))
                    conn.commit(); conn.close()
                    st.success(f"✅ Return saved: {pr_supp} — {pr_amt:,.2f}")
                    st.rerun()
                else:
                    st.error("Supplier and quantity required")

    with col2:
        if pr3.empty:
            st.info("No purchase returns recorded yet.")
        else:
            pr3["date"]          = pd.to_datetime(pr3["date"], errors="coerce")
            pr3["return_amount"] = to_num(pr3.get("return_amount", pd.Series(dtype=float)))
            pr3["credit_amount"] = to_num(pr3.get("credit_amount", pd.Series(dtype=float)))

            pr_mask = (pd.to_datetime(pr3["date"], errors="coerce") >= pd.Timestamp(start_date)) & (pd.to_datetime(pr3["date"], errors="coerce") <= pd.Timestamp(end_date))
            prp = pr3[pr_mask]

            if not prp.empty:
                tot_ret    = prp["return_amount"].sum()
                tot_credit = prp["credit_amount"].sum()
                pending    = tot_ret - tot_credit

                m = st.columns(3)
                m[0].metric("Total Returns",    f"{tot_ret:,.2f}")
                m[1].metric("Credits Received", f"{tot_credit:,.2f}")
                m[2].metric("Pending",          f"{pending:,.2f}", delta_color="inverse")

                if pending > 0:
                    st.markdown(
                        f'<div class="flag-orange">⚠️ {pending:,.2f} in returns awaiting credit notes</div>',
                        unsafe_allow_html=True)

                by_supp = prp.groupby("supplier").agg(
                    Returned=("return_amount","sum"),
                    Credits=("credit_amount","sum"),
                    Count=("return_amount","count")
                ).reset_index()
                by_supp["Pending"] = by_supp["Returned"] - by_supp["Credits"]
                st.dataframe(by_supp.round(2), use_container_width=True, height=200)

            st.dataframe(prp.sort_values("date",ascending=False),
                         use_container_width=True, height=300)
            st.download_button("📥 Download Returns",
                prp.to_csv(index=False),
                f"purchase_returns_{start_date}_{end_date}.csv","text/csv")

    # Reconcile purchases vs returns
    st.divider()
    st.markdown('<div class="section-header">⚖️ Purchases vs Returns Reconciliation</div>',
                unsafe_allow_html=True)
    if not p3.empty:
        p3["total_cost"] = to_num(p3.get("total_cost", pd.Series(dtype=float)))
        gross = p3["total_cost"].sum()
        ret_total = to_num(pr3.get("return_amount", pd.Series(dtype=float))).sum() if not pr3.empty else 0
        net_p = gross - ret_total

        m = st.columns(3)
        m[0].metric("Gross Purchases", f"{gross:,.2f}")
        m[1].metric("Less Returns",    f"{ret_total:,.2f}", delta_color="inverse")
        m[2].metric("Net Purchases",   f"{net_p:,.2f}")
        st.markdown("""
        **Formula:** Net Purchases = Gross Purchases - Purchase Returns
        This is the correct input into your COGS calculation.
        """)

# ════════════════════════════════════════════════════════
# TAB 4 — PURCHASE ANALYSIS
# ════════════════════════════════════════════════════════
with tabs[3]:
    st.markdown('<div class="section-header">📊 Purchase Analysis</div>', unsafe_allow_html=True)
    p4 = load("purchases")
    if p4.empty:
        st.warning("No purchase data.")
    else:
        p4["date"]       = pd.to_datetime(p4["date"], errors="coerce")
        p4["total_cost"] = to_num(p4.get("total_cost", pd.Series(dtype=float)))
        p4["quantity"]   = to_num(p4.get("quantity",   pd.Series(dtype=float)))

        mask4 = (pd.to_datetime(p4["date"], errors="coerce") >= pd.Timestamp(start_date)) & (pd.to_datetime(p4["date"], errors="coerce") <= pd.Timestamp(end_date))
        pf = p4[mask4]

        col_a, col_b = st.columns(2)

        # By supplier
        if not pf.empty and "supplier" in pf.columns:
            with col_a:
                by_s = pf.groupby("supplier").agg(
                    Total=("total_cost","sum"),
                    Orders=("total_cost","count"),
                    Qty=("quantity","sum")
                ).reset_index().sort_values("Total", ascending=False)
                fig_s = px.bar(by_s.head(10), x="supplier", y="Total",
                               title="Top Suppliers by Value",
                               color_discrete_sequence=["#1a237e"])
                st.plotly_chart(fig_s, use_container_width=True)
                st.dataframe(by_s.round(2), use_container_width=True, height=200)

        # By item
        if not pf.empty and "item_description" in pf.columns:
            with col_b:
                by_i = pf.groupby("item_description").agg(
                    Total=("total_cost","sum"),
                    Qty=("quantity","sum"),
                    Orders=("total_cost","count")
                ).reset_index().sort_values("Total", ascending=False)
                fig_i = px.bar(by_i.head(10), x="item_description", y="Qty",
                               title="Top Items by Quantity Purchased",
                               color_discrete_sequence=["#42a5f5"])
                st.plotly_chart(fig_i, use_container_width=True)
                st.dataframe(by_i.round(2), use_container_width=True, height=200)

# ════════════════════════════════════════════════════════
# TAB 5 — RECONCILE PURCHASES
# ════════════════════════════════════════════════════════
with tabs[4]:
    st.markdown('<div class="section-header">⚖️ Reconcile Purchases vs Payments</div>',
                unsafe_allow_html=True)
    p5   = load("purchases")
    bank5= load("banking")

    if p5.empty:
        st.warning("No purchase data.")
    else:
        p5["total_cost"] = to_num(p5.get("total_cost", pd.Series(dtype=float)))
        bank5["debit"]   = to_num(bank5.get("debit",   pd.Series(dtype=float))) if not bank5.empty else pd.Series(dtype=float)
        debits = bank5[bank5["debit"]>0] if not bank5.empty else pd.DataFrame()

        rows = []
        for _, r in p5.iterrows():
            amt = r.get("total_cost",0)
            ref = str(r.get("reference_number","") or "")
            matched = pd.DataFrame()
            if not debits.empty:
                if ref and "description" in debits.columns:
                    rm = debits[debits["description"].astype(str).str.contains(ref,case=False,na=False)]
                    if not rm.empty: matched = rm
                if matched.empty:
                    am = debits[debits["debit"].round(2)==round(amt,2)]
                    if not am.empty: matched = am
            status = "✅ PAID" if not matched.empty else "🔴 OUTSTANDING"
            bank_ref = str(matched.iloc[0].get("reference","") or "") if not matched.empty else ""
            rows.append({
                "Date": r.get("date",""), "Reference": ref,
                "Supplier": r.get("supplier",""),
                "Item": r.get("item_description",""),
                "Amount": amt, "Bank Reference": bank_ref,
                "Status": status,
                "Outstanding": 0 if not matched.empty else amt
            })

        df_r = pd.DataFrame(rows)
        tot  = df_r["Amount"].sum()
        paid = df_r[df_r["Status"]=="✅ PAID"]["Amount"].sum()
        out  = df_r[df_r["Status"]=="🔴 OUTSTANDING"]["Amount"].sum()

        m = st.columns(4)
        m[0].metric("Total Purchases",    f"{tot:,.2f}")
        m[1].metric("✅ Paid",             f"{paid:,.2f}")
        m[2].metric("🔴 Outstanding",      f"{out:,.2f}", delta_color="inverse")
        m[3].metric("Payment Rate",        f"{paid/tot*100 if tot else 0:.1f}%")

        st.dataframe(df_r, use_container_width=True, height=400)
        st.download_button("📥 Download Purchase Reconciliation",
            df_r.to_csv(index=False),
            f"purch_recon_{start_date}_{end_date}.csv","text/csv")

# ════════════════════════════════════════════════════════
# TAB 6 — MONTH-END INVENTORY BALANCE
# ════════════════════════════════════════════════════════
with tabs[5]:
    st.markdown('<div class="section-header">📦 Month-End Inventory Balance</div>',
                unsafe_allow_html=True)

    inv6 = load("inventory")
    p6   = load("purchases")
    s6   = load("sales")
    pr6  = load("purchase_returns")
    sr6  = load("sales_returns")

    if inv6.empty:
        st.warning("No inventory data. Upload inventory file first.")
    else:
        st.info(f"Period: {start_date} to {end_date}")

        # Parse dates
        for df in [p6, s6, pr6, sr6]:
            if not df.empty and "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"], errors="coerce")

        rows6 = []
        for _, item in inv6.iterrows():
            desc = str(item.get("description","") or "")
            code = str(item.get("item_code","") or "")
            cost = float(item.get("unit_cost",0) or 0)
            sell = float(item.get("selling_price",0) or 0)
            opening = float(item.get("opening_qty",0) or 0)
            rl = float(item.get("reorder_level",0) or 0)

            def get_qty(df, desc_col, qty_col, date_filter=True):
                if df.empty or desc_col not in df.columns: return 0
                mask = df[desc_col].astype(str).str.lower()==desc.lower()
                subset = df[mask]
                if date_filter:
                    subset = subset[(pd.to_datetime(subset["date"], errors="coerce") >= pd.Timestamp(start_date))&(pd.to_datetime(subset["date"], errors="coerce") <= pd.Timestamp(end_date))]
                return float(to_num(subset.get(qty_col,pd.Series(dtype=float))).sum())

            purch_qty = get_qty(p6, "item_description", "quantity")
            sales_qty = get_qty(s6, "item_description", "quantity")
            pr_qty    = get_qty(pr6,"item_description", "quantity_returned")
            sr_qty    = get_qty(sr6,"item_description", "quantity_returned")

            expected = opening + purch_qty - pr_qty - sales_qty + sr_qty
            physical = float(item.get("physical_count", expected) or expected)
            variance = physical - expected
            var_val  = variance * cost
            cl_val   = physical * cost
            retail_val = physical * sell

            if abs(variance)==0:     vstatus="✅ Balanced"
            elif abs(variance)<=2:   vstatus="🟡 Minor"
            elif abs(variance)<=10:  vstatus="🟠 Moderate"
            else:                    vstatus="🔴 Major"

            below_reorder = "⚠️ Reorder" if rl>0 and physical<=rl else "OK"

            rows6.append({
                "SKU/Code":      code,
                "Description":   desc,
                "Cost":          cost,
                "Sell Price":    sell,
                "Opening":       opening,
                "Purchased":     purch_qty,
                "Purch Returns": pr_qty,
                "Sold":          sales_qty,
                "Sale Returns":  sr_qty,
                "Expected Close":round(expected,2),
                "Physical":      physical,
                "Variance Qty":  round(variance,2),
                "Variance Value":round(var_val,2),
                "Closing Value": round(cl_val,2),
                "Retail Value":  round(retail_val,2),
                "Status":        vstatus,
                "Stock Alert":   below_reorder,
            })

        df6 = pd.DataFrame(rows6)

        # Summary
        tot_cost  = df6["Closing Value"].sum()
        tot_retail= df6["Retail Value"].sum()
        tot_var   = df6["Variance Value"].sum()
        n_issues  = len(df6[df6["Status"]!="✅ Balanced"])
        n_reorder = len(df6[df6["Stock Alert"]=="⚠️ Reorder"])

        m = st.columns(5)
        m[0].metric("Items",             len(df6))
        m[1].metric("Closing at Cost",   f"{tot_cost:,.2f}")
        m[2].metric("Closing at Retail", f"{tot_retail:,.2f}")
        m[3].metric("Variance Value",    f"{tot_var:,.2f}", delta_color="inverse")
        m[4].metric("Reorder Alerts",    n_reorder)

        # Month-end formula display
        st.markdown("""
        **📐 Month-End Inventory Formula:**
        ```
        Closing Stock = Opening
                      + Purchases
                      - Purchase Returns
                      - Sales
                      + Sales Returns
        ```
        """)

        st.dataframe(df6.round(2), use_container_width=True, height=450)

        dl1,dl2,dl3 = st.columns(3)
        with dl1:
            st.download_button("📥 Full Inventory", df6.to_csv(index=False),
                f"inventory_month_end_{end_date}.csv","text/csv",use_container_width=True)
        with dl2:
            var_df = df6[df6["Variance Qty"]!=0]
            if not var_df.empty:
                st.download_button("📥 Variances Only", var_df.to_csv(index=False),
                    f"variances_{end_date}.csv","text/csv",use_container_width=True)
        with dl3:
            reorder_df = df6[df6["Stock Alert"]=="⚠️ Reorder"]
            if not reorder_df.empty:
                st.download_button("📥 Reorder List", reorder_df.to_csv(index=False),
                    f"reorder_{end_date}.csv","text/csv",use_container_width=True)

st.markdown('<div class="finteca-footer">Finteca AuditRep v4.0 · Purchase Ledger · Bin Cards · Month-End Inventory</div>',
            unsafe_allow_html=True)
