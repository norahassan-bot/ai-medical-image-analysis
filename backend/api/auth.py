"""Authentication, Cryptographic Token Management & Role-Based Access Control (RBAC).

Task 21 Architecture:
---------------------
1. USER (Anonymous Session):
   - Cryptographically secure random opaque token generated via secrets.token_urlsafe(32).
   - Only the SHA-256 hash of the token is stored in SQLite (token_hash column).
   - Raw token is delivered to the browser ONLY via Secure HttpOnly cookie (user_session_token).
   - Analysis ownership (owner_user_id) is derived purely on the server from the authenticated session.
   - Configurable token expiration (default 30 days).
2. ADMIN (Privileged Administration):
   - Secured with username/password (ADMIN_USERNAME / ADMIN_PASSWORD).
   - Passwords hashed with bcrypt.
   - Signed JWT / Admin session token with role='ADMIN'.
   - Dedicated admin routes (/admin/*) strictly require role='ADMIN'.
"""

import os
import time
import hashlib
import logging
import secrets
from typing import Optional, Dict, Any, Union
from datetime import datetime, timedelta, timezone

import jwt
import bcrypt
from fastapi import Request, Response, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from database.database import (
    get_user_by_id,
    get_user_by_username,
    get_user_by_token_hash,
    create_anonymous_user,
    update_user_last_seen,
    invalidate_user_token,
)

logger = logging.getLogger("Auth")

# Security configuration
AUTH_SECRET_KEY = (
    os.getenv("AUTH_SECRET_KEY")
    or os.getenv("SECRET_KEY")
    or "medvision-ai-secret-key-2026-secure-token-clinical-decision-support"
)
ALGORITHM = "HS256"

