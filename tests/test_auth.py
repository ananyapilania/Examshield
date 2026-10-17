"""
ExamShield - Authentication & RBAC Test Suite
Validates:
1. Successful administrator login
2. Successful staff login
3. Incorrect password rejection
4. Unknown username or email rejection (identical error message, no leakage)
5. Inactive account rejection
6. Missing authentication credentials (401)
7. Invalid token format (401)
8. Expired token rejection (401)
9. Revoked token / logged-out session rejection (401)
10. Staff attempting administrator-only operations (403: /register-exam, /audit-logs, /users)
11. Staff accessing authorized operations (200: /verify-exam, /exams)
12. Administrator accessing all operations (200/201)
13. Attempts to modify roles without admin permission
14. Passwords stored strictly as Argon2id hashes (never plaintext)
15. Password hash never exposed in any API response
16. Initial administrator setup CLI tool functionality
"""

import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from fastapi.testclient import TestClient

import backend.audit
import backend.database
from backend.auth import (
    create_access_token,
    hash_password,
    verify_password,
)
from backend.database import (
    create_user,
    get_connection,
    get_user_by_id,
    initialize_database,
)
from backend.main import app
from backend.setup_admin import setup_administrator


class TestAuthenticationAndRBAC(unittest.TestCase):
    """Integration test suite for ExamShield Staff & Admin Authentication."""

    def setUp(self):
        """Set up an isolated temporary database and test client."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_db_path = str(Path(self.temp_dir.name) / "test_auth_examshield.db")

        # Direct modules to the isolated test database
        backend.database.DEFAULT_DB_PATH = self.test_db_path
        backend.audit.DEFAULT_DB_PATH = self.test_db_path
        initialize_database(self.test_db_path)

        self.client = TestClient(app)

        # Seed an Admin User
        self.admin_pwd = "AdminSuperSecret2026!"
        self.admin = create_user(
            user_id="USR-ADMIN-001",
            username="security_admin",
            email="admin@examshield.org",
            password_hash=hash_password(self.admin_pwd),
            role="ADMIN",
            is_active=True,
            db_path=self.test_db_path
        )

        # Seed a Staff User
        self.staff_pwd = "StaffOperationalPass2026!"
        self.staff = create_user(
            user_id="USR-STAFF-001",
            username="ops_officer",
            email="staff@examshield.org",
            password_hash=hash_password(self.staff_pwd),
            role="STAFF",
            is_active=True,
            db_path=self.test_db_path
        )

        # Seed an Inactive User
        self.inactive_pwd = "InactiveUserPass2026!"
        self.inactive_user = create_user(
            user_id="USR-INACTIVE-001",
            username="suspended_user",
            email="suspended@examshield.org",
            password_hash=hash_password(self.inactive_pwd),
            role="STAFF",
            is_active=False,
            db_path=self.test_db_path
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    # -------------------------------------------------------------------------
    # LOGIN TESTS
    # -------------------------------------------------------------------------

    def test_successful_admin_login(self):
        """Admin can log in with username or email and receive valid JWT bearer token."""
        # Login with username
        resp = self.client.post("/auth/login", json={
            "username_or_email": "security_admin",
            "password": self.admin_pwd
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["token_type"], "bearer")
        self.assertEqual(data["user"]["role"], "ADMIN")
        self.assertEqual(data["user"]["username"], "security_admin")
        self.assertNotIn("password", data["user"])
        self.assertNotIn("password_hash", data["user"])

        # Login with email
        resp_email = self.client.post("/auth/login", json={
            "username_or_email": "admin@examshield.org",
            "password": self.admin_pwd
        })
        self.assertEqual(resp_email.status_code, 200)
        self.assertEqual(resp_email.json()["user"]["role"], "ADMIN")

    def test_successful_staff_login(self):
        """Staff can log in and receive token with STAFF role."""
        resp = self.client.post("/auth/login", json={
            "username_or_email": "ops_officer",
            "password": self.staff_pwd
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["user"]["role"], "STAFF")
        self.assertEqual(data["user"]["username"], "ops_officer")
        self.assertNotIn("password_hash", data["user"])

    def test_incorrect_password(self):
        """Login with wrong password returns 401 Unauthorized."""
        resp = self.client.post("/auth/login", json={
            "username_or_email": "security_admin",
            "password": "WrongPassword123!"
        })
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json()["detail"], "Invalid username or password.")

    def test_unknown_username_or_email(self):
        """Login with non-existent account returns generic 401 without leaking user existence."""
        resp = self.client.post("/auth/login", json={
            "username_or_email": "unknown_account_xyz",
            "password": "AnyPassword123!"
        })
        self.assertEqual(resp.status_code, 401)
        # Verify message matches incorrect password response exactly to prevent account harvesting
        self.assertEqual(resp.json()["detail"], "Invalid username or password.")

    def test_inactive_account_login(self):
        """Inactive user login is rejected with 403 Forbidden."""
        resp = self.client.post("/auth/login", json={
            "username_or_email": "suspended_user",
            "password": self.inactive_pwd
        })
        self.assertEqual(resp.status_code, 403)
        self.assertIn("deactivated", resp.json()["detail"])

    # -------------------------------------------------------------------------
    # TOKEN & SESSION VALIDATION TESTS
    # -------------------------------------------------------------------------

    def test_missing_credentials(self):
        """Protected endpoint returns 401 when no token is provided."""
        resp = self.client.get("/auth/me")
        self.assertEqual(resp.status_code, 401)
        self.assertIn("credentials were not provided", resp.json()["detail"])

    def test_invalid_token(self):
        """Protected endpoint returns 401 for corrupted or malformed token."""
        resp = self.client.get(
            "/auth/me",
            headers={"Authorization": "Bearer malformed.invalid.token"}
        )
        self.assertEqual(resp.status_code, 401)
        self.assertIn("Invalid authentication token", resp.json()["detail"])

    def test_expired_token(self):
        """Protected endpoint returns 401 when token has expired."""
        expired_token, _, _ = create_access_token(
            self.admin,
            expires_delta=timedelta(seconds=-10)
        )
        resp = self.client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        self.assertEqual(resp.status_code, 401)
        self.assertIn("expired", resp.json()["detail"])

    def test_logout_and_token_revocation(self):
        """Logging out revokes token; subsequent requests with same token return 401."""
        login_resp = self.client.post("/auth/login", json={
            "username_or_email": "security_admin",
            "password": self.admin_pwd
        })
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Profile accessible before logout
        me_resp = self.client.get("/auth/me", headers=headers)
        self.assertEqual(me_resp.status_code, 200)

        # 2. Perform logout
        logout_resp = self.client.post("/auth/logout", headers=headers)
        self.assertEqual(logout_resp.status_code, 200)
        self.assertEqual(logout_resp.json()["status"], "LOGGED_OUT")

        # 3. Same token should now be rejected
        revoked_resp = self.client.get("/auth/me", headers=headers)
        self.assertEqual(revoked_resp.status_code, 401)
        self.assertIn("logged out or invalidated", revoked_resp.json()["detail"])

    # -------------------------------------------------------------------------
    # ROLE-BASED ACCESS CONTROL (RBAC) TESTS
    # -------------------------------------------------------------------------

    def test_staff_cannot_perform_admin_operations(self):
        """Staff receives 403 Forbidden when attempting administrator-only endpoints."""
        staff_token, _, _ = create_access_token(self.staff)
        staff_headers = {"Authorization": f"Bearer {staff_token}"}

        # 1. Staff cannot view audit logs
        audit_resp = self.client.get("/audit-logs", headers=staff_headers)
        self.assertEqual(audit_resp.status_code, 403)
        self.assertIn("Administrator privileges required", audit_resp.json()["detail"])

        # 2. Staff cannot register exam papers
        reg_resp = self.client.post(
            "/register-exam",
            data={
                "exam_id": "STAFF-FORBIDDEN-01",
                "exam_name": "Prohibited Upload",
                "subject": "CS",
                "academic_year": "2025-2026",
                "paper_version": "Set-A"
            },
            files={"file": ("test.bin", b"forbidden content", "application/octet-stream")},
            headers=staff_headers
        )
        self.assertEqual(reg_resp.status_code, 403)

        # 3. Staff cannot list users
        users_resp = self.client.get("/users", headers=staff_headers)
        self.assertEqual(users_resp.status_code, 403)

        # 4. Staff cannot modify roles
        role_resp = self.client.patch(
            f"/users/{self.staff.user_id}/role",
            json={"role": "ADMIN"},
            headers=staff_headers
        )
        self.assertEqual(role_resp.status_code, 403)

    def test_staff_can_perform_authorized_operations(self):
        """Staff can list exams and verify exam candidate papers."""
        # 1. Admin registers an exam first
        admin_token, _, _ = create_access_token(self.admin)
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        reg_resp = self.client.post(
            "/register-exam",
            data={
                "exam_id": "EXAM-STAFF-ACCESS-01",
                "exam_name": "Staff Verification Test",
                "subject": "Cybersecurity",
                "academic_year": "2025-2026",
                "paper_version": "v1.0"
            },
            files={"file": ("staff_test.bin", b"Official Baseline Content", "application/octet-stream")},
            headers=admin_headers
        )
        self.assertEqual(reg_resp.status_code, 201)

        # 2. Staff lists exams (authorized)
        staff_token, _, _ = create_access_token(self.staff)
        staff_headers = {"Authorization": f"Bearer {staff_token}"}

        list_resp = self.client.get("/exams", headers=staff_headers)
        self.assertEqual(list_resp.status_code, 200)
        self.assertTrue(any(e["exam_id"] == "EXAM-STAFF-ACCESS-01" for e in list_resp.json()))

        # 3. Staff verifies candidate paper (authorized)
        verify_resp = self.client.post(
            "/verify-exam/EXAM-STAFF-ACCESS-01",
            files={"file": ("candidate.bin", b"Official Baseline Content", "application/octet-stream")},
            headers=staff_headers
        )
        self.assertEqual(verify_resp.status_code, 200)
        self.assertEqual(verify_resp.json()["status"], "VERIFIED")

    def test_admin_can_access_all_operations(self):
        """Administrator has access to registration, verification, audit logs, and user management."""
        admin_token, _, _ = create_access_token(self.admin)
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # List users
        users_resp = self.client.get("/users", headers=admin_headers)
        self.assertEqual(users_resp.status_code, 200)

        # View audit logs
        audit_resp = self.client.get("/audit-logs", headers=admin_headers)
        self.assertEqual(audit_resp.status_code, 200)

    def test_admin_user_management(self):
        """Admin can create users, deactivate accounts, and update roles."""
        admin_token, _, _ = create_access_token(self.admin)
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 1. Create a new staff user
        create_resp = self.client.post("/users", json={
            "username": "new_proctor",
            "email": "proctor@examshield.org",
            "password": "ProctorPass1234!",
            "role": "STAFF",
            "is_active": True
        }, headers=admin_headers)
        self.assertEqual(create_resp.status_code, 201)
        new_user = create_resp.json()
        new_id = new_user["user_id"]
        self.assertEqual(new_user["username"], "new_proctor")
        self.assertNotIn("password_hash", new_user)

        # 2. Deactivate the user
        deactivate_resp = self.client.patch(
            f"/users/{new_id}/status",
            json={"is_active": False},
            headers=admin_headers
        )
        self.assertEqual(deactivate_resp.status_code, 200)
        self.assertFalse(deactivate_resp.json()["is_active"])

        # 3. Reactivate and promote to ADMIN
        role_resp = self.client.patch(
            f"/users/{new_id}/role",
            json={"role": "ADMIN"},
            headers=admin_headers
        )
        self.assertEqual(role_resp.status_code, 200)
        self.assertEqual(role_resp.json()["role"], "ADMIN")

    def test_passwords_stored_as_argon2_hashes(self):
        """Verify that passwords are never stored in plaintext and use Argon2id format."""
        with get_connection(self.test_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT username, password_hash FROM users WHERE username = ?;", ("security_admin",))
            row = cursor.fetchone()
            self.assertIsNotNone(row)
            self.assertNotEqual(row["password_hash"], self.admin_pwd)
            # Argon2id format starts with $argon2id$
            self.assertTrue(row["password_hash"].startswith("$argon2id$"))
            self.assertTrue(verify_password(self.admin_pwd, row["password_hash"]))

    def test_setup_admin_script(self):
        """Verify initial administrator CLI setup function."""
        cli_admin_username = "initial_root_admin"
        cli_admin_email = "root@examshield.gov"
        cli_admin_pass = "RootMasterPass9988!"

        # Initial creation succeeds
        success = setup_administrator(
            username=cli_admin_username,
            email=cli_admin_email,
            password=cli_admin_pass,
            db_path=self.test_db_path
        )
        self.assertTrue(success)

        # Duplicate attempt fails securely
        duplicate_attempt = setup_administrator(
            username=cli_admin_username,
            email=cli_admin_email,
            password=cli_admin_pass,
            db_path=self.test_db_path
        )
        self.assertFalse(duplicate_attempt)


if __name__ == "__main__":
    unittest.main()
