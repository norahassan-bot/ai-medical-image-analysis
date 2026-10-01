"""FastAPI REST API Backend for AI Medical Image Analysis & Decision Support.

Architecture:
-------------
Next.js Frontend  -->  FastAPI REST API  -->  Task 8 Inference Engine  -->  PyTorch Model + Grad-CAM
                                         -->  Task 10 SQLite Database (Persistent History)
                                         -->  Task 19 Auth & RBAC (JWT & HTTP-Only Secure Cookies)

This API module coordinates validation, AI inference, authentication, RBAC, and SQLite persistence.
All deep learning inference is delegated to the reusable inference engine (src.inference.predict).
All user accounts, analysis history, and artifact metadata are stored in SQLite (database.database).
"""

import os
import sys
import json
import logging
from uuid import uuid4
from pathlib import Path
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, UploadFile, Query, status, HTTPException, Request, Response, Depends
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from dotenv import load_dotenv

# Ensure backend root is on sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from src.inference.predict import (
    ChestXRayPredictor,
    InferenceError,
    ImageValidationError,
    FileTooLargeError,
    UnsupportedFormatError,
    ModelNotLoadedError,
    SUPPORTED_IMAGE_EXTENSIONS,
    MAX_FILE_SIZE_BYTES,
    validate_and_load_image,
)
from database.database import (
    initialize_database,
    create_analysis,
    get_analysis_by_id,
    get_analysis_history,
    count_analyses,
    save_analysis_artifacts,
    create_prescription_analysis,
    get_prescription_analysis_by_id,
    get_prescription_history,
    count_prescription_analyses,
    save_prescription_artifacts,
    create_user,
    get_user_by_username,
    get_user_by_id,
    list_users,
    count_users,
    update_user_status,
    seed_admin_user,
    get_admin_statistics,
    invalidate_user_token,
)
from src.prescriptions.prescription_understanding import (
    PrescriptionUnderstandingService,
    PrescriptionUnderstandingResult,
)
from reports.report_generator import (
    generate_analysis_pdf,
    resolve_safe_image_path,
)
from api.auth import (
    AuthenticatedUser,
    hash_password,
    verify_password,
    create_access_token,
    set_admin_cookie,
    clear_admin_cookie,
    set_user_cookie,
    clear_user_cookie,
    set_auth_cookie,
    clear_auth_cookie,
    get_current_user_optional,
    get_current_admin_optional,
    require_authenticated_user,
    require_admin,
    require_user_or_admin,
    check_login_throttling,
    record_failed_login,
    record_successful_login,
)
from api.schemas import (
    HealthResponse,
    SystemInfoResponse,
    PredictionResponse,
    ExplainResponse,
    AnalysisResponse,
    AnalysisHistoryResponse,
    AnalysisHistoryItem,
    AnalysisDetailResponse,
    ErrorResponse,
    ErrorDetail,
    UserLoginRequest,
    UserRegisterRequest,
    UserPublic,
    AuthResponse,
    AdminUserListResponse,
    AdminUserItem,
    AdminStatsResponse,
    UpdateUserStatusRequest,
)

# Load environment variables
load_dotenv()

