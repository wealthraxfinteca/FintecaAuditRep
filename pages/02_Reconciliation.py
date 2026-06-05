import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

st.set_page_config(page_title="Reconciliation - Finteca AuditRep", page_icon="🏦", layout="wide")

CSS = """<style>
.finteca-header{background:linear-gradient(135deg,#1a237e 0%,#283593 50%,#42a5f5 100%);padding:25px 30px;border-radius:12px;color:white;margin-bottom:25px;box-shadow:0 4px 15px rgba(26,35,126,0.3);}
.finteca-header h1{margin:0;font-size:2.2em;font-weight:800;}
.finteca-header p{margin:5px 0 0 0;opacity:0.85;}
.finteca-badge{background:rgba(255,255,255,0.2);padding:3px 10px;border-radius:20px;font-size:0.75em;display:inline-block;margin-top:8px;}
.section-header{background:#f5f7ff;border-left:4px solid #1a237e;padding:10px 15px;border-radius:0 8px 8px 0;margin:15px 0;font-weight:600;color:#1a237e;}
.alert-critical{background:#ffebee;border-left:5px solid #c62828;padding:12px 15px;border-radius:6px;margin:6px 0;}
.alert-ok{background:#e8f5e9;border-left:5px solid #2e7d32;padding:12px 15px;border-radius:6px;margin:6px 0;}
.finteca-footer{text-align:center;color:#999;font-size:0.8em;padding:20px;border-top:1px solid #eee;margin-top:30px;}
</style>"""
st.markdown(CSS, unsafe_allow_html=True)
st.markdown("""<div class="finteca-header"><h1>🏦 Finteca AuditRep</h1><p>Reconciliation Engine</p><span class="finteca-badge">Module 2 — Reconciliation</span></div>""", unsafe_allow_html=True)

DB_PATH = "data/reconciliation.db"

