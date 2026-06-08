"""
Finteca AuditRep — Multi-User Login System
Roles: Admin, Manager, Cashier, Auditor
"""
import streamlit as st
import sqlite3
import hashlib
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DB_PATH = "/tmp/reconciliation.db" if os.path.exists("/mount/src") \
          else "data/reconciliation.db"
if not os.path.exists("/mount/src"):
    Path("data").mkdir(exist_ok=True)

st.set_page_config(
    page_title="Login - Finteca AuditRep",
    page_icon="🏦", layout="wide"
)

CSS = """
<style>
.login-container {
    max-width:500px; margin:50px auto; padding:40px;
    background:white; border-radius:15px;
    box-shadow:0 4px 20px rgba(0,0,0,0.1);
    border-top:5px solid #1a237e;
}
.login-header {
    text-align:center; margin-bottom:30px;
}
.login-header h1 { color:#1a237e; margin:0; font-size:2em; }
.login-header p  { color:#666; margin:5px 0 0 0; }
.role-badge {
    display:inline-block; padding:4px 12px;
    border-radius:20px; font-size:0.8em;
    font-weight:600; margin:2px;
}
.role-admin   { background:#e8eaf6; color:#1a237e; }
.role-manager { background:#e8f5e9; color:#2e7d32; }
.role-cashier { background:#fff3e0; color:#e65100; }
.role-auditor { background:#fce4ec; color:#c62828; }
.finteca-footer {
    text-align:center; color:#999; font-size:0.8em;
    padding:20px; border-top:1px solid #eee; margin-top:30px;
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ── User Management ───────────────────────────────────────
ROLE_PERMISSIONS = {
    "admin": {
        "label":       "Administrator",
        "icon":        "👑",
        "color":       "role-admin",
        "pages":       "all",
        "can_upload":  True,
        "can_delete":  True,
        "can_edit":    True,
        "can_export":  True,
        "can_manage_users": True,
        "description": "Full access to all modules"
    },
    "manager": {
        "label":       "Manager",
        "icon":        "📊",
        "color":       "role-manager",
        "pages":       [
            "Upload Documents","Reconciliation","Reports",
            "Trial Balance","Financial Statements",
            "Inventory","Statements","VAT Reports"
        ],
        "can_upload":  True,
        "can_delete":  False,
        "can_edit":    True,
        "can_export":  True,
        "can_manage_users": False,
        "description": "View reports, upload docs, no delete"
    },
    "cashier": {
        "label":       "Cashier",
        "icon":        "💵",
        "color":       "role-cashier",
        "pages":       [
            "Upload Documents","Collections","Expenses"
        ],
        "can_upload":  True,
        "can_delete":  False,
        "can_edit":    False,
        "can_export":  False,
        "can_manage_users": False,
        "description": "Enter collections and expenses only"
    },
    "auditor": {
        "label":       "Auditor",
        "icon":        "🔍",
        "color":       "role-auditor",
        "pages":       [
            "Reports","Trial Balance","Financial Statements",
            "Reconciliation","Inventory","Fraud Detection",
            "VAT Reports","Statements"
        ],
        "can_upload":  False,
        "can_delete":  False,
        "can_edit":    False,
        "can_export":  True,
        "can_manage_users": False,
        "description": "View and export only — no modifications"
    },
}

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            email TEXT,
            role TEXT NOT NULL DEFAULT 'cashier',
            is_active INTEGER DEFAULT 1,
            last_login TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS login_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            action TEXT,
            ip_address TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Create default admin if no users exist
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        admin_hash = hashlib.sha256("admin123".encode()).hexdigest()
        conn.execute(
            "INSERT INTO users (username, password_hash, full_name, role) "
            "VALUES (?, ?, ?, ?)",
            ("admin", admin_hash, "System Administrator", "admin")
        )
        conn.commit()
    return conn

def verify_login(username: str, password: str) -> dict:
    conn = get_conn()
    pwd_hash = hashlib.sha256(password.encode()).hexdigest()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, full_name, role, is_active "
        "FROM users WHERE username=? AND password_hash=?",
        (username, pwd_hash)
    )
    row = cursor.fetchone()
    if row:
        if row[4] == 0:
            conn.close()
            return {"success": False, "error": "Account disabled"}
        conn.execute(
            "UPDATE users SET last_login=? WHERE id=?",
            (datetime.now().isoformat(), row[0])
        )
        conn.execute(
            "INSERT INTO login_log (username, action) VALUES (?, ?)",
            (username, "login")
        )
        conn.commit()
        conn.close()
        return {
            "success":   True,
            "user_id":   row[0],
            "username":  row[1],
            "full_name": row[2],
            "role":      row[3],
        }
    conn.close()
    return {"success": False, "error": "Invalid credentials"}

def create_user(username, password, full_name, email, role) -> dict:
    try:
        conn = get_conn()
        pwd_hash = hashlib.sha256(password.encode()).hexdigest()
        conn.execute(
            "INSERT INTO users "
            "(username, password_hash, full_name, email, role) "
            "VALUES (?, ?, ?, ?, ?)",
            (username, pwd_hash, full_name, email, role)
        )
        conn.commit()
        conn.close()
        return {"success": True}
    except sqlite3.IntegrityError:
        return {"success": False, "error": "Username already exists"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_all_users():
    try:
        import pandas as pd
        conn = get_conn()
        df = pd.read_sql(
            "SELECT id, username, full_name, email, role, "
            "is_active, last_login, created_at FROM users",
            conn
        )
        conn.close()
        return df
    except Exception:
        return None

def change_password(username, new_password) -> dict:
    try:
        conn = get_conn()
        pwd_hash = hashlib.sha256(new_password.encode()).hexdigest()
        conn.execute(
            "UPDATE users SET password_hash=? WHERE username=?",
            (pwd_hash, username)
        )
        conn.commit()
        conn.close()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

def toggle_user_active(user_id, active) -> dict:
    try:
        conn = get_conn()
        conn.execute(
            "UPDATE users SET is_active=? WHERE id=?",
            (1 if active else 0, user_id)
        )
        conn.commit()
        conn.close()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ── Initialize ────────────────────────────────────────────
get_conn()

# ── Check Login State ─────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "user" not in st.session_state:
    st.session_state.user = None

# ── Login Screen ──────────────────────────────────────────
if not st.session_state.logged_in:

    st.markdown("""
    <div class="login-header">
        <h1>🏦 Finteca AuditRep</h1>
        <p>Forensic Accounting · Fraud Detection · Reconciliation</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("### 🔐 Sign In")

        with st.form("login_form"):
            username = st.text_input(
                "Username",
                placeholder="Enter your username"
            )
            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter your password"
            )

            if st.form_submit_button(
                "🔑 Sign In",
                type="primary",
                use_container_width=True
            ):
                if username and password:
                    result = verify_login(username, password)
                    if result["success"]:
                        st.session_state.logged_in = True
                        st.session_state.user = result
                        st.success(
                            f"✅ Welcome, {result['full_name']}!"
                        )
                        st.rerun()
                    else:
                        st.error(
                            f"❌ {result.get('error', 'Login failed')}"
                        )
                else:
                    st.error("Please enter username and password")

        st.divider()
        st.markdown("""
        **Default Login:**
        - Username: `admin`
        - Password: `admin123`

        ⚠️ Change the default password after first login!
        """)

        st.markdown("""
        **User Roles:**

        👑 **Admin** — Full access to everything

        📊 **Manager** — Upload, view reports, no delete

        💵 **Cashier** — Collections and expenses only

        🔍 **Auditor** — View and export only
        """)

