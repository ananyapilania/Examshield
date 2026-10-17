"""
ExamShield - Pydantic Schemas
Part 1 Prototype: Request and response validation models for FastAPI endpoints.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class ExamRegisterResponse(BaseModel):
    """Response model returned after successful examination paper registration."""
    exam_id: str = Field(..., description="Unique Examination Identifier")
    exam_name: str = Field(..., description="Title / Display Name of the Examination")
    subject: str = Field(..., description="Subject / Course Name")
    academic_year: str = Field(..., description="Academic Session / Year")
    paper_version: str = Field(..., description="Version / Set (e.g., Set-A)")
    file_hash: str = Field(..., description="64-character SHA-256 digital fingerprint")
    timestamp: str = Field(..., description="ISO 8601 registration timestamp")
    status: str = Field(..., description="Lifecycle status (e.g., REGISTERED)")


class ExamVerifyResponse(BaseModel):
    """Response model returned after candidate paper verification."""
    exam_id: str = Field(..., description="Unique Examination Identifier")
    registered_hash: str = Field(..., description="Original registered baseline SHA-256 hash")
    uploaded_hash: str = Field(..., description="Calculated SHA-256 hash of the uploaded candidate paper")
    status: str = Field(..., description="Verification result: VERIFIED (authentic) or TAMPER_DETECTED (tampered)")
    timestamp: str = Field(..., description="ISO 8601 verification timestamp")


class ExamResponse(BaseModel):
    """Model representing an examination record in listing endpoints."""
    exam_id: str
    exam_name: str
    subject: str
    academic_year: str
    paper_version: str
    file_hash: str
    created_at: str
    status: str


class AuditEventResponse(BaseModel):
    """Model representing an audit log entry."""
    event_id: Optional[int] = None
    exam_id: str
    action: str
    timestamp: str
    result: str
    details: Optional[str] = None


class MessageResponse(BaseModel):
    """Generic message / status response model."""
    message: str
    status: str


# =========================================================================
# AUTHENTICATION & USER MANAGEMENT SCHEMAS
# =========================================================================

class LoginRequest(BaseModel):
    """User credentials for authentication."""
    username_or_email: str = Field(..., description="Username or email address")
    password: str = Field(..., description="User password")


class UserResponse(BaseModel):
    """Safe user profile response model; never exposes password hashes."""
    user_id: str
    username: str
    email: str
    role: str
    is_active: bool
    created_at: str
    updated_at: str


class TokenResponse(BaseModel):
    """JWT bearer access token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class UserCreateRequest(BaseModel):
    """Payload to create a new user account (administrator only)."""
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    email: str = Field(..., min_length=5, max_length=120, description="Unique email address")
    password: str = Field(..., min_length=8, description="Initial plain password (will be Argon2-hashed)")
    role: str = Field("STAFF", description="Role: 'ADMIN' or 'STAFF'")
    is_active: bool = Field(True, description="Account active status")


class UserStatusUpdateRequest(BaseModel):
    """Payload to activate or deactivate a user account."""
    is_active: bool


class UserRoleUpdateRequest(BaseModel):
    """Payload to update user role."""
    role: str = Field(..., description="Role: 'ADMIN' or 'STAFF'")
