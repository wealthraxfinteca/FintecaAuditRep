# 🏦 Finteca AuditRep

> Forensic Accounting · Fraud Detection · Reconciliation · Reporting

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io)

## Features

- 📤 Document Upload — Excel, CSV, PDF, Word, Images
- 🔍 Reconciliation — Bank, Collections, Purchases, Sales
- 📋 Extended Trial Balance — Full ledger with date filtering
- 🚨 Fraud Detection — 10 automated integrity checks
- 📊 Reports — Profitability, Cash, Debtors, Creditors
- 🤖 AI Investigator — GPT-4o powered forensic analysis
- 📦 Inventory Integrity — Complete movement tracking

## Quick Start

    git clone https://github.com/wealthraxfinteca/FintecaAuditRep.git
    cd FintecaAuditRep
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env
    streamlit run main_app.py

## Environment Variables

    OPENAI_API_KEY=sk-proj-your-key-here
    DATABASE_PATH=data/reconciliation.db

## Deploy on Streamlit Cloud

1. Go to share.streamlit.io
2. Connect wealthraxfinteca/FintecaAuditRep
3. Main file: main_app.py
4. Add secret: OPENAI_API_KEY
5. Deploy

## Security

- Financial data stays local (SQLite)
- API keys in .env — never committed
- Database excluded from GitHub

## License

MIT 2025 Finteca / wealthraxfinteca
