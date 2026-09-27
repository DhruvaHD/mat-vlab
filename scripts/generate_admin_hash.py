#!/usr/bin/env python3
"""
MAT-VLAB — Administrator Password Hash Generator
Generates a cryptographically secure Werkzeug password hash (scrypt) for use in
production environment variables (e.g., Render, Railway, Docker, or .env).

Usage:
  Interactive mode:
    python3 scripts/generate_admin_hash.py

  Direct argument mode:
    python3 scripts/generate_admin_hash.py <username> <password>
"""
import sys
import getpass
from werkzeug.security import generate_password_hash

def main():
    print("=" * 60)
    print("MAT-VLAB — ADMIN PASSWORD HASH GENERATOR")
    print("=" * 60)

    if len(sys.argv) >= 3:
        username = sys.argv[1].strip()
        password = sys.argv[2]
    else:
        username = input("Enter desired Admin Username [default: admin]: ").strip() or "admin"
        password = getpass.getpass("Enter desired Admin Password: ")
        if not password:
            print("[!] Error: Password cannot be empty.")
            sys.exit(1)
        confirm = getpass.getpass("Confirm Admin Password: ")
        if password != confirm:
            print("[!] Error: Passwords do not match.")
            sys.exit(1)

    if len(password) < 4:
        print("[!] Error: Password must be at least 4 characters long.")
        sys.exit(1)

    password_hash = generate_password_hash(password)

    print("\n[+] Secure Password Hash Generated Successfully!")
    print("=" * 60)
    print("RENDER ENVIRONMENT VARIABLES (Copy and paste into Render):")
    print("-" * 60)
    print(f"ADMIN_USERNAME={username}")
    print(f"ADMIN_PASSWORD_HASH={password_hash}")
    print("=" * 60)
    print("\nNote: By using ADMIN_PASSWORD_HASH, your plain-text password is")
    print("never exposed in Render environment logs, git commits, or shell history.")

if __name__ == '__main__':
    main()