logger = logging.getLogger("MedicalAPI")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def get_checkpoint_path() -> Path:
    """Resolve model checkpoint path from environment or default locations."""
    env_path = os.getenv("MODEL_CHECKPOINT_PATH")
    if env_path:
        p = Path(env_path)
        if p.exists():
            return p

    default_paths = [
        backend_root / "models" / "best_model.pth",
        Path("backend/models/best_model.pth"),
        Path("models/best_model.pth"),
    ]
    for p in default_paths:
        if p.exists():
            return p
    return backend_root / "models" / "best_model.pth"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle: initialize SQLite database, seed admin, and load AI engine."""
    # 1. Initialize SQLite database schema and seed default admin account
    try:
        initialize_database()
        admin_user = seed_admin_user()
        if admin_user:
            logger.info(f"System admin user seeded/verified: username='{admin_user.get('username')}'")
    except Exception as e:
        logger.error(f"Failed to initialize SQLite database or seed admin: {e}")

    # 2. Initialize AI inference model
    ckpt_path = get_checkpoint_path()
    logger.info(f"Initializing AI Medical Predictor with checkpoint: {ckpt_path}")

    app.state.predictor = None
    app.state.model_loaded = False

    try:
        if ckpt_path.exists():
            predictor = ChestXRayPredictor(
                checkpoint_path=ckpt_path,
                model_version=os.getenv("MODEL_VERSION", "1.0.0"),
                auto_load=True,
            )
            app.state.predictor = predictor
            app.state.model_loaded = predictor.is_loaded
            logger.info("AI Inference Predictor initialized successfully.")
        else:
            logger.warning(f"Model checkpoint not found at {ckpt_path}. Running with model_loaded=False.")
    except Exception as e:
        logger.error(f"Failed to load AI model during startup: {e}")
        app.state.model_loaded = False

    yield

    # Teardown logic
    app.state.predictor = None
    app.state.model_loaded = False
    logger.info("AI Medical API shutdown complete.")


app = FastAPI(
    title="AI Medical Image Analysis & Clinical Decision Support API",
    description=(
        "Production-ready FastAPI backend for Chest X-Ray AI classification (NORMAL vs PNEUMONIA), "
        "Explainable AI using Grad-CAM visual heatmaps, role-based access control (ADMIN vs USER), "
        "and persistent SQLite analysis history.\n\n"
        "**Clinical Disclaimer**: This AI system is designed for medical research, education, "
        "and clinical decision support only. It does NOT constitute an autonomous medical diagnosis."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# -----------------------------------------------------------------------------
# Security Headers & CORS Middleware
# -----------------------------------------------------------------------------
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add standard security response headers across all HTTP responses."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response


default_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

env_cors = os.getenv("CORS_ORIGINS") or os.getenv("CORS_ALLOWED_ORIGINS")
if env_cors:
    try:
        parsed = json.loads(env_cors)
        if isinstance(parsed, list):
            default_origins = list(set(default_origins + parsed))
        elif isinstance(parsed, str):
            default_origins = list(set(default_origins + [parsed]))
    except Exception:
        parts = [p.strip() for p in env_cors.split(",") if p.strip()]
        if parts:
            default_origins = list(set(default_origins + parts))

app.add_middleware(
    CORSMiddleware,
    allow_origins=default_origins,
    allow_credentials=True,  # Crucial for secure cookie authentication
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# -----------------------------------------------------------------------------
# Centralized Error Handlers
# -----------------------------------------------------------------------------
@app.exception_handler(FileTooLargeError)
async def file_too_large_exception_handler(request: Request, exc: FileTooLargeError):
    """Handle oversized uploaded files with HTTP 413 Payload Too Large."""
    return JSONResponse(
        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        content=ErrorResponse(
            error=ErrorDetail(
                code="FILE_TOO_LARGE",
                message=str(exc),
            )
        ).model_dump(),
    )


@app.exception_handler(UnsupportedFormatError)
async def unsupported_format_exception_handler(request: Request, exc: UnsupportedFormatError):
    """Handle unsupported file extensions and MIME types with HTTP 400."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ErrorResponse(
            error=ErrorDetail(
                code="UNSUPPORTED_FORMAT",
                message=str(exc),
            )
        ).model_dump(),
    )


@app.exception_handler(ImageValidationError)
async def image_validation_exception_handler(request: Request, exc: ImageValidationError):
    """Handle invalid/corrupt uploaded images with HTTP 400."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ErrorResponse(
            error=ErrorDetail(
                code="INVALID_IMAGE",
                message=str(exc),
            )
        ).model_dump(),
    )


@app.exception_handler(ModelNotLoadedError)
async def model_not_loaded_exception_handler(request: Request, exc: ModelNotLoadedError):
    """Handle missing or uninitialized model checkpoint with HTTP 503."""
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=ErrorResponse(
            error=ErrorDetail(
                code="MODEL_NOT_AVAILABLE",
                message="AI model checkpoint is not loaded or currently unavailable.",
            )
        ).model_dump(),
    )


@app.exception_handler(InferenceError)
async def inference_exception_handler(request: Request, exc: InferenceError):
    """Handle general inference pipeline failures with HTTP 500."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error=ErrorDetail(
                code="INFERENCE_ERROR",
                message="An error occurred during AI inference processing.",
            )
        ).model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle HTTP request schema validation errors cleanly."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error=ErrorDetail(
                code="VALIDATION_ERROR",
                message="Invalid request parameters or missing required fields.",
                details=exc.errors(),
            )
        ).model_dump(),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle general HTTP exceptions with standard error structure."""
    code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        413: "FILE_TOO_LARGE",
        422: "VALIDATION_ERROR",
        429: "TOO_MANY_REQUESTS",
        500: "INTERNAL_SERVER_ERROR",
        503: "SERVICE_UNAVAILABLE",
    }
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=ErrorDetail(
                code=code_map.get(exc.status_code, "HTTP_ERROR"),
                message=str(exc.detail),
            )
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Sanitize all unexpected server exceptions into clean HTTP 500 responses."""
    logger.error(f"Unhandled internal server error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error=ErrorDetail(
                code="INTERNAL_SERVER_ERROR",
                message="An unexpected server error occurred during request execution.",
            )
        ).model_dump(),
    )


# -----------------------------------------------------------------------------
# Helper Utilities
# -----------------------------------------------------------------------------
def get_active_predictor() -> ChestXRayPredictor:
    """Retrieve active ChestXRayPredictor instance or raise ModelNotLoadedError."""
    predictor = getattr(app.state, "predictor", None)
    if predictor is None or not predictor.is_loaded:
        raise ModelNotLoadedError("AI inference engine is not ready.")
    return predictor


def get_prescription_service() -> PrescriptionUnderstandingService:
    """Retrieve active PrescriptionUnderstandingService singleton instance."""
    service = getattr(app.state, "prescription_service", None)
    if service is None:
        service = PrescriptionUnderstandingService()
        app.state.prescription_service = service
    return service


