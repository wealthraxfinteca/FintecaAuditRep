import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
import os
import json
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

st.set_page_config(page_title="Reports - Finteca AuditRep", page_icon="🏦", layout="wide")

CSS = """<style>
.finteca-header{background:linear-gradient(135deg,#1a237e 0%,#283593 50%,#42a5f5 100%);padding:25px 30px;border-radius:12px;color:white;margin-bottom:25px;box-shadow:0 4px 15px rgba(26,35,126,0.3);}
.finteca-header h1{margin:0;font-size:2.2em;font-weight:800;}
.finteca-header p{margin:5px 0 0 0;opacity:0.85;}
.finteca-badge{background:rgba(255,255,255,0.2);padding:3px 10px;border-radius:20px;font-size:0.75em;display:inline-block;margin-top:8px;}
.metric-card{background:white;padding:20px;border-radius:10px;border-left:5px solid #1a237e;box-shadow:0 2px 8px rgba(0,0,0,0.08);margin-bottom:10px;}
.section-header{background:#f5f7ff;border-left:4px solid #1a237e;padding:10px 15px;border-radius:0 8px 8px 0;margin:15px 0;font-weight:600;color:#1a237e;}
.alert-critical{background:#ffebee;border-left:5px solid #c62828;padding:12px 15px;border-radius:6px;margin:6px 0;}
.alert-high{background:#fff3e0;border-left:5px solid #e65100;padding:12px 15px;border-radius:6px;margin:6px 0;}
.alert-ok{background:#e8f5e9;border-left:5px solid #2e7d32;padding:12px 15px;border-radius:6px;margin:6px 0;}
.finteca-footer{text-align:center;color:#999;font-size:0.8em;padding:20px;border-top:1px solid #eee;margin-top:30px;}
</style>"""
st.markdown(CSS, unsafe_allow_html=True)
st.markdown("""<div class="finteca-header"><h1>🏦 Finteca AuditRep</h1><p>Reports · Fraud Detection · AI Investigation</p><span class="finteca-badge">Module 3 — Reports</span></div>""", unsafe_allow_html=True)

DB_PATH = "data/reconciliation.db"
API_KEY = os.getenv("OPENAI_API_KEY","")

