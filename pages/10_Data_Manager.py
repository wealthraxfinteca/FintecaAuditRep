import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import os
from datetime import datetime, date
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

st.set_page_config(page_title="Data Manager - Finteca AuditRep",
                   page_icon="✏️", layout="wide")

CSS = """
<style>
.finteca-header{background:linear-gradient(135deg,#1a237e 0%,#283593 50%,#42a5f5 100%);
    padding:25px 30px;border-radius:12px;color:white;margin-bottom:25px;}
.finteca-header h1{margin:0;font-size:2.2em;font-weight:800;}
.finteca-header p{margin:5px 0 0 0;opacity:0.85;}
.finteca-badge{background:rgba(255,255,255,0.2);padding:3px 10px;
    border-radius:20px;font-size:0.75em;display:inline-block;margin-top:8px;}
.section-header{background:#f5f7ff;border-left:4px solid #1a237e;
    padding:10px 15px;border-radius:0 8px 8px 0;margin:15px 0;
    font-weight:600;color:#1a237e;}
.flag-green{background:#e8f5e9;border-left:4px solid #2e7d32;
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
    <h1>✏️ Finteca AuditRep</h1>
    <p>Full CRUD Data Manager — Create · Read · Update · Delete</p>
    <span class="finteca-badge">Module 10 — Data Manager</span>
</div>
""", unsafe_allow_html=True)

def get_db():
    if st.session_state.get("active_db_path"):
        return st.session_state.active_db_path
    if os.path.exists("/mount/src"):
        return "/tmp/reconciliation.db"
    Path("data").mkdir(exist_ok=True)
    return "data/reconciliation.db"

def get_conn():
    return sqlite3.connect(get_db(), check_same_thread=False)

def get_cols(table):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    cols = [(r[1],r[2]) for r in cur.fetchall()]
    conn.close()
    return cols

