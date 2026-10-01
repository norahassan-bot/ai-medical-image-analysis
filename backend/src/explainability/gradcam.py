"""Grad-CAM (Gradient-weighted Class Activation Mapping) for Medical Image Explainability.

Scientific & Clinical Explainability Architecture:
--------------------------------------------------
1. What Grad-CAM Is:
   Grad-CAM utilizes the gradient of a classification score (e.g. Pneumonia logit Y^c) flowing
   into the final convolutional layer to produce a coarse 2D spatial localization map highlighting
   the discriminative regions of interest in the input radiograph.

2. Why Grad-CAM Is Used in Clinical Decision Support:
   Deep convolutional networks operate as complex, non-linear function approximators. In medical imaging,
   clinicians cannot trust "black box" decisions without visual verification that the model is attending
   to pathological pulmonary features (e.g., bilateral infiltrates, consolidation, pleural opacity) rather
   than spurious artifacts (e.g., hospital lead markers, orientation tags, or imaging borders).

3. Mathematical Formulation:
   - Feature Activation: A^k in R^{U x V} (k-th channel feature map of target convolutional layer)
   - Neuron Importance Weight:
       alpha_k^c = (1 / Z) * sum_i sum_j ( d Y^c / d A_{i,j}^k )   [Global Average Pooling of gradients]
   - Class Activation Map:
       L_{Grad-CAM}^c = ReLU( sum_k alpha_k^c * A^k )
     ReLU ensures only features that positively correlate with the target diagnostic class are visualized.

4. Target Layer Selection:
   - ResNet: Final Bottleneck / BasicBlock of layer4 (`model.backbone.layer4[-1]`).
   - DenseNet: Final dense block normalization (`model.backbone.features.norm5`).
   - EfficientNet: Final depthwise separable feature block (`model.backbone.features[-1]`).

5. Clinical Interpretation Limitation:
   Grad-CAM is an algorithmic visualization tool for decision support. It does NOT provide exact anatomical
   lesion segmentation, does NOT prove medical causality, and must NEVER replace comprehensive clinical
   radiological evaluation by a licensed healthcare professional.
"""

from typing import Dict, Any, Optional, Tuple, Union, List
from pathlib import Path
import logging
import numpy as np
from PIL import Image
import cv2
import torch
import torch.nn as nn
import torch.nn.functional as F

from src.data.dataset import CLASS_TO_IDX, IDX_TO_CLASS
from src.data.preprocessing import get_eval_transforms, DEFAULT_IMAGE_SIZE
from src.models.model import MedicalClassifier, get_device

logger = logging.getLogger("GradCAM")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def resolve_target_layer(model: nn.Module, architecture: Optional[str] = None) -> nn.Module:
    """Resolve the optimal final convolutional layer for a given architecture.

    Args:
        model: PyTorch model or MedicalClassifier instance.
        architecture: Architecture string ('resnet18', 'densenet121', 'efficientnet_b0', etc.).

    Returns:
        Target convolutional PyTorch nn.Module.
    """
    # 1. If MedicalClassifier instance with helper method
    if isinstance(model, MedicalClassifier):
        return model.get_target_layer_for_gradcam()

    # 2. Derive arch name
    arch = architecture.lower().strip() if architecture else getattr(model, "arch_key", "").lower()

    if "resnet" in arch:
        if hasattr(model, "backbone") and hasattr(model.backbone, "layer4"):
            return model.backbone.layer4[-1]
        elif hasattr(model, "layer4"):
            return model.layer4[-1]
    elif "densenet" in arch:
        if hasattr(model, "backbone") and hasattr(model.backbone, "features"):
            return model.backbone.features.norm5
        elif hasattr(model, "features"):
            return model.features.norm5
    elif "efficientnet" in arch:
        if hasattr(model, "backbone") and hasattr(model.backbone, "features"):
            return model.backbone.features[-1]
        elif hasattr(model, "features"):
            return model.features[-1]

    # 3. Fallback: inspect children for layer4 or features
    for name, module in model.named_modules():
        if name in ("backbone.layer4.1", "backbone.layer4.2", "layer4.1", "layer4.2", "backbone.features.norm5", "features.norm5"):
            return module

    raise ValueError(
        f"Unable to auto-resolve target convolutional layer for architecture '{arch}'. "
        f"Please supply an explicit target_layer module (Supported: ResNet, DenseNet, EfficientNet)."
    )


