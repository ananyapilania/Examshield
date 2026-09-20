"""
API Integration tests for ExamShield FastAPI Application (backend/main.py).
Tests:
1. Register valid exam (POST /register-exam)
2. Register duplicate exam (POST /register-exam -> 400)
3. Verify original unchanged paper (POST /verify-exam/{id} -> VERIFIED)
4. Verify modified/tampered paper (POST /verify-exam/{id} -> TAMPER_DETECTED)
5. Verify unknown exam (POST /verify-exam/{id} -> 404)
6. Missing file on registration (POST /register-exam -> 400/422)
7. List all exams (GET /exams)
8. List audit logs (GET /audit-logs)
9. Health check (GET /)
"""

import io
import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

import backend.database
import backend.audit
from backend.main import app
from backend.database import initialize_database


class TestFastAPIIntegration(unittest.TestCase):
    """Test suite for FastAPI endpoints and complete security workflow."""

    def setUp(self):
        """Set up an isolated temporary SQLite database and TestClient."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_db_path = str(Path(self.temp_dir.name) / "test_api_examshield.db")

        # Point database and audit modules to the isolated test database
        backend.database.DEFAULT_DB_PATH = self.test_db_path
        backend.audit.DEFAULT_DB_PATH = self.test_db_path
        initialize_database(self.test_db_path)

        self.client = TestClient(app)

        # Synthetic paper sample contents
        self.original_paper_bytes = b"--- SYNTHETIC EXAM PAPER: CS101 DATA STRUCTURES ---\nQ1. Define Binary Trees."
        self.tampered_paper_bytes = b"--- SYNTHETIC EXAM PAPER: CS101 DATA STRUCTURES ---\nQ1. Define Leaked Answers."

    def tearDown(self):
        """Clean up temporary test directory."""
        self.temp_dir.cleanup()

    def test_health_check(self):
        """Test GET / returns 200 with active status."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "HEALTHY")

    def test_register_valid_exam(self):
        """1. Register valid exam returns 201 Created and metadata with SHA-256 hash."""
        response = self.client.post(
            "/register-exam",
            data={
                "exam_id": "EXAM-2026-CS101",
                "exam_name": "Data Structures & Algorithms",
                "subject": "Computer Science",
                "academic_year": "2025-2026",
                "paper_version": "Set-A",
            },
            files={
                "file": ("cs101_original.bin", io.BytesIO(self.original_paper_bytes), "application/octet-stream")
            }
        )

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["exam_id"], "EXAM-2026-CS101")
        self.assertEqual(data["exam_name"], "Data Structures & Algorithms")
        self.assertEqual(data["subject"], "Computer Science")
        self.assertEqual(data["academic_year"], "2025-2026")
        self.assertEqual(data["paper_version"], "Set-A")
        self.assertEqual(data["status"], "REGISTERED")
        self.assertEqual(len(data["file_hash"]), 64)
        self.assertIn("timestamp", data)

    def test_register_duplicate_exam(self):
        """2. Register duplicate exam ID returns 400 Bad Request."""
        # First registration
        self.client.post(
            "/register-exam",
            data={
                "exam_id": "EXAM-DUP-01",
                "exam_name": "Operating Systems",
                "subject": "Computer Science",
                "academic_year": "2025-2026",
                "paper_version": "Set-A",
            },
            files={
                "file": ("os_exam.bin", io.BytesIO(self.original_paper_bytes), "application/octet-stream")
            }
        )

        # Duplicate registration
        response = self.client.post(
            "/register-exam",
            data={
                "exam_id": "EXAM-DUP-01",
                "exam_name": "Operating Systems Duplicate",
                "subject": "Computer Science",
                "academic_year": "2025-2026",
                "paper_version": "Set-A",
            },
            files={
                "file": ("os_exam.bin", io.BytesIO(self.original_paper_bytes), "application/octet-stream")
            }
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("already registered", response.json()["detail"])

    def test_verify_original_unchanged_pdf(self):
        """3. Verify original unchanged candidate file returns status VERIFIED."""
        # 1. Register exam
        reg_response = self.client.post(
            "/register-exam",
            data={
                "exam_id": "EXAM-VERIFY-01",
                "exam_name": "Database Systems",
                "subject": "Computer Science",
                "academic_year": "2025-2026",
                "paper_version": "Set-A",
            },
            files={
                "file": ("db_original.bin", io.BytesIO(self.original_paper_bytes), "application/octet-stream")
            }
        )
        self.assertEqual(reg_response.status_code, 201)
        original_hash = reg_response.json()["file_hash"]

        # 2. Verify with identical content
        verify_response = self.client.post(
            "/verify-exam/EXAM-VERIFY-01",
            files={
                "file": ("db_candidate.bin", io.BytesIO(self.original_paper_bytes), "application/octet-stream")
            }
        )

        self.assertEqual(verify_response.status_code, 200)
        data = verify_response.json()
        self.assertEqual(data["exam_id"], "EXAM-VERIFY-01")
        self.assertEqual(data["status"], "VERIFIED")
        self.assertEqual(data["registered_hash"], original_hash)
        self.assertEqual(data["uploaded_hash"], original_hash)

    def test_verify_modified_pdf(self):
        """4. Verify tampered candidate file returns status TAMPER_DETECTED."""
        # 1. Register exam
        self.client.post(
            "/register-exam",
            data={
                "exam_id": "EXAM-TAMPER-01",
                "exam_name": "Computer Networks",
                "subject": "Computer Science",
                "academic_year": "2025-2026",
                "paper_version": "Set-A",
            },
            files={
                "file": ("cn_original.bin", io.BytesIO(self.original_paper_bytes), "application/octet-stream")
            }
        )

        # 2. Verify with tampered content
        verify_response = self.client.post(
            "/verify-exam/EXAM-TAMPER-01",
            files={
                "file": ("cn_tampered.bin", io.BytesIO(self.tampered_paper_bytes), "application/octet-stream")
            }
        )

        self.assertEqual(verify_response.status_code, 200)
        data = verify_response.json()
        self.assertEqual(data["exam_id"], "EXAM-TAMPER-01")
        self.assertEqual(data["status"], "TAMPER_DETECTED")
        self.assertNotEqual(data["registered_hash"], data["uploaded_hash"])

    def test_verify_unknown_exam(self):
        """5. Verify nonexistent exam ID returns 404 Not Found."""
        response = self.client.post(
            "/verify-exam/NONEXISTENT-EXAM-ID",
            files={
                "file": ("dummy.bin", io.BytesIO(self.original_paper_bytes), "application/octet-stream")
            }
        )

        self.assertEqual(response.status_code, 404)
        self.assertIn("not found", response.json()["detail"])

    def test_missing_pdf_on_registration(self):
        """6. Missing file upload returns 422 Unprocessable Entity."""
        response = self.client.post(
            "/register-exam",
            data={
                "exam_id": "EXAM-MISSING-FILE",
                "exam_name": "Software Engineering",
                "subject": "Computer Science",
                "academic_year": "2025-2026",
                "paper_version": "Set-A",
            }
        )

        self.assertEqual(response.status_code, 422)

    def test_get_exams(self):
        """7. GET /exams returns list of all registered exams."""
        # Register 2 exams
        self.client.post(
            "/register-exam",
            data={
                "exam_id": "EXAM-LIST-1",
                "exam_name": "Mathematics I",
                "subject": "Mathematics",
                "academic_year": "2025-2026",
                "paper_version": "v1.0",
            },
            files={"file": ("math1.bin", io.BytesIO(b"Math Paper 1"), "application/octet-stream")}
        )
        self.client.post(
            "/register-exam",
            data={
                "exam_id": "EXAM-LIST-2",
                "exam_name": "Physics I",
                "subject": "Physics",
                "academic_year": "2025-2026",
                "paper_version": "v1.0",
            },
            files={"file": ("phys1.bin", io.BytesIO(b"Physics Paper 1"), "application/octet-stream")}
        )

        response = self.client.get("/exams")
        self.assertEqual(response.status_code, 200)
        exams = response.json()
        self.assertEqual(len(exams), 2)
        exam_ids = [e["exam_id"] for e in exams]
        self.assertIn("EXAM-LIST-1", exam_ids)
        self.assertIn("EXAM-LIST-2", exam_ids)

    def test_get_audit_logs(self):
        """8. GET /audit-logs returns chronological audit log records."""
        # Trigger an upload event
        self.client.post(
            "/register-exam",
            data={
                "exam_id": "EXAM-AUDIT-1",
                "exam_name": "Cyber Security",
                "subject": "Computer Science",
                "academic_year": "2025-2026",
                "paper_version": "Set-A",
            },
            files={"file": ("sec.bin", io.BytesIO(b"Cyber Sec Paper"), "application/octet-stream")}
        )

        # Trigger a verification event
        self.client.post(
            "/verify-exam/EXAM-AUDIT-1",
            files={"file": ("sec.bin", io.BytesIO(b"Cyber Sec Paper"), "application/octet-stream")}
        )

        # Retrieve all logs
        response = self.client.get("/audit-logs")
        self.assertEqual(response.status_code, 200)
        logs = response.json()
        self.assertGreaterEqual(len(logs), 2)

        # Retrieve filtered logs by exam_id
        filtered_response = self.client.get("/audit-logs?exam_id=EXAM-AUDIT-1")
        self.assertEqual(filtered_response.status_code, 200)
        filtered_logs = filtered_response.json()
        self.assertEqual(len(filtered_logs), 2)
        actions = [log["action"] for log in filtered_logs]
        self.assertIn("PAPER_REGISTERED", actions)
        self.assertIn("PAPER_VERIFIED", actions)


if __name__ == "__main__":
    unittest.main()
