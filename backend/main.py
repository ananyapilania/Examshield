"""
ExamShield - FastAPI Backend API
Part 1 Prototype: Examination paper upload, SHA-256 fingerprinting, verification,
audit logging, and role-based authentication (ADMIN & STAFF).

Security Workflow:
    Staff / Admin Login (Argon2 + Expiring JWT)
        ↓
    Role-Based Access Enforcement (RBAC)
        ↓
    PDF Upload & SHA-256 Digest Calculation (Admin Only)
        ↓
    Candidate Paper Verification & Tamper Detection (Staff & Admin)
        ↓
    Append-Only Forensic Audit Logging (Admin View)
"""

import os
import shutil
import tempfile
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials

import backend.database
import backend.audit
from backend.audit import (
    ACTION_HASH_MISMATCH,
    ACTION_LOGIN_FAILED,
    ACTION_LOGIN_INACTIVE,
    ACTION_LOGIN_SUCCESS,
    ACTION_LOGOUT,
    ACTION_PAPER_REGISTERED,
    ACTION_PAPER_VERIFIED,
    ACTION_TAMPER_DETECTED,
    ACTION_USER_CREATED,
    ACTION_USER_ROLE_UPDATED,
    ACTION_USER_STATUS_UPDATED,
    RESULT_FAILURE,
    RESULT_FLAGGED,
    RESULT_SUCCESS,
    get_audit_logs,
    log_audit_event,
)
from backend.auth import (
    create_access_token,
    decode_access_token,
    get_current_user,
    hash_password,
    require_admin,
    require_staff_or_admin,
    security_bearer,
    verify_dummy_constant_time,
    verify_password,
)
from backend.database import (
    create_user,
    get_all_exams,
    get_all_users,
    get_exam,
    get_user_by_id,
    get_user_by_username_or_email,
    initialize_database,
    register_exam,
    revoke_token,
    update_exam_status,
    update_user_role,
    update_user_status,
)
from backend.hashing import calculate_sha256
from backend.models import UserRecord
from backend.schemas import (
    AuditEventResponse,
    ExamRegisterResponse,
    ExamResponse,
    ExamVerifyResponse,
    LoginRequest,
    MessageResponse,
    TokenResponse,
    UserCreateRequest,
    UserRoleUpdateRequest,
    UserResponse,
    UserStatusUpdateRequest,
)