class GradCAM:
    """Computes Gradient-weighted Class Activation Mapping (Grad-CAM) explanations."""

    def __init__(
        self,
        model: nn.Module,
        target_layer: Optional[Union[nn.Module, str]] = None,
        architecture: Optional[str] = None,
        device: Optional[Union[str, torch.device]] = None,
    ):
        """Initialize GradCAM explainer.

        Args:
            model: Trained PyTorch classification model.
            target_layer: Target convolutional layer or string name. If None, auto-resolved.
            architecture: Optional architecture family key (e.g. 'resnet50').
            device: Execution device.
        """
        self.model = model
        self.device = torch.device(device) if device else get_device()
        self.model = self.model.to(self.device)
        self.model.eval()

        if isinstance(target_layer, nn.Module):
            self.target_layer = target_layer
        else:
            self.target_layer = resolve_target_layer(model, architecture=architecture)

        self.gradients: Optional[torch.Tensor] = None
        self.activations: Optional[torch.Tensor] = None
        self._hook_handles: List[Any] = []
        self._register_hooks()

    def _register_hooks(self):
        """Register forward and backward hooks on the target convolutional layer."""
        def forward_hook(module, input_tensor, output_tensor):
            self.activations = output_tensor.detach()

        def backward_hook(module, grad_input, grad_output):
            self.gradients = grad_output[0].detach()

        self._hook_handles.append(self.target_layer.register_forward_hook(forward_hook))
        self._hook_handles.append(self.target_layer.register_full_backward_hook(backward_hook))

    def generate_cam(
        self,
        input_tensor: torch.Tensor,
        target_class: Optional[int] = None,
    ) -> Tuple[np.ndarray, int, float]:
        """Generate normalized 2D Class Activation Map.

        Args:
            input_tensor: 4D preprocessed input tensor (1, 3, H, W).
            target_class: Target class index (0=NORMAL, 1=PNEUMONIA). If None, uses model prediction.

        Returns:
            Tuple of (cam_2d: np.ndarray, predicted_class: int, target_probability: float).
        """
        self.model.eval()
        input_tensor = input_tensor.to(self.device)

        if input_tensor.dim() == 3:
            input_tensor = input_tensor.unsqueeze(0)

        # Forward pass
        self.model.zero_grad()
        output = self.model(input_tensor)
        probabilities = F.softmax(output, dim=1)

        predicted_class = int(output.argmax(dim=1).item())

        if target_class is None:
            target_class = predicted_class

        target_prob = float(probabilities[0, target_class].item())

        # Backward pass for target class score
        score = output[0, target_class]
        score.backward(retain_graph=True)

        if self.gradients is None or self.activations is None:
            raise RuntimeError("Failed to capture gradients or activations during Grad-CAM backward pass.")

        # Global Average Pooling of gradients over spatial dimensions (H, W) -> alpha weights (1, C, 1, 1)
        weights = torch.mean(self.gradients, dim=(2, 3), keepdim=True)

        # Weighted combination of forward activation maps
        cam = torch.sum(weights * self.activations, dim=1).squeeze()

        # Apply ReLU (retain positive contributions only)
        cam = torch.clamp(cam, min=0)

        # Convert to numpy and normalize to [0.0, 1.0]
        cam_np = cam.cpu().numpy()
        max_val = np.max(cam_np)
        if max_val > 1e-8:
            cam_np = cam_np / max_val
        else:
            cam_np = np.zeros_like(cam_np)

        return cam_np, predicted_class, target_prob

    def generate_heatmap(
        self,
        cam_2d: np.ndarray,
        target_size: Optional[Tuple[int, int]] = None,
        colormap: int = cv2.COLORMAP_JET,
    ) -> np.ndarray:
        """Upsample 2D CAM array to target resolution and apply OpenCV color palette.

        Args:
            cam_2d: Normalized 2D activation map (H_feat, W_feat) with values in [0.0, 1.0].
            target_size: Target dimensions (Width, Height). If None, keeps CAM native resolution.
            colormap: OpenCV colormap constant (default: cv2.COLORMAP_JET).

        Returns:
            RGB uint8 heatmap image array (Height, Width, 3).
        """
        if target_size is not None:
            # cv2.resize expects (width, height)
            w, h = target_size
            cam_resized = cv2.resize(cam_2d, (w, h), interpolation=cv2.INTER_LINEAR)
        else:
            cam_resized = cam_2d

        # Scale to [0, 255] uint8
        heatmap_gray = np.uint8(255 * np.clip(cam_resized, 0.0, 1.0))

        # Apply OpenCV colormap (outputs BGR)
        heatmap_bgr = cv2.applyColorMap(heatmap_gray, colormap)

        # Convert BGR to RGB
        heatmap_rgb = cv2.cvtColor(heatmap_bgr, cv2.COLOR_BGR2RGB)
        return heatmap_rgb

    def generate_overlay(
        self,
        original_image: Union[Image.Image, np.ndarray, str, Path],
        heatmap_rgb: np.ndarray,
        alpha: float = 0.45,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Blend original medical image with Grad-CAM heatmap while preserving original image.

        Args:
            original_image: Original X-ray (PIL Image, numpy array, or file path).
            heatmap_rgb: RGB uint8 heatmap (H, W, 3).
            alpha: Heatmap blending weight in [0.0, 1.0]. Original image receives (1 - alpha).

        Returns:
            Tuple of (overlay_rgb: np.ndarray, original_rgb: np.ndarray).
        """
        # Load and standardize original image to RGB uint8
        if isinstance(original_image, (str, Path)):
            with Image.open(original_image) as raw_img:
                pil_img = raw_img.convert("RGB")
                orig_np = np.array(pil_img, dtype=np.uint8)
        elif isinstance(original_image, Image.Image):
            pil_img = original_image.convert("RGB")
            orig_np = np.array(pil_img, dtype=np.uint8)
        elif isinstance(original_image, np.ndarray):
            if original_image.ndim == 2:
                # Grayscale to 3-channel RGB
                orig_np = np.stack([original_image] * 3, axis=-1).astype(np.uint8)
            elif original_image.shape[2] == 1:
                orig_np = np.repeat(original_image, 3, axis=-1).astype(np.uint8)
            else:
                orig_np = original_image.astype(np.uint8)
        else:
            raise TypeError(f"Unsupported image type: {type(original_image)}")

        h, w = orig_np.shape[:2]

        # Ensure heatmap matches original image dimensions exactly
        if heatmap_rgb.shape[:2] != (h, w):
            heatmap_matched = cv2.resize(heatmap_rgb, (w, h), interpolation=cv2.INTER_LINEAR)
        else:
            heatmap_matched = heatmap_rgb

        # Alpha blending: (1 - alpha) * Original + alpha * Heatmap
        alpha = float(np.clip(alpha, 0.0, 1.0))
        overlay = cv2.addWeighted(orig_np, 1.0 - alpha, heatmap_matched, alpha, 0)

        return overlay, orig_np

    def cleanup(self):
        """Safely deregister forward and backward hooks to prevent memory leaks."""
        for handle in self._hook_handles:
            handle.remove()
        self._hook_handles.clear()
        self.gradients = None
        self.activations = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()


# Backwards compatibility
GradCAMExplainer = GradCAM


def explain_medical_image(
    model: nn.Module,
    image_input: Union[str, Path, Image.Image, torch.Tensor],
    target_class: Optional[int] = None,
    image_size: Tuple[int, int] = DEFAULT_IMAGE_SIZE,
    device: Optional[Union[str, torch.device]] = None,
    alpha: float = 0.45,
) -> Dict[str, Any]:
    """High-level functional API to generate Grad-CAM explanations for an individual study.

    Args:
        model: Trained PyTorch model.
        image_input: File path, PIL Image, or preprocessed tensor.
        target_class: Optional target class (0=NORMAL, 1=PNEUMONIA).
        image_size: Target image dimensions for model input.
        device: Execution device.
        alpha: Overlay blending weight.

    Returns:
        Dictionary containing diagnosis, probabilities, heatmap, and overlay arrays.
    """
    target_device = torch.device(device) if device else get_device()

    # Load PIL image
    if isinstance(image_input, (str, Path)):
        raw_pil = Image.open(image_input).convert("RGB")
        source_path = str(image_input)
    elif isinstance(image_input, Image.Image):
        raw_pil = image_input.convert("RGB")
        source_path = None
    elif isinstance(image_input, torch.Tensor):
        # Inverse normalize for display
        raw_pil = None
        source_path = None
    else:
        raise TypeError(f"Unsupported image input type: {type(image_input)}")

    # Preprocess tensor
    transform = get_eval_transforms(image_size=image_size)
    if raw_pil is not None:
        input_tensor = transform(raw_pil).unsqueeze(0).to(target_device)
        orig_width, orig_height = raw_pil.size
    else:
        input_tensor = image_input.to(target_device)
        orig_width, orig_height = image_size

    with GradCAM(model=model, device=target_device) as explainer:
        cam_2d, pred_idx, pred_prob = explainer.generate_cam(
            input_tensor=input_tensor,
            target_class=target_class,
        )

        heatmap_rgb = explainer.generate_heatmap(
            cam_2d=cam_2d,
            target_size=(orig_width, orig_height),
        )

        if raw_pil is not None:
            overlay_rgb, original_rgb = explainer.generate_overlay(
                original_image=raw_pil,
                heatmap_rgb=heatmap_rgb,
                alpha=alpha,
            )
        else:
            overlay_rgb = heatmap_rgb
            original_rgb = None

    return {
        "predicted_class_index": pred_idx,
        "predicted_class_name": IDX_TO_CLASS[pred_idx],
        "target_class_index": target_class if target_class is not None else pred_idx,
        "target_class_name": IDX_TO_CLASS[target_class if target_class is not None else pred_idx],
        "confidence": pred_prob,
        "cam_raw": cam_2d,
        "heatmap_rgb": heatmap_rgb,
        "overlay_rgb": overlay_rgb,
        "original_rgb": original_rgb,
        "source_path": source_path,
        "disclaimer": "Grad-CAM visualizes contributory convolutional activation features. It does not provide clinical diagnostic verification or lesion margin segmentation.",
    }


def save_gradcam_artifacts(
    explanation: Dict[str, Any],
    output_dir: Union[str, Path] = "reports/gradcam",
    prefix: str = "study",
) -> Dict[str, Path]:
    """Save original, heatmap, and overlay images to disk.

    Args:
        explanation: Dictionary returned by explain_medical_image.
        output_dir: Output folder for PNG files.
        prefix: Filename prefix.

    Returns:
        Dictionary of saved file paths.
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    saved_paths = {}

    # Save original
    if explanation.get("original_rgb") is not None:
        orig_file = out_path / f"{prefix}_original.png"
        Image.fromarray(explanation["original_rgb"]).save(orig_file)
        saved_paths["original_path"] = orig_file

    # Save heatmap
    if explanation.get("heatmap_rgb") is not None:
        heat_file = out_path / f"{prefix}_heatmap.png"
        Image.fromarray(explanation["heatmap_rgb"]).save(heat_file)
        saved_paths["heatmap_path"] = heat_file

    # Save overlay
    if explanation.get("overlay_rgb") is not None:
        over_file = out_path / f"{prefix}_overlay.png"
        Image.fromarray(explanation["overlay_rgb"]).save(over_file)
        saved_paths["overlay_path"] = over_file

    logger.info(f"Saved Grad-CAM explainability artifacts to {out_path} with prefix '{prefix}'")
    return saved_paths