def load(t):
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql(f"SELECT * FROM {t}",conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

def to_num(s):
    return pd.to_numeric(s,errors="coerce").fillna(0)

tabs = st.tabs(["📊 Executive Dashboard","💰 Profitability","🏦 Cash Position","🚨 Fraud Detection","📋 Financial Ratios","🤖 AI Investigator"])

with tabs[0]:
    st.markdown('<div class="section-header">📊 Executive Dashboard</div>', unsafe_allow_html=True)
    sales=load("sales"); coll=load("collections"); bank=load("banking"); ret=load("sales_returns"); inv=load("inventory")
    revenue=to_num(sales.get("net_amount",pd.Series(dtype=float))).sum() if not sales.empty else 0
    cogs=to_num(sales.get("cost_of_goods",pd.Series(dtype=float))).sum() if not sales.empty else 0
    gp=revenue-cogs
    gp_pct=gp/revenue*100 if revenue else 0
    collected=to_num(coll.get("amount",pd.Series(dtype=float))).sum() if not coll.empty else 0
    bank_in=to_num(bank.get("credit",pd.Series(dtype=float))).sum() if not bank.empty else 0
    bank_out=to_num(bank.get("debit",pd.Series(dtype=float))).sum() if not bank.empty else 0
    net_cash=bank_in-bank_out
    ret_val=to_num(ret.get("return_amount",pd.Series(dtype=float))).sum() if not ret.empty else 0
    c1,c2,c3,c4,c5,c6=st.columns(6)
    c1.metric("💰 Revenue",f"{revenue:,.0f}")
    c2.metric("📈 Gross Profit",f"{gp:,.0f}",delta=f"{gp_pct:.1f}%")
    c3.metric("💵 Collected",f"{collected:,.0f}")
    c4.metric("🏦 Net Cash",f"{net_cash:,.0f}")
    c5.metric("↩️ Returns",f"{ret_val:,.0f}",delta_color="inverse")
    c6.metric("📦 Inventory Items",len(inv) if not inv.empty else 0)
    col_a,col_b=st.columns(2)
    with col_a:
        if revenue>0:
            fig=go.Figure(data=[go.Bar(name="Revenue",x=["Summary"],y=[revenue],marker_color="#1a237e"),go.Bar(name="COGS",x=["Summary"],y=[cogs],marker_color="#e53935"),go.Bar(name="Gross Profit",x=["Summary"],y=[gp],marker_color="#2e7d32")])
            fig.update_layout(title="Revenue vs COGS vs Gross Profit",barmode="group",height=320)
            st.plotly_chart(fig,use_container_width=True)
        else:
            st.info("Upload sales data to see profitability chart.")
    with col_b:
        if bank_in>0 or bank_out>0:
            fig2=go.Figure(data=[go.Bar(name="Cash In",x=["Banking"],y=[bank_in],marker_color="#2e7d32"),go.Bar(name="Cash Out",x=["Banking"],y=[bank_out],marker_color="#c62828")])
            fig2.update_layout(title="Cash Inflows vs Outflows",barmode="group",height=320)
            st.plotly_chart(fig2,use_container_width=True)
        else:
            st.info("Upload bank statement to see cash chart.")

with tabs[1]:
    st.markdown('<div class="section-header">💰 Profitability Analysis</div>', unsafe_allow_html=True)
    sales2=load("sales"); ret2=load("sales_returns")
    if sales2.empty:
        st.warning("No sales data found.")
    else:
        sales2["net_amount"]=to_num(sales2.get("net_amount",pd.Series(dtype=float)))
        sales2["cost_of_goods"]=to_num(sales2.get("cost_of_goods",pd.Series(dtype=float)))
        sales2["gross_profit"]=sales2["net_amount"]-sales2["cost_of_goods"]
        sales2["discount"]=to_num(sales2.get("discount",pd.Series(dtype=float)))
        total_rev=sales2["net_amount"].sum(); total_cogs=sales2["cost_of_goods"].sum(); total_gp=sales2["gross_profit"].sum()
        ret_total=to_num(ret2.get("return_amount",pd.Series(dtype=float))).sum() if not ret2.empty else 0
        net_rev=total_rev-ret_total; gpm=total_gp/total_rev*100 if total_rev else 0
        m1,m2,m3,m4,m5=st.columns(5)
        m1.metric("Gross Revenue",f"{total_rev:,.2f}"); m2.metric("Returns",f"{ret_total:,.2f}",delta_color="inverse")
        m3.metric("Net Revenue",f"{net_rev:,.2f}"); m4.metric("Gross Profit",f"{total_gp:,.2f}"); m5.metric("Gross Margin",f"{gpm:.1f}%")
        if "item_description" in sales2.columns:
            by_item=sales2.groupby("item_description").agg(Revenue=("net_amount","sum"),COGS=("cost_of_goods","sum"),GrossProfit=("gross_profit","sum"),Qty=("quantity","sum")).reset_index()
            by_item["Margin_pct"]=by_item["GrossProfit"]/by_item["Revenue"].clip(lower=0.01)*100
            by_item=by_item.sort_values("GrossProfit",ascending=False)
            fig3=px.bar(by_item.head(15),x="item_description",y="GrossProfit",color="Margin_pct",title="Gross Profit by Item",color_continuous_scale="RdYlGn")
            st.plotly_chart(fig3,use_container_width=True)
            st.dataframe(by_item,use_container_width=True,height=300)

with tabs[2]:
    st.markdown('<div class="section-header">🏦 Cash Position & Banking</div>', unsafe_allow_html=True)
    bank3=load("banking"); coll3=load("collections")
    if bank3.empty:
        st.warning("No banking data found.")
    else:
        bank3["credit"]=to_num(bank3.get("credit",pd.Series(dtype=float)))
        bank3["debit"]=to_num(bank3.get("debit",pd.Series(dtype=float)))
        bank3["balance"]=to_num(bank3.get("balance",pd.Series(dtype=float)))
        tot_in=bank3["credit"].sum(); tot_out=bank3["debit"].sum(); net_c=tot_in-tot_out
        tot_col=to_num(coll3.get("amount",pd.Series(dtype=float))).sum() if not coll3.empty else 0
        m1,m2,m3,m4=st.columns(4)
        m1.metric("Total Inflows",f"{tot_in:,.2f}"); m2.metric("Total Outflows",f"{tot_out:,.2f}",delta_color="inverse")
        m3.metric("Net Cash",f"{net_c:,.2f}"); m4.metric("Total Collected",f"{tot_col:,.2f}")
        try:
            bank3["date"]=pd.to_datetime(bank3["date"],errors="coerce")
            monthly=bank3.groupby(bank3["date"].dt.to_period("M")).agg(Inflows=("credit","sum"),Outflows=("debit","sum")).reset_index()
            monthly["date"]=monthly["date"].astype(str); monthly["Net"]=monthly["Inflows"]-monthly["Outflows"]
            fig4=px.line(monthly,x="date",y=["Inflows","Outflows","Net"],title="Monthly Cash Flow",color_discrete_sequence=["#2e7d32","#c62828","#1a237e"])
            fig4.add_hline(y=0,line_dash="dash",line_color="gray")
            st.plotly_chart(fig4,use_container_width=True)
        except Exception:
            pass
        st.dataframe(bank3,use_container_width=True,height=300)

with tabs[3]:
    st.markdown('<div class="section-header">🚨 Fraud Detection Engine</div>', unsafe_allow_html=True)
    alerts=[]
    coll4=load("collections"); bank4=load("banking"); sales4=load("sales"); ret4=load("sales_returns"); inv5=load("inventory")
    if not coll4.empty and not bank4.empty and "credit" in bank4.columns:
        coll4["amount"]=to_num(coll4.get("amount",pd.Series(dtype=float)))
        bank4["credit"]=to_num(bank4["credit"])
        unbanked=coll4[~coll4["amount"].round(2).isin(bank4["credit"].round(2))]
        if not unbanked.empty:
            alerts.append({"severity":"🔴 HIGH","type":"UNBANKED COLLECTIONS","description":f"{len(unbanked)} collections totalling {unbanked['amount'].sum():,.2f} not found in bank","count":len(unbanked),"data":unbanked})
    if not sales4.empty and "invoice_number" in sales4.columns:
        dups=sales4[sales4.duplicated("invoice_number",keep=False)&sales4["invoice_number"].notna()]
        if not dups.empty:
            alerts.append({"severity":"🔴 HIGH","type":"DUPLICATE INVOICES","description":f"{len(dups)} duplicate invoice numbers detected","count":len(dups),"data":dups})
    if not ret4.empty and not sales4.empty:
        if "original_invoice" in ret4.columns and "invoice_number" in sales4.columns:
            orphans=ret4[~ret4["original_invoice"].isin(sales4["invoice_number"])]
            if not orphans.empty:
                alerts.append({"severity":"🔴 HIGH","type":"RETURN FRAUD","description":f"{len(orphans)} returns with no matching original sale","count":len(orphans),"data":orphans})
    if not sales4.empty and "discount" in sales4.columns and "net_amount" in sales4.columns:
        sales4["discount"]=to_num(sales4["discount"]); sales4["net_amount"]=to_num(sales4["net_amount"])
        sales4["disc_pct"]=sales4["discount"]/sales4["net_amount"].clip(lower=0.01)*100
        high_disc=sales4[sales4["disc_pct"]>20]
        if not high_disc.empty:
            alerts.append({"severity":"🟠 MEDIUM","type":"EXCESSIVE DISCOUNTS","description":f"{len(high_disc)} sales with >20% discount — total: {high_disc['discount'].sum():,.2f}","count":len(high_disc),"data":high_disc})
    if not inv5.empty and "variance_value" in inv5.columns:
        inv5["variance_value"]=to_num(inv5["variance_value"])
        major=inv5[abs(inv5["variance_value"])>100]
        if not major.empty:
            alerts.append({"severity":"🟠 MEDIUM","type":"INVENTORY VARIANCE","description":f"{len(major)} items with variance >100 — total: {major['variance_value'].sum():,.2f}","count":len(major),"data":major})
    high_alerts=[a for a in alerts if "HIGH" in a["severity"]]
    med_alerts=[a for a in alerts if "MEDIUM" in a["severity"]]
    m1,m2,m3=st.columns(3)
    m1.metric("🔴 High Risk Alerts",len(high_alerts)); m2.metric("🟠 Medium Risk Alerts",len(med_alerts)); m3.metric("Total Alerts",len(alerts))
    if not alerts:
        st.markdown('<div class="alert-ok">✅ No fraud alerts detected. Upload more data for deeper analysis.</div>',unsafe_allow_html=True)
    else:
        for alert in alerts:
            sev=alert["severity"]; css="alert-critical" if "HIGH" in sev else "alert-high"
            with st.expander(f"{sev} — {alert['type']} ({alert['count']} items)",expanded=True):
                st.markdown(f'<div class="{css}">{alert["description"]}</div>',unsafe_allow_html=True)
                if "data" in alert and not alert["data"].empty:
                    st.dataframe(alert["data"].head(10),use_container_width=True)

with tabs[4]:
    st.markdown('<div class="section-header">📋 Financial Ratios & KPIs</div>', unsafe_allow_html=True)
    s5=load("sales"); c5=load("collections"); r5=load("sales_returns"); b5=load("banking"); i5=load("inventory")
    rev5=to_num(s5.get("net_amount",pd.Series(dtype=float))).sum() if not s5.empty else 0
    cogs5=to_num(s5.get("cost_of_goods",pd.Series(dtype=float))).sum() if not s5.empty else 0
    ret5v=to_num(r5.get("return_amount",pd.Series(dtype=float))).sum() if not r5.empty else 0
    col5v=to_num(c5.get("amount",pd.Series(dtype=float))).sum() if not c5.empty else 0
    bnk5=to_num(b5.get("credit",pd.Series(dtype=float))).sum() if not b5.empty else 0
    gp5=rev5-cogs5; gpm5=gp5/rev5*100 if rev5 else 0
    ret_r=ret5v/rev5*100 if rev5 else 0; col_r=col5v/rev5*100 if rev5 else 0
    avg_inv5=0
    if not i5.empty:
        ov=to_num(i5.get("opening_value",pd.Series(dtype=float))).sum(); cv=to_num(i5.get("closing_value",pd.Series(dtype=float))).sum()
        avg_inv5=(ov+cv)/2
    inv_turn=cogs5/avg_inv5 if avg_inv5 else 0
    avg_tx=rev5/len(s5) if (not s5.empty and len(s5)>0) else 0
    disc5=to_num(s5.get("discount",pd.Series(dtype=float))).sum() if not s5.empty else 0
    ratios=[("Gross Profit Margin",f"{gpm5:.1f}%","Higher is better. Typical: 30-50%"),("COGS to Revenue",f"{cogs5/rev5*100 if rev5 else 0:.1f}%","Lower is better"),("Return Rate",f"{ret_r:.2f}%","Healthy below 5%"),("Collection Rate",f"{col_r:.1f}%","Should be near 100%"),("Inventory Turnover",f"{inv_turn:.2f}x","Higher = faster moving stock"),("Cash vs Revenue",f"{bnk5/rev5*100 if rev5 else 0:.1f}%","Should be near 100%"),("Avg Transaction Value",f"{avg_tx:,.2f}","Average sale size"),("Total Discounts Given",f"{disc5:,.2f}","Monitor for abuse")]
    rcols=st.columns(4)
    for i,(name,value,note) in enumerate(ratios):
        with rcols[i%4]:
            st.markdown(f"""<div class="metric-card"><h3>{name}</h3><h2>{value}</h2><small style="color:#999">{note}</small></div>""",unsafe_allow_html=True)
            st.write("")

with tabs[5]:
    st.markdown('<div class="section-header">🤖 AI Financial Investigator</div>', unsafe_allow_html=True)
    if not API_KEY:
        st.error("Add your OpenAI API key to the .env file to enable AI features.")
    else:
        from openai import OpenAI
        client=OpenAI(api_key=API_KEY)
        if "chat_history" not in st.session_state:
            st.session_state.chat_history=[]
        quick_qs=["Summarise the overall financial health","What are the biggest fraud risks?","Which items have inventory losses?","What collections are not banked?"]
        qcols=st.columns(4)
        for qcol,q in zip(qcols,quick_qs):
            if qcol.button(q,use_container_width=True):
                st.session_state.pending_q=q
        user_q=st.chat_input("Ask anything about your financial data...")
        if user_q: st.session_state.pending_q=user_q
        if "pending_q" in st.session_state:
            question=st.session_state.pop("pending_q")
            context={}
            for t in ["sales","purchases","banking","collections","sales_returns","swap_deals","inventory"]:
                df=load(t)
                if not df.empty:
                    context[t]={"rows":len(df),"columns":list(df.columns),"sample":df.head(3).to_dict("records")}
            with st.spinner("🤖 Investigating..."):
                try:
                    resp=client.chat.completions.create(model="gpt-4o",messages=[{"role":"system","content":"You are Finteca AuditRep AI forensic accountant. Be specific, cite numbers, flag risks."},{"role":"user","content":f"Question: {question}\n\nData:\n{json.dumps(context,indent=2,default=str)[:4000]}"}],max_tokens=1200)
                    answer=resp.choices[0].message.content
                    st.session_state.chat_history.append({"q":question,"a":answer})
                except Exception as e:
                    st.error(f"AI Error: {e}")
        for chat in reversed(st.session_state.chat_history[-8:]):
            with st.chat_message("user"): st.write(chat["q"])
            with st.chat_message("assistant"): st.markdown(chat["a"])
        if st.session_state.chat_history:
            if st.button("🗑️ Clear Chat"): st.session_state.chat_history=[]; st.rerun()
        st.divider()
        if st.button("📄 Generate Executive Report",type="primary",use_container_width=True):
            with st.spinner("Generating executive report..."):
                try:
                    ctx={t:{"rows":len(load(t))} for t in ["sales","purchases","banking","collections","inventory"]}
                    resp2=client.chat.completions.create(model="gpt-4o",messages=[{"role":"system","content":"You are a CFO writing an executive audit report for Finteca AuditRep."},{"role":"user","content":f"Write a comprehensive executive financial report.\nData: {json.dumps(ctx,default=str)}\nDate: {datetime.now().strftime('%B %d, %Y')}\n\nStructure:\n# FINTECA AUDITREP — EXECUTIVE INVESTIGATION REPORT\n## 1. Executive Summary\n## 2. Financial Performance\n## 3. Cash & Banking\n## 4. Inventory Status\n## 5. Fraud & Irregularities\n## 6. Key Risks\n## 7. Recommendations"}],max_tokens=2500)
                    report=resp2.choices[0].message.content
                    st.markdown(report)
                    st.download_button("📥 Download Report",report,f"finteca_report_{datetime.now().strftime('%Y%m%d')}.txt","text/plain")
                except Exception as e:
                    st.error(f"Error: {e}")

st.markdown('<div class="finteca-footer">Finteca AuditRep v1.0.0 · Powered by OpenAI GPT-4o</div>', unsafe_allow_html=True)