# User Session Expiration (Configurable: default 30 days)
USER_SESSION_EXPIRE_DAYS = int(os.getenv("USER_SESSION_EXPIRE_DAYS", "30"))
USER_SESSION_EXPIRE_SECONDS = USER_SESSION_EXPIRE_DAYS * 86400
ADMIN_TOKEN_EXPIRE_MINUTES = int(os.getenv("ADMIN_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours

USER_COOKIE_NAME = "user_session_token"
ADMIN_COOKIE_NAME = "admin_session_token"
COOKIE_NAME = USER_COOKIE_NAME
LEGACY_COOKIE_NAME = "access_token"

# In-memory login attempt tracker for Admin brute-force protection
LOGIN_ATTEMPTS: Dict[str, list] = {}
FAILED_LOGIN_ATTEMPTS = LOGIN_ATTEMPTS
MAX_FAILED_ATTEMPTS = 5
THROTTLE_WINDOW_SECONDS = 60

bearer_scheme = HTTPBearer(auto_error=False)


class AuthenticatedUser:
    """Represents an active authenticated user with role-based permissions."""
    def __init__(
        self,
        id: str,
        username: str,
        role: str = "USER",
        is_active: bool = True,
        created_at: Optional[str] = None,
        is_anonymous: bool = False,
    ):
        self.id = id
        self.username = username
        self.role = role.upper()
        self.is_active = is_active
        self.created_at = created_at
        self.is_anonymous = is_anonymous or (self.role == "USER" and username.startswith("anon_"))

    @property
    def is_admin(self) -> bool:
        return self.role == "ADMIN"

    def __getitem__(self, item: str):
        return getattr(self, item)

    def get(self, item: str, default=None):
        return getattr(self, item, default)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "is_anonymous": self.is_anonymous,
        }


# -----------------------------------------------------------------------------
# Cryptographic Token & Hash Utilities
# -----------------------------------------------------------------------------

def generate_secure_token() -> str:
    """Generate a cryptographically secure random opaque token with high entropy."""
    return secrets.token_urlsafe(32)


def hash_token(raw_token: str) -> str:
    """Compute deterministic SHA-256 hash of raw token for secure database lookup."""
    return hashlib.sha256(raw_token.strip().encode("utf-8")).hexdigest()


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt with automatic salt generation (ADMIN)."""
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against its bcrypt hash in constant time (ADMIN)."""
    try:
        password_bytes = plain_password.encode("utf-8")
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception as e:
        logger.warning(f"Password verification error: {e}")
        return False


def create_access_token(
    user_id: str,
    username: str,
    role: str,
    expires_delta: Optional[timedelta] = None,
    expires_delta_seconds: Optional[int] = None,
) -> str:
    """Generate a cryptographically signed JWT access token for ADMIN users."""
    now = datetime.now(timezone.utc)
    if expires_delta_seconds is not None:
        delta = timedelta(seconds=expires_delta_seconds)
    elif expires_delta is not None:
        delta = expires_delta
    else:
        delta = timedelta(minutes=ADMIN_TOKEN_EXPIRE_MINUTES)

    expire = now + delta

    payload = {
        "sub": user_id,
        "username": username.lower(),
        "role": role.upper(),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": secrets.token_hex(8),
    }

    token = jwt.encode(payload, AUTH_SECRET_KEY, algorithm=ALGORITHM)
    return token


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a signed JWT token."""
    try:
        payload = jwt.decode(token, AUTH_SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.debug("Admin JWT token has expired")
        return None
    except jwt.InvalidTokenError:
        return None


def set_admin_cookie(
    response: Response,
    token: str,
    max_age_seconds: int = ADMIN_TOKEN_EXPIRE_MINUTES * 60,
) -> None:
    """Set the HTTP-only secure cookie for ADMIN authenticated sessions."""
    is_prod = os.getenv("ENVIRONMENT", "development").lower() == "production"
    response.set_cookie(
        key=ADMIN_COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=max_age_seconds,
        expires=max_age_seconds,
        samesite="lax",
        secure=is_prod,
        path="/",
    )


def clear_admin_cookie(response: Response) -> None:
    """Clear ADMIN authentication cookie without affecting anonymous USER session."""
    response.delete_cookie(
        key=ADMIN_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax",
    )


def set_user_cookie(
    response: Response,
    token: str,
    max_age_seconds: int = USER_SESSION_EXPIRE_SECONDS,
) -> None:
    """Set the HTTP-only secure cookie for anonymous USER sessions."""
    is_prod = os.getenv("ENVIRONMENT", "development").lower() == "production"
    response.set_cookie(
        key=USER_COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=max_age_seconds,
        expires=max_age_seconds,
        samesite="lax",
        secure=is_prod,
        path="/",
    )
    # Mirror legacy name for backward compatibility
    response.set_cookie(
        key=LEGACY_COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=max_age_seconds,
        expires=max_age_seconds,
        samesite="lax",
        secure=is_prod,
        path="/",
    )


def clear_user_cookie(response: Response) -> None:
    """Clear anonymous USER session cookie without affecting ADMIN session."""
    for key in [USER_COOKIE_NAME, LEGACY_COOKIE_NAME]:
        response.delete_cookie(
            key=key,
            path="/",
            httponly=True,
            samesite="lax",
        )


set_auth_cookie = set_user_cookie
clear_auth_cookie = clear_user_cookie


# -----------------------------------------------------------------------------
# Brute-Force Login Throttling (Admin Authentication)
# -----------------------------------------------------------------------------

def _extract_ip_and_user(req_or_ip: Union[Request, str], username: str) -> str:
    if isinstance(req_or_ip, Request):
        client_host = req_or_ip.client.host if req_or_ip.client else "unknown"
    else:
        client_host = str(req_or_ip)
    return f"{client_host}:{username.lower()}"


def check_login_throttling(req_or_ip: Union[Request, str], username: str) -> None:
    """Check if admin login attempts exceed threshold in the throttle window."""
    now = time.time()
    key = _extract_ip_and_user(req_or_ip, username)

    if key in LOGIN_ATTEMPTS:
        valid_attempts = [t for t in LOGIN_ATTEMPTS[key] if now - t < THROTTLE_WINDOW_SECONDS]
        LOGIN_ATTEMPTS[key] = valid_attempts

        if len(valid_attempts) >= MAX_FAILED_ATTEMPTS:
            logger.warning(f"Admin login rate limit exceeded for {key}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed login attempts. Please wait 60 seconds before trying again.",
            )


def record_failed_login(req_or_ip: Union[Request, str], username: str) -> None:
    """Record a failed login attempt for admin rate-limiting."""
    now = time.time()
    key = _extract_ip_and_user(req_or_ip, username)
    if key not in LOGIN_ATTEMPTS:
        LOGIN_ATTEMPTS[key] = []
    LOGIN_ATTEMPTS[key].append(now)


def record_successful_login(req_or_ip: Union[Request, str], username: str) -> None:
    """Clear failed attempts upon successful admin login."""
    key = _extract_ip_and_user(req_or_ip, username)
    LOGIN_ATTEMPTS.pop(key, None)


# -----------------------------------------------------------------------------
# FastAPI Authentication & RBAC Dependencies
# -----------------------------------------------------------------------------

def resolve_admin_from_token(token: str) -> Optional[AuthenticatedUser]:
    """Resolve an authenticated administrator strictly from signed Admin JWT token."""
    if not token or not isinstance(token, str):
        return None

    jwt_payload = decode_access_token(token)
    if jwt_payload and jwt_payload.get("sub"):
        admin_user = get_user_by_id(jwt_payload["sub"])
        if admin_user and admin_user.get("is_active", True) and admin_user.get("role") == "ADMIN":
            return AuthenticatedUser(
                id=admin_user["id"],
                username=admin_user["username"],
                role="ADMIN",
                is_active=True,
                created_at=admin_user.get("created_at"),
                is_anonymous=False,
            )
    return None


def resolve_user_from_token(token: str) -> Optional[AuthenticatedUser]:
    """Resolve an authenticated anonymous user strictly from hashed session token in SQLite."""
    if not token or not isinstance(token, str):
        return None

    t_hash = hash_token(token)
    user_db = get_user_by_token_hash(t_hash)
    if user_db:
        # Verify expiration
        expires_str = user_db.get("token_expires_at")
        if expires_str:
            try:
                expires_dt = datetime.fromisoformat(expires_str)
                if expires_dt.tzinfo is None:
                    expires_dt = expires_dt.replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc) > expires_dt:
                    logger.info(f"User session {user_db['id']} has expired.")
                    invalidate_user_token(user_db["id"])
                    return None
            except Exception as e:
                logger.warning(f"Error parsing token expiration: {e}")

        if not user_db.get("is_active", True):
            return None

        # Update last seen timestamp
        update_user_last_seen(user_db["id"])

        return AuthenticatedUser(
            id=user_db["id"],
            username=user_db["username"],
            role=user_db.get("role", "USER"),
            is_active=True,
            created_at=user_db.get("created_at"),
            is_anonymous=True,
        )

    return None


async def get_current_admin_optional(
    request: Request,
    bearer: Optional[HTTPAuthorizationCredentials] = None,
) -> Optional[AuthenticatedUser]:
    """Extract and resolve authenticated administrator from admin_session_token cookie or Bearer."""
    token = None

    # 1. Check dedicated admin_session_token cookie
    if ADMIN_COOKIE_NAME in request.cookies:
        token = request.cookies[ADMIN_COOKIE_NAME]
    elif LEGACY_COOKIE_NAME in request.cookies:
        token = request.cookies[LEGACY_COOKIE_NAME]

    # 2. Check Bearer credentials object if passed
    if not token and bearer and hasattr(bearer, "credentials"):
        token = bearer.credentials

    # 3. Check raw Authorization header
    if not token and "authorization" in request.headers:
        auth_hdr = request.headers["authorization"]
        if auth_hdr.startswith("Bearer "):
            token = auth_hdr[7:].strip()

    if not token:
        return None

    return resolve_admin_from_token(token)


async def get_current_user_optional(
    request: Request,
) -> Optional[AuthenticatedUser]:
    """Extract and resolve authenticated user from user_session_token cookie."""
    token = None

    if USER_COOKIE_NAME in request.cookies:
        token = request.cookies[USER_COOKIE_NAME]
    elif LEGACY_COOKIE_NAME in request.cookies:
        token = request.cookies[LEGACY_COOKIE_NAME]

    if not token:
        return None

    return resolve_user_from_token(token)


async def get_or_create_user_session(
    request: Request,
    response: Response,
) -> AuthenticatedUser:
    """Resolve current anonymous USER session or automatically create a new one."""
    user = await get_current_user_optional(request)
    if user:
        return user

    # Automatically provision a new anonymous USER identity
    raw_token = generate_secure_token()
    token_h = hash_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=USER_SESSION_EXPIRE_DAYS)

    new_user = create_anonymous_user(token_hash=token_h, expires_at=expires_at)
    set_user_cookie(response, raw_token)

    return AuthenticatedUser(
        id=new_user["id"],
        username=new_user["username"],
        role="USER",
        is_active=True,
        created_at=new_user["created_at"],
        is_anonymous=True,
    )


async def require_authenticated_user(
    request: Request,
    response: Response,
) -> AuthenticatedUser:
    """FastAPI dependency: resolve existing identity or automatically issue anonymous USER identity."""
    user = await get_current_user_optional(request)
    if user:
        return user

    admin_user = await get_current_admin_optional(request)
    if admin_user:
        return admin_user

    return await get_or_create_user_session(request, response)


async def require_admin(
    request: Request,
    bearer: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> AuthenticatedUser:
    """FastAPI dependency: strictly enforce server-side ADMIN authentication and authorization."""
    admin_user = await get_current_admin_optional(request, bearer)
    if not admin_user:
        user = await get_current_user_optional(request)
        if user:
            logger.warning(
                f"Forbidden admin access attempt by non-admin user '{user.username}' (role: {user.role})"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Administrative privileges are required for this action.",
            )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in with administrator credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not admin_user.is_admin:
        logger.warning(
            f"Forbidden admin access attempt by non-admin user '{admin_user.username}' (role: {admin_user.role})"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Administrative privileges are required for this action.",
        )

    return admin_user


async def require_user_or_admin(
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
) -> AuthenticatedUser:
    """Alias for require_authenticated_user."""
    return current_user
