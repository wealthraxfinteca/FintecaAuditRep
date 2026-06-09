import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime, date
from pathlib import Path
from dotenv import load_dotenv
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv()

try:
    from assignment_manager import (
        create_assignment, get_assignment, update_assignment,
        delete_assignment, archive_assignment, list_assignments,
        get_assignment_db, list_uploaded_files,
        delete_uploaded_file_data, get_assignment_stats,
        init_assignment_db
    )
    AM_OK = True
except Exception as e:
    AM_OK = False
    AM_ERROR = str(e)

st.set_page_config(page_title="Assignments - Finteca AuditRep",
                   page_icon="🗂️", layout="wide")

CSS = """
<style>
.finteca-header {
    background:linear-gradient(135deg,#1a237e 0%,#283593 50%,#42a5f5 100%);
    padding:25px 30px; border-radius:12px; color:white;
    margin-bottom:25px; box-shadow:0 4px 15px rgba(26,35,126,0.3);
}
.finteca-header h1{margin:0;font-size:2.2em;font-weight:800;}
.finteca-header p{margin:5px 0 0 0;opacity:0.85;}
.finteca-badge{background:rgba(255,255,255,0.2);padding:3px 10px;
    border-radius:20px;font-size:0.75em;display:inline-block;margin-top:8px;}
.section-header{background:#f5f7ff;border-left:4px solid #1a237e;
    padding:10px 15px;border-radius:0 8px 8px 0;margin:15px 0;
    font-weight:600;color:#1a237e;}
.stat-pill{display:inline-block;background:#f5f7ff;color:#1a237e;
    padding:2px 8px;border-radius:12px;font-size:0.75em;margin:2px;}
.flag-green{background:#e8f5e9;border-left:4px solid #2e7d32;
    padding:10px;border-radius:5px;margin:5px 0;}
.flag-orange{background:#fff3e0;border-left:4px solid #e65100;
    padding:10px;border-radius:5px;margin:5px 0;}
.flag-red{background:#ffebee;border-left:4px solid #c62828;
    padding:10px;border-radius:5px;margin:5px 0;}
.finteca-footer{text-align:center;color:#999;font-size:0.8em;
    padding:20px;border-top:1px solid #eee;margin-top:30px;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)
st.markdown("""
<div class="finteca-header">
    <h1>🗂️ Finteca AuditRep</h1>
    <p>Assignment Manager — Each Client Gets Their Own Workspace</p>
    <span class="finteca-badge">v3.0 — Multi-Assignment</span>