def _get_db_path():
    """Retrieve the current active database path dynamically."""
    return backend.database.DEFAULT_DB_PATH


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.
    Initializes SQLite database tables on startup.
    """
    initialize_database(_get_db_path())
    yield


app = FastAPI(
    title="ExamShield Security API",
    description="Examination paper integrity verification, forensic audit logging, and RBAC authentication system.",
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


# =========================================================================
# GENERAL / HEALTH CHECK
# =========================================================================

@app.get("/", response_model=MessageResponse, tags=["General"])
async def root():
    """Root health-check endpoint."""
    return MessageResponse(
        message="ExamShield Examination Paper Security API is operational.",
        status="HEALTHY"
    )


# =========================================================================
# AUTHENTICATION ENDPOINTS
# =========================================================================

@app.post("/auth/login", response_model=TokenResponse, tags=["Authentication"])
async def login(credentials: LoginRequest):
    """
    Authenticate user credentials (username or email + password),
    generate an expiring JWT access token, and record security audit log.
    Uses constant-time dummy verification for non-existent users to prevent enumeration.
    """
    db_path = _get_db_path()
    clean_identifier = credentials.username_or_email.strip()

    user = get_user_by_username_or_email(clean_identifier, db_path=db_path)
    if not user:
        verify_dummy_constant_time()
        log_audit_event(
            exam_id="AUTH",
            action=ACTION_LOGIN_FAILED,
            result=RESULT_FAILURE,
            details=f"Failed login attempt for unknown account identifier: '{clean_identifier}'.",
            db_path=db_path
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not verify_password(credentials.password, user.password_hash):
        log_audit_event(
            exam_id="AUTH",
            action=ACTION_LOGIN_FAILED,
            result=RESULT_FAILURE,
            details=f"Failed login attempt (incorrect password) for user '{user.username}'.",
            db_path=db_path
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.is_active:
        log_audit_event(
            exam_id="AUTH",
            action=ACTION_LOGIN_INACTIVE,
            result=RESULT_FLAGGED,
            details=f"Rejected login attempt for deactivated user account '{user.username}'.",
            db_path=db_path
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Please contact an administrator."
        )

    token, expires_in, _ = create_access_token(user)
    log_audit_event(
        exam_id="AUTH",
        action=ACTION_LOGIN_SUCCESS,
        result=RESULT_SUCCESS,
        details=f"User '{user.username}' authenticated successfully with role {user.role}.",
        db_path=db_path
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in,
        user=UserResponse(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
    )


@app.post("/auth/logout", response_model=MessageResponse, tags=["Authentication"])
async def logout(
    current_user: UserRecord = Depends(get_current_user),
    auth_credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
):
    """
    Invalidate the current session token server-side and log logout event.
    """
    db_path = _get_db_path()
    if auth_credentials and auth_credentials.credentials:
        try:
            payload = decode_access_token(auth_credentials.credentials)
            jti = payload.get("jti")
            exp = payload.get("exp")
            if jti and exp:
                exp_iso = datetime.fromtimestamp(exp, tz=timezone.utc).isoformat()
                revoke_token(jti, exp_iso, db_path=db_path)
        except Exception:
            pass

    log_audit_event(
        exam_id="AUTH",
        action=ACTION_LOGOUT,
        result=RESULT_SUCCESS,
        details=f"User '{current_user.username}' successfully logged out. Session invalidated.",
        db_path=db_path
    )
    return MessageResponse(
        message="Successfully logged out.",
        status="LOGGED_OUT"
    )


@app.get("/auth/me", response_model=UserResponse, tags=["Authentication"])
async def get_my_profile(current_user: UserRecord = Depends(get_current_user)):
    """Retrieve profile and role of the currently authenticated user."""
    return UserResponse(
        user_id=current_user.user_id,
        username=current_user.username,
        email=current_user.email,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at
    )


# =========================================================================
# ADMINISTRATOR USER MANAGEMENT
# =========================================================================

@app.get("/users", response_model=List[UserResponse], tags=["User Management"])
async def list_users(current_admin: UserRecord = Depends(require_admin)):
    """Administrator-only: retrieve list of all users."""
    db_path = _get_db_path()
    users = get_all_users(db_path=db_path)
    return [
        UserResponse(
            user_id=u.user_id,
            username=u.username,
            email=u.email,
            role=u.role,
            is_active=u.is_active,
            created_at=u.created_at,
            updated_at=u.updated_at
        )
        for u in users
    ]


@app.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED, tags=["User Management"])
async def create_user_account(
    req: UserCreateRequest,
    current_admin: UserRecord = Depends(require_admin)
):
    """Administrator-only: create a new user account."""
    db_path = _get_db_path()
    clean_username = req.username.strip()
    clean_email = req.email.strip().lower()
    clean_role = req.role.strip().upper()

    if clean_role not in ("ADMIN", "STAFF"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be either 'ADMIN' or 'STAFF'."
        )

    # Check for duplicates
    existing = get_user_by_username_or_email(clean_username, db_path=db_path)
    if not existing:
        existing = get_user_by_username_or_email(clean_email, db_path=db_path)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with username '{clean_username}' or email '{clean_email}' already exists."
        )

    password_hash = hash_password(req.password)
    user_id = f"USR-{uuid.uuid4().hex[:12].upper()}"

    new_user = create_user(
        user_id=user_id,
        username=clean_username,
        email=clean_email,
        password_hash=password_hash,
        role=clean_role,
        is_active=req.is_active,
        db_path=db_path
    )

    log_audit_event(
        exam_id="AUTH",
        action=ACTION_USER_CREATED,
        result=RESULT_SUCCESS,
        details=f"Admin '{current_admin.username}' created user '{new_user.username}' with role '{new_user.role}'.",
        db_path=db_path
    )

    return UserResponse(
        user_id=new_user.user_id,
        username=new_user.username,
        email=new_user.email,
        role=new_user.role,
        is_active=new_user.is_active,
        created_at=new_user.created_at,
        updated_at=new_user.updated_at
    )


@app.patch("/users/{user_id}/status", response_model=UserResponse, tags=["User Management"])
async def update_account_status(
    user_id: str,
    req: UserStatusUpdateRequest,
    current_admin: UserRecord = Depends(require_admin)
):
    """Administrator-only: activate or deactivate a user account."""
    db_path = _get_db_path()
    clean_user_id = user_id.strip()

    target_user = get_user_by_id(clean_user_id, db_path=db_path)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{clean_user_id}' not found."
        )

    # Prevent admin from deactivating their own active account
    if target_user.user_id == current_admin.user_id and not req.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Administrators cannot deactivate their own active account."
        )

    update_user_status(clean_user_id, req.is_active, db_path=db_path)
    updated_user = get_user_by_id(clean_user_id, db_path=db_path)

    log_audit_event(
        exam_id="AUTH",
        action=ACTION_USER_STATUS_UPDATED,
        result=RESULT_SUCCESS,
        details=f"Admin '{current_admin.username}' set status of user '{target_user.username}' to {'ACTIVE' if req.is_active else 'INACTIVE'}.",
        db_path=db_path
    )

    return UserResponse(
        user_id=updated_user.user_id,
        username=updated_user.username,
        email=updated_user.email,
        role=updated_user.role,
        is_active=updated_user.is_active,
        created_at=updated_user.created_at,
        updated_at=updated_user.updated_at
    )


@app.patch("/users/{user_id}/role", response_model=UserResponse, tags=["User Management"])
async def change_user_role(
    user_id: str,
    req: UserRoleUpdateRequest,
    current_admin: UserRecord = Depends(require_admin)
):
    """Administrator-only: assign or update user role."""
    db_path = _get_db_path()
    clean_user_id = user_id.strip()
    clean_role = req.role.strip().upper()

    if clean_role not in ("ADMIN", "STAFF"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be either 'ADMIN' or 'STAFF'."
        )

    target_user = get_user_by_id(clean_user_id, db_path=db_path)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{clean_user_id}' not found."
        )

    update_user_role(clean_user_id, clean_role, db_path=db_path)
    updated_user = get_user_by_id(clean_user_id, db_path=db_path)

    log_audit_event(
        exam_id="AUTH",
        action=ACTION_USER_ROLE_UPDATED,
        result=RESULT_SUCCESS,
        details=f"Admin '{current_admin.username}' changed role of user '{target_user.username}' from '{target_user.role}' to '{clean_role}'.",
        db_path=db_path
    )

    return UserResponse(
        user_id=updated_user.user_id,
        username=updated_user.username,
        email=updated_user.email,
        role=updated_user.role,
        is_active=updated_user.is_active,
        created_at=updated_user.created_at,
        updated_at=updated_user.updated_at
    )


# =========================================================================
# EXAMINATION PAPERS (RBAC PROTECTED)
# =========================================================================

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
    file: UploadFile = File(..., description="Examination Paper PDF / Document"),
    current_admin: UserRecord = Depends(require_admin)
):
    """
    Register a new examination paper (ADMIN only):
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
        details=f"Original paper registered by admin '{current_admin.username}'. SHA-256: {file_hash}",
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
    file: UploadFile = File(..., description="Candidate Examination Paper to Verify"),
    current_user: UserRecord = Depends(require_staff_or_admin)
):
    """
    Verify candidate examination paper integrity (STAFF & ADMIN authorized):
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
            details=f"Verified authentic by {current_user.role.lower()} '{current_user.username}'. SHA-256 digest matches.",
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
                f"Tamper detected during check by {current_user.role.lower()} '{current_user.username}'! "
                f"Candidate hash ({uploaded_hash}) differs from registered baseline ({exam.file_hash})."
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
async def list_all_exams(current_user: UserRecord = Depends(require_staff_or_admin)):
    """Retrieve all registered examination records (STAFF & ADMIN authorized)."""
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
async def list_audit_logs(
    exam_id: Optional[str] = None,
    current_admin: UserRecord = Depends(require_admin)
):
    """
    Retrieve forensic audit trail records (ADMIN only).
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
