"""Reusable AI Inference Engine for Clinical Chest X-Ray Classification.

Inference Pipeline Flow:
-----------------------
Input X-ray (Path, Bytes, PIL Image, Tensor)
    ↓
File & Image Validation (Format, Size, Dimensions, Readability)
    ↓
Inference Preprocessing (Deterministic Resize, ImageNet Normalization)
    ↓
Model Initialization (Persistent Checkpoint & Device Placement)
    ↓
Forward Pass (No-Grad Evaluation Mode)
    ↓
Class Probabilities & Confidence Computation
    ↓
Optional Grad-CAM Activation Heatmap & Alpha Overlay
    ↓
Typed Structured Result (PredictionResult / ExplainabilityResult)

Decoupling Principle:
--------------------
This module is decoupled from FastAPI route handlers and frontend clients.
The same underlying engine is reused across APIs, CLI utilities, and testing suites.
"""

import os
import sys
import io
import time
import base64
import logging
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, Union, Tuple, List

import numpy as np
from PIL import Image
import cv2
import torch
import torch.nn.functional as F

# Add backend root to path if executed directly
current_dir = Path(__file__).resolve().parent
backend_root = current_dir.parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from src.data.dataset import CLASS_TO_IDX, IDX_TO_CLASS
from src.data.preprocessing import get_eval_transforms, DEFAULT_IMAGE_SIZE
from src.models.model import MedicalClassifier, load_model_checkpoint, get_device
from src.explainability.gradcam import GradCAM, explain_medical_image

logger = logging.getLogger("InferenceEngine")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
MIN_IMAGE_DIMENSION = 32                # Minimum width and height (px)
MAX_IMAGE_DIMENSION = 10000             # Maximum width and height (px) to prevent decompression bombs


def get_max_file_size_bytes() -> int:
    """Resolve maximum allowable upload file size from environment variable or default (15 MB)."""
    env_mb = os.getenv("MAX_UPLOAD_SIZE_MB")
    if env_mb:
        try:
            return int(float(env_mb) * 1024 * 1024)
        except ValueError:
            pass
    env_bytes = os.getenv("MAX_FILE_SIZE_BYTES")
    if env_bytes:
        try:
            return int(env_bytes)
        except ValueError:
            pass
    return 15 * 1024 * 1024  # Default 15 MB


MAX_FILE_SIZE_BYTES = get_max_file_size_bytes()


class InferenceError(Exception):
    """Base exception for all inference engine failures."""
    pass


class ImageValidationError(InferenceError):
    """Raised when an input image fails format, size, or readability validation."""
    pass


class FileTooLargeError(ImageValidationError):
    """Raised when an uploaded file exceeds the configured size limit."""
    pass


class UnsupportedFormatError(ImageValidationError):
    """Raised when an uploaded file format is not in allowed formats."""
    pass


class ModelNotLoadedError(InferenceError):
    """Raised when inference is attempted on an uninitialized model."""
    pass



@dataclass
class PredictionResult:
    """Structured data container for standard clinical inference outputs."""
    prediction: str                       # 'NORMAL' or 'PNEUMONIA'
    predicted_index: int                  # 0 or 1
    confidence: float                     # Probability of predicted class in [0.0, 1.0]
    probabilities: Dict[str, float]       # {'NORMAL': p0, 'PNEUMONIA': p1}
    model_version: str                    # e.g. '1.0.0'
    architecture: str                     # e.g. 'resnet18'
    device: str                           # 'cpu' or 'cuda'
    inference_time_ms: float              # Latency in milliseconds
    class_mapping: Dict[str, int] = field(default_factory=lambda: CLASS_TO_IDX)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExplainabilityResult:
    """Structured data container for explainable inference with Grad-CAM visualizations."""
    prediction: str
    predicted_index: int
    confidence: float
    probabilities: Dict[str, float]
    model_version: str
    architecture: str
    device: str
    inference_time_ms: float
    target_class: str
    original_base64: Optional[str] = None
    heatmap_base64: Optional[str] = None
    overlay_base64: Optional[str] = None
    original_dimensions: Optional[Tuple[int, int]] = None
    disclaimer: str = (
        "Grad-CAM visualizes contributory convolutional activation features. "
        "It is for clinical decision-support only and does NOT constitute an autonomous diagnosis."
    )
    class_mapping: Dict[str, int] = field(default_factory=lambda: CLASS_TO_IDX)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def array_to_base64_png(img_array: np.ndarray) -> str:
    """Convert RGB numpy array to base64 data URI string."""
    pil_img = Image.fromarray(img_array.astype(np.uint8))
    buffer = io.BytesIO()
    pil_img.save(buffer, format="PNG")
    b64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64_str}"


