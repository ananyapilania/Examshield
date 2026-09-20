"""
ExamShield - FastAPI Backend API
Part 1 Prototype: Examination paper upload, SHA-256 fingerprinting, verification, and audit logging.

Security Workflow:
    PDF Upload
        ↓
    SHA-256 Digest Calculation (Chunked)
        ↓
    SQLite Metadata & Fingerprint Persistence
        ↓
    Candidate Paper Verification & Tamper Detection
        ↓
    Append-Only Audit Logging
"""

import os
import shutil
import tempfile
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware

import backend.database
import backend.audit
from backend.audit import (
    ACTION_HASH_MISMATCH,
    ACTION_PAPER_REGISTERED,
    ACTION_PAPER_VERIFIED,
    ACTION_TAMPER_DETECTED,
    RESULT_FLAGGED,
    RESULT_SUCCESS,
    get_audit_logs,
    log_audit_event,
)
from backend.database import (
    get_all_exams,
    get_exam,
    initialize_database,
    register_exam,
    update_exam_status,
)
from backend.hashing import calculate_sha256
from backend.schemas import (
    AuditEventResponse,
    ExamRegisterResponse,
    ExamResponse,
    ExamVerifyResponse,
    MessageResponse,
)


def _get_db_path():
    """Retrieve the current active database path dynamically."""
    return backend.database.DEFAULT_DB_PATH


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.
    Initializes the SQLite database on startup.
    """
    initialize_database(_get_db_path())
    yield


app = FastAPI(
    title="ExamShield Security API",
    description="Examination paper integrity verification and tamper detection system (Part 1 Prototype).",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for local development and frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_model=MessageResponse, tags=["General"])
async def root():
    """Root health-check endpoint."""
    return MessageResponse(
        message="ExamShield Examination Paper Security API is operational.",
        status="HEALTHY"
    )


@app.post(
    "/register-exam",
    response_model=ExamRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Exams"]
)
async def register_new_exam(
    exam_id: str = Form(..., description="Unique Exam ID (e.g. EXAM-2026-CS101)"),
    exam_name: str = Form(..., description="Full Name of the Exam"),
    subject: str = Form(..., description="Subject / Course"),
    academic_year: str = Form(..., description="Academic Session / Year"),
    paper_version: str = Form(..., description="Paper Version / Set (e.g. Set-A)"),
    file: UploadFile = File(..., description="Examination Paper PDF / Document")
):
    """
    Register a new examination paper:
    1. Validates upload and fields.
    2. Checks for existing exam ID.
    3. Streams file into a temporary location and calculates SHA-256 fingerprint.
    4. Persists metadata and hash in SQLite (PDF contents are never stored).
    5. Records an immutable audit log event.
    """
    db_path = _get_db_path()

    # 1. Field validation
    clean_exam_id = exam_id.strip()
    clean_exam_name = exam_name.strip()
    clean_subject = subject.strip()
    clean_academic_year = academic_year.strip()
    clean_paper_version = paper_version.strip()

    if not clean_exam_id or not clean_exam_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Exam ID and Exam Name must not be empty."
        )

    # 2. Check for duplicate exam ID
    existing = get_exam(clean_exam_id, db_path=db_path)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Exam with ID '{clean_exam_id}' is already registered."
        )

    # 3. Validate file upload
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No examination file was uploaded."
        )

    # 4. Stream to temporary file to calculate SHA-256 fingerprint
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".tmp") as temp_file:
            temp_path = temp_file.name
            shutil.copyfileobj(file.file, temp_file)

        # Check for empty file
        if os.path.getsize(temp_path) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty."
            )

        # Calculate SHA-256 digital fingerprint
        file_hash = calculate_sha256(temp_path)

    finally:
        # Secure cleanup: Remove temporary binary file from disk immediately
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

    # 5. Persist metadata & hash in SQLite database
    created_at = datetime.now(timezone.utc).isoformat()
    record = register_exam(
        exam_id=clean_exam_id,
        exam_name=clean_exam_name,
        subject=clean_subject,
        academic_year=clean_academic_year,
        paper_version=clean_paper_version,
        file_hash=file_hash,
        status="REGISTERED",
        created_at=created_at,
        db_path=db_path
    )

    # 6. Record audit log
    log_audit_event(
        exam_id=clean_exam_id,
        action=ACTION_PAPER_REGISTERED,
        result=RESULT_SUCCESS,
        details=f"Original paper registered. SHA-256: {file_hash}",
        timestamp=created_at,
        db_path=db_path
    )

    # 7. Return registration response
    return ExamRegisterResponse(
        exam_id=record.exam_id,
        exam_name=record.exam_name,
        subject=record.subject,
        academic_year=record.academic_year,
        paper_version=record.paper_version,
        file_hash=record.file_hash,
        timestamp=record.created_at,
        status=record.status
    )


@app.post(
    "/verify-exam/{exam_id}",
    response_model=ExamVerifyResponse,
    tags=["Verification"]
)
async def verify_exam_paper(
    exam_id: str,
    file: UploadFile = File(..., description="Candidate Examination Paper to Verify")
):
    """
    Verify candidate examination paper integrity:
    1. Checks if the Exam ID exists in SQLite.
    2. Calculates SHA-256 digest of uploaded candidate file.
    3. Compares calculated hash with registered baseline hash.
    4. Sets status to VERIFIED (match) or TAMPER_DETECTED (mismatch).
    5. Records an immutable audit log entry.
    """
    db_path = _get_db_path()
    clean_exam_id = exam_id.strip()

    # 1. Lookup registered exam metadata
    exam = get_exam(clean_exam_id, db_path=db_path)
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exam with ID '{clean_exam_id}' not found."
        )

    # 2. Validate candidate file
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Candidate examination file is required for verification."
        )

    # 3. Stream candidate file to calculate SHA-256
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".tmp") as temp_file:
            temp_path = temp_file.name
            shutil.copyfileobj(file.file, temp_file)

        if os.path.getsize(temp_path) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded verification file is empty."
            )

        uploaded_hash = calculate_sha256(temp_path)

    finally:
        # Secure cleanup
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

    timestamp = datetime.now(timezone.utc).isoformat()

    # 4. Compare cryptographic hashes
    if uploaded_hash.lower() == exam.file_hash.lower():
        verification_status = "VERIFIED"
        update_exam_status(clean_exam_id, "VERIFIED", db_path=db_path)
        log_audit_event(
            exam_id=clean_exam_id,
            action=ACTION_PAPER_VERIFIED,
            result=RESULT_SUCCESS,
            details="Cryptographic hash matches registered baseline. Document integrity authentic.",
            timestamp=timestamp,
            db_path=db_path
        )
    else:
        verification_status = "TAMPER_DETECTED"
        update_exam_status(clean_exam_id, "TAMPER_DETECTED", db_path=db_path)
        log_audit_event(
            exam_id=clean_exam_id,
            action=ACTION_HASH_MISMATCH,
            result=RESULT_FLAGGED,
            details=(
                f"Tamper detected! Candidate hash ({uploaded_hash}) "
                f"differs from registered baseline ({exam.file_hash})."
            ),
            timestamp=timestamp,
            db_path=db_path
        )

    # 5. Return verification response
    return ExamVerifyResponse(
        exam_id=clean_exam_id,
        registered_hash=exam.file_hash,
        uploaded_hash=uploaded_hash,
        status=verification_status,
        timestamp=timestamp
    )


@app.get("/exams", response_model=List[ExamResponse], tags=["Exams"])
async def list_all_exams():
    """Retrieve all registered examination records."""
    db_path = _get_db_path()
    records = get_all_exams(db_path=db_path)
    return [
        ExamResponse(
            exam_id=r.exam_id,
            exam_name=r.exam_name,
            subject=r.subject,
            academic_year=r.academic_year,
            paper_version=r.paper_version,
            file_hash=r.file_hash,
            created_at=r.created_at,
            status=r.status
        )
        for r in records
    ]


@app.get("/audit-logs", response_model=List[AuditEventResponse], tags=["Audit Logs"])
async def list_audit_logs(exam_id: Optional[str] = None):
    """
    Retrieve audit trail records.
    Optionally filter logs by a specific exam_id.
    """
    db_path = _get_db_path()
    logs = get_audit_logs(exam_id=exam_id, db_path=db_path)
    return [
        AuditEventResponse(
            event_id=log.event_id,
            exam_id=log.exam_id,
            action=log.action,
            timestamp=log.timestamp,
            result=log.result,
            details=log.details
        )
        for log in logs
    ]
