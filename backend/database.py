"""
ExamShield - Database Layer (Security Core)
Part 1 Prototype: SQLite metadata persistence for examination papers and records.
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Union

from backend.models import ExamRecord

DEFAULT_DB_PATH = "examshield.db"


def get_connection(db_path: Union[str, Path] = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """
    Establish a connection to the SQLite database with row factory enabled.

    Args:
        db_path (Union[str, Path]): Path to the SQLite database file.

    Returns:
        sqlite3.Connection: Database connection object.
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    # Enable foreign key support
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def initialize_database(db_path: Union[str, Path] = DEFAULT_DB_PATH) -> None:
    """
    Initialize SQLite database tables for exams and audit logs if they do not exist.

    Args:
        db_path (Union[str, Path]): Path to the SQLite database file.
    """
    with get_connection(db_path) as conn:
        cursor = conn.cursor()

        # Create exams table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS exams (
                exam_id TEXT PRIMARY KEY,
                exam_name TEXT NOT NULL,
                subject TEXT NOT NULL,
                academic_year TEXT NOT NULL,
                paper_version TEXT NOT NULL,
                file_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL
            );
        """)

        # Create audit_logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                exam_id TEXT NOT NULL,
                action TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                result TEXT NOT NULL,
                details TEXT
            );
        """)

        conn.commit()


def register_exam(
    exam_id: str,
    exam_name: str,
    subject: str,
    academic_year: str,
    paper_version: str,
    file_hash: str,
    status: str = "REGISTERED",
    created_at: Optional[str] = None,
    db_path: Union[str, Path] = DEFAULT_DB_PATH
) -> ExamRecord:
    """
    Register a new examination paper metadata record in the database.

    Args:
        exam_id (str): Unique identifier for the examination.
        exam_name (str): Title or display name of the exam.
        subject (str): Subject / course name.
        academic_year (str): Academic session/year (e.g., "2025-2026").
        paper_version (str): Version identifier (e.g., "Set-A", "v1.0").
        file_hash (str): 64-character SHA-256 digital fingerprint.
        status (str, optional): Lifecycle status (default: "REGISTERED").
        created_at (Optional[str], optional): Timestamp string (defaults to current UTC ISO format).
        db_path (Union[str, Path], optional): Database file path.

    Returns:
        ExamRecord: The registered exam model instance.

    Raises:
        sqlite3.IntegrityError: If an exam with the same exam_id already exists.
    """
    if created_at is None:
        created_at = datetime.now(timezone.utc).isoformat()

    record = ExamRecord(
        exam_id=exam_id.strip(),
        exam_name=exam_name.strip(),
        subject=subject.strip(),
        academic_year=academic_year.strip(),
        paper_version=paper_version.strip(),
        file_hash=file_hash.strip().lower(),
        created_at=created_at,
        status=status.strip().upper()
    )

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO exams (
                exam_id, exam_name, subject, academic_year,
                paper_version, file_hash, created_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            record.exam_id,
            record.exam_name,
            record.subject,
            record.academic_year,
            record.paper_version,
            record.file_hash,
            record.created_at,
            record.status
        ))
        conn.commit()

    return record


def get_exam(exam_id: str, db_path: Union[str, Path] = DEFAULT_DB_PATH) -> Optional[ExamRecord]:
    """
    Retrieve an exam record by its unique Exam ID.

    Args:
        exam_id (str): Unique exam identifier.
        db_path (Union[str, Path], optional): Database file path.

    Returns:
        Optional[ExamRecord]: ExamRecord instance if found, None otherwise.
    """
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM exams WHERE exam_id = ?;", (exam_id.strip(),))
        row = cursor.fetchone()

        if row is None:
            return None

        return ExamRecord(
            exam_id=row["exam_id"],
            exam_name=row["exam_name"],
            subject=row["subject"],
            academic_year=row["academic_year"],
            paper_version=row["paper_version"],
            file_hash=row["file_hash"],
            created_at=row["created_at"],
            status=row["status"]
        )


def get_all_exams(db_path: Union[str, Path] = DEFAULT_DB_PATH) -> List[ExamRecord]:
    """
    Retrieve all registered examination records ordered by creation time (newest first).

    Args:
        db_path (Union[str, Path], optional): Database file path.

    Returns:
        List[ExamRecord]: List of registered ExamRecord instances.
    """
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM exams ORDER BY created_at DESC;")
        rows = cursor.fetchall()

        return [
            ExamRecord(
                exam_id=row["exam_id"],
                exam_name=row["exam_name"],
                subject=row["subject"],
                academic_year=row["academic_year"],
                paper_version=row["paper_version"],
                file_hash=row["file_hash"],
                created_at=row["created_at"],
                status=row["status"]
            )
            for row in rows
        ]


def update_exam_status(
    exam_id: str,
    status: str,
    db_path: Union[str, Path] = DEFAULT_DB_PATH
) -> bool:
    """
    Update the status of an existing examination record.

    Args:
        exam_id (str): Unique exam identifier.
        status (str): New status value (e.g., "VERIFIED", "FLAGGED", "TAMPERED").
        db_path (Union[str, Path], optional): Database file path.

    Returns:
        bool: True if record was found and updated, False otherwise.
    """
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE exams SET status = ? WHERE exam_id = ?;",
            (status.strip().upper(), exam_id.strip())
        )
        conn.commit()
        return cursor.rowcount > 0
