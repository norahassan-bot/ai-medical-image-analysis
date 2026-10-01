import pytest
from pathlib import Path
import numpy as np
from PIL import Image
import torch
import torch.nn as nn

from src.explainability.gradcam import (
    GradCAM,
    resolve_target_layer,
    explain_medical_image,
    save_gradcam_artifacts,
)
from src.models.model import build_model, CLASS_TO_IDX, IDX_TO_CLASS


def test_target_layer_resolution_for_all_architectures():
    """Verify target convolutional layer resolution across ResNet, DenseNet, and EfficientNet."""
    for arch in ["resnet18", "resnet50", "densenet121", "efficientnet_b0"]:
        model = build_model(architecture=arch, num_classes=2, pretrained=False, device="cpu")
        target_layer = resolve_target_layer(model, architecture=arch)
        assert isinstance(target_layer, nn.Module), f"Failed resolving target layer for {arch}"


def test_unsupported_architecture_error():
    """Verify that unsupported architecture raises ValueError."""
    dummy_model = nn.Sequential(nn.Linear(10, 2))
    with pytest.raises(ValueError, match="Unable to auto-resolve target convolutional layer"):
        resolve_target_layer(dummy_model, architecture="unsupported_vgg99")


def test_gradcam_initialization_and_hook_registration():
    """Verify forward and backward hook registration on target layer."""
    model = build_model(architecture="resnet18", num_classes=2, pretrained=False, device="cpu")
    explainer = GradCAM(model=model, device="cpu")

    assert len(explainer._hook_handles) == 2
    assert explainer.target_layer is not None

    explainer.cleanup()
    assert len(explainer._hook_handles) == 0


def test_gradcam_computation_and_gradient_capture():
    """Verify forward pass, backward pass, gradient capture, and CAM normalization."""
    model = build_model(architecture="resnet18", num_classes=2, pretrained=False, device="cpu")
    explainer = GradCAM(model=model, device="cpu")

    # Synthetic test tensor (for technical verification only, not synthetic patient study)
    synthetic_input = torch.randn(1, 3, 224, 224)

    cam_2d, pred_class, prob = explainer.generate_cam(synthetic_input, target_class=1)

    assert isinstance(cam_2d, np.ndarray)
    assert cam_2d.ndim == 2
    assert cam_2d.min() >= 0.0
    assert cam_2d.max() <= 1.0 + 1e-6
    assert pred_class in (0, 1)
    assert 0.0 <= prob <= 1.0

    # Ensure gradients and activations were captured
    assert explainer.gradients is not None
    assert explainer.activations is not None

    explainer.cleanup()


def test_heatmap_generation_and_dimensions():
    """Verify heatmap upsampling to target size and RGB colormap rendering."""
    model = build_model(architecture="resnet18", num_classes=2, pretrained=False, device="cpu")
    with GradCAM(model=model, device="cpu") as explainer:
        synthetic_input = torch.randn(1, 3, 224, 224)
        cam_2d, _, _ = explainer.generate_cam(synthetic_input)

        target_w, target_h = 500, 400
        heatmap_rgb = explainer.generate_heatmap(cam_2d, target_size=(target_w, target_h))

        assert isinstance(heatmap_rgb, np.ndarray)
        assert heatmap_rgb.shape == (target_h, target_w, 3)
        assert heatmap_rgb.dtype == np.uint8
        assert heatmap_rgb.min() >= 0
        assert heatmap_rgb.max() <= 255


def test_overlay_generation_and_original_image_preservation():
    """Verify overlay blending and that the original image is preserved unaltered."""
    model = build_model(architecture="resnet18", num_classes=2, pretrained=False, device="cpu")
    with GradCAM(model=model, device="cpu") as explainer:
        # Create test PIL image
        orig_pil = Image.new("RGB", (300, 300), color=(100, 150, 200))
        orig_copy = np.array(orig_pil.copy())

        heatmap_dummy = np.full((300, 300, 3), fill_value=128, dtype=np.uint8)

        overlay_rgb, original_returned = explainer.generate_overlay(
            original_image=orig_pil,
            heatmap_rgb=heatmap_dummy,
            alpha=0.4
        )

        assert overlay_rgb.shape == (300, 300, 3)
        assert overlay_rgb.dtype == np.uint8

        # Verify original image was preserved
        assert np.array_equal(original_returned, orig_copy), "Original image must remain unaltered"


def test_class_mapping_consistency():
    """Verify canonical class mappings in explainability."""
    assert CLASS_TO_IDX["NORMAL"] == 0
    assert CLASS_TO_IDX["PNEUMONIA"] == 1
    assert IDX_TO_CLASS[0] == "NORMAL"
    assert IDX_TO_CLASS[1] == "PNEUMONIA"


def test_artifact_saving(tmp_path):
    """Verify saving original, heatmap, and overlay PNG files to disk."""
    model = build_model(architecture="resnet18", num_classes=2, pretrained=False, device="cpu")
    test_img = Image.new("RGB", (224, 224), color=(80, 80, 80))

    explanation = explain_medical_image(
        model=model,
        image_input=test_img,
        target_class=1,
        device="cpu"
    )

    out_dir = tmp_path / "gradcam_artifacts"
    saved = save_gradcam_artifacts(explanation, output_dir=out_dir, prefix="test_case")

    assert "original_path" in saved and saved["original_path"].exists()
    assert "heatmap_path" in saved and saved["heatmap_path"].exists()
    assert "overlay_path" in saved and saved["overlay_path"].exists()
