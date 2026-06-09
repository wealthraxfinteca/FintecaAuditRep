"""
bin_card_engine.py
Finteca AuditRep — Bin Card & Inventory Reconciliation Engine

Formula per SKU per period:
  Closing Stock (Qty)   = Opening Stock + Purchases - Purchase Returns - Sales + Sales Returns
  Closing Stock (Value) = Closing Stock (Qty) × Weighted Average Cost

Supports:
  - Per SKU / Item Code
  - Per date range
  - Per assignment (client isolation)
  - Weighted Average Cost (WAC) method
  - FIFO (future)
"""

import sqlite3
import pandas as pd
import os
from datetime import datetime, date
from typing import Optional


# ── DB Connection ────────────────────────────────────────────

def get_conn(db_path: str) -> sqlite3.Connection:
    return sqlite3.connect(db_path, check_same_thread=False)


def load_table(db_path: str, table: str) -> pd.DataFrame:
    """Load a full table into a DataFrame."""
    try:
        conn = get_conn(db_path)
        df = pd.read_sql(f"SELECT * FROM '{table}'", conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()


# ── Date Normalisation ───────────────────────────────────────

def normalise_dates(df: pd.DataFrame, col: str = "date") -> pd.DataFrame:
    """Convert date column to pandas datetime safely."""
    if col in df.columns:
        df = df.copy()
        df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def filter_by_period(
    df: pd.DataFrame,
    date_from: date,
    date_to: date,
    col: str = "date"
) -> pd.DataFrame:
    """Filter DataFrame to a date range (inclusive)."""
    if df.empty or col not in df.columns:
        return df
    df = normalise_dates(df, col)
    _from = pd.Timestamp(date_from)
    _to   = pd.Timestamp(date_to) + pd.Timedelta(hours=23, minutes=59, seconds=59)
    mask  = (df[col] >= _from) & (df[col] <= _to)
    return df[mask].copy()


# ── Column Resolution ────────────────────────────────────────

def resolve_col(df: pd.DataFrame, candidates: list, default=0) -> pd.Series:
    """Return first matching column, or a zero Series."""
    for c in candidates:
        if c in df.columns:
            return pd.to_numeric(df[c], errors="coerce").fillna(0)
    return pd.Series([default] * len(df), index=df.index)


def resolve_sku(df: pd.DataFrame) -> pd.Series:
    """Resolve SKU/item_code column."""
    for c in ["item_code", "sku", "product_code", "code", "part_no"]:
        if c in df.columns:
            return df[c].fillna("UNKNOWN").astype(str).str.strip().str.upper()
    return pd.Series(["UNKNOWN"] * len(df), index=df.index)


def resolve_name(df: pd.DataFrame) -> pd.Series:
    """Resolve item name/description column."""
    for c in ["description", "item_description", "item_name",
              "product", "particulars", "item"]:
        if c in df.columns:
            return df[c].fillna("").astype(str).str.strip()
    return pd.Series([""] * len(df), index=df.index)


# ════════════════════════════════════════════════════════════
# CORE BIN CARD ENGINE
# ════════════════════════════════════════════════════════════

def compute_bin_cards(
    db_path:       str,
    date_from:     date,
    date_to:       date,
    assignment_id: Optional[str] = None,
    sku_filter:    Optional[str] = None,
) -> pd.DataFrame:
    """
    Compute bin card for all SKUs in the given period.

    Returns a DataFrame with one row per SKU:
        sku, item_name,
        opening_qty, opening_value,
        purchases_qty, purchases_value,
        purchase_returns_qty, purchase_returns_value,
        sales_qty, sales_value,
        sales_returns_qty, sales_returns_value,
        closing_qty, closing_value,
        weighted_avg_cost,
        gross_profit, gross_margin_pct
    """

    # ── Load all tables ──────────────────────────────────────
    inv  = load_table(db_path, "inventory")
    purch = load_table(db_path, "purchases")
    pr    = load_table(db_path, "purchase_returns")
    sales = load_table(db_path, "sales")
    sr    = load_table(db_path, "sales_returns")

    # ── Normalise dates ──────────────────────────────────────
    for df in [purch, pr, sales, sr]:
        if not df.empty:
            normalise_dates(df)

    # ── Filter by period ─────────────────────────────────────
    purch_p = filter_by_period(purch, date_from, date_to) if not purch.empty else purch
    pr_p    = filter_by_period(pr,    date_from, date_to) if not pr.empty    else pr
    sales_p = filter_by_period(sales, date_from, date_to) if not sales.empty else sales
    sr_p    = filter_by_period(sr,    date_from, date_to) if not sr.empty    else sr

    # ── Build SKU universe ───────────────────────────────────
    # Collect all SKUs from all transaction tables
    sku_sets = {}

    def extract_skus(df, source):
        if df.empty:
            return
        skus  = resolve_sku(df)
        names = resolve_name(df)
        for sku, name in zip(skus, names):
            if sku and sku != "UNKNOWN":
                if sku not in sku_sets:
                    sku_sets[sku] = name
                elif not sku_sets[sku] and name:
                    sku_sets[sku] = name

    extract_skus(purch,   "purchases")
    extract_skus(pr,      "purchase_returns")
    extract_skus(sales,   "sales")
    extract_skus(sr,      "sales_returns")

    # Add SKUs from inventory master
    if not inv.empty:
        inv_skus  = resolve_sku(inv)
        inv_names = resolve_name(inv)
        for sku, name in zip(inv_skus, inv_names):
            if sku not in sku_sets:
                sku_sets[sku] = name

    if not sku_sets:
        return pd.DataFrame()

    # ── Apply SKU filter ─────────────────────────────────────
    if sku_filter:
        sku_sets = {
            k: v for k, v in sku_sets.items()
            if sku_filter.upper() in k.upper()
        }

    # ── Compute per SKU ──────────────────────────────────────
    records = []

    for sku, item_name in sku_sets.items():

        # ── Opening Stock (from inventory master) ────────────
        opening_qty   = 0.0
        opening_value = 0.0

        if not inv.empty:
            inv["_sku"] = resolve_sku(inv)
            inv_row = inv[inv["_sku"] == sku]
            if not inv_row.empty:
                opening_qty = float(
                    resolve_col(inv_row,
                        ["opening_stock", "opening_qty",
                         "qty", "quantity", "stock"]
                    ).sum()
                )
                unit_cost = float(
                    resolve_col(inv_row,
                        ["unit_cost", "cost_price",
                         "purchase_price", "cost"]
                    ).mean() or 0
                )
                opening_value = opening_qty * unit_cost

        # ── Purchases IN ─────────────────────────────────────
        purch_qty   = 0.0
        purch_value = 0.0

        if not purch_p.empty:
            purch_p["_sku"] = resolve_sku(purch_p)
            p_rows = purch_p[purch_p["_sku"] == sku]
            if not p_rows.empty:
                purch_qty = float(
                    resolve_col(p_rows,
                        ["quantity", "qty", "units"]
                    ).sum()
                )
                purch_value = float(
                    resolve_col(p_rows,
                        ["total_amount", "total_cost",
                         "amount", "net_amount"]
                    ).sum()
                )
                # If value not available, compute from qty × rate
                if purch_value == 0 and purch_qty > 0:
                    rates = resolve_col(p_rows,
                        ["rate", "unit_cost", "unit_price", "price"])
                    purch_value = float((
                        resolve_col(p_rows, ["quantity","qty"]) * rates
                    ).sum())

        # ── Purchase Returns OUT ──────────────────────────────
        pr_qty   = 0.0
        pr_value = 0.0

        if not pr_p.empty:
            pr_p["_sku"] = resolve_sku(pr_p)
            pr_rows = pr_p[pr_p["_sku"] == sku]
            if not pr_rows.empty:
                pr_qty = float(
                    resolve_col(pr_rows,
                        ["quantity_returned", "qty_returned",
                         "quantity", "qty"]
                    ).sum()
                )
                pr_value = float(
                    resolve_col(pr_rows,
                        ["return_amount", "amount", "value"]
                    ).sum()
                )
                if pr_value == 0 and pr_qty > 0:
                    rates = resolve_col(pr_rows,
                        ["rate", "unit_cost", "unit_price"])
                    pr_value = float((
                        resolve_col(pr_rows,
                            ["quantity_returned","qty_returned","quantity","qty"]
                        ) * rates
                    ).sum())

        # ── Sales OUT ─────────────────────────────────────────
        sales_qty   = 0.0
        sales_value = 0.0
        sales_revenue = 0.0

        if not sales_p.empty:
            sales_p["_sku"] = resolve_sku(sales_p)
            s_rows = sales_p[sales_p["_sku"] == sku]
            if not s_rows.empty:
                sales_qty = float(
                    resolve_col(s_rows,
                        ["quantity", "qty", "units"]
                    ).sum()
                )
                sales_revenue = float(
                    resolve_col(s_rows,
                        ["total_amount", "gross_amount",
                         "amount", "net_amount"]
                    ).sum()
                )
                if sales_revenue == 0 and sales_qty > 0:
                    rates = resolve_col(s_rows,
                        ["rate", "unit_price", "selling_price", "price"])
                    sales_revenue = float((
                        resolve_col(s_rows, ["quantity","qty"]) * rates
                    ).sum())
                # Cost of sales = qty × weighted avg cost (computed later)
                sales_value = sales_qty  # placeholder

        # ── Sales Returns IN ──────────────────────────────────
        sr_qty   = 0.0
        sr_value = 0.0

        if not sr_p.empty:
            sr_p["_sku"] = resolve_sku(sr_p)
            sr_rows = sr_p[sr_p["_sku"] == sku]
            if not sr_rows.empty:
                sr_qty = float(
                    resolve_col(sr_rows,
                        ["quantity_returned", "qty_returned",
                         "quantity", "qty"]
                    ).sum()
                )
                sr_value = float(
                    resolve_col(sr_rows,
                        ["return_amount", "amount", "value"]
                    ).sum()
                )

        # ── Closing Stock ─────────────────────────────────────
        # Formula: Opening + Purchases - Purchase Returns - Sales + Sales Returns
        closing_qty = (
            opening_qty
            + purch_qty
            - pr_qty
            - sales_qty
            + sr_qty
        )

        # ── Weighted Average Cost ─────────────────────────────
        total_cost_in  = opening_value + purch_value
        total_qty_in   = opening_qty   + purch_qty
        wac = (total_cost_in / total_qty_in) if total_qty_in > 0 else 0.0

        closing_value  = closing_qty * wac
        sales_cost     = sales_qty   * wac  # COGS
        sr_cost        = sr_qty      * wac

        # ── Gross Profit ──────────────────────────────────────
        gross_profit    = sales_revenue - sales_cost
        gross_margin    = (
            (gross_profit / sales_revenue * 100)
            if sales_revenue > 0 else 0.0
        )

        records.append({
            "sku":                    sku,
            "item_name":              item_name,
            # Opening
            "opening_qty":            round(opening_qty,   4),
            "opening_value":          round(opening_value, 2),
            # Purchases IN
            "purchases_qty":          round(purch_qty,     4),
            "purchases_value":        round(purch_value,   2),
            # Purchase Returns OUT
            "purchase_returns_qty":   round(pr_qty,        4),
            "purchase_returns_value": round(pr_value,      2),
            # Sales OUT
            "sales_qty":              round(sales_qty,     4),
            "sales_revenue":          round(sales_revenue, 2),
            "sales_cost":             round(sales_cost,    2),
            # Sales Returns IN
            "sales_returns_qty":      round(sr_qty,        4),
            "sales_returns_value":    round(sr_value,      2),
            # Closing
            "closing_qty":            round(closing_qty,   4),
            "closing_value":          round(closing_value, 2),
            # Costing
            "weighted_avg_cost":      round(wac,           4),
            # Profitability
            "gross_profit":           round(gross_profit,  2),
            "gross_margin_pct":       round(gross_margin,  2),
        })

    df_result = pd.DataFrame(records)

    if not df_result.empty:
        df_result = df_result.sort_values("sku").reset_index(drop=True)

    return df_result


# ── Daily Movement (for detailed bin card view) ──────────────

def compute_daily_movements(
    db_path:   str,
    sku:       str,
    date_from: date,
    date_to:   date,
) -> pd.DataFrame:
    """
    Return day-by-day bin card movements for one SKU.
    Shows running balance after each transaction.
    """

    purch = load_table(db_path, "purchases")
    pr    = load_table(db_path, "purchase_returns")
    sales = load_table(db_path, "sales")
    sr    = load_table(db_path, "sales_returns")
    inv   = load_table(db_path, "inventory")

    sku_upper = sku.strip().upper()

    # ── Opening balance ──────────────────────────────────────
    opening_qty  = 0.0
    opening_cost = 0.0

    if not inv.empty:
        inv["_sku"] = resolve_sku(inv)
        row = inv[inv["_sku"] == sku_upper]
        if not row.empty:
            opening_qty  = float(resolve_col(row,
                ["opening_stock","opening_qty","qty","quantity","stock"]).sum())
            opening_cost = float(resolve_col(row,
                ["unit_cost","cost_price","purchase_price","cost"]).mean() or 0)

    movements = []

    # ── Add opening balance row ──────────────────────────────
    movements.append({
        "date":        pd.Timestamp(date_from),
        "type":        "Opening Balance",
        "reference":   "—",
        "party":       "—",
        "qty_in":      opening_qty,
        "qty_out":     0.0,
        "unit_cost":   opening_cost,
        "value_in":    opening_qty * opening_cost,
        "value_out":   0.0,
        "balance_qty": opening_qty,
        "balance_val": opening_qty * opening_cost,
    })

    # ── Helper to add rows ───────────────────────────────────
    def add_movements(df, txn_type, qty_col_in, qty_col_out,
                      party_col, ref_col, cost_cols):
        if df.empty:
            return
        df = normalise_dates(df.copy())
        df["_sku"] = resolve_sku(df)
        df = df[df["_sku"] == sku_upper]
        df = filter_by_period(df, date_from, date_to)
        if df.empty:
            return

        for _, row in df.iterrows():
            qty_in  = float(resolve_col(
                pd.DataFrame([row]), qty_col_in).sum()
            ) if qty_col_in else 0.0
            qty_out = float(resolve_col(
                pd.DataFrame([row]), qty_col_out).sum()
            ) if qty_col_out else 0.0
            cost    = float(resolve_col(
                pd.DataFrame([row]), cost_cols).mean() or 0)

            party = ""
            for pc in party_col:
                if pc in row.index and row[pc]:
                    party = str(row[pc])
                    break

            ref = ""
            for rc in ref_col:
                if rc in row.index and row[rc]:
                    ref = str(row[rc])
                    break

            movements.append({
                "date":        row.get("date", pd.NaT),
                "type":        txn_type,
                "reference":   ref,
                "party":       party,
                "qty_in":      round(qty_in,  4),
                "qty_out":     round(qty_out, 4),
                "unit_cost":   round(cost,    4),
                "value_in":    round(qty_in  * cost, 2),
                "value_out":   round(qty_out * cost, 2),
                "balance_qty": 0.0,  # computed below
                "balance_val": 0.0,
            })

    add_movements(
        purch,
        txn_type   = "Purchase",
        qty_col_in = ["quantity","qty","units"],
        qty_col_out= None,
        party_col  = ["supplier_name","supplier","vendor"],
        ref_col    = ["invoice_no","reference_number","ref"],
        cost_cols  = ["rate","unit_cost","unit_price","price"],
    )
    add_movements(
        pr,
        txn_type    = "Purchase Return",
        qty_col_in  = None,
        qty_col_out = ["quantity_returned","qty_returned","quantity","qty"],
        party_col   = ["supplier_name","supplier"],
        ref_col     = ["return_reference","original_invoice_no","ref"],
        cost_cols   = ["rate","unit_cost","unit_price"],
    )
    add_movements(
        sales,
        txn_type    = "Sale",
        qty_col_in  = None,
        qty_col_out = ["quantity","qty","units"],
        party_col   = ["customer_name","customer","client"],
        ref_col     = ["invoice_no","invoice_number","ref"],
        cost_cols   = ["rate","unit_price","selling_price"],
    )
    add_movements(
        sr,
        txn_type   = "Sales Return",
        qty_col_in = ["quantity_returned","qty_returned","quantity","qty"],
        qty_col_out= None,
        party_col  = ["customer_name","customer"],
        ref_col    = ["return_reference","original_invoice_no","ref"],
        cost_cols  = ["rate","unit_price","unit_cost"],
    )

    # ── Sort by date ─────────────────────────────────────────
    df_mov = pd.DataFrame(movements)
    df_mov["date"] = pd.to_datetime(df_mov["date"], errors="coerce")
    df_mov = df_mov.sort_values("date").reset_index(drop=True)

    # ── Compute running balance ───────────────────────────────
    bal_qty = 0.0
    bal_val = 0.0
    for idx, row in df_mov.iterrows():
        bal_qty += row["qty_in"]  - row["qty_out"]
        bal_val += row["value_in"] - row["value_out"]
        df_mov.at[idx, "balance_qty"] = round(bal_qty, 4)
        df_mov.at[idx, "balance_val"] = round(bal_val, 2)

    return df_mov


# ── Summary helpers ──────────────────────────────────────────

def get_bin_card_summary(df_bins: pd.DataFrame) -> dict:
    """Return aggregate summary from bin card DataFrame."""
    if df_bins.empty:
        return {}
    return {
        "total_skus":          len(df_bins),
        "total_opening_qty":   df_bins["opening_qty"].sum(),
        "total_purchases_qty": df_bins["purchases_qty"].sum(),
        "total_pr_qty":        df_bins["purchase_returns_qty"].sum(),
        "total_sales_qty":     df_bins["sales_qty"].sum(),
        "total_sr_qty":        df_bins["sales_returns_qty"].sum(),
        "total_closing_qty":   df_bins["closing_qty"].sum(),
        "total_closing_value": df_bins["closing_value"].sum(),
        "total_sales_revenue": df_bins["sales_revenue"].sum(),
        "total_gross_profit":  df_bins["gross_profit"].sum(),
        "avg_gross_margin":    df_bins["gross_margin_pct"].mean(),
        "low_stock_items":     len(df_bins[df_bins["closing_qty"] <= 0]),
    }


if __name__ == "__main__":
    # Quick test
    import sys

    DB = (sys.argv[1] if len(sys.argv) > 1
          else "data/reconciliation.db")

    if not os.path.exists(DB):
        print(f"DB not found: {DB}")
        sys.exit(1)

    print("=" * 60)
    print("BIN CARD ENGINE TEST")
    print("=" * 60)
    print(f"DB: {DB}")
    print()

    df = compute_bin_cards(
        db_path   = DB,
        date_from = date(2025, 5, 1),
        date_to   = date(2026, 5, 31),
    )

    if df.empty:
        print("No SKU data found - upload inventory/purchases/sales first")
    else:
        print(df.to_string())
        print()
        summary = get_bin_card_summary(df)
        print("SUMMARY:")
        for k, v in summary.items():
            print(f"  {k:<25} {v}")