def validate_analysis_id_format(analysis_id: str) -> str:
    """Validate that analysis_id contains only safe alphanumeric and dash/underscore characters.

    Rejects path traversal (e.g. '../', '..\\') and malformed inputs with HTTP 400.
    """
    if not analysis_id or not isinstance(analysis_id, str):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid analysis ID.")
    if ".." in analysis_id or "/" in analysis_id or "\\" in analysis_id or "\x00" in analysis_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid analysis ID format.")
    if not all(c.isalnum() or c in "-_" for c in analysis_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid analysis ID format.")
    if len(analysis_id) > 128:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Analysis ID exceeds maximum length.")
    return analysis_id


async def validate_uploaded_file(file: UploadFile) -> bytes:
    """Validate uploaded file existence, filename extension, size limits, and content."""
    if not file or not file.filename:
        raise ImageValidationError("No image file provided in upload request.")

    # Sanitize user filename
    safe_filename = Path(file.filename).name
    ext = Path(safe_filename).suffix.lower()
    if ext not in SUPPORTED_IMAGE_EXTENSIONS:
        raise UnsupportedFormatError(
            f"Unsupported file format '{ext}'. Allowed formats: {sorted(list(SUPPORTED_IMAGE_EXTENSIONS))}"
        )

    contents = await file.read()
    if len(contents) == 0:
        raise ImageValidationError("Uploaded image file is empty (0 bytes).")
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise FileTooLargeError(
            f"File size ({len(contents) / (1024 * 1024):.1f} MB) exceeds maximum allowed limit ({MAX_FILE_SIZE_BYTES / (1024 * 1024):.0f} MB)."
        )

    # Perform content-based validation with Pillow
    validate_and_load_image(contents, max_file_size_bytes=MAX_FILE_SIZE_BYTES)

    return contents


# -----------------------------------------------------------------------------
# Authentication Endpoints (Task 21 - Secure Token & Admin Login)
# -----------------------------------------------------------------------------
@app.post(
    "/auth/login",
    response_model=AuthResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin Login",
    description="Authenticate administrator with username and password, issuing a signed admin session.",
    tags=["Authentication"],
)
@app.post(
    "/api/v1/auth/login",
    response_model=AuthResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def login_user(
    body: UserLoginRequest,
    request: Request,
    response: Response,
) -> AuthResponse:
    """Validate administrator credentials, handle brute-force throttling, and issue signed Admin token."""
    # 1. Brute-force throttling check
    check_login_throttling(request, body.username)

    # 2. Query admin user from database
    user = get_user_by_username(body.username)
    if not user or user.get("role") != "ADMIN" or not user.get("password_hash"):
        record_failed_login(request, body.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid administrator username or password.",
        )

    # 3. Check account active status
    if not user.get("is_active", True):
        record_failed_login(request, body.username)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been deactivated. Please contact the system administrator.",
        )

    # 4. Verify password hash securely
    if not verify_password(body.password, user["password_hash"]):
        record_failed_login(request, body.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid administrator username or password.",
        )

    # 5. Record successful login and clear throttling history
    record_successful_login(request, body.username)

    # 6. Issue secure JWT access token for Admin
    token = create_access_token(
        user_id=user["id"],
        username=user["username"],
        role="ADMIN",
    )

    # 7. Set secure HTTP-only cookie on response for Admin session
    set_admin_cookie(response, token)

    return AuthResponse(
        user=UserPublic(
            id=user["id"],
            username=user["username"],
            role="ADMIN",
            is_active=bool(user.get("is_active", True)),
            created_at=user.get("created_at"),
        ),
        message="Administrator authentication successful.",
    )


@app.post(
    "/auth/register",
    status_code=status.HTTP_400_BAD_REQUEST,
    summary="Disabled User Registration",
    description="User registration is disabled. Secure anonymous identities are issued automatically.",
    tags=["Authentication"],
)
@app.post(
    "/api/v1/auth/register",
    status_code=status.HTTP_400_BAD_REQUEST,
    include_in_schema=False,
)
def register_user() -> Dict[str, str]:
    """Reject traditional user registration since anonymous token-based identity is active."""
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="User registration is disabled. Anonymous sessions are automatically established.",
    )


