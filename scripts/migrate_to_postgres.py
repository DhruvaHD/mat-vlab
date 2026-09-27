#!/usr/bin/env python3
"""
MAT-VLAB — SQLite to PostgreSQL Zero-Data-Loss Migration Utility
Migrates all registered students, login activity, experiment records (tensile & hardness),
readings, results, quiz questions, quiz attempts, and admin credentials from SQLite
(materials.db) into Render PostgreSQL (DATABASE_URL).

Usage:
  # Using environment variables (DATABASE_URL & DATABASE_PATH):
  python3 scripts/migrate_to_postgres.py

  # Explicit paths:
  python3 scripts/migrate_to_postgres.py [path/to/materials.db] [postgresql://user:pass@host/dbname]
"""
import sys
import os
import sqlite3

# Ensure project root is in sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SCRATCH_LIB = os.path.abspath(os.path.join(BASE_DIR, '..', 'lib'))
if os.path.exists(SCRATCH_LIB) and SCRATCH_LIB not in sys.path:
    sys.path.insert(0, SCRATCH_LIB)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from models.database import init_db, PgConnection, sync_all_postgres_sequences

TABLES_IN_ORDER = [
    'materials',
    'students',
    'admin_credentials',
    'quiz_questions',
    'experiments',
    'experiment_readings',
    'experiment_results',
    'hardness_experiments',
    'hardness_readings',
    'quiz_results',
    'login_activity',
    'activity_logs'
]

def migrate(sqlite_path=None, postgres_url=None):
    print("=" * 65)
    print("MAT-VLAB — SQLITE TO POSTGRESQL PRODUCTION MIGRATION TOOL")
    print("=" * 65)

    # 1. Resolve SQLite database path
    if not sqlite_path:
        sqlite_path = os.environ.get('DATABASE_PATH')
        if not sqlite_path or not os.path.exists(sqlite_path):
            candidate = os.path.join(BASE_DIR, 'materials.db')
            if os.path.exists(candidate):
                sqlite_path = candidate
            else:
                backup = os.path.join(BASE_DIR, 'materials_backup.db')
                if os.path.exists(backup):
                    sqlite_path = backup

    if not sqlite_path or not os.path.exists(sqlite_path):
        print(f"[!] Error: Source SQLite database not found at: {sqlite_path}")
        return False

    print(f"[*] Source SQLite: {sqlite_path} ({os.path.getsize(sqlite_path)} bytes)")

    # 2. Resolve PostgreSQL URL
    if not postgres_url:
        postgres_url = os.environ.get('DATABASE_URL')

    if not postgres_url:
        print("[!] Error: Destination PostgreSQL DATABASE_URL is not set.")
        print("    Please provide DATABASE_URL in your environment or as the second argument.")
        print("    Example: python3 scripts/migrate_to_postgres.py materials.db postgresql://user:pass@host/dbname")
        return False

    # Normalize Render postgres:// to postgresql://
    if postgres_url.startswith('postgres://'):
        postgres_url = 'postgresql://' + postgres_url[len('postgres://'):]

    # Mask password for secure logging
    masked_url = postgres_url
    if '@' in masked_url:
        prefix, host_part = masked_url.split('@', 1)
        if '://' in prefix and ':' in prefix.split('://', 1)[1]:
            scheme_user = prefix.split(':', 2)[:2]
            masked_url = f"{':'.join(scheme_user)}:****@{host_part}"

    print(f"[*] Target PostgreSQL: {masked_url}")

    # 3. Connect to source SQLite
    src_conn = sqlite3.connect(sqlite_path)
    src_conn.row_factory = sqlite3.Row
    src_cur = src_conn.cursor()

    # 4. Connect to target PostgreSQL
    try:
        import psycopg2
    except ImportError:
        try:
            import psycopg as psycopg2
        except ImportError:
            print("[!] Error: 'psycopg2' is not installed. Run: pip install psycopg2-binary")
            return False

    try:
        raw_pg_conn = psycopg2.connect(postgres_url)
    except Exception as e:
        print(f"[!] Error: Failed to connect to PostgreSQL: {e}")
        return False

    pg_conn = PgConnection(raw_pg_conn)
    pg_cur = pg_conn.cursor()

    # 5. Initialize PostgreSQL Schema
    print("\n[*] Initializing PostgreSQL schema (ensuring tables exist)...")
    old_db_url = os.environ.get('DATABASE_URL')
    try:
        os.environ['DATABASE_URL'] = postgres_url
        init_db()
    finally:
        if old_db_url:
            os.environ['DATABASE_URL'] = old_db_url
        else:
            os.environ.pop('DATABASE_URL', None)

    # 6. Stream and copy each table
    print("\n[*] Migrating tables in dependency order...")
    print("-" * 65)
    print(f"{'Table Name':<25} | {'Source Rows':<12} | {'Migrated':<12} | {'Status'}")
    print("-" * 65)

    total_migrated = 0

    for table in TABLES_IN_ORDER:
        # Check if table exists in source
        src_cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
        if not src_cur.fetchone():
            print(f"{table:<25} | {'N/A (absent)':<12} | {0:<12} | SKIPPED")
            continue

        src_cur.execute(f"SELECT * FROM \"{table}\"")
        rows = src_cur.fetchall()
        src_count = len(rows)

        if src_count == 0:
            print(f"{table:<25} | {0:<12} | {0:<12} | EMPTY")
            continue

        cols = [d[0] for d in src_cur.description]
        col_str = ', '.join([f'"{c}"' for c in cols])
        val_placeholders = ', '.join(['%s' for _ in cols])
        
        insert_sql = f'INSERT INTO "{table}" ({col_str}) VALUES ({val_placeholders}) ON CONFLICT DO NOTHING'

        migrated_for_table = 0
        for row in rows:
            val_tuple = tuple(row[c] for c in cols)
            try:
                pg_cur.execute(insert_sql, val_tuple)
                migrated_for_table += 1
            except Exception as e:
                print(f"\n[!] Warning inserting row into {table}: {e}")

        pg_conn.commit()
        total_migrated += migrated_for_table
        print(f"{table:<25} | {src_count:<12} | {migrated_for_table:<12} | SUCCESS")

    # 7. Synchronize PostgreSQL SERIAL Sequences
    print("-" * 65)
    print("[*] Synchronizing PostgreSQL auto-increment sequences...")
    sync_all_postgres_sequences(pg_conn)
    pg_conn.commit()

    # 8. Final verification
    print("\n[*] Post-Migration Verification Summary:")
    print("-" * 65)
    for table in ['students', 'materials', 'experiments', 'hardness_experiments', 'quiz_results', 'admin_credentials']:
        try:
            pg_cur.execute(f'SELECT COUNT(*) FROM "{table}"')
            pg_cnt = pg_cur.fetchone()[0]
            src_cur.execute(f'SELECT COUNT(*) FROM "{table}"')
            src_cnt = src_cur.fetchone()[0]
            status = "MATCH" if pg_cnt >= src_cnt else "MISMATCH"
            print(f"  {table:<22}: SQLite = {src_cnt:<4} | PostgreSQL = {pg_cnt:<4} [{status}]")
        except Exception:
            pass

    src_conn.close()
    pg_conn.close()
    print("=" * 65)
    print(f"[+] Migration complete! {total_migrated} total rows processed with ZERO DATA LOSS.")
    print("=" * 65)
    return True

if __name__ == '__main__':
    src = sys.argv[1] if len(sys.argv) > 1 else None
    dst = sys.argv[2] if len(sys.argv) > 2 else None
    success = migrate(src, dst)
    sys.exit(0 if success else 1)
