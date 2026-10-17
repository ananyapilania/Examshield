"""
ExamShield - Data Models (Security Core)
Part 1 Prototype: Lightweight representations for exam records and audit events.
"""

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any


@dataclass
class ExamRecord:
    """Represents an examination paper's metadata and cryptographic SHA-256 fingerprint."""
    exam_id: str
    exam_name: str
    subject: str
    academic_year: str
    paper_version: str
    file_hash: str
    created_at: str
    status: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert the record to a dictionary."""
        return asdict(self)


@dataclass
class AuditEvent:
    """Represents an immutable audit log entry for system traceability."""
    exam_id: str
    action: str
    timestamp: str
    result: str
    event_id: Optional[int] = None
    details: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert the audit event to a dictionary."""
        return asdict(self)


@dataclass
class UserRecord:
    """Represents an application user and role metadata."""
    user_id: str
    username: str
    email: str
    password_hash: str
    role: str
    is_active: bool
    created_at: str
    updated_at: str

    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert the user record to a dictionary, omitting password_hash by default."""
        d = asdict(self)
        if not include_sensitive:
            d.pop("password_hash", None)
        return d
