#!/usr/bin/env python3
"""
MAT-VLAB — Direct Admin Password Reset Utility
Directly updates or creates the admin credentials in the active database
(SQLite materials.db or PostgreSQL via DATABASE_URL).

Usage:
  python3 scripts/reset_admin_password.py <username> <new_password>
"""
import sys
import os

# Ensure project root is in sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SCRATCH_LIB = os.path.abspath(os.path.join(BASE_DIR, '..', 'lib'))
if os.path.exists(SCRATCH_LIB) and SCRATCH_LIB not in sys.path:
    sys.path.insert(0, SCRATCH_LIB)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from werkzeug.security import generate_password_hash
from models.database import get_db_connection, is_postgres, init_db

def reset_admin(username, password):
    if not username or not username.strip():
        print("[!] Error: Username cannot be empty.")
        return False
    if not password or len(password) < 4:
        print("[!] Error: Password must be at least 4 characters long.")
        return False

    username = username.strip()
    password_hash = generate_password_hash(password)

    # Initialize tables if not already present
    init_db()

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT id FROM admin_credentials ORDER BY id DESC LIMIT 1')
    existing = cursor.fetchone()

    if existing:
        cursor.execute('''
        UPDATE admin_credentials 
        SET username = ?, password_hash = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        ''', (username, password_hash, existing['id']))
        action = "updated"
    else:
        cursor.execute('''
        INSERT INTO admin_credentials (username, password_hash)
        VALUES (?, ?)
        ''', (username, password_hash))
        action = "created"

    conn.commit()
    conn.close()

    db_type = "PostgreSQL" if is_postgres() else "SQLite"
    print(f"[+] Administrator credentials successfully {action} in {db_type} database!")
    print(f"    Username: {username}")
    print(f"    Password: [PROTECTED]")
    print(f"    Login URL: /portal-admin/login or /admin/login")
    return True

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python3 scripts/reset_admin_password.py <username> <new_password>")
        sys.exit(1)
    
    success = reset_admin(sys.argv[1], sys.argv[2])
    sys.exit(0 if success else 1)