</div>
""", unsafe_allow_html=True)

if not AM_OK:
    st.error(f"Assignment Manager error: {AM_ERROR}")
    st.stop()

# Session state
if "active_assignment" not in st.session_state:
    st.session_state.active_assignment = None
if "active_assignment_name" not in st.session_state:
    st.session_state.active_assignment_name = None
if "active_db_path" not in st.session_state:
    st.session_state.active_db_path = None

# Active banner
if st.session_state.active_assignment:
    a = get_assignment(st.session_state.active_assignment)
    st.markdown(f"""
    <div class="flag-green">
    Active Assignment: <b>{a.get("name","")}</b> |
    Client: {a.get("client","")} |
    Type: {a.get("type","")} |
    Period: {a.get("period_from","")} to {a.get("period_to","")}
    </div>""", unsafe_allow_html=True)
else:
    st.markdown("""
    <div class="flag-orange">
    No active assignment. Create or select one below.
    </div>""", unsafe_allow_html=True)

tabs = st.tabs([
    "📋 All Assignments",
    "➕ New Assignment",
    "📁 Manage Files",
    "✏️ Edit Assignment",
    "🗑️ Delete / Archive",
])

# TAB 1 — ALL ASSIGNMENTS
with tabs[0]:
    st.markdown('<div class="section-header">📋 All Assignments</div>',
                unsafe_allow_html=True)
    col_f, col_s = st.columns([1,2])
    with col_f:
        sf = st.selectbox("Status:", ["All","active","archived"])
    with col_s:
        sq = st.text_input("Search:", placeholder="Name, client, type...")

    assignments = list_assignments(None if sf=="All" else sf)
    if sq:
        assignments = [a for a in assignments if sq.lower() in
            (a.get("name","")+a.get("client","")+a.get("type","")).lower()]

    if not assignments:
        st.info("No assignments found. Create one using the New Assignment tab.")
    else:
        st.markdown(f"**{len(assignments)} assignment(s)**")
        for a in assignments:
            aid = a.get("id","")
            is_active = aid == st.session_state.active_assignment
            stats = get_assignment_stats(aid)
            total_rec = sum(stats.values())

            with st.expander(
                f"{'✅' if is_active else '🔘'} {a.get('name','')} | "
                f"{a.get('client','')} | {a.get('type','')} | "
                f"{total_rec} records | {a.get('status','').upper()}",
                expanded=is_active
            ):
                c1, c2, c3 = st.columns([3,2,1])
                with c1:
                    st.markdown(f"""
                    **Name:** {a.get("name","")}
                    **Client:** {a.get("client","")}
                    **Type:** {a.get("type","")}
                    **Period:** {a.get("period_from","")} to {a.get("period_to","")}
                    **Description:** {a.get("description","")}
                    **Created:** {str(a.get("created_at",""))[:10]} by {a.get("created_by","")}
                    """)
                    st.markdown(
                        f'<span class="stat-pill">Purchases: {stats.get("purchases",0)}</span>'
                        f'<span class="stat-pill">Sales: {stats.get("sales",0)}</span>'
                        f'<span class="stat-pill">Banking: {stats.get("banking",0)}</span>'
                        f'<span class="stat-pill">Collections: {stats.get("collections",0)}</span>'
                        f'<span class="stat-pill">Inventory: {stats.get("inventory",0)}</span>',
                        unsafe_allow_html=True
                    )
                with c2:
                    if not is_active:
                        if st.button("▶️ Activate", key=f"act_{aid}",
                                     type="primary", use_container_width=True):
                            st.session_state.active_assignment = aid
                            st.session_state.active_assignment_name = a.get("name")
                            db = get_assignment_db(aid)
                            init_assignment_db(db)
                            st.session_state.active_db_path = db
                            st.success(f"Activated: {a.get('name')}")
                            st.rerun()
                    else:
                        st.success("Currently Active")
                        if st.button("Deactivate", key=f"deact_{aid}",
                                     use_container_width=True):
                            st.session_state.active_assignment = None
                            st.session_state.active_assignment_name = None
                            st.session_state.active_db_path = None
                            st.rerun()
                with c3:
                    if st.button("📦 Archive", key=f"arch_{aid}",
                                 use_container_width=True):
                        archive_assignment(aid)
                        st.rerun()

# TAB 2 — NEW ASSIGNMENT
with tabs[1]:
    st.markdown('<div class="section-header">➕ Create New Assignment</div>',
                unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        with st.form("new_assign", clear_on_submit=True):
            an = st.text_input("Assignment Name *", placeholder="ABC Ltd Audit Q1 2025")
            ac = st.text_input("Client Name *", placeholder="ABC Limited")
            at = st.selectbox("Type *", [
                "Forensic Audit","Reconciliation","Monthly Bookkeeping",
                "Annual Audit","Fraud Investigation","Tax Compliance",
                "Management Accounts","Due Diligence","Internal Audit",
                "Stock Count","Bank Reconciliation","Other"
            ])
            ad = st.text_area("Description", height=80)
            af = st.date_input("Period From", date.today().replace(day=1))
            ato = st.date_input("Period To", date.today())
            ab = st.text_input("Created By")
            activate_now = st.checkbox("Activate immediately", value=True)
            if st.form_submit_button("🚀 Create", type="primary",
                                     use_container_width=True):
                if an and ac:
                    r = create_assignment(an, ac, ad, at,
                                          str(af), str(ato), ab or "Unknown")
                    if r["success"]:
                        st.success(f"Created: {an}")
                        if activate_now:
                            st.session_state.active_assignment = r["id"]
                            st.session_state.active_assignment_name = an
                            db = get_assignment_db(r["id"])
                            st.session_state.active_db_path = db
                        st.rerun()
                    else:
                        st.error(r.get("error"))
                else:
                    st.error("Name and Client required")
    with c2:
        st.markdown("""
        **What is an Assignment?**

        A completely isolated workspace for one client or job.
        Each assignment has its own:
        - Database (no data mixing between clients)
        - Uploaded files
        - Reports and reconciliation
        - Inventory records

        **Examples:**
        - ABC Ltd Monthly Accounts May 2025
        - Fraud Investigation Branch A
        - XYZ Company Annual Audit 2024
        - Stock Count Warehouse June 2025
        """)
        all_a = list_assignments()
        s1,s2,s3 = st.columns(3)
        s1.metric("Total", len(all_a))
        s2.metric("Active", len([x for x in all_a if x.get("status")=="active"]))
        s3.metric("Archived", len([x for x in all_a if x.get("status")=="archived"]))

# TAB 3 — MANAGE FILES
with tabs[2]:
    st.markdown('<div class="section-header">📁 Manage Uploaded Files</div>',
                unsafe_allow_html=True)
    if not st.session_state.active_assignment:
        st.warning("Activate an assignment first.")
    else:
        aid = st.session_state.active_assignment
        a = get_assignment(aid)
        st.markdown(f"**{a.get('name','')}** | Client: {a.get('client','')}")
        files = list_uploaded_files(aid)
        if not files:
            st.info("No files uploaded yet.")
        else:
            st.markdown(f"**{len(files)} file(s) uploaded**")
            for f in files:
                fname = f.get("filename","")
                ftype = f.get("document_type","")
                frows = f.get("rows_saved",0)
                fdate = str(f.get("uploaded_at",""))[:16]
                with st.expander(
                    f"📄 {fname} | {ftype} | {frows} rows | {fdate}"
                ):
                    c1, c2 = st.columns([3,1])
                    with c1:
                        db_path = get_assignment_db(aid)
                        conn = sqlite3.connect(db_path)
                        for tbl in ["purchases","sales","banking","collections",
                                    "sales_returns","swap_deals","inventory",
                                    "expenses","purchase_returns"]:
                            try:
                                cur = conn.execute(
                                    f"SELECT COUNT(*) FROM {tbl} WHERE document_source=?",
                                    (fname,))
                                cnt = cur.fetchone()[0]
                                if cnt > 0:
                                    st.text(f"  {tbl}: {cnt} rows")
                            except Exception:
                                pass
                        conn.close()
                    with c2:
                        if st.button(f"Delete Data", key=f"delf_{fname}"):
                            st.session_state[f"cdelf_{fname}"] = True
                        if st.session_state.get(f"cdelf_{fname}"):
                            st.error("Delete all data from this file?")
                            if st.button("YES DELETE", key=f"ydf_{fname}"):
                                r = delete_uploaded_file_data(aid, fname)
                                st.success(f"Deleted {r.get('rows_deleted',0)} rows")
                                st.session_state[f"cdelf_{fname}"] = False
                                st.rerun()
                            if st.button("Cancel", key=f"cdf_{fname}"):
                                st.session_state[f"cdelf_{fname}"] = False

# TAB 4 — EDIT
with tabs[3]:
    st.markdown('<div class="section-header">✏️ Edit Assignment</div>',
                unsafe_allow_html=True)
    all_a2 = list_assignments()
    if not all_a2:
        st.info("No assignments to edit.")
    else:
        sel = st.selectbox("Select:", [a.get("id") for a in all_a2],
            format_func=lambda x: next(
                (a.get("name","") for a in all_a2 if a.get("id")==x), x))
        if sel:
            ad2 = get_assignment(sel)
            if ad2:
                with st.form("edit_a"):
                    en = st.text_input("Name", ad2.get("name",""))
                    ec = st.text_input("Client", ad2.get("client",""))
                    ed = st.text_area("Description", ad2.get("description",""))
                    ef = st.text_input("Period From", ad2.get("period_from",""))
                    et = st.text_input("Period To", ad2.get("period_to",""))
                    es = st.selectbox("Status", ["active","archived"],
                        index=0 if ad2.get("status")=="active" else 1)
                    if st.form_submit_button("Save", type="primary"):
                        r = update_assignment(sel, {
                            "name":en,"client":ec,"description":ed,
                            "period_from":ef,"period_to":et,"status":es
                        })
                        if r["success"]:
                            st.success("Updated!")
                            st.rerun()

# TAB 5 — DELETE/ARCHIVE
with tabs[4]:
    st.markdown('<div class="section-header">🗑️ Delete or Archive</div>',
                unsafe_allow_html=True)
    all_a3 = list_assignments()
    st.markdown("""
    **Archive** keeps data but marks as inactive.
    **Delete** permanently removes ALL data.
    """)
    for a in all_a3:
        aid3 = a.get("id","")
        stats3 = get_assignment_stats(aid3)
        total3 = sum(stats3.values())
        with st.expander(
            f"{'Active' if a.get('status')=='active' else 'Archived'}: "
            f"{a.get('name','')} | {total3} records"
        ):
            c1,c2,c3 = st.columns(3)
            with c1:
                st.markdown(f"""
                **Name:** {a.get("name","")}
                **Client:** {a.get("client","")}
                **Records:** {total3}
                """)
            with c2:
                if st.button("Archive", key=f"a3_{aid3}",
                             use_container_width=True):
                    archive_assignment(aid3)
                    if st.session_state.active_assignment == aid3:
                        st.session_state.active_assignment = None
                    st.rerun()
            with c3:
                if st.button("DELETE ALL", key=f"d3_{aid3}",
                             use_container_width=True):
                    st.session_state[f"cd3_{aid3}"] = True
                if st.session_state.get(f"cd3_{aid3}"):
                    st.error(f"Permanently delete {a.get('name','')} and all {total3} records?")
                    cc1,cc2 = st.columns(2)
                    with cc1:
                        if st.button("YES DELETE", key=f"yd3_{aid3}",
                                     type="primary"):
                            if st.session_state.active_assignment == aid3:
                                st.session_state.active_assignment = None
                                st.session_state.active_db_path = None
                            delete_assignment(aid3)
                            st.success("Deleted!")
                            st.session_state[f"cd3_{aid3}"] = False
                            st.rerun()
                    with cc2:
                        if st.button("Cancel", key=f"ca3_{aid3}"):
                            st.session_state[f"cd3_{aid3}"] = False

st.markdown('<div class="finteca-footer">Finteca AuditRep v3.0.0</div>',
            unsafe_allow_html=True)