def load_table(table, limit=100, offset=0, search=None, scol=None):
    try:
        conn = get_conn()
        if search and scol:
            df = pd.read_sql(
                f"SELECT * FROM {table} WHERE {scol} LIKE ? "
                f"ORDER BY id DESC LIMIT {limit} OFFSET {offset}",
                conn, params=(f"%{search}%",))
        else:
            df = pd.read_sql(
                f"SELECT * FROM {table} ORDER BY id DESC "
                f"LIMIT {limit} OFFSET {offset}", conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

def get_record(table, rid):
    try:
        conn = get_conn()
        df = pd.read_sql(f"SELECT * FROM {table} WHERE id=?",
                         conn, params=(rid,))
        conn.close()
        return df.iloc[0].to_dict() if not df.empty else None
    except Exception:
        return None

def update_record(table, rid, data):
    try:
        conn = get_conn()
        clause = ", ".join([f"{k}=?" for k in data.keys()])
        conn.execute(f"UPDATE {table} SET {clause} WHERE id=?",
                     list(data.values())+[rid])
        conn.commit(); conn.close()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

def delete_record(table, rid):
    try:
        conn = get_conn()
        conn.execute(f"DELETE FROM {table} WHERE id=?", (rid,))
        conn.commit(); conn.close()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

def insert_record(table, data):
    try:
        conn = get_conn()
        cols = ", ".join(data.keys())
        vals = ", ".join(["?" for _ in data])
        conn.execute(f"INSERT INTO {table} ({cols}) VALUES ({vals})",
                     list(data.values()))
        conn.commit(); conn.close()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

def count_table(table):
    try:
        conn = get_conn()
        c = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        conn.close()
        return c
    except Exception:
        return 0

TABLES = {
    "purchases":"Purchases","sales":"Sales",
    "banking":"Banking","collections":"Collections",
    "sales_returns":"Sales Returns","swap_deals":"Swap Deals",
    "inventory":"Inventory","expenses":"Expenses",
    "purchase_returns":"Purchase Returns","upload_log":"Upload Log",
}

if st.session_state.get("active_assignment_name"):
    st.markdown(
        f'<div class="flag-green">Managing: <b>{st.session_state.active_assignment_name}</b></div>',
        unsafe_allow_html=True)
else:
    st.markdown('<div class="flag-red">No assignment active — using default database.</div>',
                unsafe_allow_html=True)

c1, c2 = st.columns([2,1])
with c1:
    sel_table = st.selectbox("Table:", list(TABLES.keys()),
        format_func=lambda x: TABLES.get(x,x))
with c2:
    cnt = count_table(sel_table)
    st.metric(f"{TABLES.get(sel_table,'')} Records", cnt)

tabs = st.tabs(["📋 View","➕ Add","✏️ Edit","🗑️ Delete","📊 Stats","🔧 Bulk"])

# VIEW
with tabs[0]:
    st.markdown('<div class="section-header">📋 View Records</div>',
                unsafe_allow_html=True)
    f1,f2,f3,f4 = st.columns([2,2,1,1])
    with f1: srch = st.text_input("Search:", key="vsrch")
    with f2:
        col_names = [c[0] for c in get_cols(sel_table)]
        scol = st.selectbox("In column:", col_names, key="vcol")
    with f3: psz = st.selectbox("Show:", [25,50,100,200], key="vpsz")
    with f4: pg = st.number_input("Page:", min_value=1, value=1, key="vpg")

    df = load_table(sel_table, limit=psz, offset=(pg-1)*psz,
                    search=srch or None, scol=scol if srch else None)
    if df.empty:
        st.info("No records found.")
    else:
        st.caption(f"Showing {len(df)} records | Total: {cnt}")
        st.dataframe(df, use_container_width=True, height=450)
        sel_id = st.number_input("Row ID to Edit/Delete:", min_value=1, value=1, key="sel_rid")
        st.session_state["crud_id"] = sel_id
        st.session_state["crud_table"] = sel_table
        c1,c2 = st.columns(2)
        with c1:
            st.download_button("📥 Download Page", df.to_csv(index=False),
                f"{sel_table}_p{pg}.csv","text/csv",use_container_width=True)
        with c2:
            full = load_table(sel_table, limit=999999)
            st.download_button("📥 Download All", full.to_csv(index=False),
                f"{sel_table}_all.csv","text/csv",use_container_width=True)

# ADD
with tabs[1]:
    st.markdown('<div class="section-header">➕ Add New Record</div>',
                unsafe_allow_html=True)
    editable = [(n,t) for n,t in get_cols(sel_table)
                if n not in ("id","uploaded_at","created_at","last_updated")]
    if editable:
        with st.form("add_rec", clear_on_submit=True):
            new_data = {}
            pairs = [editable[i:i+2] for i in range(0,len(editable),2)]
            for pair in pairs:
                c1,c2 = st.columns(2)
                for idx,(fname,ftype) in enumerate(pair):
                    with (c1 if idx==0 else c2):
                        lbl = fname.replace("_"," ").title()
                        if "date" in fname.lower():
                            v = st.date_input(lbl, date.today())
                            new_data[fname] = str(v)
                        elif any(t in ftype.upper() for t in ["REAL","INT","NUMERIC"]):
                            v = st.number_input(lbl, min_value=0.0, value=0.0)
                            new_data[fname] = v
                        elif "status" in fname.lower():
                            v = st.selectbox(lbl, ["unpaid","paid","partial","pending"])
                            new_data[fname] = v
                        elif "method" in fname.lower():
                            v = st.selectbox(lbl, ["Cash","Bank Transfer","Cheque","Card","Other"])
                            new_data[fname] = v
                        else:
                            v = st.text_input(lbl, "")
                            new_data[fname] = v
            new_data["uploaded_at"] = datetime.now().isoformat()
            if st.form_submit_button("💾 Add", type="primary", use_container_width=True):
                r = insert_record(sel_table, new_data)
                if r["success"]:
                    st.success("Added!")
                    st.rerun()
                else:
                    st.error(r.get("error"))

# EDIT
with tabs[2]:
    st.markdown('<div class="section-header">✏️ Edit Record</div>',
                unsafe_allow_html=True)
    eid = st.number_input("Record ID:", min_value=1,
                          value=st.session_state.get("crud_id",1), key="eid")
    if st.button("Load Record", type="primary"):
        rec = get_record(sel_table, eid)
        if rec:
            st.session_state["editing"] = rec
            st.success(f"Loaded ID {eid}")
        else:
            st.error("Not found")
    if st.session_state.get("editing"):
        rec = st.session_state["editing"]
        st.markdown(f"**Editing ID: {rec.get('id')}**")
        with st.form("edit_rec"):
            upd = {}
            editable2 = [(n,t) for n,t in get_cols(sel_table)
                         if n not in ("id","uploaded_at","created_at","last_updated")]
            pairs2 = [editable2[i:i+2] for i in range(0,len(editable2),2)]
            for pair in pairs2:
                c1,c2 = st.columns(2)
                for idx,(fname,ftype) in enumerate(pair):
                    with (c1 if idx==0 else c2):
                        lbl = fname.replace("_"," ").title()
                        cur = rec.get(fname,"")
                        if "date" in fname.lower():
                            try:
                                dv = pd.to_datetime(cur).date() if cur else date.today()
                            except Exception:
                                dv = date.today()
                            v = st.date_input(lbl, value=dv)
                            upd[fname] = str(v)
                        elif any(t in ftype.upper() for t in ["REAL","INT","NUMERIC"]):
                            try: nv = float(cur or 0)
                            except Exception: nv = 0.0
                            v = st.number_input(lbl, value=nv)
                            upd[fname] = v
                        else:
                            v = st.text_input(lbl, str(cur or ""))
                            upd[fname] = v
            cs, cc = st.columns(2)
            with cs:
                if st.form_submit_button("Save", type="primary", use_container_width=True):
                    r = update_record(sel_table, rec["id"], upd)
                    if r["success"]:
                        st.success("Updated!")
                        st.session_state["editing"] = None
                        st.rerun()
                    else:
                        st.error(r.get("error"))
            with cc:
                if st.form_submit_button("Cancel", use_container_width=True):
                    st.session_state["editing"] = None
                    st.rerun()

# DELETE
with tabs[3]:
    st.markdown('<div class="section-header">🗑️ Delete Records</div>',
                unsafe_allow_html=True)
    st.warning("Deletion is permanent and cannot be undone.")
    dopt = st.radio("Option:", [
        "Single record by ID",
        "By date range",
        "By field value",
        "ALL records in table",
    ])

    if dopt == "Single record by ID":
        did = st.number_input("ID:", min_value=1, value=1, key="did")
        rp = get_record(sel_table, did)
        if rp: st.json(rp)
        else: st.warning("Not found")
        if st.button("Delete This Record"):
            st.session_state["csd"] = did
        if st.session_state.get("csd") == did:
            cc1,cc2 = st.columns(2)
            with cc1:
                if st.button("YES DELETE", type="primary"):
                    r = delete_record(sel_table, did)
                    if r["success"]:
                        st.success("Deleted!")
                        st.session_state["csd"] = None
                        st.rerun()
            with cc2:
                if st.button("Cancel"):
                    st.session_state["csd"] = None

    elif dopt == "By date range":
        dc1,dc2 = st.columns(2)
        with dc1: df_ = st.date_input("From:", date.today().replace(day=1))
        with dc2: dt_ = st.date_input("To:", date.today())
        if st.button("Delete Date Range"):
            st.session_state["cdr"] = True
        if st.session_state.get("cdr"):
            cc1,cc2 = st.columns(2)
            with cc1:
                if st.button("CONFIRM DELETE", type="primary"):
                    try:
                        conn = get_conn()
                        cur = conn.execute(
                            f"DELETE FROM {sel_table} WHERE date>=? AND date<=?",
                            (str(df_),str(dt_)))
                        conn.commit(); conn.close()
                        st.success(f"Deleted {cur.rowcount} records!")
                        st.session_state["cdr"] = False
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
            with cc2:
                if st.button("Cancel", key="cdrcancel"):
                    st.session_state["cdr"] = False

    elif dopt == "By field value":
        fcols = [c[0] for c in get_cols(sel_table)]
        ff = st.selectbox("Field:", fcols, key="dfield")
        fv = st.text_input("Value:", key="dvalue")
        if fv:
            try:
                conn = get_conn()
                prv = pd.read_sql(f"SELECT * FROM {sel_table} WHERE {ff}=? LIMIT 5",
                                  conn, params=(fv,))
                conn.close()
                st.dataframe(prv, use_container_width=True)
                if st.button("Delete Matching"):
                    st.session_state["cfv"] = True
                if st.session_state.get("cfv"):
                    cc1,cc2 = st.columns(2)
                    with cc1:
                        if st.button("CONFIRM", type="primary"):
                            conn = get_conn()
                            c = conn.execute(
                                f"DELETE FROM {sel_table} WHERE {ff}=?",(fv,))
                            conn.commit(); conn.close()
                            st.success(f"Deleted {c.rowcount} records!")
                            st.session_state["cfv"] = False
                            st.rerun()
                    with cc2:
                        if st.button("Cancel", key="cfvc"):
                            st.session_state["cfv"] = False
            except Exception as e:
                st.error(str(e))

    else:
        st.error(f"This deletes ALL {cnt} records from {sel_table}!")
        ct = st.text_input(f"Type '{sel_table}' to confirm:")
        if ct == sel_table:
            if st.button(f"DELETE ALL {cnt} RECORDS"):
                conn = get_conn()
                conn.execute(f"DELETE FROM {sel_table}")
                conn.commit(); conn.close()
                st.success("All records deleted!")
                st.rerun()

# STATS
with tabs[4]:
    st.markdown('<div class="section-header">📊 Database Statistics</div>',
                unsafe_allow_html=True)
    all_counts = {t: count_table(t) for t in TABLES}
    cdf = pd.DataFrame([{"Table":TABLES.get(t,t),"Records":c}
                        for t,c in all_counts.items()]).sort_values("Records",ascending=False)
    c1,c2 = st.columns(2)
    with c1: st.dataframe(cdf, use_container_width=True)
    with c2:
        fig = px.bar(cdf, x="Table", y="Records", title="Records by Table",
                     color_discrete_sequence=["#1a237e"])
        fig.update_layout(xaxis_tickangle=-30)
        st.plotly_chart(fig, use_container_width=True)
    st.markdown(f"**{TABLES.get(sel_table,'')} — Columns:**")
    cinfo = pd.DataFrame(get_cols(sel_table), columns=["Column","Type"])
    st.dataframe(cinfo, use_container_width=True)

# BULK
with tabs[5]:
    st.markdown('<div class="section-header">🔧 Bulk Operations</div>',
                unsafe_allow_html=True)
    bop = st.selectbox("Operation:", [
        "Bulk Update Field Value",
        "Import CSV to Table",
        "Export and Clear Table",
    ])

    if bop == "Bulk Update Field Value":
        bcols = [c[0] for c in get_cols(sel_table)]
        bc1,bc2,bc3 = st.columns(3)
        with bc1: btf = st.selectbox("Update field:", bcols, key="btf")
        with bc2: bnv = st.text_input("New value:", key="bnv")
        with bc3: bwf = st.selectbox("Where field:", bcols, key="bwf")
        bwv = st.text_input("Where value:", key="bwv")
        if bnv and bwv:
            if st.button("Apply Bulk Update", type="primary"):
                try:
                    conn = get_conn()
                    c = conn.execute(
                        f"UPDATE {sel_table} SET {btf}=? WHERE {bwf}=?",
                        (bnv,bwv))
                    conn.commit(); conn.close()
                    st.success(f"Updated {c.rowcount} records!")
                except Exception as e:
                    st.error(str(e))

    elif bop == "Import CSV to Table":
        csv_file = st.file_uploader("Upload CSV:", type=["csv"])
        if csv_file:
            try:
                idf = pd.read_csv(csv_file)
                st.dataframe(idf.head(), use_container_width=True)
                st.info(f"{len(idf)} rows, {len(idf.columns)} columns")
                if st.button("Import", type="primary"):
                    idf["uploaded_at"] = datetime.now().isoformat()
                    idf["document_source"] = csv_file.name
                    valid = [c[0] for c in get_cols(sel_table)]
                    sc = [c for c in idf.columns if c in valid]
                    conn = get_conn()
                    idf[sc].to_sql(sel_table, conn,
                                   if_exists="append", index=False)
                    conn.close()
                    st.success(f"Imported {len(idf)} rows!")
                    st.rerun()
            except Exception as e:
                st.error(str(e))

    else:
        full2 = load_table(sel_table, limit=999999)
        if not full2.empty:
            st.info(f"{len(full2)} records")
            st.download_button("📥 Download Before Clearing",
                full2.to_csv(index=False),
                f"{sel_table}_backup_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                "text/csv", use_container_width=True)
            ct2 = st.text_input(f"Type CLEAR {sel_table}:")
            if ct2 == f"CLEAR {sel_table}":
                if st.button("Clear Table"):
                    conn = get_conn()
                    conn.execute(f"DELETE FROM {sel_table}")
                    conn.commit(); conn.close()
                    st.success("Cleared!")
                    st.rerun()

st.markdown('<div class="finteca-footer">Finteca AuditRep v3.0.0 · CRUD Manager</div>',
            unsafe_allow_html=True)
