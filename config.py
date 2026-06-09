import os
from pathlib import Path

# ── Base directory ────────────────────────────────────────
BASE_DIR = Path(__file__).parent

# ── Database path — works locally AND on Streamlit Cloud ──
# On Streamlit Cloud, /tmp is the only writable directory
if os.path.exists("/mount/src"):
    # Running on Streamlit Cloud
    DB_PATH = "/tmp/reconciliation.db"
    DATA_DIR = Path("/tmp")
else:
    # Running locally
    DATA_DIR = BASE_DIR / "data"
    DATA_DIR.mkdir(exist_ok=True)
    DB_PATH = str(DATA_DIR / "reconciliation.db")

APP_CONFIG = {
    'name':            'Finteca AuditRep',
    'tagline':         'Forensic Accounting | Fraud Detection | Reconciliation | Reporting',
    'version':         '1.0.0',
    'company':         'Finteca',
    'logo_icon':       '🏦',
    'primary_color':   '#1a237e',
    'secondary_color': '#283593',
    'accent_color':    '#42a5f5',
    'db_path':         DB_PATH,
}
