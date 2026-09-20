"""
Unit tests for SQLite Database Layer and Audit Logging (backend/database.py & backend/audit.py).
Tests:
1. Database initializes correctly
2. Exam can be registered
3. Exam can be retrieved
4. Exam metadata is stored correctly
5. Exam status can be updated
6. Listing all exams
7. Audit log recording and retrieval
8. Duplicate Exam ID constraint handling
"""

import sqlite3
import tempfile
import unittest
from pathlib import Path

from backend.database import (
    initialize_database,
    register_exam,
    get_exam,
    get_all_exams,
    update_exam_status,
    get_connection
)
from backend.audit import (
    log_audit_event,
    get_audit_logs,
    ACTION_PAPER_REGISTERED,
    ACTION_PAPER_VERIFIED,
    ACTION_HASH_MISMATCH,
    RESULT_SUCCESS,
    RESULT_FLAGGED
)
from backend.models import ExamRecord, AuditEvent


class TestDatabaseAndAudit(unittest.TestCase):
    """Test suite for SQLite persistence and audit logging operations."""

    def setUp(self):
        """Create a temporary SQLite database for test isolation."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_examshield.db"
        initialize_database(self.db_path)

    def tearDown(self):
        """Clean up temporary test database."""
        self.temp_dir.cleanup()

    def test_database_initializes_correctly(self):
        """1. Database initializes correctly with required tables."""
        self.assertTrue(self.db_path.exists())

        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            # Check exams table exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='exams';"
            )
            self.assertIsNotNone(cursor.fetchone())

            # Check audit_logs table exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='audit_logs';"
            )
            self.assertIsNotNone(cursor.fetchone())

    def test_register_and_get_exam(self):
        """2 & 3. Exam can be registered and retrieved accurately."""
        sample_hash = "a" * 64
        record = register_exam(
            exam_id="EXAM-2026-CS101",
            exam_name="Data Structures & Algorithms",
            subject="Computer Science",
            academic_year="2025-2026",
            paper_version="Set-A",
            file_hash=sample_hash,
            status="REGISTERED",
            db_path=self.db_path
        )

        self.assertIsInstance(record, ExamRecord)
        self.assertEqual(record.exam_id, "EXAM-2026-CS101")
        self.assertEqual(record.file_hash, sample_hash)

        # Retrieve exam by ID
        fetched = get_exam("EXAM-2026-CS101", db_path=self.db_path)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.exam_id, "EXAM-2026-CS101")
        self.assertEqual(fetched.exam_name, "Data Structures & Algorithms")
        self.assertEqual(fetched.subject, "Computer Science")
        self.assertEqual(fetched.academic_year, "2025-2026")
        self.assertEqual(fetched.paper_version, "Set-A")
        self.assertEqual(fetched.file_hash, sample_hash)
        self.assertEqual(fetched.status, "REGISTERED")

    def test_exam_metadata_stored_correctly(self):
        """4. Exam metadata is stored with valid timestamp and fields."""
        custom_time = "2026-09-20T12:00:00+00:00"
        register_exam(
            exam_id="EXAM-2026-MATH201",
            exam_name="Discrete Mathematics",
            subject="Mathematics",
            academic_year="2025-2026",
            paper_version="v1.0",
            file_hash="b" * 64,
            status="REGISTERED",
            created_at=custom_time,
            db_path=self.db_path
        )

        fetched = get_exam("EXAM-2026-MATH201", db_path=self.db_path)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.created_at, custom_time)
        self.assertEqual(fetched.to_dict()["subject"], "Mathematics")

    def test_update_exam_status(self):
        """5. Exam status can be updated from REGISTERED to VERIFIED or FLAGGED."""
        register_exam(
            exam_id="EXAM-2026-PHY101",
            exam_name="Engineering Physics",
            subject="Physics",
            academic_year="2025-2026",
            paper_version="Set-B",
            file_hash="c" * 64,
            db_path=self.db_path
        )

        # Update status
        updated = update_exam_status("EXAM-2026-PHY101", "VERIFIED", db_path=self.db_path)
        self.assertTrue(updated)

        fetched = get_exam("EXAM-2026-PHY101", db_path=self.db_path)
        self.assertEqual(fetched.status, "VERIFIED")

        # Update nonexistent exam returns False
        self.assertFalse(update_exam_status("NON_EXISTENT_ID", "VERIFIED", db_path=self.db_path))

    def test_get_all_exams(self):
        """6. Retrieve all registered exams in correct order."""
        register_exam("EXAM-1", "Exam 1", "Sub1", "2026", "v1", "1" * 64, db_path=self.db_path)
        register_exam("EXAM-2", "Exam 2", "Sub2", "2026", "v1", "2" * 64, db_path=self.db_path)

        all_exams = get_all_exams(db_path=self.db_path)
        self.assertEqual(len(all_exams), 2)
        exam_ids = [e.exam_id for e in all_exams]
        self.assertIn("EXAM-1", exam_ids)
        self.assertIn("EXAM-2", exam_ids)

    def test_get_nonexistent_exam_returns_none(self):
        """Retrieving an unknown exam ID returns None."""
        self.assertIsNone(get_exam("UNKNOWN-ID", db_path=self.db_path))

    def test_duplicate_exam_id_raises_integrity_error(self):
        """Registering duplicate exam_id raises sqlite3.IntegrityError."""
        register_exam("EXAM-DUP", "Exam", "Sub", "2026", "v1", "d" * 64, db_path=self.db_path)
        with self.assertRaises(sqlite3.IntegrityError):
            register_exam("EXAM-DUP", "Exam Dup", "Sub", "2026", "v1", "e" * 64, db_path=self.db_path)

    def test_audit_logging_and_retrieval(self):
        """Audit events are logged and retrieved correctly."""
        event1 = log_audit_event(
            exam_id="EXAM-2026-CS101",
            action=ACTION_PAPER_REGISTERED,
            result=RESULT_SUCCESS,
            details="Original paper uploaded and hash registered.",
            db_path=self.db_path
        )
        self.assertIsInstance(event1, AuditEvent)
        self.assertIsNotNone(event1.event_id)

        event2 = log_audit_event(
            exam_id="EXAM-2026-CS101",
            action=ACTION_PAPER_VERIFIED,
            result=RESULT_SUCCESS,
            details="Paper verified successfully before exam distribution.",
            db_path=self.db_path
        )

        event3 = log_audit_event(
            exam_id="EXAM-2026-OTHER",
            action=ACTION_HASH_MISMATCH,
            result=RESULT_FLAGGED,
            details="Hash mismatch detected during pre-exam integrity verification.",
            db_path=self.db_path
        )

        # Get all audit logs
        all_logs = get_audit_logs(db_path=self.db_path)
        self.assertEqual(len(all_logs), 3)

        # Get logs filtered by exam_id
        cs101_logs = get_audit_logs(exam_id="EXAM-2026-CS101", db_path=self.db_path)
        self.assertEqual(len(cs101_logs), 2)
        for log in cs101_logs:
            self.assertEqual(log.exam_id, "EXAM-2026-CS101")


if __name__ == "__main__":
    unittest.main()
