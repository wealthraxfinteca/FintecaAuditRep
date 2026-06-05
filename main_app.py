import streamlit as st
import sqlite3
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

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
    <span class="finteca-badge">v1.0.0 · Linux Mint Edition</span>
</div>
""", unsafe_allow_html=True)

api_key = os.getenv("OPENAI_API_KEY", "")
if api_key and api_key.startswith("sk-"):
    st.sidebar.success("✅ AI Connected")
else:
    st.sidebar.error("❌ Check API key in .env")

DB_PATH = "data/reconciliation.db"
TABLES  = ["purchases","sales","banking","collections",
           "sales_returns","swap_deals","inventory"]
ICONS   = ["🛒","💰","🏦","💵","↩️","🔄","📦"]

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

counts = get_counts()
total  = sum(counts.values())

st.markdown("## 📊 Database Overview")
st.metric("Total Records Loaded", total)

cols = st.columns(7)
for col, icon, table in zip(cols, ICONS, TABLES):
    with col:
        st.metric(
            f"{icon} {table.replace('_',' ').title()}",
            counts.get(table, 0)
        )

st.divider()
st.markdown("### 🚀 Quick Start")
c1, c2, c3 = st.columns(3)
with c1:
    st.info(
        "**Step 1 — Upload**\n\n"
        "Go to Upload Documents in the sidebar.\n"
        "Upload Excel, PDF, Word or image files."
    )
with c2:
    st.info(
        "**Step 2 — Reconcile**\n\n"
        "Go to Reconciliation.\n"
        "Match collections to bank deposits.\n"
        "Verify purchases and inventory."
    )
with c3:
    st.info(
        "**Step 3 — Report**\n\n"
        "Go to Reports.\n"
        "View fraud alerts, cash position,\n"
        "profitability and export reports."
    )

st.markdown("""
<div style="text-align:center;color:#999;margin-top:30px;font-size:0.8em">
Finteca AuditRep v1.0.0 · Powered by OpenAI GPT-4o · Linux Mint 22.3
</div>
""", unsafe_allow_html=True)