def validate_and_load_image(
    image_input: Union[str, Path, bytes, io.BytesIO, Image.Image],
    max_file_size_bytes: int = MAX_FILE_SIZE_BYTES,
    min_dimension: int = MIN_IMAGE_DIMENSION,
    max_dimension: int = MAX_IMAGE_DIMENSION,
) -> Tuple[Image.Image, Tuple[int, int]]:
    """Validate format, dimensions, size, and decodability of raw image input.

    Returns:
        Tuple of (PIL.Image in RGB mode, original (width, height) tuple).
    """
    if isinstance(image_input, (str, Path)):
        file_path = Path(image_input)
        if not file_path.exists():
            raise ImageValidationError(f"Image file does not exist: {file_path}")
        if file_path.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
            raise UnsupportedFormatError(
                f"Unsupported image extension '{file_path.suffix}'. Allowed formats: {sorted(list(SUPPORTED_IMAGE_EXTENSIONS))}"
            )
        file_size = file_path.stat().st_size
        if file_size == 0:
            raise ImageValidationError("Uploaded image file is empty (0 bytes).")
        if file_size > max_file_size_bytes:
            raise FileTooLargeError(
                f"Image file size ({file_size / (1024*1024):.1f} MB) exceeds maximum allowed limit ({max_file_size_bytes / (1024*1024):.0f} MB)."
            )
        try:
            with Image.open(file_path) as raw_img:
                fmt = str(raw_img.format).upper() if raw_img.format else ""
                if fmt not in ["JPEG", "PNG", "JPG"]:
                    raise UnsupportedFormatError(f"Unsupported image format '{fmt}'. Allowed formats: JPG, JPEG, PNG.")
                raw_img.verify()
            with Image.open(file_path) as raw_img:
                pil_img = raw_img.convert("RGB")
        except (UnsupportedFormatError, FileTooLargeError):
            raise
        except Exception as e:
            raise ImageValidationError("The uploaded file could not be processed as a valid image: corrupted or unreadable image content.")

    elif isinstance(image_input, (bytes, io.BytesIO)):
        data = image_input if isinstance(image_input, bytes) else image_input.getvalue()
        if len(data) == 0:
            raise ImageValidationError("Uploaded image file is empty (0 bytes).")
        if len(data) > max_file_size_bytes:
            raise FileTooLargeError(
                f"File size exceeds maximum allowable limit of {max_file_size_bytes / (1024*1024):.0f} MB."
            )
        try:
            with Image.open(io.BytesIO(data)) as raw_img:
                fmt = str(raw_img.format).upper() if raw_img.format else ""
                if fmt not in ["JPEG", "PNG", "JPG"]:
                    raise UnsupportedFormatError(f"Unsupported image format '{fmt}'. Allowed formats: JPG, JPEG, PNG.")
                raw_img.verify()
            with Image.open(io.BytesIO(data)) as raw_img:
                pil_img = raw_img.convert("RGB")
        except (UnsupportedFormatError, FileTooLargeError):
            raise
        except Exception as e:
            raise ImageValidationError("The uploaded file could not be processed as a valid image: corrupted or unreadable image content.")

    elif isinstance(image_input, Image.Image):
        try:
            pil_img = image_input.convert("RGB")
        except Exception as e:
            raise ImageValidationError("The uploaded file could not be processed as a valid image: corrupted or unreadable image content.")

    else:
        raise ImageValidationError(f"Unsupported image input type: {type(image_input)}")

    # Dimension validation
    width, height = pil_img.size
    if width <= 0 or height <= 0:
        raise ImageValidationError("Image dimensions must be greater than zero.")
    if width < min_dimension or height < min_dimension:
        raise ImageValidationError(
            f"Image spatial resolution ({width}x{height}) is below minimum allowable threshold ({min_dimension}x{min_dimension})."
        )
    if width > max_dimension or height > max_dimension:
        raise ImageValidationError(
            f"Image spatial resolution ({width}x{height}) exceeds maximum allowable threshold ({max_dimension}x{max_dimension})."
        )

    return pil_img, (width, height)