# ── Logged In — Show Dashboard + User Management ─────────
else:
    user = st.session_state.user
    role = user.get("role", "cashier")
    perms = ROLE_PERMISSIONS.get(role, ROLE_PERMISSIONS["cashier"])

    # Sidebar user info
    st.sidebar.markdown(f"""
    **{perms['icon']} {user.get('full_name', user['username'])}**

    Role: `{perms['label']}`

    <span class="role-badge {perms['color']}">
    {perms['label']}</span>
    """, unsafe_allow_html=True)

    if st.sidebar.button("🚪 Sign Out", use_container_width=True):
        try:
            conn = get_conn()
            conn.execute(
                "INSERT INTO login_log (username, action) "
                "VALUES (?, ?)",
                (user["username"], "logout")
            )
            conn.commit()
            conn.close()
        except Exception:
            pass
        st.session_state.logged_in = False
        st.session_state.user = None
        st.rerun()

    # Header
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#1a237e 0%,#283593 50%,#42a5f5 100%);
                padding:25px 30px;border-radius:12px;color:white;margin-bottom:25px;">
        <h1 style="margin:0;font-size:2em;">
        {perms['icon']} Welcome, {user.get('full_name', user['username'])}
        </h1>
        <p style="margin:5px 0 0 0;opacity:0.85;">
        Role: {perms['label']} · {perms['description']}
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── Tabs ──────────────────────────────────────────
    if perms.get("can_manage_users"):
        admin_tabs = st.tabs([
            "🏠 Dashboard",
            "👥 User Management",
            "🔑 Change Password",
            "📜 Login History",
        ])
    else:
        admin_tabs = st.tabs([
            "🏠 Dashboard",
            "🔑 Change Password",
        ])

    # ── Dashboard ─────────────────────────────────────
    with admin_tabs[0]:
        st.markdown("### Your Accessible Modules")

        pages_access = perms.get("pages", [])
        if pages_access == "all":
            pages_access = [
                "Upload Documents", "Reconciliation", "Reports",
                "Data Manager", "Trial Balance",
                "Financial Statements", "Expenses",
                "Purchase Returns", "Inventory",
                "Statements", "VAT Reports",
                "User Management", "GitHub Deploy"
            ]

        cols = st.columns(4)
        module_icons = {
            "Upload Documents":    "📤",
            "Reconciliation":      "🔍",
            "Reports":             "📊",
            "Data Manager":        "🗃️",
            "Trial Balance":       "📋",
            "Financial Statements":"📈",
            "Expenses":            "💳",
            "Purchase Returns":    "↩️",
            "Inventory":           "📦",
            "Statements":          "📄",
            "VAT Reports":         "🧾",
            "User Management":     "👥",
            "GitHub Deploy":       "🚀",
            "Collections":         "💵",
            "Fraud Detection":     "🚨",
        }

        for i, page in enumerate(pages_access):
            icon = module_icons.get(page, "📋")
            with cols[i % 4]:
                st.markdown(f"""
                <div style="background:white;border:1px solid #e0e0e0;
                            border-radius:10px;padding:15px;text-align:center;
                            margin:5px 0;box-shadow:0 1px 3px rgba(0,0,0,0.05)">
                    <div style="font-size:2em">{icon}</div>
                    <div style="font-weight:600;color:#1a237e;font-size:0.9em">
                    {page}</div>
                    <div style="color:#999;font-size:0.7em">
                    {'✅ Access' if True else '❌ No Access'}</div>
                </div>
                """, unsafe_allow_html=True)

        st.divider()

        st.markdown("**Your Permissions:**")
        perm_cols = st.columns(5)
        perm_items = [
            ("📤 Upload",  perms.get("can_upload")),
            ("✏️ Edit",     perms.get("can_edit")),
            ("🗑️ Delete",   perms.get("can_delete")),
            ("📥 Export",   perms.get("can_export")),
            ("👥 Users",   perms.get("can_manage_users")),
        ]
        for col, (label, has) in zip(perm_cols, perm_items):
            col.metric(
                label,
                "✅ Yes" if has else "❌ No"
            )

    # ── User Management (Admin Only) ──────────────────
    if perms.get("can_manage_users") and len(admin_tabs) > 1:
        with admin_tabs[1]:
            st.markdown("### 👥 User Management")

            # Create new user
            with st.expander("➕ Create New User", expanded=False):
                with st.form("create_user_form", clear_on_submit=True):
                    new_user    = st.text_input("Username")
                    new_pass    = st.text_input(
                        "Password", type="password"
                    )
                    new_name    = st.text_input("Full Name")
                    new_email   = st.text_input("Email")
                    new_role    = st.selectbox(
                        "Role",
                        ["cashier","manager","auditor","admin"]
                    )

                    if st.form_submit_button(
                        "➕ Create User",
                        type="primary",
                        use_container_width=True
                    ):
                        if new_user and new_pass and new_name:
                            result = create_user(
                                new_user, new_pass,
                                new_name, new_email, new_role
                            )
                            if result["success"]:
                                st.success(
                                    f"✅ User '{new_user}' created "
                                    f"as {new_role}"
                                )
                                st.rerun()
                            else:
                                st.error(
                                    f"❌ {result.get('error')}"
                                )
                        else:
                            st.error(
                                "Username, password, and name required"
                            )

            # List users
            import pandas as pd
            users_df = get_all_users()
            if users_df is not None and not users_df.empty:
                st.markdown("**Current Users:**")
                st.dataframe(
                    users_df,
                    use_container_width=True,
                    height=300
                )

                # Toggle active/inactive
                st.markdown("**Enable/Disable User:**")
                tc1, tc2 = st.columns(2)
                with tc1:
                    sel_user_id = st.selectbox(
                        "Select User",
                        users_df["id"].tolist(),
                        format_func=lambda x: (
                            f"{users_df[users_df['id']==x]['username'].iloc[0]}"
                            f" ({users_df[users_df['id']==x]['role'].iloc[0]})"
                        )
                    )
                with tc2:
                    action = st.selectbox(
                        "Action",
                        ["Enable","Disable"]
                    )
                if st.button("Apply"):
                    result = toggle_user_active(
                        sel_user_id,
                        action == "Enable"
                    )
                    if result["success"]:
                        st.success(
                            f"✅ User {action.lower()}d"
                        )
                        st.rerun()

    # ── Change Password ───────────────────────────────
    pwd_tab_idx = 2 if perms.get("can_manage_users") else 1
    with admin_tabs[pwd_tab_idx]:
        st.markdown("### 🔑 Change Your Password")
        with st.form("change_pwd_form"):
            new_pwd = st.text_input(
                "New Password", type="password"
            )
            confirm_pwd = st.text_input(
                "Confirm Password", type="password"
            )
            if st.form_submit_button(
                "🔑 Change Password",
                type="primary"
            ):
                if new_pwd and new_pwd == confirm_pwd:
                    if len(new_pwd) < 6:
                        st.error(
                            "Password must be at least 6 characters"
                        )
                    else:
                        result = change_password(
                            user["username"], new_pwd
                        )
                        if result["success"]:
                            st.success("✅ Password changed!")
                        else:
                            st.error(
                                f"❌ {result.get('error')}"
                            )
                elif new_pwd != confirm_pwd:
                    st.error("Passwords do not match")

    # ── Login History (Admin Only) ─────────────────────
    if perms.get("can_manage_users") and len(admin_tabs) > 3:
        with admin_tabs[3]:
            st.markdown("### 📜 Login History")
            try:
                import pandas as pd
                conn = get_conn()
                log = pd.read_sql(
                    "SELECT * FROM login_log "
                    "ORDER BY timestamp DESC LIMIT 100",
                    conn
                )
                conn.close()
                if not log.empty:
                    st.dataframe(
                        log,
                        use_container_width=True,
                        height=400
                    )
                else:
                    st.info("No login history yet.")
            except Exception:
                st.info("No login history available.")

st.markdown("""
<div class="finteca-footer">
    Finteca AuditRep v2.0.0 · Secure Multi-User Access
</div>
""", unsafe_allow_html=True)
