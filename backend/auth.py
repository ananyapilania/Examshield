"""
ExamShield - Authentication & Security Core
Handles Argon2 password hashing, JWT bearer token lifecycle,
session invalidation/revocation, and FastAPI role-based access dependencies.
"""

import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, Dict, Any

import argon2
import argon2.exceptions
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

import backend.database
from backend.models import UserRecord


# Password Hashing Setup (Argon2id)
_hasher = argon2.PasswordHasher(
    time_cost=2,
    memory_cost=65536,  # 64 MiB
    parallelism=2,
    hash_len=32,
    salt_len=16,
    type=argon2.Type.ID
)

# Precomputed dummy hash used to equalize response time when username is not found
# (mitigates timing attacks and user enumeration)
_DUMMY_HASH = _hasher.hash("examshield-dummy-constant-time-salt")

# Secret Key and JWT Configuration
SECRET_KEY = os.environ.get(
    "EXAMSHIELD_SECRET_KEY",
    "examshield-dev-secret-key-do-not-use-in-production-min-32-chars"
)
JWT_ALGORITHM = "HS256"
DEFAULT_EXPIRATION_MINUTES = int(os.environ.get("EXAMSHIELD_TOKEN_EXPIRE_MINUTES", "480"))  # 8 hours

security_bearer = HTTPBearer(auto_error=False)


def _get_active_db_path():
    """Retrieve current active database path dynamically."""
    return backend.database.DEFAULT_DB_PATH


def hash_password(plain_password: str) -> str:
    """
    Hash a plaintext password using Argon2id with automatic salt generation.

    Args:
        plain_password (str): The plaintext password.

    Returns:
        str: Argon2 encoded hash string.
    """
    return _hasher.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against an Argon2 hash.

    Args:
        plain_password (str): Plaintext password to verify.
        hashed_password (str): Argon2 hash to compare against.

    Returns:
        bool: True if password matches hash, False otherwise.
    """
    try:
        return _hasher.verify(hashed_password, plain_password)
    except (argon2.exceptions.VerifyMismatchError, argon2.exceptions.VerificationError, argon2.exceptions.InvalidHashError):
        return False


def verify_dummy_constant_time():
    """Perform a constant-time dummy verify when a user does not exist."""
    try:
        _hasher.verify(_DUMMY_HASH, "wrong-password")
    except Exception:
        pass


def create_access_token(
    user: UserRecord,
    expires_delta: Optional[timedelta] = None
) -> Tuple[str, int, str]:
    """
    Generate an expiring JWT bearer token with a unique session ID (jti).

    Args:
        user (UserRecord): The authenticated user instance.
        expires_delta (Optional[timedelta]): Custom token lifetime.

    Returns:
        Tuple[str, int, str]: (encoded_jwt_token, expires_in_seconds, jti)
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=DEFAULT_EXPIRATION_MINUTES)

    now = datetime.now(timezone.utc)
    expire = now + expires_delta
    jti = uuid.uuid4().hex

    payload = {
        "sub": user.user_id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp())
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)
    expires_in = int(expires_delta.total_seconds())
    return token, expires_in, jti


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT bearer token.

    Args:
        token (str): JWT string.

    Returns:
        Dict[str, Any]: Decoded payload claims.

    Raises:
        jwt.ExpiredSignatureError: If token has expired.
        jwt.InvalidTokenError: If token signature or format is invalid.
    """
    return jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])


# =========================================================================
# FASTAPI SECURITY DEPENDENCIES
# =========================================================================

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
) -> UserRecord:
    """
    FastAPI dependency: Extract and validate JWT Bearer token, check revocation,
    and return the active authenticated UserRecord.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    jti = payload.get("jti")
    if not jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token structure: missing session identifier.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    db_path = _get_active_db_path()

    # Check if session token was invalidated / logged out
    if backend.database.is_token_revoked(jti, db_path=db_path):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has been logged out or invalidated.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims: missing subject.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user = backend.database.get_user_by_id(user_id, db_path=db_path)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account associated with this token was not found.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated. Contact an administrator."
        )

    return user


async def require_admin(
    current_user: UserRecord = Depends(get_current_user)
) -> UserRecord:
    """
    FastAPI dependency: Ensure current authenticated user has the 'ADMIN' role.
    Raises 403 Forbidden if user is not an administrator.
    """
    if current_user.role != "ADMIN":
        # Log unauthorized access event for forensic auditing
        db_path = _get_active_db_path()
        backend.audit.log_audit_event(
            exam_id="AUTH",
            action=backend.audit.ACTION_UNAUTHORIZED_ACCESS,
            result=backend.audit.RESULT_FAILURE,
            details=f"User '{current_user.username}' (role: {current_user.role}) attempted administrator-restricted operation.",
            db_path=db_path
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Administrator privileges required."
        )
    return current_user


async def require_staff_or_admin(
    current_user: UserRecord = Depends(get_current_user)
) -> UserRecord:
    """
    FastAPI dependency: Ensure current user is an active STAFF member or ADMIN.
    """
    if current_user.role not in ("ADMIN", "STAFF"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Operational privileges required."
        )
    return current_user