class ChestXRayPredictor:
    """Production-grade reusable AI inference engine for Chest X-Ray diagnosis."""

    def __init__(
        self,
        checkpoint_path: Union[str, Path] = "backend/models/best_model.pth",
        device: Optional[Union[str, torch.device]] = None,
        model_version: str = "1.0.0",
        image_size: Tuple[int, int] = DEFAULT_IMAGE_SIZE,
        auto_load: bool = True,
    ):
        """Initialize the inference predictor.

        Args:
            checkpoint_path: Path to serialized trained model checkpoint.
            device: Target execution device ('cpu' or 'cuda'). If None, auto-detects.
            model_version: Semantic version identifier for the inference pipeline.
            image_size: Preprocessing spatial input dimensions (H, W).
            auto_load: Whether to load checkpoint weights immediately on init.
        """
        self.checkpoint_path = Path(checkpoint_path)
        self.target_device = torch.device(device) if device else get_device()
        self.model_version = model_version
        self.image_size = image_size
        self.model: Optional[MedicalClassifier] = None
        self.is_loaded: bool = False
        self.checkpoint_metadata: Dict[str, Any] = {}

        self.transform = get_eval_transforms(image_size=self.image_size)

        if auto_load:
            self.load_model()

    def load_model(self) -> bool:
        """Load and persist trained weights into memory.

        Returns:
            bool: True if loaded successfully.
        """
        if not self.checkpoint_path.exists():
            # Check alternative relative path
            alt_path = Path(__file__).resolve().parent.parent.parent / self.checkpoint_path
            if alt_path.exists():
                self.checkpoint_path = alt_path
            else:
                raise FileNotFoundError(f"Trained checkpoint not found at: {self.checkpoint_path}")

        try:
            self.model, ckpt_info = load_model_checkpoint(
                self.checkpoint_path,
                device=self.target_device,
            )
            self.model.eval()
            self.is_loaded = True
            self.checkpoint_metadata = ckpt_info.get("metadata", {})
            logger.info(
                f"Successfully initialized ChestXRayPredictor on {self.target_device} "
                f"(Arch: {self.model.arch_key}, Version: {self.model_version})"
            )
            return True
        except Exception as e:
            self.is_loaded = False
            raise InferenceError(f"Failed loading model weights from {self.checkpoint_path}: {e}")

    def predict(
        self,
        image_input: Union[str, Path, bytes, io.BytesIO, Image.Image],
    ) -> PredictionResult:
        """Execute fast forward-pass diagnostic inference on a single medical scan.

        Args:
            image_input: Image file path, raw bytes, or PIL Image.

        Returns:
            PredictionResult dataclass with prediction, confidence, probabilities, and latency.
        """
        if not self.is_loaded or self.model is None:
            raise ModelNotLoadedError("Inference engine is not loaded. Call load_model() first.")

        start_time = time.perf_counter()

        # Validate & load PIL image
        pil_img, _ = validate_and_load_image(image_input)

        # Preprocessing tensor
        tensor = self.transform(pil_img).unsqueeze(0).to(self.target_device)

        # Forward pass (no gradients)
        with torch.no_grad():
            logits = self.model(tensor)
            probabilities = F.softmax(logits, dim=1).squeeze(0)

        prob_normal = float(probabilities[0].item())
        prob_pneumonia = float(probabilities[1].item())

        predicted_idx = int(probabilities.argmax().item())
        predicted_name = IDX_TO_CLASS[predicted_idx]
        confidence = float(probabilities[predicted_idx].item())

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        return PredictionResult(
            prediction=predicted_name,
            predicted_index=predicted_idx,
            confidence=round(confidence, 4),
            probabilities={
                "NORMAL": round(prob_normal, 4),
                "PNEUMONIA": round(prob_pneumonia, 4),
            },
            model_version=self.model_version,
            architecture=self.model.arch_key,
            device=str(self.target_device),
            inference_time_ms=round(latency_ms, 2),
        )

    def predict_with_explanation(
        self,
        image_input: Union[str, Path, bytes, io.BytesIO, Image.Image],
        target_class: Optional[int] = None,
        alpha: float = 0.45,
        encode_base64: bool = True,
    ) -> ExplainabilityResult:
        """Execute diagnostic inference with Grad-CAM visual activation heatmaps and overlays.

        Args:
            image_input: Image file path, raw bytes, or PIL Image.
            target_class: Specific target class (0=NORMAL, 1=PNEUMONIA). If None, uses predicted class.
            alpha: Heatmap overlay blending factor in [0.0, 1.0].
            encode_base64: Whether to generate base64 data URIs for direct frontend/API consumption.

        Returns:
            ExplainabilityResult dataclass with diagnosis, probabilities, and visual base64 overlays.
        """
        if not self.is_loaded or self.model is None:
            raise ModelNotLoadedError("Inference engine is not loaded. Call load_model() first.")

        start_time = time.perf_counter()

        # Validate & load PIL image
        pil_img, (orig_w, orig_h) = validate_and_load_image(image_input)

        # Run Explainable AI pipeline via Task 7 module
        explanation = explain_medical_image(
            model=self.model,
            image_input=pil_img,
            target_class=target_class,
            image_size=self.image_size,
            device=self.target_device,
            alpha=alpha,
        )

        pred_idx = explanation["predicted_class_index"]
        pred_name = explanation["predicted_class_name"]
        target_idx = explanation["target_class_index"]
        target_name = explanation["target_class_name"]
        confidence = float(explanation["confidence"])

        # Compute full probabilities
        tensor = self.transform(pil_img).unsqueeze(0).to(self.target_device)
        with torch.no_grad():
            logits = self.model(tensor)
            probabilities = F.softmax(logits, dim=1).squeeze(0)
        prob_normal = float(probabilities[0].item())
        prob_pneumonia = float(probabilities[1].item())

        # Base64 encodings for API transport
        orig_b64 = array_to_base64_png(explanation["original_rgb"]) if (encode_base64 and explanation.get("original_rgb") is not None) else None
        heat_b64 = array_to_base64_png(explanation["heatmap_rgb"]) if (encode_base64 and explanation.get("heatmap_rgb") is not None) else None
        over_b64 = array_to_base64_png(explanation["overlay_rgb"]) if (encode_base64 and explanation.get("overlay_rgb") is not None) else None

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        return ExplainabilityResult(
            prediction=pred_name,
            predicted_index=pred_idx,
            confidence=round(confidence, 4),
            probabilities={
                "NORMAL": round(prob_normal, 4),
                "PNEUMONIA": round(prob_pneumonia, 4),
            },
            model_version=self.model_version,
            architecture=self.model.arch_key,
            device=str(self.target_device),
            inference_time_ms=round(latency_ms, 2),
            target_class=target_name,
            original_base64=orig_b64,
            heatmap_base64=heat_b64,
            overlay_base64=over_b64,
            original_dimensions=(orig_w, orig_h),
        )


# Backward-compatible alias
MedicalPredictor = ChestXRayPredictor

# Singleton engine cache for API lifecycle reuse
_CACHED_PREDICTOR: Optional[ChestXRayPredictor] = None


def get_default_predictor(
    checkpoint_path: str = "backend/models/best_model.pth",
    device: Optional[str] = None,
) -> ChestXRayPredictor:
    """Retrieve or initialize the singleton ChestXRayPredictor instance."""
    global _CACHED_PREDICTOR
    if _CACHED_PREDICTOR is None or not _CACHED_PREDICTOR.is_loaded:
        _CACHED_PREDICTOR = ChestXRayPredictor(
            checkpoint_path=checkpoint_path,
            device=device,
            auto_load=True,
        )
    return _CACHED_PREDICTOR
