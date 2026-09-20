"""
ExamShield - Audit Logging (Security Core)
Part 1 Prototype: Append-only audit trail for forensic traceability and tamper logs.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Union

from backend.database import DEFAULT_DB_PATH, get_connection
from backend.models import AuditEvent

# Standard Action Constants
ACTION_PAPER_REGISTERED = "PAPER_REGISTERED"
ACTION_PAPER_VERIFIED = "PAPER_VERIFIED"
ACTION_HASH_MISMATCH = "HASH_MISMATCH"
ACTION_TAMPER_DETECTED = "TAMPER_DETECTED"
ACTION_STATUS_UPDATED = "STATUS_UPDATED"

# Result Constants
RESULT_SUCCESS = "SUCCESS"
RESULT_FAILURE = "FAILURE"
RESULT_FLAGGED = "FLAGGED"


def log_audit_event(
    exam_id: str,
    action: str,
    result: str,
    details: Optional[str] = None,
    timestamp: Optional[str] = None,
    db_path: Union[str, Path] = DEFAULT_DB_PATH
) -> AuditEvent:
    """
    Record an immutable audit event in the database.

    Args:
        exam_id (str): Associated Exam ID.
        action (str): Event action identifier (e.g., "PAPER_REGISTERED", "PAPER_VERIFIED", "HASH_MISMATCH").
        result (str): Outcome of the action (e.g., "SUCCESS", "FAILURE", "FLAGGED").
        details (Optional[str], optional): Additional contextual description or error detail.
        timestamp (Optional[str], optional): ISO 8601 timestamp string (default: current UTC time).
        db_path (Union[str, Path], optional): Database file path.

    Returns:
        AuditEvent: The persisted audit event with its generated event_id.
    """
    if timestamp is None:
        timestamp = datetime.now(timezone.utc).isoformat()

    event = AuditEvent(
        exam_id=exam_id.strip(),
        action=action.strip().upper(),
        result=result.strip().upper(),
        details=details.strip() if details else None,
        timestamp=timestamp
    )

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO audit_logs (exam_id, action, timestamp, result, details)
            VALUES (?, ?, ?, ?, ?);
        """, (
            event.exam_id,
            event.action,
            event.timestamp,
            event.result,
            event.details
        ))
        conn.commit()
        event.event_id = cursor.lastrowid

    return event


def get_audit_logs(
    exam_id: Optional[str] = None,
    db_path: Union[str, Path] = DEFAULT_DB_PATH
) -> List[AuditEvent]:
    """
    Retrieve audit log records, optionally filtered by a specific Exam ID.
    Returned in reverse chronological order (newest first).

    Args:
        exam_id (Optional[str], optional): Filter logs by Exam ID. If None, retrieves all logs.
        db_path (Union[str, Path], optional): Database file path.

    Returns:
        List[AuditEvent]: List of retrieved audit events.
    """
    with get_connection(db_path) as conn:
        cursor = conn.cursor()

        if exam_id:
            cursor.execute(
                "SELECT * FROM audit_logs WHERE exam_id = ? ORDER BY event_id DESC;",
                (exam_id.strip(),)
            )
        else:
            cursor.execute("SELECT * FROM audit_logs ORDER BY event_id DESC;")

        rows = cursor.fetchall()

        return [
            AuditEvent(
                event_id=row["event_id"],
                exam_id=row["exam_id"],
                action=row["action"],
                timestamp=row["timestamp"],
                result=row["result"],
                details=row["details"]
            )
            for row in rows
        ]
