#!/usr/bin/env python3
"""
purge_database.py - Finteca AuditRep Purge Utility
Usage:
  python purge_database.py           # Purge all
  python purge_database.py --list    # List tables
  python purge_database.py --table NAME
  python purge_database.py --assign ID
  python purge_database.py --force   # Skip confirmation
"""
import sqlite3, os, sys, argparse
from datetime import datetime

DB_PATHS = [
    "data/reconciliation.db",
    "finteca.db",
    "/tmp/reconciliation.db",
]

def find_db():
    for p in DB_PATHS:
        if os.path.exists(p):
            return p
    return None

def get_size(path):
    b = os.path.getsize(path)
    return f"{b/1024:.1f} KB" if b < 1024**2 else f"{b/1024**2:.2f} MB"

def banner(db):
    print()
    print("=" * 60)
    print("    FINTECA AUDITREP - DATABASE PURGE UTILITY")
    print("=" * 60)
    print(f"    Database : {os.path.abspath(db)}")
    print(f"    Size     : {get_size(db)}")
    print(f"    Time     : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()

def get_counts(conn):
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in cur.fetchall()]
    counts = {}
    for t in tables:
        try:
            cur.execute(f"SELECT COUNT(*) FROM '{t}'")
            counts[t] = cur.fetchone()[0]
        except Exception:
            counts[t] = -1
    return counts

def print_stats(counts, title="Database Contents"):
    print(title)
    print("-" * 55)
    total = 0
    for t, c in counts.items():
        flag = ">> " if c > 0 else "   "
        print(f"  {flag}{t:<38} {c if c >= 0 else 'ERR':>8}")
        if c > 0:
            total += c
    print("-" * 55)
    print(f"  {'TOTAL ROWS':<38} {total:>8,}")
    print()
    return total

def ask(expected, force):
    if force:
        print("  --force: skipping confirmation.")
        return True
    ans = input(f"  Type '{expected}' to confirm: ").strip()
    return ans == expected

def do_purge(conn, tables):
    cur = conn.cursor()
    print("  Purging...")
    print("  " + "-" * 50)
    total = 0
    for t in tables:
        try:
            cur.execute(f"DELETE FROM '{t}'")
            n = cur.rowcount
            total += max(n, 0)
            try:
                cur.execute(
                    "DELETE FROM sqlite_sequence WHERE name=?", (t,)
                )
            except Exception:
                pass
            print(f"  OK  {t:<38} {n:>6,} rows deleted")
        except Exception as e:
            print(f"  ERR {t:<38} {e}")
    conn.commit()
    print("  " + "-" * 50)
    print(f"  {'TOTAL DELETED':<38} {total:>6,}")
    print()

def cmd_list(db):
    conn = sqlite3.connect(db)
    print_stats(get_counts(conn))
    conn.close()

def cmd_all(db, force):
    conn = sqlite3.connect(db)
    counts = get_counts(conn)
    total = print_stats(counts)
    if total == 0:
        print("Already empty.\n")
        conn.close()
        return
    print("  WARNING: Permanently deletes ALL data from ALL tables.")
    if not ask("PURGE ALL", force):
        print("\nCancelled.\n")
        conn.close()
        return
    do_purge(conn, list(counts.keys()))
    print("Verification:")
    print_stats(get_counts(conn))
    conn.close()
    print("=" * 60)
    print("  DONE:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("=" * 60)
    print()

def cmd_table(db, table, force):
    conn = sqlite3.connect(db)
    counts = get_counts(conn)
    if table not in counts:
        print(f"Table '{table}' not found.")
        print(f"Available: {', '.join(counts.keys())}")
        conn.close()
        return
    c = counts[table]
    print(f"  Table: {table}  Rows: {c:,}\n")
    if c == 0:
        print("Already empty.\n")
        conn.close()
        return
    if not ask("PURGE", force):
        print("\nCancelled.\n")
        conn.close()
        return
    do_purge(conn, [table])
    conn.close()

def cmd_assign(db, assign_id, force):
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    eligible = []
    print(f"  Assignment ID: {assign_id}\n")
    for t in tables:
        try:
            cur.execute(f"PRAGMA table_info('{t}')")
            cols = [c[1] for c in cur.fetchall()]
            if "assignment_id" in cols:
                cur.execute(
                    f"SELECT COUNT(*) FROM '{t}' WHERE assignment_id=?",
                    (assign_id,)
                )
                c = cur.fetchone()[0]
                eligible.append((t, c))
                print(f"  {'*' if c>0 else ' '}  {t:<38} {c:>6,} rows")
        except Exception as e:
            print(f"  ERR {t}: {e}")
    total = sum(c for _, c in eligible)
    print(f"\n  Total: {total:,} rows\n")
    if total == 0:
        print("No data for this assignment.\n")
        conn.close()
        return
    if not ask("PURGE", force):
        print("\nCancelled.\n")
        conn.close()
        return
    for t, c in eligible:
        if c > 0:
            cur.execute(
                f"DELETE FROM '{t}' WHERE assignment_id=?", (assign_id,)
            )
            print(f"  OK  {t:<38} {cur.rowcount:,} deleted")
        else:
            print(f"  --  {t:<38} skipped")
    conn.commit()
    conn.close()
    print(f"\nDone: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

def main():
    parser = argparse.ArgumentParser(
        description="Finteca AuditRep - Database Purge Utility",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Examples:
  python purge_database.py                  Purge all
  python purge_database.py --list           List tables
  python purge_database.py --table sales    Purge one table
  python purge_database.py --assign 1       Purge assignment 1
  python purge_database.py --force          Skip confirmation
  python purge_database.py --db mydb.db     Custom DB path
        """
    )
    parser.add_argument("--list",   action="store_true")
    parser.add_argument("--table",  type=str, metavar="NAME")
    parser.add_argument("--assign", type=int, metavar="ID")
    parser.add_argument("--force",  action="store_true")
    parser.add_argument("--db",     type=str, metavar="PATH")
    args = parser.parse_args()

    db = args.db or find_db()
    if not db:
        print("No database found.")
        print(f"Searched: {DB_PATHS}")
        sys.exit(1)

    banner(db)

    if args.list:
        cmd_list(db)
    elif args.table:
        cmd_table(db, args.table, args.force)
    elif args.assign:
        cmd_assign(db, args.assign, args.force)
    else:
        cmd_all(db, args.force)

if __name__ == "__main__":
    main()
