import pytest
from pathlib import Path
import torch
import torch.nn as nn

from src.models.model import (
    MedicalClassifier,
    build_model,
    save_model_checkpoint,
    load_model_checkpoint,
    get_device,
    CLASS_TO_IDX,
    IDX_TO_CLASS,
)


@pytest.mark.parametrize("arch", ["resnet18", "resnet50", "densenet121", "efficientnet_b0"])
def test_model_instantiation_and_forward_pass(arch):
    """Verify that ResNet, DenseNet, and EfficientNet can be instantiated and run a forward pass."""
    # Use pretrained=False for fast deterministic unit tests
    model = build_model(
        architecture=arch,
        num_classes=2,
        pretrained=False,
        dropout=0.2,
        device="cpu",
    )
    model.eval()

    # Small synthetic batch for technical verification (NOT a fabricated medical image)
    dummy_input = torch.randn(2, 3, 224, 224)

    with torch.no_grad():
        output = model(dummy_input)

    assert isinstance(output, torch.Tensor)
    assert output.shape == (2, 2), f"Expected shape (2, 2) for {arch}, got {output.shape}"
    assert output.dtype == torch.float32


def test_class_mapping_preservation():
    """Verify standard binary class mapping across models module."""
    assert CLASS_TO_IDX["NORMAL"] == 0
    assert CLASS_TO_IDX["PNEUMONIA"] == 1
    assert IDX_TO_CLASS[0] == "NORMAL"
    assert IDX_TO_CLASS[1] == "PNEUMONIA"


def test_custom_num_classes():
    """Verify that model factory supports configurable number of classes."""
    model = build_model(architecture="resnet18", num_classes=5, pretrained=False, device="cpu")
    dummy_input = torch.randn(1, 3, 224, 224)
    with torch.no_grad():
        out = model(dummy_input)
    assert out.shape == (1, 5)


def test_backbone_freezing_and_unfreezing():
    """Verify that freezing locks the feature extractor and unfreezing restores gradients."""
    model = build_model(
        architecture="resnet18",
        num_classes=2,
        pretrained=False,
        freeze_backbone=True,
        device="cpu"
    )

    metadata = model.get_model_metadata()
    assert metadata["is_frozen"] is True
    assert metadata["trainable_parameters"] < metadata["total_parameters"]
    assert metadata["frozen_parameters"] > 0

    # Ensure classifier head is trainable while backbone is not
    for name, param in model.backbone.named_parameters():
        if "fc" in name:
            assert param.requires_grad is True, "Classification head must remain trainable"
        else:
            assert param.requires_grad is False, "Backbone parameters must be frozen"

    # Now unfreeze backbone completely
    model.unfreeze_backbone()
    metadata_unfrozen = model.get_model_metadata()
    assert metadata_unfrozen["is_frozen"] is False
    assert metadata_unfrozen["frozen_parameters"] == 0
    assert metadata_unfrozen["trainable_parameters"] == metadata_unfrozen["total_parameters"]

    for param in model.parameters():
        assert param.requires_grad is True


def test_model_metadata():
    """Verify that model metadata returns accurate counts and keys."""
    model = build_model(
        architecture="densenet121",
        num_classes=2,
        pretrained=False,
        dropout=0.35,
        device="cpu"
    )

    meta = model.get_model_metadata()
    assert meta["architecture"] == "densenet121"
    assert meta["num_classes"] == 2
    assert meta["class_mapping"] == {"NORMAL": 0, "PNEUMONIA": 1}
    assert meta["dropout_rate"] == 0.35
    assert meta["total_parameters"] > 6_000_000
    assert meta["device"] == "cpu"


def test_gradcam_target_layers():
    """Verify that Grad-CAM target layers are accessible across all model families."""
    for arch in ["resnet50", "densenet121", "efficientnet_b0"]:
        model = build_model(architecture=arch, num_classes=2, pretrained=False, device="cpu")
        target_layer = model.get_target_layer_for_gradcam()
        assert isinstance(target_layer, nn.Module)


def test_device_selection():
    """Verify CPU and CUDA device discovery."""
    cpu_device = get_device(prefer_cuda=False)
    assert cpu_device.type == "cpu"

    detected_device = get_device(prefer_cuda=True)
    if torch.cuda.is_available():
        assert detected_device.type == "cuda"
    else:
        assert detected_device.type == "cpu"


def test_checkpoint_saving_and_loading(tmp_path):
    """Verify model state saving and loading cycle."""
    ckpt_file = tmp_path / "test_model_checkpoint.pth"

    orig_model = build_model(
        architecture="resnet18",
        num_classes=2,
        pretrained=False,
        dropout=0.4,
        device="cpu"
    )

    saved_path = save_model_checkpoint(
        model=orig_model,
        filepath=ckpt_file,
        epoch=1,
        metrics={"val_loss": 0.25, "val_acc": 0.92},
        extra_config={"dataset": "chest_xray"}
    )

    assert saved_path.exists()

    loaded_model, ckpt_dict = load_model_checkpoint(saved_path, device="cpu")

    assert loaded_model.arch_key == "resnet18"
    assert loaded_model.num_classes == 2
    assert loaded_model.dropout_rate == 0.4
    assert ckpt_dict["epoch"] == 1
    assert ckpt_dict["metrics"]["val_acc"] == 0.92

    # Verify identical output from loaded model
    test_tensor = torch.randn(1, 3, 224, 224)
    orig_model.eval()
    loaded_model.eval()
    with torch.no_grad():
        out_orig = orig_model(test_tensor)
        out_loaded = loaded_model(test_tensor)

    assert torch.allclose(out_orig, out_loaded, atol=1e-6)


def test_invalid_architecture():
    """Verify that unsupported architecture strings raise descriptive ValueError."""
    with pytest.raises(ValueError, match="Unsupported architecture"):
        build_model(architecture="unsupported_vgg99")