@app.post(
    "/auth/admin/logout",
    status_code=status.HTTP_200_OK,
    summary="Admin Logout",
    description="Terminate active administrator session and clear admin session cookie.",
    tags=["Authentication"],
)
@app.post(
    "/api/v1/auth/admin/logout",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def logout_admin(
    response: Response,
) -> Dict[str, str]:
    """Clear admin session cookie without affecting anonymous USER session."""
    clear_admin_cookie(response)
    return {"message": "Administrator logged out successfully."}


@app.post(
    "/auth/logout",
    status_code=status.HTTP_200_OK,
    summary="Logout / End Session",
    description="Invalidate active session and clear authentication cookies.",
    tags=["Authentication"],
)
@app.post(
    "/api/v1/auth/logout",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
@app.post(
    "/auth/session/reset",
    status_code=status.HTTP_200_OK,
    summary="Reset User Session",
    description="Invalidate current anonymous user token and clear user session cookie.",
    tags=["Authentication"],
)
@app.post(
    "/api/v1/auth/session/reset",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def logout_user(
    request: Request,
    response: Response,
) -> Dict[str, str]:
    """Invalidate anonymous user session in database and clear user auth cookie."""
    user = await get_current_user_optional(request)
    if user and not user.is_admin:
        invalidate_user_token(user.id)
    clear_user_cookie(response)
    return {"message": "User session invalidated successfully."}


@app.get(
    "/auth/admin/me",
    response_model=UserPublic,
    status_code=status.HTTP_200_OK,
    summary="Get Authenticated Admin Profile",
    description="Return public identity of currently authenticated administrator session.",
    tags=["Authentication"],
)
@app.get(
    "/api/v1/auth/admin/me",
    response_model=UserPublic,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_current_admin_profile(
    admin_user: AuthenticatedUser = Depends(require_admin),
) -> UserPublic:
    """Return profile details strictly for the active administrator session."""
    return UserPublic(
        id=admin_user.id,
        username=admin_user.username,
        role=admin_user.role,
        is_active=bool(admin_user.is_active),
        created_at=admin_user.created_at,
    )


@app.get(
    "/auth/session",
    response_model=UserPublic,
    status_code=status.HTTP_200_OK,
    summary="Get or Establish Session",
    description="Return active session profile or automatically provision a new anonymous USER session.",
    tags=["Authentication"],
)
@app.get(
    "/api/v1/auth/session",
    response_model=UserPublic,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
@app.get(
    "/auth/me",
    response_model=UserPublic,
    status_code=status.HTTP_200_OK,
    summary="Get Authenticated User Profile",
    description="Return public identity and role of currently authenticated session.",
    tags=["Authentication"],
)
@app.get(
    "/api/v1/auth/me",
    response_model=UserPublic,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_current_user_profile(
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
) -> UserPublic:
    """Return profile details for the active user/admin session."""
    return UserPublic(
        id=current_user.id,
        username=current_user.username,
        role=current_user.role,
        is_active=bool(current_user.is_active),
        created_at=current_user.created_at,
    )


# -----------------------------------------------------------------------------
# Admin Management Endpoints (Task 19 RBAC)
# -----------------------------------------------------------------------------
@app.get(
    "/admin/statistics",
    response_model=AdminStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin Platform Statistics",
    description="Aggregated platform statistics and diagnostic metrics (ADMIN only).",
    tags=["Administration"],
)
@app.get(
    "/api/v1/admin/statistics",
    response_model=AdminStatsResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_admin_stats(
    admin_user: Dict[str, Any] = Depends(require_admin),
) -> AdminStatsResponse:
    """Return aggregated platform metrics for the administrator dashboard."""
    stats = get_admin_statistics()
    predictor = getattr(app.state, "predictor", None)
    return AdminStatsResponse(
        total_analyses=stats.get("total_analyses", 0),
        normal_count=stats.get("normal_count", 0),
        pneumonia_count=stats.get("pneumonia_count", 0),
        total_users=stats.get("total_users", 0),
        active_users=stats.get("active_users", 0),
        admin_users=stats.get("admin_users", 0),
        regular_users=stats.get("regular_users", 0),
        avg_confidence=stats.get("avg_confidence", 0.0),
        model_version=predictor.model_version if (predictor and predictor.is_loaded) else "1.0.0",
        architecture=predictor.model.arch_key if (predictor and predictor.model) else "densenet121",
        environment=os.getenv("ENVIRONMENT", "development"),
    )


@app.get(
    "/admin/users",
    response_model=AdminUserListResponse,
    status_code=status.HTTP_200_OK,
    summary="List All Platform Users",
    description="Retrieve list of all registered users with activity metrics (ADMIN only).",
    tags=["Administration"],
)
@app.get(
    "/api/v1/admin/users",
    response_model=AdminUserListResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_admin_users(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    admin_user: Dict[str, Any] = Depends(require_admin),
) -> AdminUserListResponse:
    """List registered users with roles and status for admin management."""
    users, total = list_users(limit=limit, offset=offset)
    return AdminUserListResponse(
        users=[
            AdminUserItem(
                id=u["id"],
                username=u["username"],
                role=u["role"],
                is_active=bool(u.get("is_active", True)),
                created_at=u.get("created_at", ""),
                analysis_count=u.get("analysis_count", 0),
            )
            for u in users
        ],
        total=total,
    )


@app.post(
    "/admin/users/{user_id}/status",
    status_code=status.HTTP_200_OK,
    summary="Toggle User Active Status",
    description="Activate or deactivate a user account (ADMIN only).",
    tags=["Administration"],
)
@app.post(
    "/api/v1/admin/users/{user_id}/status",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def set_user_status(
    user_id: str,
    body: UpdateUserStatusRequest,
    admin_user: Dict[str, Any] = Depends(require_admin),
) -> Dict[str, Any]:
    """Activate or deactivate user accounts."""
    target_user = get_user_by_id(user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target user not found.",
        )

    # Prevent admin from deactivating themselves
    if target_user["id"] == admin_user["id"] and not body.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Administrators cannot deactivate their own active account.",
        )

    updated = update_user_status(user_id, body.is_active)
    return {
        "id": updated["id"],
        "username": updated["username"],
        "is_active": bool(updated["is_active"]),
        "message": f"User status updated to {'active' if body.is_active else 'inactive'}.",
    }


@app.get(
    "/admin/analyses",
    response_model=AnalysisHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin View of All Platform Analyses",
    description="Retrieve all clinical analyses across all users (ADMIN only).",
    tags=["Administration"],
)
@app.get(
    "/api/v1/admin/analyses",
    response_model=AnalysisHistoryResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_admin_analyses(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin_user: Dict[str, Any] = Depends(require_admin),
) -> AnalysisHistoryResponse:
    """Retrieve all historical analyses across all users."""
    items, total = get_analysis_history(limit=limit, offset=offset, owner_user_id=None)
    return AnalysisHistoryResponse(
        items=[
            AnalysisHistoryItem(
                analysis_id=item["analysis_id"],
                created_at=item["created_at"],
                filename=item.get("filename"),
                prediction=item["prediction"],
                confidence=item["confidence"],
                model_version=item["model_version"],
                architecture=item.get("architecture"),
                image_reference=item.get("image_reference"),
                overlay_reference=item.get("overlay_reference"),
                status=item.get("status", "completed"),
            )
            for item in items
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@app.get(
    "/admin/system",
    response_model=SystemInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin System Information",
    description="Detailed operational environment and configuration diagnostics (ADMIN only).",
    tags=["Administration"],
)
@app.get(
    "/api/v1/admin/system",
    response_model=SystemInfoResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_admin_system_info(
    admin_user: Dict[str, Any] = Depends(require_admin),
) -> SystemInfoResponse:
    """Return detailed system information for administrative inspection."""
    return SystemInfoResponse(
        app_name="AI Medical Image Analysis Platform",
        version="1.0.0",
        environment=os.getenv("ENVIRONMENT", "development"),
        docs_url="/docs",
        cors_allowed_origins=default_origins,
    )


# -----------------------------------------------------------------------------
# Core Public & Protected Application Endpoints
# -----------------------------------------------------------------------------
@app.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check endpoint",
    tags=["System"],
)
@app.get(
    "/api/v1/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="API v1 Health check endpoint",
    tags=["System"],
)
def get_health() -> HealthResponse:
    """Return backend operational status and AI model readiness."""
    predictor: Optional[ChestXRayPredictor] = getattr(app.state, "predictor", None)
    is_loaded = (predictor is not None and predictor.is_loaded)

    return HealthResponse(
        status="healthy",
        model_loaded=is_loaded,
        model_version=predictor.model_version if is_loaded else None,
        architecture=predictor.model.arch_key if is_loaded and predictor.model else None,
        device=str(predictor.target_device) if is_loaded else None,
    )


@app.get(
    "/api/v1/system/info",
    response_model=SystemInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="System and Environment Information",
    tags=["System"],
)
def get_system_info() -> SystemInfoResponse:
    """Return system information and metadata for dashboard diagnostics."""
    return SystemInfoResponse(
        app_name="AI Medical Image Analysis Platform",
        version="1.0.0",
        environment=os.getenv("ENVIRONMENT", "development"),
        docs_url="/docs",
        cors_allowed_origins=default_origins,
    )


@app.post(
    "/predict",
    response_model=PredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="Chest X-Ray Diagnostic Prediction",
    description="Analyze an uploaded chest X-ray image and return binary diagnosis (NORMAL vs PNEUMONIA) with confidence.",
    tags=["AI Inference"],
)
@app.post(
    "/api/v1/predict",
    response_model=PredictionResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def predict_xray(
    file: UploadFile = File(..., description="Chest radiograph image (PNG, JPG, JPEG)"),
    current_user: Dict[str, Any] = Depends(require_authenticated_user),
):
    """Execute standard AI inference on an uploaded chest X-ray scan."""
    predictor = get_active_predictor()
    image_bytes = await validate_uploaded_file(file)

    result = predictor.predict(image_bytes)

    return PredictionResponse(
        prediction=result.prediction,
        predicted_index=result.predicted_index,
        confidence=result.confidence,
        probabilities=result.probabilities,
        model_version=result.model_version,
        architecture=result.architecture,
        device=result.device,
        inference_time_ms=result.inference_time_ms,
        class_mapping=result.class_mapping,
    )


@app.post(
    "/explain",
    response_model=ExplainResponse,
    status_code=status.HTTP_200_OK,
    summary="Grad-CAM Visual Explainability",
    description="Compute Grad-CAM activation heatmaps and overlay visualizations for the uploaded radiograph.",
    tags=["Explainable AI"],
)
@app.post(
    "/api/v1/explain",
    response_model=ExplainResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def explain_xray(
    file: UploadFile = File(..., description="Chest radiograph image (PNG, JPG, JPEG)"),
    target_class: Optional[int] = Form(None, description="Optional target class (0=NORMAL, 1=PNEUMONIA). Default: predicted class"),
    alpha: float = Form(0.45, ge=0.0, le=1.0, description="Overlay blending transparency factor"),
    current_user: Dict[str, Any] = Depends(require_authenticated_user),
):
    """Generate Grad-CAM activation heatmap and alpha-blended overlay for an uploaded X-ray."""
    predictor = get_active_predictor()
    image_bytes = await validate_uploaded_file(file)

    result = predictor.predict_with_explanation(
        image_input=image_bytes,
        target_class=target_class,
        alpha=alpha,
        encode_base64=True,
    )

    return ExplainResponse(
        prediction=result.prediction,
        predicted_index=result.predicted_index,
        confidence=result.confidence,
        probabilities=result.probabilities,
        model_version=result.model_version,
        architecture=result.architecture,
        device=result.device,
        inference_time_ms=result.inference_time_ms,
        target_class=result.target_class,
        original_base64=result.original_base64,
        heatmap_base64=result.heatmap_base64,
        overlay_base64=result.overlay_base64,
        original_dimensions=result.original_dimensions,
        disclaimer=result.disclaimer,
    )


@app.post(
    "/analyze",
    response_model=AnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Complete Diagnostic, Explainability, & Persistence Analysis",
    description="Full diagnostic pipeline: runs prediction, Grad-CAM overlays, and persists the analysis record into SQLite with ownership.",
    tags=["AI Inference", "Explainable AI", "History"],
)
@app.post(
    "/api/v1/analyze",
    response_model=AnalysisResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def analyze_xray(
    file: UploadFile = File(..., description="Chest radiograph image (PNG, JPG, JPEG)"),
    target_class: Optional[int] = Form(None, description="Optional target class (0=NORMAL, 1=PNEUMONIA)"),
    alpha: float = Form(0.45, ge=0.0, le=1.0, description="Overlay blending transparency factor"),
    current_user: Dict[str, Any] = Depends(require_authenticated_user),
):
    """Execute complete analysis workflow and persist record to SQLite database with authenticated user ownership."""
    predictor = get_active_predictor()
    image_bytes = await validate_uploaded_file(file)

    # 1. AI Forward Pass & Explainability Inference (Task 8)
    result = predictor.predict_with_explanation(
        image_input=image_bytes,
        target_class=target_class,
        alpha=alpha,
        encode_base64=True,
    )

    # 2. Generate unique UUID and safe artifact references (Task 10)
    analysis_id = str(uuid4())
    artifact_refs = save_analysis_artifacts(
        analysis_id=analysis_id,
        original_bytes=image_bytes,
        original_filename=file.filename,
        heatmap_base64=result.heatmap_base64,
        overlay_base64=result.overlay_base64,
    )

    # 3. Persist analysis record in SQLite with server-derived owner_user_id
    saved_record = create_analysis({
        "analysis_id": analysis_id,
        "filename": Path(file.filename).name if file.filename else None,
        "prediction": result.prediction,
        "predicted_index": result.predicted_index,
        "confidence": result.confidence,
        "probabilities": result.probabilities,
        "model_version": result.model_version,
        "architecture": result.architecture,
        "device": result.device,
        "inference_time_ms": result.inference_time_ms,
        "target_class": result.target_class,
        "image_reference": artifact_refs.get("image_reference"),
        "heatmap_reference": artifact_refs.get("heatmap_reference"),
        "overlay_reference": artifact_refs.get("overlay_reference"),
        "original_dimensions": result.original_dimensions,
        "owner_user_id": current_user["id"],  # Derived solely from server authenticated session
        "status": "completed",
    })

    return AnalysisResponse(
        analysis_id=saved_record["analysis_id"],
        created_at=saved_record["created_at"],
        filename=saved_record["filename"],
        prediction=result.prediction,
        predicted_index=result.predicted_index,
        confidence=result.confidence,
        probabilities=result.probabilities,
        model_version=result.model_version,
        architecture=result.architecture,
        device=result.device,
        inference_time_ms=result.inference_time_ms,
        target_class=result.target_class,
        image_reference=saved_record["image_reference"],
        heatmap_reference=saved_record["heatmap_reference"],
        overlay_reference=saved_record["overlay_reference"],
        original_base64=result.original_base64,
        heatmap_base64=result.heatmap_base64,
        overlay_base64=result.overlay_base64,
        original_dimensions=result.original_dimensions,
        class_mapping=result.class_mapping,
        disclaimer=result.disclaimer,
    )


@app.get(
    "/history",
    response_model=AnalysisHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="List Clinical Analysis History",
    description="Retrieve paginated list of analyses. Regular users view their own; administrators view all.",
    tags=["History"],
)
@app.get(
    "/api/v1/history",
    response_model=AnalysisHistoryResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_history(
    limit: int = Query(50, ge=1, le=100, description="Max number of records per page"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    current_user: Dict[str, Any] = Depends(require_authenticated_user),
) -> AnalysisHistoryResponse:
    """Retrieve paginated analysis history from SQLite with strict user isolation."""
    # Admins see all records; regular users strictly see their own records
    owner_filter = None if current_user.get("role") == "ADMIN" else current_user["id"]
    items, total = get_analysis_history(limit=limit, offset=offset, owner_user_id=owner_filter)

    return AnalysisHistoryResponse(
        items=[
            AnalysisHistoryItem(
                analysis_id=item["analysis_id"],
                created_at=item["created_at"],
                filename=item.get("filename"),
                prediction=item["prediction"],
                confidence=item["confidence"],
                model_version=item["model_version"],
                architecture=item.get("architecture"),
                image_reference=item.get("image_reference"),
                overlay_reference=item.get("overlay_reference"),
                status=item.get("status", "completed"),
            )
            for item in items
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@app.get(
    "/history/{analysis_id}",
    response_model=AnalysisDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Analysis Detail by ID",
    description="Retrieve a single persistent analysis record by UUID with ownership verification.",
    tags=["History"],
)
@app.get(
    "/api/v1/history/{analysis_id}",
    response_model=AnalysisDetailResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_history_detail(
    analysis_id: str,
    current_user: Dict[str, Any] = Depends(require_authenticated_user),
) -> AnalysisDetailResponse:
    """Retrieve detailed record of a past analysis with strict authorization checks."""
    validate_analysis_id_format(analysis_id)
    record = get_analysis_by_id(analysis_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis with ID '{analysis_id}' not found.",
        )

    # Authorization check: ADMIN can access any record; USER can only access their own
    if current_user.get("role") != "ADMIN":
        record_owner = record.get("owner_user_id")
        if record_owner and record_owner != current_user["id"]:
            logger.warning(
                f"Unauthorized analysis access attempt by user '{current_user['username']}' for analysis '{analysis_id}'"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You do not have permission to view this analysis.",
            )

    return AnalysisDetailResponse(
        analysis_id=record["analysis_id"],
        created_at=record["created_at"],
        filename=record.get("filename"),
        prediction=record["prediction"],
        predicted_index=record["predicted_index"],
        confidence=record["confidence"],
        probabilities=record.get("probabilities", {}),
        model_version=record["model_version"],
        architecture=record["architecture"],
        device=record["device"],
        inference_time_ms=record["inference_time_ms"],
        target_class=record["target_class"],
        image_reference=record.get("image_reference"),
        heatmap_reference=record.get("heatmap_reference"),
        overlay_reference=record.get("overlay_reference"),
        original_dimensions=record.get("original_dimensions"),
        status=record.get("status", "completed"),
    )


@app.get(
    "/history/{analysis_id}/report",
    summary="Download Clinical PDF Report",
    description="Generate and stream clinical PDF report with ownership authorization.",
    tags=["Reports", "History"],
    response_class=FileResponse,
)
@app.get(
    "/api/v1/history/{analysis_id}/report",
    response_class=FileResponse,
    include_in_schema=False,
)
def download_analysis_report(
    analysis_id: str,
    current_user: Dict[str, Any] = Depends(require_authenticated_user),
) -> FileResponse:
    """Retrieve or generate and stream PDF report for the given analysis ID with RBAC."""
    validate_analysis_id_format(analysis_id)
    record = get_analysis_by_id(analysis_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis with ID '{analysis_id}' not found.",
        )

    # Authorization check
    if current_user.get("role") != "ADMIN":
        record_owner = record.get("owner_user_id")
        if record_owner and record_owner != current_user["id"]:
            logger.warning(
                f"Unauthorized report download attempt by user '{current_user['username']}' for analysis '{analysis_id}'"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You do not have permission to download this report.",
            )

    try:
        pdf_path = generate_analysis_pdf(analysis_id)
    except Exception as e:
        logger.error(f"Failed to generate PDF report for {analysis_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate clinical PDF report.",
        )

    if not pdf_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generated report file not found on server.",
        )

    safe_filename = f"analysis_{analysis_id}.pdf"
    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=safe_filename,
        headers={
            "Content-Disposition": f'attachment; filename="{safe_filename}"'
        },
    )


@app.get(
    "/history/{analysis_id}/artifacts/{artifact_type}",
    summary="Get Analysis Image Artifact",
    description="Retrieve stored radiograph, heatmap, or overlay artifact by type with authorization.",
    tags=["History"],
    response_class=FileResponse,
)
@app.get(
    "/api/v1/history/{analysis_id}/artifacts/{artifact_type}",
    response_class=FileResponse,
    include_in_schema=False,
)
def get_analysis_artifact(
    analysis_id: str,
    artifact_type: str,
    current_user: Dict[str, Any] = Depends(require_authenticated_user),
) -> FileResponse:
    """Stream stored image artifact safely with user authorization."""
    validate_analysis_id_format(analysis_id)
    if not artifact_type or not all(c.isalnum() or c in "-_" for c in artifact_type) or len(artifact_type) > 32:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid artifact type format.",
        )

    record = get_analysis_by_id(analysis_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis with ID '{analysis_id}' not found.",
        )

    # Authorization check
    if current_user.get("role") != "ADMIN":
        record_owner = record.get("owner_user_id")
        if record_owner and record_owner != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You do not have permission to view this artifact.",
            )

    ref_map = {
        "image": record.get("image_reference"),
        "original": record.get("image_reference"),
        "heatmap": record.get("heatmap_reference"),
        "overlay": record.get("overlay_reference"),
    }

    if artifact_type not in ref_map or not ref_map[artifact_type]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact '{artifact_type}' not found for analysis '{analysis_id}'.",
        )

    resolved_path = resolve_safe_image_path(ref_map[artifact_type])
    if not resolved_path or not resolved_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact file not found on server for analysis '{analysis_id}'.",
        )

    media_type = "image/jpeg" if resolved_path.suffix.lower() in [".jpg", ".jpeg"] else "image/png"
    return FileResponse(path=str(resolved_path), media_type=media_type)


# -----------------------------------------------------------------------------
# Prescription Reader & Analysis Endpoints (Task 25 & Task 26)
# -----------------------------------------------------------------------------
@app.post(
    "/prescription/analyze",
    status_code=status.HTTP_200_OK,
    summary="Prescription Image Analysis & Understanding",
    description="Analyze prescription handwriting, retrieve verified educational drug facts, and extract explicit written instructions.",
    tags=["Prescription Reader", "History"],
)
@app.post(
    "/api/v1/prescription/analyze",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def analyze_prescription_endpoint(
    file: UploadFile = File(..., description="Prescription image (JPG, JPEG, PNG, WEBP)"),
    current_user: Dict[str, Any] = Depends(require_authenticated_user),
):
    """Execute prescription recognition pipeline, match medications, retrieve indications, parse instructions, and persist record."""
    service = get_prescription_service()
    image_bytes = await validate_uploaded_file(file)

    # Execute full understanding on the image
    result = service.understand_prescription(image_bytes)

    analysis_id = str(uuid4())
    artifact_refs = save_prescription_artifacts(
        analysis_id=analysis_id,
        original_bytes=image_bytes,
        original_filename=file.filename,
    )

    saved_record = create_prescription_analysis({
        "analysis_id": analysis_id,
        "filename": Path(file.filename).name if file.filename else None,
        "total_medications": result.total_medications,
        "status": result.status,
        "processing_time_ms": result.processing_time_ms,
        "image_reference": artifact_refs.get("image_reference"),
        "owner_user_id": current_user["id"],
        "result": result.model_dump(),
    })

    return {
        "analysis_id": saved_record["analysis_id"],
        "created_at": saved_record["created_at"],
        "filename": saved_record["filename"],
        "image_reference": saved_record["image_reference"],
        "status": saved_record["status"],
        "total_medications": saved_record["total_medications"],
        "processing_time_ms": saved_record["processing_time_ms"],
        "result": saved_record["result"],
    }


@app.get(
    "/prescription/history",
    status_code=status.HTTP_200_OK,
    summary="List Prescription History",
    description="Retrieve paginated prescription history. Users view their own; admins view all.",
    tags=["Prescription Reader", "History"],
)
@app.get(
    "/api/v1/prescription/history",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_user_prescription_history_endpoint(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(require_authenticated_user),
):
    """Retrieve user-isolated or admin-wide prescription analysis history."""
    owner_filter = None if current_user.get("role") == "ADMIN" else current_user["id"]
    items, total = get_prescription_history(limit=limit, offset=offset, owner_user_id=owner_filter)
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@app.get(
    "/prescription/history/{analysis_id}",
    status_code=status.HTTP_200_OK,
    summary="Get Prescription Analysis Detail",
    tags=["Prescription Reader", "History"],
)
@app.get(
    "/api/v1/prescription/history/{analysis_id}",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_prescription_detail_endpoint(
    analysis_id: str,
    current_user: Dict[str, Any] = Depends(require_authenticated_user),
):
    """Retrieve detailed prescription understanding result with ownership check."""
    validate_analysis_id_format(analysis_id)
    record = get_prescription_analysis_by_id(analysis_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prescription analysis with ID '{analysis_id}' not found.",
        )
    if current_user.get("role") != "ADMIN":
        record_owner = record.get("owner_user_id")
        if record_owner and record_owner != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You do not have permission to view this prescription analysis.",
            )
    return record


@app.get(
    "/prescription/history/{analysis_id}/artifacts/{artifact_type}",
    summary="Get Prescription Image Artifact",
    tags=["Prescription Reader", "History"],
    response_class=FileResponse,
)
@app.get(
    "/api/v1/prescription/history/{analysis_id}/artifacts/{artifact_type}",
    response_class=FileResponse,
    include_in_schema=False,
)
def get_prescription_artifact_endpoint(
    analysis_id: str,
    artifact_type: str,
    current_user: Dict[str, Any] = Depends(require_authenticated_user),
) -> FileResponse:
    """Stream saved prescription image artifact."""
    validate_analysis_id_format(analysis_id)
    record = get_prescription_analysis_by_id(analysis_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prescription analysis with ID '{analysis_id}' not found.",
        )
    if current_user.get("role") != "ADMIN":
        record_owner = record.get("owner_user_id")
        if record_owner and record_owner != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You do not have permission to view this artifact.",
            )
    image_ref = record.get("image_reference")
    if not image_ref:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image artifact not found for prescription analysis '{analysis_id}'.",
        )
    resolved_path = resolve_safe_image_path(image_ref)
    if not resolved_path or not resolved_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prescription artifact file not found on server.",
        )
    media_type = "image/jpeg" if resolved_path.suffix.lower() in [".jpg", ".jpeg"] else "image/png"
    return FileResponse(path=str(resolved_path), media_type=media_type)


@app.get(
    "/admin/prescriptions",
    status_code=status.HTTP_200_OK,
    summary="Admin Platform-Wide Prescription Analyses",
    tags=["Administration"],
)
@app.get(
    "/api/v1/admin/prescriptions",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_admin_prescriptions_endpoint(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin_user: Dict[str, Any] = Depends(require_admin),
):
    """List all prescription records across the entire platform for admin audit."""
    items, total = get_prescription_history(limit=limit, offset=offset, owner_user_id=None)
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("api.main:app", host=host, port=port, reload=True)
