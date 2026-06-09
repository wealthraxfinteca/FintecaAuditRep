"""
Finteca AuditRep v4.0 — AI Probe
Natural language search and analysis of assignment data
"""
import streamlit as st
import pandas as pd
import sqlite3
import os
import json
from datetime import datetime, date
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

try:
    from openai import OpenAI
    OPENAI_OK = True
except Exception:
    OPENAI_OK = False

st.set_page_config(
    page_title="AI Probe - Finteca AuditRep",
    page_icon="🔬", layout="wide"
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
.probe-result{background:white;border:1px solid #e0e0e0;border-radius:10px;
    padding:20px;margin:10px 0;box-shadow:0 2px 8px rgba(0,0,0,0.06);}
.flag-green{background:#e8f5e9;border-left:4px solid #2e7d32;
    padding:10px;border-radius:5px;margin:5px 0;}
.flag-red{background:#ffebee;border-left:4px solid #c62828;
    padding:10px;border-radius:5px;margin:5px 0;}
.flag-blue{background:#e3f2fd;border-left:4px solid #1565c0;
    padding:10px;border-radius:5px;margin:5px 0;}
.finteca-footer{text-align:center;color:#999;font-size:0.8em;
    padding:20px;border-top:1px solid #eee;margin-top:30px;}
</style>"""
st.markdown(CSS, unsafe_allow_html=True)
st.markdown("""
<div class="finteca-header">
    <h1>🔬 Finteca AuditRep</h1>
    <p>AI Probe — Natural Language Data Search & Analysis</p>
    <span class="finteca-badge">Module 12 — AI Probe</span>
</div>
""", unsafe_allow_html=True)

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

def get_db_summary():
    """Get a summary of all data for AI context"""
    tables = ["purchases","sales","banking","collections",
              "sales_returns","purchase_returns","swap_deals",
              "inventory","expenses"]
    summary = {}
    for table in tables:
        try:
            conn = get_conn()
            df = pd.read_sql(f"SELECT * FROM {table} LIMIT 5", conn)
            count = pd.read_sql(f"SELECT COUNT(*) as c FROM {table}", conn)["c"].iloc[0]
            conn.close()
            if int(count) > 0:
                summary[table] = {
                    "count": int(count),
                    "columns": list(df.columns),
                    "sample": df.to_dict("records")
                }
        except Exception:
            pass
    return summary

def run_sql_probe(query: str) -> dict:
    """Execute a SQL query safely"""
    try:
        query = query.strip()
        if not query.upper().startswith("SELECT"):
            return {"success": False, "error": "Only SELECT queries allowed"}
        conn = get_conn()
        df = pd.read_sql(query, conn)
        conn.close()
        return {"success": True, "data": df, "rows": len(df)}
    except Exception as e:
        return {"success": False, "error": str(e)}

def ai_probe(question: str, api_key: str) -> dict:
    """Use AI to answer questions about the data"""
    if not OPENAI_OK or not api_key:
        return {"success": False, "error": "OpenAI not available"}

    try:
        client  = OpenAI(api_key=api_key)
        db_summary = get_db_summary()
        context = json.dumps(db_summary, indent=2, default=str)[:6000]

        # Ask AI to generate SQL and analysis
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "system",
                "content": """You are Finteca AuditRep AI forensic accountant.
You have access to a SQLite database with these tables:
purchases, sales, banking, collections, sales_returns,
purchase_returns, swap_deals, inventory, expenses.

When asked a question:
1. Generate the SQL query to answer it
2. Provide analysis and insights
3. Flag any anomalies or risks

Always return valid JSON:
{
    "sql": "SELECT ... (valid SQLite query or empty string)",
    "analysis": "Your detailed analysis",
    "anomalies": ["list of any issues found"],
    "recommendations": ["actionable recommendations"],
    "risk_level": "LOW/MEDIUM/HIGH/CRITICAL"
}"""
            }, {
                "role": "user",
                "content": f"""Database contents:
{context}

Question: {question}

Generate SQL if needed and provide full analysis."""
            }],
            max_tokens=2000,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)

        # Execute SQL if provided
        sql = result.get("sql","").strip()
        data = None
        if sql and sql.upper().startswith("SELECT"):
            sql_result = run_sql_probe(sql)
            if sql_result["success"]:
                data = sql_result["data"]

        # Save to probe history
        try:
            conn = get_conn()
            conn.execute(
                "INSERT INTO probe_history (query, result) VALUES (?,?)",
                (question, json.dumps(result, default=str)[:2000])
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

        return {
            "success": True,
            "sql": sql,
            "data": data,
            "analysis": result.get("analysis",""),
            "anomalies": result.get("anomalies",[]),
            "recommendations": result.get("recommendations",[]),
            "risk_level": result.get("risk_level","LOW"),
        }

    except Exception as e:
        return {"success": False, "error": str(e)}

# Active assignment
if st.session_state.get("active_assignment_name"):
    st.markdown(
        f'<div class="flag-green">Assignment: <b>{st.session_state.active_assignment_name}</b></div>',
        unsafe_allow_html=True)

api_key = os.getenv("OPENAI_API_KEY","")

tabs = st.tabs([
    "🤖 AI Natural Language Probe",
    "🔍 Quick Searches",
    "💻 SQL Probe",
    "📜 Probe History",
])

# ════════════════════════════════════════════════════════
# TAB 1 — AI PROBE
# ════════════════════════════════════════════════════════
with tabs[0]:
    st.markdown('<div class="section-header">🤖 AI Natural Language Probe</div>',
                unsafe_allow_html=True)

    if not api_key:
        st.error("Add OPENAI_API_KEY to your .env file to use AI Probe")
    else:
        st.markdown("""
        Ask any question about your financial data in plain English.
        The AI will search the data and give you a detailed analysis.
        """)

        # Quick probe buttons
        st.markdown("**⚡ Quick Probes:**")
        quick = st.columns(4)
        quick_questions = [
            "Show me all unbanked collections",
            "Which customers have the highest outstanding balances?",
            "Find any duplicate invoice numbers in sales",
            "Which items have stock below reorder level?",
            "Show purchases not yet paid",
            "What are the top 10 sales by value?",
            "Find any sales below cost price",
            "Show me all purchase returns pending credit",
            "Which suppliers have the most outstanding payments?",
            "Find anomalies in banking transactions",
            "Show slow moving inventory items",
            "What is the total VAT collected this month?",
        ]
        for i, q in enumerate(quick_questions[:8]):
            with quick[i%4]:
                if st.button(q[:30]+"..." if len(q)>30 else q,
                             key=f"qp_{i}", use_container_width=True):
                    st.session_state["probe_question"] = q

        # Main input
        user_q = st.text_area(
            "Your question:",
            value=st.session_state.get("probe_question",""),
            placeholder="e.g. Show me all collections from last week that were not deposited in the bank",
            height=80,
            key="probe_input"
        )

        col_run, col_clear = st.columns([1,1])
        with col_run:
            run_probe = st.button("🔬 Run AI Probe", type="primary",
                                  use_container_width=True)
        with col_clear:
            if st.button("Clear", use_container_width=True):
                st.session_state["probe_question"] = ""
                st.rerun()

        if run_probe and user_q.strip():
            with st.spinner("🤖 AI analysing your data..."):
                result = ai_probe(user_q.strip(), api_key)

            if result["success"]:
                # Risk level badge
                risk = result.get("risk_level","LOW")
                risk_css = {
                    "LOW":"flag-green","MEDIUM":"flag-blue",
                    "HIGH":"flag-red","CRITICAL":"flag-red"
                }.get(risk,"flag-blue")
                st.markdown(
                    f'<div class="{risk_css}">Risk Level: <b>{risk}</b></div>',
                    unsafe_allow_html=True)

                # Analysis
                st.markdown("**📊 Analysis:**")
                st.markdown(result.get("analysis",""))

                # Data results
                if result.get("data") is not None and not result["data"].empty:
                    st.markdown(f"**📋 Query Results ({len(result['data'])} rows):**")
                    st.dataframe(result["data"], use_container_width=True, height=300)
                    st.download_button(
                        "📥 Download Results",
                        result["data"].to_csv(index=False),
                        f"probe_results_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                        "text/csv"
                    )

                # SQL used
                if result.get("sql"):
                    with st.expander("💻 SQL Query Used"):
                        st.code(result["sql"], language="sql")

                # Anomalies
                anomalies = result.get("anomalies",[])
                if anomalies:
                    st.markdown("**🚨 Anomalies Found:**")
                    for a in anomalies:
                        st.markdown(f'<div class="flag-red">🚩 {a}</div>',
                                    unsafe_allow_html=True)

                # Recommendations
                recs = result.get("recommendations",[])
                if recs:
                    st.markdown("**💡 Recommendations:**")
                    for r in recs:
                        st.markdown(f"- {r}")
            else:
                st.error(f"Probe failed: {result.get('error')}")

# ════════════════════════════════════════════════════════
# TAB 2 — QUICK SEARCHES
# ════════════════════════════════════════════════════════
with tabs[1]:
    st.markdown('<div class="section-header">🔍 Quick Searches</div>', unsafe_allow_html=True)

    search_type = st.selectbox("Search Type:", [
        "Find customer transactions",
        "Find supplier transactions",
        "Find by amount",
        "Find by date",
        "Find by invoice/reference number",
        "Find by item/product",
        "Find unmatched/missing data",
        "Fast & Slow moving items",
        "Cash collection analysis",
    ])

    if search_type == "Find customer transactions":
        cust = st.text_input("Customer name (partial):")
        if cust and st.button("Search", type="primary"):
            tables_to_search = {
                "Sales": ("sales","customer","net_amount"),
                "Collections": ("collections","customer","amount"),
                "Sales Returns": ("sales_returns","customer","return_amount"),
            }
            for label, (tbl, name_col, amt_col) in tables_to_search.items():
                df = load(tbl)
                if not df.empty and name_col in df.columns:
                    filtered = df[df[name_col].astype(str).str.contains(
                        cust, case=False, na=False)]
                    if not filtered.empty:
                        st.markdown(f"**{label}: {len(filtered)} records**")
                        st.dataframe(filtered, use_container_width=True, height=200)

    elif search_type == "Find supplier transactions":
        supp = st.text_input("Supplier name (partial):")
        if supp and st.button("Search", type="primary"):
            for label, tbl, col in [
                ("Purchases","purchases","supplier"),
                ("Purchase Returns","purchase_returns","supplier")
            ]:
                df = load(tbl)
                if not df.empty and col in df.columns:
                    filtered = df[df[col].astype(str).str.contains(
                        supp,case=False,na=False)]
                    if not filtered.empty:
                        st.markdown(f"**{label}: {len(filtered)} records**")
                        st.dataframe(filtered, use_container_width=True, height=200)

    elif search_type == "Find by amount":
        c1,c2,c3 = st.columns(3)
        with c1: min_amt = st.number_input("Minimum amount:", min_value=0.0, value=0.0)
        with c2: max_amt = st.number_input("Maximum amount:", min_value=0.0, value=1000000.0)
        with c3: search_tbl = st.selectbox("In table:",
            ["sales","purchases","collections","banking","expenses"])
        amt_col_map = {"sales":"net_amount","purchases":"total_cost",
                       "collections":"amount","banking":"credit",
                       "expenses":"total_amount"}
        if st.button("Search", type="primary"):
            df = load(search_tbl)
            acol = amt_col_map.get(search_tbl,"amount")
            if not df.empty and acol in df.columns:
                df[acol] = to_num(df[acol])
                filtered = df[(df[acol]>=min_amt)&(df[acol]<=max_amt)]
                st.markdown(f"**{len(filtered)} records between {min_amt:,.2f} and {max_amt:,.2f}:**")
                st.dataframe(filtered, use_container_width=True, height=350)

    elif search_type == "Find by invoice/reference number":
        ref_q = st.text_input("Invoice/Reference number:")
        if ref_q and st.button("Search", type="primary"):
            for label,tbl,col in [
                ("Sales","sales","invoice_number"),
                ("Purchases","purchases","reference_number"),
                ("Collections","collections","invoice_reference"),
                ("Banking","banking","reference"),
            ]:
                df = load(tbl)
                if not df.empty and col in df.columns:
                    f = df[df[col].astype(str).str.contains(ref_q,case=False,na=False)]
                    if not f.empty:
                        st.markdown(f"**{label}: {len(f)} matches**")
                        st.dataframe(f, use_container_width=True, height=200)

    elif search_type == "Find by item/product":
        item_q = st.text_input("Item name or SKU:")
        if item_q and st.button("Search", type="primary"):
            for label,tbl,col in [
                ("Sales","sales","item_description"),
                ("Purchases","purchases","item_description"),
                ("Inventory","inventory","description"),
                ("Sales Returns","sales_returns","item_description"),
                ("Purchase Returns","purchase_returns","item_description"),
            ]:
                df = load(tbl)
                if not df.empty and col in df.columns:
                    f = df[df[col].astype(str).str.contains(item_q,case=False,na=False)]
                    if not f.empty:
                        st.markdown(f"**{label}: {len(f)} records**")
                        st.dataframe(f, use_container_width=True, height=200)

    elif search_type == "Fast & Slow moving items":
        sales_sm = load("sales")
        if sales_sm.empty:
            st.warning("No sales data.")
        else:
            sales_sm["quantity"] = to_num(sales_sm.get("quantity",pd.Series(dtype=float)))
            sales_sm["net_amount"]= to_num(sales_sm.get("net_amount",pd.Series(dtype=float)))
            if "item_description" in sales_sm.columns:
                by_item = sales_sm.groupby("item_description").agg(
                    Total_Qty=("quantity","sum"),
                    Total_Revenue=("net_amount","sum"),
                    Transactions=("quantity","count"),
                    Avg_Qty=("quantity","mean"),
                ).reset_index().sort_values("Total_Qty",ascending=False)

                threshold = st.slider("Fast/Slow threshold (units):", 1, 100, 10)
                fast = by_item[by_item["Total_Qty"]>=threshold]
                slow = by_item[by_item["Total_Qty"]<threshold]

                c1,c2 = st.columns(2)
                with c1:
                    st.markdown(f"**🏃 Fast Moving ({len(fast)} items — {threshold}+ units):**")
                    st.dataframe(fast.head(20).round(2), use_container_width=True, height=300)
                    if not fast.empty:
                        st.download_button("📥 Fast Moving",fast.to_csv(index=False),
                            "fast_moving.csv","text/csv",use_container_width=True)
                with c2:
                    st.markdown(f"**🐢 Slow Moving ({len(slow)} items — <{threshold} units):**")
                    st.dataframe(slow.head(20).round(2), use_container_width=True, height=300)
                    if not slow.empty:
                        st.download_button("📥 Slow Moving",slow.to_csv(index=False),
                            "slow_moving.csv","text/csv",use_container_width=True)

    elif search_type == "Cash collection analysis":
        coll_ca = load("collections")
        bank_ca = load("banking")
        if coll_ca.empty:
            st.warning("No collections data.")
        else:
            coll_ca["amount"] = to_num(coll_ca.get("amount",pd.Series(dtype=float)))
            bank_ca["credit"] = to_num(bank_ca.get("credit",pd.Series(dtype=float))) if not bank_ca.empty else pd.Series(dtype=float)

            tot_collected = coll_ca["amount"].sum()
            tot_banked    = bank_ca["credit"].sum() if not bank_ca.empty else 0

            m = st.columns(3)
            m[0].metric("Total Collected", f"{tot_collected:,.2f}")
            m[1].metric("Total Banked",    f"{tot_banked:,.2f}")
            m[2].metric("Unbanked",        f"{tot_collected-tot_banked:,.2f}",
                        delta_color="inverse")

            # By collector
            if "received_by" in coll_ca.columns:
                by_col = coll_ca.groupby("received_by").agg(
                    Total=("amount","sum"),Count=("amount","count")
                ).reset_index().sort_values("Total",ascending=False)
                st.markdown("**By Collector:**")
                st.dataframe(by_col.round(2), use_container_width=True, height=200)

            # By payment method
            if "payment_method" in coll_ca.columns:
                by_m = coll_ca.groupby("payment_method").agg(
                    Total=("amount","sum"),Count=("amount","count")
                ).reset_index()
                fig_m = px.pie(by_m, names="payment_method", values="Total",
                               title="Collections by Payment Method")
                st.plotly_chart(fig_m, use_container_width=True)

# ════════════════════════════════════════════════════════
# TAB 3 — SQL PROBE
# ════════════════════════════════════════════════════════
with tabs[2]:
    st.markdown('<div class="section-header">💻 SQL Probe</div>', unsafe_allow_html=True)
    st.markdown("""
    Write custom SQL queries against your assignment data.
    Only SELECT queries are allowed.
    """)

    # Sample queries
    with st.expander("📋 Sample Queries"):
        samples = {
            "Unbanked collections": "SELECT date, customer, amount, payment_method, received_by FROM collections WHERE reconciled=0 OR reconciled IS NULL ORDER BY date DESC",
            "Sales without COGS": "SELECT id, date, invoice_number, customer, net_amount FROM sales WHERE cost_of_goods=0 OR cost_of_goods IS NULL",
            "Duplicate invoices": "SELECT invoice_number, COUNT(*) as count, SUM(net_amount) as total FROM sales GROUP BY invoice_number HAVING COUNT(*)>1",
            "Top customers": "SELECT customer, SUM(net_amount) as total_sales, COUNT(*) as invoices FROM sales GROUP BY customer ORDER BY total_sales DESC LIMIT 10",
            "Outstanding purchases": "SELECT supplier, reference_number, total_cost, date FROM purchases WHERE payment_status='unpaid' OR payment_status IS NULL ORDER BY date",
            "Inventory variances": "SELECT item_code, description, closing_qty, physical_count, (physical_count-closing_qty) as variance FROM inventory WHERE ABS(physical_count-closing_qty)>0",
        }
        for name, sql in samples.items():
            if st.button(f"Use: {name}", key=f"sql_{name}"):
                st.session_state["sql_query"] = sql

    sql_q = st.text_area(
        "SQL Query:",
        value=st.session_state.get("sql_query","SELECT * FROM sales LIMIT 20"),
        height=120, key="sql_input"
    )

    if st.button("▶️ Run Query", type="primary"):
        result = run_sql_probe(sql_q)
        if result["success"]:
            st.success(f"✅ {result['rows']} rows returned")
            st.dataframe(result["data"], use_container_width=True, height=400)
            st.download_button(
                "📥 Download Results",
                result["data"].to_csv(index=False),
                f"sql_probe_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                "text/csv"
            )
        else:
            st.error(f"❌ {result['error']}")

# ════════════════════════════════════════════════════════
# TAB 4 — PROBE HISTORY
# ════════════════════════════════════════════════════════
with tabs[3]:
    st.markdown('<div class="section-header">📜 Probe History</div>', unsafe_allow_html=True)
    try:
        conn = get_conn()
        history = pd.read_sql(
            "SELECT * FROM probe_history ORDER BY created_at DESC LIMIT 50",
            conn)
        conn.close()
        if not history.empty:
            st.dataframe(history[["created_at","query"]],
                         use_container_width=True, height=400)
        else:
            st.info("No probe history yet.")
    except Exception:
        st.info("No probe history available.")

st.markdown('<div class="finteca-footer">Finteca AuditRep v4.0 · AI Probe · Natural Language Search</div>',
            unsafe_allow_html=True)
