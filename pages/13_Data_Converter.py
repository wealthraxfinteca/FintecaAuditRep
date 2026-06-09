"""
Finteca AuditRep — Collections Data Converter
Convert text/narrative collections data to uploadable format
"""
import streamlit as st
import pandas as pd
import re
import io
import os
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
    page_title="Data Converter - Finteca AuditRep",
    page_icon="🔄", layout="wide"
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
.flag-green{background:#e8f5e9;border-left:4px solid #2e7d32;
    padding:10px;border-radius:5px;margin:5px 0;}
.flag-blue{background:#e3f2fd;border-left:4px solid #1565c0;
    padding:10px;border-radius:5px;margin:5px 0;}
.finteca-footer{text-align:center;color:#999;font-size:0.8em;
    padding:20px;border-top:1px solid #eee;margin-top:30px;}
</style>"""
st.markdown(CSS, unsafe_allow_html=True)
st.markdown("""
<div class="finteca-header">
    <h1>🔄 Finteca AuditRep</h1>
    <p>Data Converter — Text, PDF, CSV to Uploadable Format</p>
    <span class="finteca-badge">Module 13 — Converter</span>
</div>
""", unsafe_allow_html=True)

DB_PATH = (st.session_state.get("active_db_path") or
    ("/tmp/reconciliation.db" if os.path.exists("/mount/src")
     else "data/reconciliation.db"))

import sqlite3
def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def to_num(s):
    return pd.to_numeric(s, errors="coerce").fillna(0)

if st.session_state.get("active_assignment_name"):
    st.markdown(
        f'<div class="flag-green">Assignment: <b>{st.session_state.active_assignment_name}</b></div>',
        unsafe_allow_html=True)

api_key = os.getenv("OPENAI_API_KEY","")

tabs = st.tabs([
    "📝 Text Collections Converter",
    "📊 Manual Collections Entry",
    "🤖 AI Data Extractor",
    "✅ Preview & Save",
])

# ════════════════════════════════════════════════════════
# TAB 1 — TEXT CONVERTER
# ════════════════════════════════════════════════════════
with tabs[0]:
    st.markdown('<div class="section-header">📝 Convert Text Collections to Table</div>',
                unsafe_allow_html=True)

    st.markdown("""
    Paste your collections text data below.
    The converter will extract dates, amounts, customers and methods.
    """)

    format_help = st.expander("📋 Supported Formats")
    with format_help:
        st.markdown("""
        **Format 1 — Date | Customer | Amount | Method**
        ```
        01/05/2025 | ABC Ltd | 50,000 | Cash
        02/05/2025 | XYZ Company | 125,000 | Bank Transfer
        ```

        **Format 2 — CSV style**
        ```
        date,customer,amount,method,received_by
        2025-05-01,ABC Ltd,50000,Cash,John
        ```

        **Format 3 — Narrative**
        ```
        May 1 2025 - Collected N50,000 from ABC Ltd in cash
        May 2 2025 - Bank transfer of N125,000 received from XYZ
        ```

        **Format 4 — Column data (space/tab separated)**
        ```
        01-05-2025  ABC Ltd         50000   Cash      John
        02-05-2025  XYZ Company    125000   Transfer  Mary
        ```
        """)

    raw_text = st.text_area(
        "Paste your collections data here:",
        height=300,
        placeholder="""01/05/2025 | ABC Ltd | 50,000 | Cash | John
02/05/2025 | XYZ Company | 125,000 | Bank Transfer | Mary
03/05/2025 | DEF Store | 75,500 | Cheque | John"""
    )

    col_format = st.selectbox("Format type:", [
        "Auto-detect",
        "Pipe separated (|)",
        "Comma separated (CSV)",
        "Tab separated",
        "Space separated",
        "Narrative text (use AI)",
    ])

    if st.button("🔄 Convert Text to Table", type="primary") and raw_text.strip():

        lines = [l.strip() for l in raw_text.strip().splitlines() if l.strip()]
        rows  = []

        if col_format == "Pipe separated (|)":
            for line in lines:
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 3:
                    rows.append({
                        "date":           parts[0] if len(parts)>0 else "",
                        "customer":       parts[1] if len(parts)>1 else "",
                        "amount":         re.sub(r"[^0-9.]","",parts[2]) if len(parts)>2 else "0",
                        "payment_method": parts[3] if len(parts)>3 else "Cash",
                        "received_by":    parts[4] if len(parts)>4 else "",
                        "invoice_reference": parts[5] if len(parts)>5 else "",
                    })

        elif col_format == "Comma separated (CSV)":
            try:
                df_csv = pd.read_csv(io.StringIO(raw_text))
                for _, r in df_csv.iterrows():
                    rows.append({
                        "date":           str(r.get("date",r.get("Date",""))),
                        "customer":       str(r.get("customer",r.get("Customer",r.get("name","")))),
                        "amount":         str(r.get("amount",r.get("Amount","0"))),
                        "payment_method": str(r.get("method",r.get("payment_method",r.get("Method","Cash")))),
                        "received_by":    str(r.get("received_by",r.get("collector",""))),
                        "invoice_reference": str(r.get("invoice",r.get("reference",""))),
                    })
            except Exception as e:
                st.error(f"CSV parse error: {e}")

        elif col_format in ["Tab separated","Space separated","Auto-detect"]:
            delim = "\t" if col_format=="Tab separated" else r"\s{2,}"
            for line in lines:
                # Skip header lines
                if any(h in line.lower() for h in ["date","customer","amount","header"]):
                    continue
                # Try to find date pattern
                date_match = re.search(
                    r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|"
                    r"\d{4}[/-]\d{1,2}[/-]\d{1,2})", line)
                # Try to find amount
                amt_match  = re.search(r"[N₦]?[\d,]+\.?\d{0,2}", line)
                # Try payment method
                method = "Cash"
                for m in ["cash","transfer","cheque","card","bank","mobile"]:
                    if m in line.lower():
                        method = m.title()
                        break

                if date_match and amt_match:
                    amt_str = re.sub(r"[^0-9.]","",amt_match.group())
                    rows.append({
                        "date":           date_match.group(),
                        "customer":       line[:date_match.start()].strip() or
                                         line[date_match.end():amt_match.start()].strip(),
                        "amount":         amt_str,
                        "payment_method": method,
                        "received_by":    "",
                        "invoice_reference": "",
                    })

        if rows:
            df_converted = pd.DataFrame(rows)
            # Clean amount
            df_converted["amount"] = df_converted["amount"].apply(
                lambda x: float(re.sub(r"[^0-9.]","",str(x)) or "0")
            )
            # Parse dates
            df_converted["date"] = pd.to_datetime(
                df_converted["date"], dayfirst=True, errors="coerce"
            ).dt.strftime("%Y-%m-%d")

            st.session_state["converted_collections"] = df_converted
            st.success(f"✅ Converted {len(df_converted)} records!")
            st.dataframe(df_converted, use_container_width=True, height=300)

            # Quick edit
            st.markdown("**Edit if needed:**")
            edited = st.data_editor(
                df_converted,
                use_container_width=True,
                num_rows="dynamic",
                key="coll_editor"
            )
            st.session_state["converted_collections"] = edited
        else:
            st.error("Could not parse the text. Try a different format or use AI Extractor.")

# ════════════════════════════════════════════════════════
# TAB 2 — MANUAL ENTRY
# ════════════════════════════════════════════════════════
with tabs[1]:
    st.markdown('<div class="section-header">📊 Manual Collections Entry</div>',
                unsafe_allow_html=True)

    st.markdown("Enter collections one by one or paste a batch:")

    # Batch entry using data editor
    if "manual_collections" not in st.session_state:
        st.session_state.manual_collections = pd.DataFrame({
            "date": [str(date.today())],
            "customer": [""],
            "invoice_reference": [""],
            "amount": [0.0],
            "payment_method": ["Cash"],
            "received_by": [""],
            "bank_deposit_date": [""],
            "bank_deposit_ref": [""],
            "notes": [""],
        })

    edited_manual = st.data_editor(
        st.session_state.manual_collections,
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "date": st.column_config.DateColumn("Date"),
            "amount": st.column_config.NumberColumn("Amount", min_value=0, format="%.2f"),
            "payment_method": st.column_config.SelectboxColumn(
                "Payment Method",
                options=["Cash","Bank Transfer","Cheque","Card","Mobile Money","Other"]
            ),
        },
        key="manual_coll_editor"
    )
    st.session_state.manual_collections = edited_manual

    if st.button("✅ Use This Data", type="primary"):
        valid = edited_manual[edited_manual["amount"]>0]
        if not valid.empty:
            st.session_state["converted_collections"] = valid
            st.success(f"✅ {len(valid)} entries ready to save")
        else:
            st.error("Enter at least one collection with amount > 0")

# ════════════════════════════════════════════════════════
# TAB 3 — AI EXTRACTOR
# ════════════════════════════════════════════════════════
with tabs[2]:
    st.markdown('<div class="section-header">🤖 AI Data Extractor</div>',
                unsafe_allow_html=True)

    if not api_key:
        st.error("Add OPENAI_API_KEY to .env to use AI extraction")
    else:
        st.markdown("""
        Paste ANY format of collections data.
        AI will extract and structure it automatically.
        Works with narrative text, mixed formats, etc.
        """)

        ai_text = st.text_area(
            "Paste any collections data:",
            height=250,
            placeholder="Any format works — narrative, table, mixed..."
        )

        if st.button("🤖 Extract with AI", type="primary") and ai_text.strip():
            with st.spinner("AI extracting data..."):
                try:
                    client = OpenAI(api_key=api_key)
                    response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[{
                            "role": "system",
                            "content": """You are a financial data extraction AI.
Extract collection records from the text provided.
Return ONLY valid JSON array:
[
  {
    "date": "YYYY-MM-DD",
    "customer": "customer name",
    "invoice_reference": "invoice or reference number if mentioned",
    "amount": 0.00,
    "payment_method": "Cash|Bank Transfer|Cheque|Card|Other",
    "received_by": "name of collector if mentioned",
    "bank_deposit_date": "YYYY-MM-DD or empty",
    "bank_deposit_ref": "bank reference if mentioned",
    "notes": "any other relevant info"
  }
]
Extract every single collection record. Be precise with amounts."""
                        }, {
                            "role": "user",
                            "content": f"Extract all collection records from this text:\n\n{ai_text}"
                        }],
                        max_tokens=3000,
                    )

                    content_str = response.choices[0].message.content
                    # Extract JSON array
                    json_match = re.search(r"\[.*\]", content_str, re.DOTALL)
                    if json_match:
                        import json
                        records = json.loads(json_match.group())
                        df_ai = pd.DataFrame(records)
                        df_ai["amount"] = to_num(df_ai.get("amount", pd.Series(dtype=float)))
                        st.session_state["converted_collections"] = df_ai
                        st.success(f"✅ AI extracted {len(df_ai)} records!")
                        st.dataframe(df_ai, use_container_width=True, height=300)

                        # Allow editing
                        edited_ai = st.data_editor(
                            df_ai,
                            use_container_width=True,
                            num_rows="dynamic",
                            key="ai_edit"
                        )
                        st.session_state["converted_collections"] = edited_ai
                    else:
                        st.error("AI could not extract structured data. Try different format.")
                except Exception as e:
                    st.error(f"AI Error: {e}")

# ════════════════════════════════════════════════════════
# TAB 4 — PREVIEW & SAVE
# ════════════════════════════════════════════════════════
with tabs[3]:
    st.markdown('<div class="section-header">✅ Preview & Save to Database</div>',
                unsafe_allow_html=True)

    df_ready = st.session_state.get("converted_collections")

    if df_ready is None or (hasattr(df_ready,"empty") and df_ready.empty):
        st.info("No data ready yet. Use one of the converter tabs above first.")
    else:
        st.markdown(f"**{len(df_ready)} records ready to save:**")

        total_amt = to_num(df_ready.get("amount",pd.Series(dtype=float))).sum()
        m = st.columns(3)
        m[0].metric("Records",      len(df_ready))
        m[1].metric("Total Amount", f"{total_amt:,.2f}")
        m[2].metric("Target Table", "collections")

        st.dataframe(df_ready, use_container_width=True, height=300)

        # Download as CSV
        st.download_button(
            "📥 Download as CSV (for manual upload)",
            df_ready.to_csv(index=False),
            "collections_data.csv", "text/csv",
            use_container_width=True
        )

        st.divider()
        source_name = st.text_input(
            "Source name (for audit trail):",
            value="Collections_Text_Data",
            key="coll_source"
        )

        if st.button("💾 Save to Collections Table",
                     type="primary", use_container_width=True):
            try:
                conn = get_conn()
                save_df = df_ready.copy()
                save_df["document_source"] = source_name
                save_df["uploaded_at"]     = datetime.now().isoformat()
                save_df["reconciled"]      = 0

                # Get valid columns
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(collections)")
                valid_cols = [r[1] for r in cursor.fetchall()]
                save_cols  = [c for c in save_df.columns if c in valid_cols]
                save_df[save_cols].to_sql(
                    "collections", conn,
                    if_exists="append", index=False
                )

                # Log upload
                conn.execute(
                    "INSERT INTO upload_log (filename,document_type,rows_saved,status) VALUES (?,?,?,?)",
                    (source_name,"collections",len(save_df),"success")
                )
                conn.commit()
                conn.close()

                st.success(f"✅ Saved {len(save_df)} collections to database!")
                st.session_state["converted_collections"] = None
                st.rerun()
            except Exception as e:
                st.error(f"❌ Save failed: {e}")

st.markdown('<div class="finteca-footer">Finteca AuditRep v4.0 · Data Converter</div>',
            unsafe_allow_html=True)
