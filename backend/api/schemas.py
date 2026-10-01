"""Pydantic request and response schemas for the AI Medical Image Analysis REST API."""

from typing import Dict, Any, Optional, List, Tuple
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response schema."""
    status: str = Field(..., description="API operational status (e.g. 'healthy')")
    model_loaded: bool = Field(..., description="Whether the PyTorch model checkpoint is successfully loaded")
    model_version: Optional[str] = Field(None, description="Active model version identifier")
    architecture: Optional[str] = Field(None, description="Underlying CNN architecture")
    device: Optional[str] = Field(None, description="Execution device (CPU or CUDA)")


class SystemInfoResponse(BaseModel):
    """System and environment metadata schema."""
    app_name: str
    version: str
    environment: str
    docs_url: str
    cors_allowed_origins: List[str]


class PredictionResponse(BaseModel):
    """Diagnostic prediction response schema for standard inference."""
    prediction: str = Field(..., description="Predicted diagnosis class ('NORMAL' or 'PNEUMONIA')")
    predicted_index: int = Field(..., description="Integer index of the predicted class (0 or 1)")
    confidence: float = Field(..., description="Confidence score in range [0.0, 1.0]")
    probabilities: Dict[str, float] = Field(
        ..., description="Full class probability distribution (e.g. {'NORMAL': 0.12, 'PNEUMONIA': 0.88})"
    )
    model_version: str = Field(..., description="Semantic version of the AI model")
    architecture: str = Field(..., description="CNN backbone architecture name")
    device: str = Field(..., description="Inference hardware device")
    inference_time_ms: float = Field(..., description="Model forward-pass latency in milliseconds")
    class_mapping: Dict[str, int] = Field(
        default_factory=lambda: {"NORMAL": 0, "PNEUMONIA": 1},
        description="Canonical label to index mapping"
    )
    disclaimer: str = Field(
        default="AI predictions are for clinical decision support and research only. Not an autonomous medical diagnosis.",
        description="Regulatory medical disclaimer"
    )


class ExplainResponse(BaseModel):
    """Explainability response schema with Grad-CAM visual heatmaps."""
    prediction: str = Field(..., description="Predicted diagnosis class")
    predicted_index: int = Field(..., description="Integer index of the predicted class")
    confidence: float = Field(..., description="Confidence score in range [0.0, 1.0]")
    probabilities: Dict[str, float] = Field(..., description="Full class probability distribution")
    model_version: str = Field(..., description="Semantic version of the AI model")
    architecture: str = Field(..., description="CNN backbone architecture name")
    device: str = Field(..., description="Inference hardware device")
    inference_time_ms: float = Field(..., description="Total inference and Grad-CAM latency in milliseconds")
    target_class: str = Field(..., description="Target class evaluated by Grad-CAM")
    original_base64: Optional[str] = Field(None, description="Original image encoded as PNG base64 data URI")
    heatmap_base64: Optional[str] = Field(None, description="Grad-CAM activation heatmap encoded as PNG base64 data URI")
    overlay_base64: Optional[str] = Field(None, description="Grad-CAM alpha-blended overlay encoded as PNG base64 data URI")
    original_dimensions: Optional[Tuple[int, int]] = Field(None, description="Original image dimensions (width, height)")
    disclaimer: str = Field(
        default="Grad-CAM visualizes contributory convolutional features. It is intended for decision-support and does not constitute a confirmed clinical diagnosis.",
        description="Clinical explainability disclaimer"
    )


class AnalysisResponse(BaseModel):
    """Complete diagnostic and explainability response schema with persistent analysis_id."""
    analysis_id: str = Field(..., description="Unique persistent identifier for this analysis (UUID)")
    created_at: str = Field(..., description="ISO 8601 UTC creation timestamp")
    filename: Optional[str] = Field(None, description="Original uploaded filename")
    prediction: str = Field(..., description="Predicted diagnosis class ('NORMAL' or 'PNEUMONIA')")
    predicted_index: int = Field(..., description="Integer index of predicted class")
    confidence: float = Field(..., description="Confidence score in range [0.0, 1.0]")
    probabilities: Dict[str, float] = Field(..., description="Full class probability distribution")
    model_version: str = Field(..., description="Semantic version of the AI model")
    architecture: str = Field(..., description="CNN backbone architecture name")
    device: str = Field(..., description="Inference hardware device")
    inference_time_ms: float = Field(..., description="Total pipeline latency in milliseconds")
    target_class: str = Field(..., description="Target class evaluated by Grad-CAM")
    image_reference: Optional[str] = Field(None, description="Persistent relative reference to stored input image")
    heatmap_reference: Optional[str] = Field(None, description="Persistent relative reference to stored heatmap")
    overlay_reference: Optional[str] = Field(None, description="Persistent relative reference to stored overlay")
    original_base64: Optional[str] = Field(None, description="Original image as base64 PNG data URI")
    heatmap_base64: Optional[str] = Field(None, description="Grad-CAM heatmap as base64 PNG data URI")
    overlay_base64: Optional[str] = Field(None, description="Grad-CAM overlay as base64 PNG data URI")
    original_dimensions: Optional[Tuple[int, int]] = Field(None, description="Original image dimensions (width, height)")
    class_mapping: Dict[str, int] = Field(
        default_factory=lambda: {"NORMAL": 0, "PNEUMONIA": 1},
        description="Canonical label to index mapping"
    )
    disclaimer: str = Field(
        default="AI Medical Image Analysis decision support system. For clinical research and verification only.",
        description="Regulatory medical disclaimer"
    )


class AnalysisHistoryItem(BaseModel):
    """Summarized analysis item in historical query results."""
    analysis_id: str = Field(..., description="Unique persistent identifier (UUID)")
    created_at: str = Field(..., description="ISO 8601 UTC creation timestamp")
    filename: Optional[str] = Field(None, description="Original uploaded filename")
    prediction: str = Field(..., description="Predicted diagnosis class")
    confidence: float = Field(..., description="Confidence score in range [0.0, 1.0]")
    model_version: str = Field(..., description="Model version")
    architecture: Optional[str] = Field(None, description="Model architecture")
    image_reference: Optional[str] = Field(None, description="Stored image reference")
    overlay_reference: Optional[str] = Field(None, description="Stored overlay reference")
    status: Optional[str] = Field("completed", description="Analysis processing status")


class AnalysisHistoryResponse(BaseModel):
    """Paginated list of historical clinical analyses."""
    items: List[AnalysisHistoryItem] = Field(..., description="List of analysis records ordered newest first")
    total: int = Field(..., description="Total number of stored analyses in database")
    limit: int = Field(..., description="Requested page item limit")
    offset: int = Field(..., description="Requested item offset")


class AnalysisDetailResponse(BaseModel):
    """Detailed record of a single persisted analysis retrieved by ID."""
    analysis_id: str
    created_at: str
    filename: Optional[str] = None
    prediction: str
    predicted_index: int
    confidence: float
    probabilities: Dict[str, float]
    model_version: str
    architecture: str
    device: str
    inference_time_ms: float
    target_class: str
    image_reference: Optional[str] = None
    heatmap_reference: Optional[str] = None
    overlay_reference: Optional[str] = None
    original_dimensions: Optional[Tuple[int, int]] = None
    status: str = "completed"


class ErrorDetail(BaseModel):
    """Structured error detail schema."""
    code: str = Field(..., description="Machine-readable error classification code")
    message: str = Field(..., description="Human-readable error description")
    details: Optional[Any] = Field(None, description="Additional contextual error metadata")


class ErrorResponse(BaseModel):
    """Standardized API error response container."""
    error: ErrorDetail


# ---------------------------------------------------------------------------
# Authentication & Role-Based Access Control Schemas
# ---------------------------------------------------------------------------

class UserLoginRequest(BaseModel):
    """Credentials payload for user/admin login."""
    username: str = Field(..., min_length=1, max_length=100, description="Username")
    password: str = Field(..., min_length=1, max_length=200, description="Plaintext password")


class UserRegisterRequest(BaseModel):
    """Registration payload for new user accounts."""
    username: str = Field(..., min_length=3, max_length=50, description="Desired unique username")
    password: str = Field(..., min_length=6, max_length=200, description="Password (min 6 characters)")


class UserPublic(BaseModel):
    """Public user identity schema safe for frontend consumption."""
    id: str = Field(..., description="Unique user identifier")
    username: str = Field(..., description="Username")
    role: str = Field(..., description="Access role (ADMIN or USER)")
    is_active: bool = Field(True, description="Account active status")
    created_at: Optional[str] = Field(None, description="ISO timestamp of account creation")


class AuthResponse(BaseModel):
    """Authentication response returning public user record."""
    user: UserPublic
    message: str = "Authentication successful"


class AdminUserItem(BaseModel):
    """User representation for admin management dashboards."""
    id: str
    username: str
    role: str
    is_active: bool
    created_at: str
    analysis_count: Optional[int] = 0


class AdminUserListResponse(BaseModel):
    """Admin response for listing all system users."""
    users: List[AdminUserItem]
    total: int


class AdminStatsResponse(BaseModel):
    """Aggregated platform statistics for admin dashboard."""
    total_analyses: int
    normal_count: int
    pneumonia_count: int
    total_users: int
    active_users: int
    admin_users: int
    regular_users: int
    avg_confidence: float
    model_version: str
    architecture: str
    environment: str


class UpdateUserStatusRequest(BaseModel):
    """Admin request to activate or deactivate a user."""
    is_active: bool

