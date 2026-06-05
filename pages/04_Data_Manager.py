import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
from crud_engine import (
    read_table, read_record, update_record, delete_record,
    delete_multiple, insert_record, move_record, move_multiple,
    duplicate_record, get_table_cols, get_table_summary,
    TABLES, TABLE_DISPLAY, DB_PATH
)

load_dotenv()

st.set_page_config(
    page_title="Data Manager - Finteca AuditRep",
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
.stat-card {
    background:white; padding:15px; border-radius:8px;
    border:1px solid #e0e0e0; text-align:center; margin:5px;
}
.alert-ok {
    background:#e8f5e9; border-left:5px solid #2e7d32;
    padding:10px 15px; border-radius:6px; margin:6px 0;
}
.alert-warn {
    background:#fff8e1; border-left:5px solid #f9a825;
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
    <p>Data Manager — CRUD & Transaction Mapping</p>
    <span class="finteca-badge">Module 4 — Data Manager</span>
</div>
""", unsafe_allow_html=True)

# ── Sidebar — Table selector ──────────────────────────────
st.sidebar.markdown("## 📋 Select Table")
selected_table = st.sidebar.selectbox(
    "Table",
    TABLES,
    format_func=lambda x: TABLE_DISPLAY.get(x, x)
)

st.sidebar.markdown("---")
st.sidebar.markdown("## 🔍 Filter")
search_term = st.sidebar.text_input(
    "Search", placeholder="Search any field..."
)
date_filter_on = st.sidebar.checkbox("Filter by Date")
date_from = date_to = None
if date_filter_on:
    date_from = st.sidebar.date_input(
        "From", value=date.today() - timedelta(days=30)
    )
    date_to   = st.sidebar.date_input("To", value=date.today())

# ── Table Summary ─────────────────────────────────────────
summary = get_table_summary(selected_table)
s1, s2, s3, s4 = st.columns(4)
s1.metric(
    f"{TABLE_DISPLAY.get(selected_table,'Table')}",
    f"{summary.get('count', 0)} records"
)
s2.metric(
    "Total Amount",
    f"{summary.get('total_amount', 0):,.2f}"
    if "total_amount" in summary else "—"
)
s3.metric("Date From", summary.get("date_from", "—"))
s4.metric("Date To",   summary.get("date_to",   "—"))

# ── Main Tabs ─────────────────────────────────────────────
tabs = st.tabs([
    "📋 View & Edit",
    "➕ Add New Record",
    "🔄 Move / Remap",
    "🗑️ Bulk Actions",
])

# ══════════════════════════════════════════════════════════
# TAB 1 — VIEW & EDIT
# ══════════════════════════════════════════════════════════
with tabs[0]:
    st.markdown(
        '<div class="section-header">📋 View & Edit Records</div>',
        unsafe_allow_html=True,
    )

    df = read_table(
        selected_table,
        date_from=date_from,
        date_to=date_to,
        search=search_term,
        limit=1000,
    )

    if df.empty:
        st.info("No records found. Upload documents or add records manually.")
    else:
        st.markdown(
            f"**{len(df)} records found**  "
            f"{'(filtered)' if search_term or date_filter_on else ''}"
        )

        # Editable dataframe
        edited_df = st.data_editor(
            df,
            use_container_width=True,
            height=420,
            num_rows="fixed",
            disabled=["id", "uploaded_at"],
            key=f"editor_{selected_table}",
        )

        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            if st.button(
                "💾 Save All Changes",
                type="primary",
                use_container_width=True,
                key="save_all"
            ):
                # Find changed rows
                changes = 0
                errors  = []
                for i, (orig_row, edit_row) in enumerate(
                    zip(df.itertuples(), edited_df.itertuples())
                ):
                    orig_dict = df.iloc[i].to_dict()
                    edit_dict = edited_df.iloc[i].to_dict()

                    changed_fields = {
                        k: v for k, v in edit_dict.items()
                        if str(v) != str(orig_dict.get(k, ""))
                        and k != "id"
                    }

                    if changed_fields:
                        res = update_record(
                            selected_table,
                            int(orig_dict["id"]),
                            changed_fields
                        )
                        if res["success"]:
                            changes += 1
                        else:
                            errors.append(res["error"])

                if changes > 0:
                    st.success(f"✅ {changes} records updated!")
                    st.rerun()
                elif errors:
                    for e in errors:
                        st.error(f"❌ {e}")
                else:
                    st.info("No changes detected.")

        with col2:
            st.download_button(
                "📥 Export CSV",
                df.to_csv(index=False),
                f"{selected_table}_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv",
                use_container_width=True,
            )

        with col3:
            if st.button(
                "🔄 Refresh",
                use_container_width=True
            ):
                st.rerun()

        # ── Individual Record Edit ────────────────────────
        st.markdown("---")
        st.markdown(
            '<div class="section-header">✏️ Edit Individual Record</div>',
            unsafe_allow_html=True,
        )

        if not df.empty and "id" in df.columns:
            record_ids = df["id"].tolist()
            sel_id     = st.selectbox(
                "Select Record ID to Edit",
                record_ids,
                key="edit_record_id"
            )

            record = read_record(selected_table, sel_id)
            if record:
                valid_cols = [
                    c for c in get_table_cols(selected_table)
                    if c not in ["id", "uploaded_at", "last_updated"]
                ]

                with st.form(f"edit_form_{selected_table}_{sel_id}"):
                    updated = {}
                    n_cols  = 3
                    rows    = [
                        valid_cols[i:i+n_cols]
                        for i in range(0, len(valid_cols), n_cols)
                    ]
                    for row_cols in rows:
                        form_cols = st.columns(len(row_cols))
                        for fc, col_name in zip(form_cols, row_cols):
                            with fc:
                                current_val = record.get(col_name, "")
                                new_val = st.text_input(
                                    col_name.replace("_", " ").title(),
                                    value=str(current_val)
                                    if current_val is not None
                                    else "",
                                    key=f"field_{col_name}_{sel_id}"
                                )
                                updated[col_name] = new_val

                    fc1, fc2, fc3 = st.columns(3)
                    with fc1:
                        if st.form_submit_button(
                            "💾 Update Record",
                            type="primary",
                            use_container_width=True
                        ):
                            res = update_record(
                                selected_table, sel_id, updated
                            )
                            if res["success"]:
                                st.success("✅ Record updated!")
                                st.rerun()
                            else:
                                st.error(f"❌ {res['error']}")

                    with fc2:
                        if st.form_submit_button(
                            "📋 Duplicate",
                            use_container_width=True
                        ):
                            res = duplicate_record(
                                selected_table, sel_id
                            )
                            if res["success"]:
                                st.success("✅ Record duplicated!")
                                st.rerun()
                            else:
                                st.error(f"❌ {res['error']}")

                    with fc3:
                        if st.form_submit_button(
                            "🗑️ Delete Record",
                            use_container_width=True
                        ):
                            res = delete_record(selected_table, sel_id)
                            if res["success"]:
                                st.success("✅ Record deleted!")
                                st.rerun()
                            else:
                                st.error(f"❌ {res['error']}")

# ══════════════════════════════════════════════════════════
# TAB 2 — ADD NEW RECORD
# ══════════════════════════════════════════════════════════
with tabs[1]:
    st.markdown(
        '<div class="section-header">➕ Add New Record</div>',
        unsafe_allow_html=True,
    )

    valid_cols = [
        c for c in get_table_cols(selected_table)
        if c not in ["id", "uploaded_at", "last_updated"]
    ]

    with st.form(f"add_form_{selected_table}"):
        new_record = {}
        n_cols     = 3
        rows       = [
            valid_cols[i:i+n_cols]
            for i in range(0, len(valid_cols), n_cols)
        ]

        for row_cols in rows:
            form_cols = st.columns(len(row_cols))
            for fc, col_name in zip(form_cols, row_cols):
                with fc:
                    # Smart input types
                    if "date" in col_name:
                        val = st.date_input(
                            col_name.replace("_"," ").title(),
                            key=f"new_{col_name}"
                        )
                        new_record[col_name] = str(val)
                    elif any(x in col_name for x in
                             ["amount","cost","price","qty",
                              "quantity","debit","credit","balance"]):
                        val = st.number_input(
                            col_name.replace("_"," ").title(),
                            min_value=0.0, value=0.0,
                            key=f"new_{col_name}"
                        )
                        new_record[col_name] = val
                    elif "method" in col_name:
                        val = st.selectbox(
                            col_name.replace("_"," ").title(),
                            ["Cash","Bank Transfer","Cheque",
                             "Card","Credit","Other"],
                            key=f"new_{col_name}"
                        )
                        new_record[col_name] = val
                    elif "status" in col_name:
                        val = st.selectbox(
                            col_name.replace("_"," ").title(),
                            ["unpaid","paid","pending","completed"],
                            key=f"new_{col_name}"
                        )
                        new_record[col_name] = val
                    else:
                        val = st.text_input(
                            col_name.replace("_"," ").title(),
                            key=f"new_{col_name}"
                        )
                        new_record[col_name] = val

        new_record["document_source"] = "manual_entry"

        if st.form_submit_button(
            f"➕ Add to {TABLE_DISPLAY.get(selected_table, selected_table)}",
            type="primary",
            use_container_width=True
        ):
            res = insert_record(selected_table, new_record)
            if res["success"]:
                st.success("✅ Record added successfully!")
                st.rerun()
            else:
                st.error(f"❌ {res['error']}")

# ══════════════════════════════════════════════════════════
# TAB 3 — MOVE / REMAP
# ══════════════════════════════════════════════════════════
with tabs[2]:
    st.markdown(
        '<div class="section-header">🔄 Move & Remap Transactions</div>',
        unsafe_allow_html=True,
    )

    st.info(
        "Use this to move transactions that were saved to the wrong table. "
        "For example, move a banking transaction that was saved to sales."
    )

    # Load source data
    df_move = read_table(
        selected_table,
        date_from=date_from,
        date_to=date_to,
        search=search_term,
        limit=500
    )

    if df_move.empty:
        st.warning("No records in this table to move.")
    else:
        # Target table selector
        other_tables = [t for t in TABLES if t != selected_table]
        target_table = st.selectbox(
            "Move selected records TO:",
            other_tables,
            format_func=lambda x: TABLE_DISPLAY.get(x, x),
            key="move_target"
        )

        st.markdown(f"""
        **Moving FROM:** {TABLE_DISPLAY.get(selected_table, selected_table)}
        → **Moving TO:** {TABLE_DISPLAY.get(target_table, target_table)}
        """)

        # Show records with selection
        st.markdown("**Select records to move:**")

        # Add selection column
        df_display = df_move.copy()

        # Multi-select by ID
        all_ids   = df_display["id"].tolist() if "id" in df_display.columns else []
        sel_ids   = st.multiselect(
            "Select Record IDs to move:",
            all_ids,
            key="move_ids"
        )

        # Show preview of selected records
        if sel_ids:
            preview = df_display[df_display["id"].isin(sel_ids)]
            st.markdown(f"**Preview — {len(preview)} records selected:**")
            st.dataframe(preview, use_container_width=True, height=200)

            col_mv1, col_mv2 = st.columns(2)
            with col_mv1:
                if st.button(
                    f"🔄 Move {len(sel_ids)} Records to "
                    f"{TABLE_DISPLAY.get(target_table,target_table)}",
                    type="primary",
                    use_container_width=True,
                    key="do_move"
                ):
                    result = move_multiple(
                        selected_table, sel_ids, target_table
                    )
                    if result["success"]:
                        st.success(
                            f"✅ Moved {result['moved']} records to "
                            f"{target_table}!"
                        )
                        if result["failed"] > 0:
                            st.warning(
                                f"⚠️ {result['failed']} records failed to move."
                            )
                        st.rerun()
                    else:
                        st.error(f"❌ Move failed: {result.get('error')}")

            with col_mv2:
                if st.button(
                    "🔍 Preview Column Compatibility",
                    use_container_width=True,
                    key="preview_compat"
                ):
                    src_cols = set(get_table_cols(selected_table))
                    tgt_cols = set(get_table_cols(target_table))
                    matching = src_cols & tgt_cols
                    missing  = src_cols - tgt_cols

                    st.markdown(
                        f"**✅ Matching columns ({len(matching)}):** "
                        f"{sorted(matching)}"
                    )
                    if missing:
                        st.markdown(
                            f"**⚠️ Columns that will be lost ({len(missing)}):** "
                            f"{sorted(missing)}"
                        )

        # Show all records
        st.markdown("**All Records in Table:**")
        st.dataframe(df_display, use_container_width=True, height=300)

# ══════════════════════════════════════════════════════════
# TAB 4 — BULK ACTIONS
# ══════════════════════════════════════════════════════════
with tabs[3]:
    st.markdown(
        '<div class="section-header">🗑️ Bulk Actions</div>',
        unsafe_allow_html=True,
    )

    df_bulk = read_table(
        selected_table,
        date_from=date_from,
        date_to=date_to,
        search=search_term,
        limit=1000
    )

    if df_bulk.empty:
        st.info("No records found.")
    else:
        st.markdown(f"**{len(df_bulk)} records in current view**")

        # Bulk delete options
        st.markdown("### 🗑️ Bulk Delete")
        del_option = st.radio(
            "Delete which records?",
            [
                "Select specific IDs",
                "Delete all filtered records",
                "Delete by date range",
                "Delete by source file",
            ],
            key="del_option"
        )

        if del_option == "Select specific IDs":
            all_ids  = df_bulk["id"].tolist() if "id" in df_bulk.columns else []
            del_ids  = st.multiselect(
                "Select IDs to delete:", all_ids, key="bulk_del_ids"
            )
            if del_ids:
                st.warning(f"⚠️ You are about to delete {len(del_ids)} records!")
                col1, col2 = st.columns(2)
                with col1:
                    confirm = st.checkbox(
                        "I confirm I want to delete these records",
                        key="confirm_del"
                    )
                with col2:
                    if st.button(
                        f"🗑️ Delete {len(del_ids)} Records",
                        type="primary",
                        disabled=not confirm,
                        use_container_width=True,
                        key="do_bulk_del"
                    ):
                        res = delete_multiple(selected_table, del_ids)
                        if res["success"]:
                            st.success(
                                f"✅ Deleted {res['deleted']} records!"
                            )
                            st.rerun()
                        else:
                            st.error(f"❌ {res['error']}")

        elif del_option == "Delete all filtered records":
            st.warning(
                f"⚠️ This will delete ALL {len(df_bulk)} "
                f"records in current filter!"
            )
            confirm2 = st.checkbox(
                "I confirm I want to delete all filtered records",
                key="confirm_del2"
            )
            if st.button(
                f"🗑️ Delete All {len(df_bulk)} Records",
                type="primary",
                disabled=not confirm2,
                use_container_width=True,
                key="del_all"
            ):
                ids = df_bulk["id"].tolist()
                res = delete_multiple(selected_table, ids)
                if res["success"]:
                    st.success(f"✅ Deleted {res['deleted']} records!")
                    st.rerun()
                else:
                    st.error(f"❌ {res['error']}")

        elif del_option == "Delete by source file":
            if "document_source" in df_bulk.columns:
                sources = df_bulk["document_source"].dropna().unique().tolist()
                sel_src = st.selectbox(
                    "Select source file to delete:", sources, key="del_src"
                )
                src_count = len(df_bulk[df_bulk["document_source"]==sel_src])
                st.warning(f"⚠️ Will delete {src_count} records from {sel_src}")
                if st.button(
                    f"🗑️ Delete records from {sel_src}",
                    use_container_width=True,
                    key="del_src_btn"
                ):
                    ids = df_bulk[
                        df_bulk["document_source"]==sel_src
                    ]["id"].tolist()
                    res = delete_multiple(selected_table, ids)
                    if res["success"]:
                        st.success(f"✅ Deleted {res['deleted']} records!")
                        st.rerun()
                    else:
                        st.error(f"❌ {res['error']}")

        # Show current records
        st.markdown("---")
        st.markdown("**Current Records:**")
        st.dataframe(df_bulk, use_container_width=True, height=300)

        # Export
        st.download_button(
            "📥 Export Current View as CSV",
            df_bulk.to_csv(index=False),
            f"{selected_table}_export_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            "text/csv",
            use_container_width=True,
        )

st.markdown(
    '<div class="finteca-footer">Finteca AuditRep v1.0.0</div>',
    unsafe_allow_html=True,
)