def load(table):
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql(f"SELECT * FROM {table}", conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

def to_num(s):
    return pd.to_numeric(s, errors="coerce").fillna(0)

tabs = st.tabs(["🏦 Bank vs Collections","🛒 Purchases vs Payments","💰 Sales vs Collections","📦 Inventory","🔄 Swap Deals","↩️ Returns"])

with tabs[0]:
    st.markdown('<div class="section-header">🏦 Bank Statement vs Collections</div>', unsafe_allow_html=True)
    st.info("Matches every collection against actual bank deposits. Unmatched items require immediate investigation.")
    coll = load("collections")
    bank = load("banking")
    if coll.empty:
        st.warning("No collections data found. Please upload collections first.")
    else:
        coll["amount"] = to_num(coll.get("amount", pd.Series(dtype=float)))
        if not bank.empty and "credit" in bank.columns:
            bank["credit"] = to_num(bank["credit"])
        rows = []
        for _, r in coll.iterrows():
            amt = float(r.get("amount", 0) or 0)
            cust = str(r.get("customer", "") or "")
            invref = str(r.get("invoice_reference", "") or "")
            c_date = str(r.get("date", "") or "")
            rec_by = str(r.get("received_by", "") or "")
            method = str(r.get("payment_method", "") or "")
            matched = pd.DataFrame()
            match_type = "NO MATCH"
            b_date = ""
            b_ref = ""
            days_diff = 0
            if not bank.empty and "credit" in bank.columns:
                exact = bank[bank["credit"].round(2) == round(amt, 2)]
                if not exact.empty:
                    matched = exact
                    match_type = "EXACT MATCH"
                else:
                    tol = max(amt * 0.01, 0.50)
                    near = bank[abs(bank["credit"] - amt) <= tol]
                    if not near.empty:
                        matched = near
                        match_type = "NEAR MATCH"
            if not matched.empty:
                b_date = str(matched.iloc[0].get("date", "") or "")
                b_ref = str(matched.iloc[0].get("reference", "") or "")
                try:
                    d1 = datetime.strptime(c_date[:10], "%Y-%m-%d")
                    d2 = datetime.strptime(b_date[:10], "%Y-%m-%d")
                    days_diff = abs((d2 - d1).days)
                except Exception:
                    days_diff = 0
                status = f"⚠️ LATE BANKING ({days_diff} days)" if days_diff > 3 else "✅ BANKED"
                unbanked = 0.0
            else:
                status = "🔴 NOT BANKED"
                unbanked = amt
            rows.append({"Date":c_date,"Customer":cust,"Invoice Ref":invref,"Amount":amt,"Method":method,"Received By":rec_by,"Bank Date":b_date,"Bank Ref":b_ref,"Match":match_type,"Status":status,"Unbanked":unbanked})
        df_r = pd.DataFrame(rows)
        if not df_r.empty:
            tot = df_r["Amount"].sum()
            banked = df_r[df_r["Status"].str.contains("BANKED",na=False) & ~df_r["Status"].str.contains("NOT",na=False)]["Amount"].sum()
            not_bnkd = df_r[df_r["Status"]=="🔴 NOT BANKED"]["Amount"].sum()
            eff = banked/tot*100 if tot>0 else 0
            m1,m2,m3,m4,m5 = st.columns(5)
            m1.metric("Total Collected",f"{tot:,.2f}")
            m2.metric("✅ Banked",f"{banked:,.2f}")
            m3.metric("🔴 Not Banked",f"{not_bnkd:,.2f}",delta_color="inverse")
            m4.metric("Banking Efficiency",f"{eff:.1f}%")
            m5.metric("Transactions",len(df_r))
            status_sum = df_r.groupby("Status")["Amount"].sum().reset_index()
            fig = px.pie(status_sum,names="Status",values="Amount",title="Collections Banking Status",color_discrete_sequence=["#2e7d32","#c62828","#f57f17","#1a237e"])
            st.plotly_chart(fig,use_container_width=True)
            def highlight(row):
                if "NOT BANKED" in str(row["Status"]): return ["background-color:#ffebee"]*len(row)
                elif "LATE" in str(row["Status"]): return ["background-color:#fff8e1"]*len(row)
                return ["background-color:#e8f5e9"]*len(row)
            st.dataframe(df_r.style.apply(highlight,axis=1),use_container_width=True,height=350)
            st.download_button("📥 Download Reconciliation",df_r.to_csv(index=False),f"bank_recon_{datetime.now().strftime('%Y%m%d')}.csv","text/csv")

with tabs[1]:
    st.markdown('<div class="section-header">🛒 Purchases vs Bank Payments</div>', unsafe_allow_html=True)
    purch = load("purchases")
    bank2 = load("banking")
    if purch.empty:
        st.warning("No purchases data found.")
    else:
        purch["total_cost"] = to_num(purch.get("total_cost",pd.Series(dtype=float)))
        debits = pd.DataFrame()
        if not bank2.empty and "debit" in bank2.columns:
            bank2["debit"] = to_num(bank2["debit"])
            debits = bank2[bank2["debit"]>0]
        rows2 = []
        for _, r in purch.iterrows():
            amt = float(r.get("total_cost",0) or 0)
            ref = str(r.get("reference_number","") or "")
            matched2 = pd.DataFrame()
            if not debits.empty:
                if ref and "description" in debits.columns:
                    rm = debits[debits["description"].astype(str).str.contains(ref,case=False,na=False)]
                    if not rm.empty: matched2 = rm
                if matched2.empty:
                    am = debits[debits["debit"].round(2)==round(amt,2)]
                    if not am.empty: matched2 = am
            status2 = "✅ PAID" if not matched2.empty else "🔴 OUTSTANDING"
            bank_ref = str(matched2.iloc[0].get("reference","") or "") if not matched2.empty else ""
            rows2.append({"Date":r.get("date",""),"Reference":ref,"Supplier":r.get("supplier",""),"Item":r.get("item_description",""),"Amount":amt,"Bank Ref":bank_ref,"Status":status2,"Outstanding":0 if not matched2.empty else amt})
        df_p = pd.DataFrame(rows2)
        tot_p = df_p["Amount"].sum()
        paid_p = df_p[df_p["Status"]=="✅ PAID"]["Amount"].sum()
        out_p = df_p[df_p["Status"]=="🔴 OUTSTANDING"]["Amount"].sum()
        m1,m2,m3,m4 = st.columns(4)
        m1.metric("Total Purchases",f"{tot_p:,.2f}")
        m2.metric("✅ Confirmed Paid",f"{paid_p:,.2f}")
        m3.metric("🔴 Outstanding",f"{out_p:,.2f}",delta_color="inverse")
        m4.metric("Payment Rate",f"{paid_p/tot_p*100 if tot_p else 0:.1f}%")
        st.dataframe(df_p,use_container_width=True,height=380)
        st.download_button("📥 Download",df_p.to_csv(index=False),f"purchase_recon_{datetime.now().strftime('%Y%m%d')}.csv","text/csv")

with tabs[2]:
    st.markdown('<div class="section-header">💰 Sales vs Collections</div>', unsafe_allow_html=True)
    sales3 = load("sales")
    coll3 = load("collections")
    if sales3.empty:
        st.warning("No sales data found.")
    else:
        sales3["net_amount"] = to_num(sales3.get("net_amount",pd.Series(dtype=float)))
        rows3 = []
        for _, r in sales3.iterrows():
            inv = str(r.get("invoice_number","") or "")
            amt = float(r.get("net_amount",0) or 0)
            collected = 0.0
            if not coll3.empty and "invoice_reference" in coll3.columns and inv:
                mc = coll3[coll3["invoice_reference"].astype(str).str.contains(inv,case=False,na=False)]
                if not mc.empty: collected = float(to_num(mc["amount"]).sum())
            bal = amt - collected
            if abs(bal)<0.01: st3="✅ FULLY COLLECTED"
            elif collected>0: st3="🟡 PARTIAL"
            else: st3="🔴 NOT COLLECTED"
            rows3.append({"Date":r.get("date",""),"Invoice":inv,"Customer":r.get("customer",""),"Invoice Amt":amt,"Collected":collected,"Balance Due":bal,"Status":st3,"Salesperson":r.get("salesperson","")})
        df_s = pd.DataFrame(rows3)
        tot_s = df_s["Invoice Amt"].sum()
        col_s = df_s["Collected"].sum()
        bal_s = df_s["Balance Due"].sum()
        m1,m2,m3,m4 = st.columns(4)
        m1.metric("Total Sales",f"{tot_s:,.2f}")
        m2.metric("✅ Collected",f"{col_s:,.2f}")
        m3.metric("🔴 Outstanding",f"{bal_s:,.2f}",delta_color="inverse")
        m4.metric("Collection Rate",f"{col_s/tot_s*100 if tot_s else 0:.1f}%")
        st.dataframe(df_s,use_container_width=True,height=380)
        st.download_button("📥 Download",df_s.to_csv(index=False),f"sales_recon_{datetime.now().strftime('%Y%m%d')}.csv","text/csv")

with tabs[3]:
    st.markdown('<div class="section-header">📦 Inventory Reconciliation</div>', unsafe_allow_html=True)
    inv4 = load("inventory")
    sales4 = load("sales")
    purch4 = load("purchases")
    ret4 = load("sales_returns")
    if inv4.empty:
        st.warning("No inventory data found.")
    else:
        rows4 = []
        for _, item in inv4.iterrows():
            desc = str(item.get("description","") or "")
            opening = float(item.get("opening_qty",0) or 0)
            purch_qty = float(item.get("purchases_qty",0) or 0)
            sales_qty = float(item.get("sales_qty",0) or 0)
            ret_qty = float(item.get("returns_in_qty",0) or 0)
            swap_out = float(item.get("swap_out_qty",0) or 0)
            swap_in = float(item.get("swap_in_qty",0) or 0)
            adj = float(item.get("adjustments_qty",0) or 0)
            unit_cost = float(item.get("unit_cost",0) or 0)
            if not sales4.empty and "item_description" in sales4.columns:
                ms = sales4[sales4["item_description"].astype(str).str.lower()==desc.lower()]
                sales_qty += float(to_num(ms.get("quantity",pd.Series(dtype=float))).sum())
            if not purch4.empty and "item_description" in purch4.columns:
                mp = purch4[purch4["item_description"].astype(str).str.lower()==desc.lower()]
                purch_qty += float(to_num(mp.get("quantity",pd.Series(dtype=float))).sum())
            if not ret4.empty and "item_description" in ret4.columns:
                mr = ret4[ret4["item_description"].astype(str).str.lower()==desc.lower()]
                ret_qty += float(to_num(mr.get("quantity_returned",pd.Series(dtype=float))).sum())
            expected = opening+purch_qty-sales_qty+ret_qty-swap_out+swap_in+adj
            book = float(item.get("closing_qty",0) or 0)
            physical = float(item.get("physical_count",book) or book)
            variance = physical-expected
            var_val = variance*unit_cost
            if abs(variance)==0: vstatus="✅ BALANCED"
            elif abs(variance)<=2: vstatus="🟡 MINOR"
            elif abs(variance)<=10: vstatus="🟠 MODERATE"
            else: vstatus="🔴 MAJOR"
            rows4.append({"Code":item.get("item_code",""),"Description":desc,"Opening":opening,"Purchased":purch_qty,"Sold":sales_qty,"Returns":ret_qty,"Swap Out":swap_out,"Swap In":swap_in,"Expected Closing":round(expected,2),"Physical Count":physical,"Variance Qty":round(variance,2),"Unit Cost":unit_cost,"Variance Value":round(var_val,2),"Status":vstatus})
        df_i = pd.DataFrame(rows4)
        m1,m2,m3,m4 = st.columns(4)
        m1.metric("Items",len(df_i))
        m2.metric("✅ Balanced",len(df_i[df_i["Status"]=="✅ BALANCED"]))
        m3.metric("🔴 Major Issues",len(df_i[df_i["Status"]=="🔴 MAJOR"]))
        m4.metric("Total Variance Value",f"{df_i['Variance Value'].sum():,.2f}",delta_color="inverse")
        vd = df_i[df_i["Variance Qty"]!=0]
        if not vd.empty:
            fig4 = px.bar(vd,x="Description",y="Variance Value",color="Status",title="Inventory Variance by Item",color_discrete_map={"✅ BALANCED":"#2e7d32","🟡 MINOR":"#f9a825","🟠 MODERATE":"#e65100","🔴 MAJOR":"#c62828"})
            fig4.add_hline(y=0,line_dash="dash",line_color="gray")
            st.plotly_chart(fig4,use_container_width=True)
        st.dataframe(df_i,use_container_width=True,height=350)
        st.download_button("📥 Download",df_i.to_csv(index=False),f"inventory_recon_{datetime.now().strftime('%Y%m%d')}.csv","text/csv")

with tabs[4]:
    st.markdown('<div class="section-header">🔄 Swap Deal Verification</div>', unsafe_allow_html=True)
    swaps = load("swap_deals")
    if swaps.empty:
        st.warning("No swap deals found.")
    else:
        swaps["difference_amount"] = to_num(swaps.get("difference_amount",pd.Series(dtype=float)))
        swaps["customer_paid"] = to_num(swaps.get("customer_paid",pd.Series(dtype=float)))
        swaps["variance"] = swaps["customer_paid"]-swaps["difference_amount"]
        m1,m2,m3 = st.columns(3)
        m1.metric("Total Difference Due",f"{swaps['difference_amount'].sum():,.2f}")
        m2.metric("Total Collected",f"{swaps['customer_paid'].sum():,.2f}")
        m3.metric("Variance",f"{swaps['variance'].sum():,.2f}",delta_color="inverse")
        st.dataframe(swaps,use_container_width=True,height=350)

with tabs[5]:
    st.markdown('<div class="section-header">↩️ Sales Returns Reconciliation</div>', unsafe_allow_html=True)
    ret6 = load("sales_returns")
    sales6 = load("sales")
    if ret6.empty:
        st.warning("No returns data found.")
    else:
        ret6["return_amount"] = to_num(ret6.get("return_amount",pd.Series(dtype=float)))
        orphan = 0
        restocked = 0
        if not sales6.empty and "original_invoice" in ret6.columns and "invoice_number" in sales6.columns:
            orphan = len(ret6[~ret6["original_invoice"].isin(sales6["invoice_number"])])
        if "restocked" in ret6.columns:
            restocked = int(ret6["restocked"].sum())
        m1,m2,m3,m4 = st.columns(4)
        m1.metric("Total Returns",len(ret6))
        m2.metric("Total Return Value",f"{ret6['return_amount'].sum():,.2f}")
        m3.metric("Restocked",restocked)
        m4.metric("🚨 No Original Sale",orphan,delta_color="inverse")
        if orphan>0:
            st.markdown(f'<div class="alert-critical">🚨 {orphan} returns have no matching original sale — investigate immediately.</div>',unsafe_allow_html=True)
        st.dataframe(ret6,use_container_width=True,height=350)

st.markdown('<div class="finteca-footer">Finteca AuditRep v1.0.0</div>', unsafe_allow_html=True)
