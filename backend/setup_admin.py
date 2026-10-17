"""
ExamShield - Initial Administrator Setup Script
Provides a secure CLI procedure to initialize or create administrator accounts.

Usage:
    python -m backend.setup_admin --username <admin_username> --email <admin_email> [--password <password>]

Environment variables fallback:
    EXAMSHIELD_ADMIN_USERNAME
    EXAMSHIELD_ADMIN_EMAIL
    EXAMSHIELD_ADMIN_PASSWORD
"""

import argparse
import getpass
import os
import sys
import uuid

import backend.database
import backend.audit
from backend.auth import hash_password
from backend.database import (
    create_user,
    get_user_by_username_or_email,
    initialize_database,
)


def setup_administrator(
    username: str,
    email: str,
    password: str,
    db_path: str = backend.database.DEFAULT_DB_PATH
) -> bool:
    """
    Initialize an administrator account with Argon2 password hashing.

    Args:
        username (str): Admin username.
        email (str): Admin email.
        password (str): Plaintext admin password (will be Argon2-hashed immediately).
        db_path (str): Database file path.

    Returns:
        bool: True on success, False otherwise.
    """
    clean_username = username.strip()
    clean_email = email.strip().lower()

    if not clean_username or len(clean_username) < 3:
        print("[ERROR] Username must be at least 3 characters long.", file=sys.stderr)
        return False

    if not clean_email or "@" not in clean_email:
        print("[ERROR] A valid email address is required.", file=sys.stderr)
        return False

    if not password or len(password) < 8:
        print("[ERROR] Password must be at least 8 characters long.", file=sys.stderr)
        return False

    # Ensure database tables exist
    initialize_database(db_path)

    # Prevent duplicate administrator creation
    existing_user = get_user_by_username_or_email(clean_username, db_path=db_path)
    if not existing_user:
        existing_user = get_user_by_username_or_email(clean_email, db_path=db_path)

    if existing_user:
        print(f"[ERROR] User with username '{clean_username}' or email '{clean_email}' already exists.", file=sys.stderr)
        print(f"        Existing user ID: {existing_user.user_id}, Role: {existing_user.role}", file=sys.stderr)
        return False

    # Hash password securely with Argon2id
    password_hash = hash_password(password)
    user_id = f"USR-{uuid.uuid4().hex[:12].upper()}"

    created_user = create_user(
        user_id=user_id,
        username=clean_username,
        email=clean_email,
        password_hash=password_hash,
        role="ADMIN",
        is_active=True,
        db_path=db_path
    )

    # Record security audit event
    backend.audit.log_audit_event(
        exam_id="AUTH",
        action=backend.audit.ACTION_USER_CREATED,
        result=backend.audit.RESULT_SUCCESS,
        details=f"Initial administrator '{created_user.username}' ({created_user.email}) registered with role ADMIN.",
        db_path=db_path
    )

    print("==================================================")
    print(" ExamShield Administrator Initialized Successfully")
    print("==================================================")
    print(f" User ID   : {created_user.user_id}")
    print(f" Username  : {created_user.username}")
    print(f" Email     : {created_user.email}")
    print(f" Role      : {created_user.role}")
    print(f" Status    : ACTIVE")
    print(f" Hashing   : Argon2id (salt generated automatically)")
    print("==================================================")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="ExamShield Secure Administrator Initialization CLI"
    )
    parser.add_argument("--username", help="Admin username")
    parser.add_argument("--email", help="Admin email address")
    parser.add_argument("--password", help="Admin password (leave blank to prompt securely)")
    parser.add_argument("--db", default=backend.database.DEFAULT_DB_PATH, help="Path to SQLite DB")

    args = parser.parse_args()

    # Determine username
    username = args.username or os.environ.get("EXAMSHIELD_ADMIN_USERNAME")
    if not username:
        username = input("Enter Admin Username: ").strip()

    # Determine email
    email = args.email or os.environ.get("EXAMSHIELD_ADMIN_EMAIL")
    if not email:
        email = input("Enter Admin Email: ").strip()

    # Determine password
    password = args.password or os.environ.get("EXAMSHIELD_ADMIN_PASSWORD")
    if not password:
        password = getpass.getpass("Enter Admin Password (min 8 characters): ")
        confirm_pwd = getpass.getpass("Confirm Admin Password: ")
        if password != confirm_pwd:
            print("[ERROR] Passwords do not match.", file=sys.stderr)
            sys.exit(1)

    success = setup_administrator(
        username=username,
        email=email,
        password=password,
        db_path=args.db
    )

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
