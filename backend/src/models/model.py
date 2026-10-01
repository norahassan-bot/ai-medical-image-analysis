"""Deep Learning Transfer Learning Architectures for Binary Chest X-Ray Classification.

Transfer Learning & Clinical Rationale:
--------------------------------------
1. What Transfer Learning Is:
   Transfer Learning leverages feature representations learned from vast general visual datasets
   (ImageNet with >1.2 million images across 1,000 categories) and adapts them to a specialized downstream
   medical vision domain (Pediatric Chest X-Ray: NORMAL vs PNEUMONIA).

2. Why Pretrained CNNs Are Used:
   Medical datasets (e.g. 5,856 radiographs) are relatively small compared to millions of natural images.
   Training deep architectures from scratch on modest datasets often induces catastrophic overfitting,
   requires prolonged training, and risks convergence to suboptimal local minima. Pretrained CNNs
   already encode generalized low-level edge detectors, gradient textures, and shape filters in their
   initial layers, requiring only fine-tuning for domain-specific radiographic consolidation patterns.

3. Frozen Backbone vs. Fine-Tuning:
   - Frozen Backbone (Feature Extraction): All convolutional feature extraction layers are locked
     (requires_grad=False). Only the newly initialized binary classification head is trained.
     This is computationally rapid and prevents destructive gradient updates into pretrained weights.
   - Fine-Tuning: After the classification head stabilizes, top convolutional layers (or the entire backbone)
     are unlocked with a low learning rate (e.g., 1e-5) to adapt specialized clinical high-level representations
     (e.g., lung field opacity, pleural effusion, and lobar infiltrates).

4. Supported Architectures:
   - ResNet Family (ResNet-18, ResNet-34, ResNet-50, ResNet-101): Residual skip connections prevent vanishing gradients.
   - DenseNet Family (DenseNet-121, DenseNet-169, DenseNet-201): Direct feature concatenation maximizes gradient flow.
   - EfficientNet Family (EfficientNet-B0, EfficientNet-B2, EfficientNet-V2-S): Compound scaling of depth, width, resolution.

5. Architectural Agnosticism:
   No single CNN architecture should be declared optimal a priori. Different inductive biases, depth limits,
   and parameter counts yield distinct sensitivity/specificity tradeoffs on clinical validation benchmarks.
"""

from typing import Dict, Any, Optional, Tuple, List, Union
from pathlib import Path
import logging
import torch
import torch.nn as nn
from torchvision import models

logger = logging.getLogger(__name__)

# Canonical binary class mapping
CLASS_TO_IDX: Dict[str, int] = {
    "NORMAL": 0,
    "PNEUMONIA": 1,
}

IDX_TO_CLASS: Dict[int, str] = {
    0: "NORMAL",
    1: "PNEUMONIA",
}


def get_device(prefer_cuda: bool = True) -> torch.device:
    """Detect and return appropriate execution device (CUDA GPU or CPU)."""
    if prefer_cuda and torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


class MedicalClassifier(nn.Module):
    """Configurable Transfer Learning classifier for clinical chest radiograph diagnosis."""

    SUPPORTED_ARCHITECTURES = {
        # ResNet family
        "resnet18": (models.resnet18, models.ResNet18_Weights.DEFAULT),
        "resnet34": (models.resnet34, models.ResNet34_Weights.DEFAULT),
        "resnet50": (models.resnet50, models.ResNet50_Weights.DEFAULT),
        "resnet101": (models.resnet101, models.ResNet101_Weights.DEFAULT),
        # DenseNet family
        "densenet121": (models.densenet121, models.DenseNet121_Weights.DEFAULT),
        "densenet169": (models.densenet169, models.DenseNet169_Weights.DEFAULT),
        "densenet201": (models.densenet201, models.DenseNet201_Weights.DEFAULT),
        # EfficientNet family
        "efficientnet_b0": (models.efficientnet_b0, models.EfficientNet_B0_Weights.DEFAULT),
        "efficientnet_b2": (models.efficientnet_b2, models.EfficientNet_B2_Weights.DEFAULT),
        "efficientnet_v2_s": (models.efficientnet_v2_s, models.EfficientNet_V2_S_Weights.DEFAULT),
    }

    def __init__(
        self,
        architecture: str = "resnet50",
        num_classes: int = 2,
        pretrained: bool = True,
        dropout: float = 0.3,
        freeze_backbone: bool = False,
    ):
        """Initialize MedicalClassifier.

        Args:
            architecture: Model family name (e.g. 'resnet50', 'densenet121', 'efficientnet_b0').
            num_classes: Number of target diagnosis classes (default: 2 for NORMAL vs PNEUMONIA).
            pretrained: Whether to load ImageNet pretrained weights.
            dropout: Dropout probability in classification head.
            freeze_backbone: Whether to freeze feature extractor weights initially.
        """
        super().__init__()
        self.arch_key = architecture.lower().strip()
        self.num_classes = num_classes
        self.pretrained = pretrained
        self.dropout_rate = dropout
        self.is_frozen = False

        if self.arch_key not in self.SUPPORTED_ARCHITECTURES:
            raise ValueError(
                f"Unsupported architecture '{architecture}'. "
                f"Supported options: {list(self.SUPPORTED_ARCHITECTURES.keys())}"
            )

        model_builder, default_weights = self.SUPPORTED_ARCHITECTURES[self.arch_key]
        weights = default_weights if pretrained else None

        # Build base backbone
        self.backbone = model_builder(weights=weights)

        # Replace classification head
        self._replace_classifier_head()

        # Apply initial freezing if requested
        if freeze_backbone:
            self.freeze_backbone()

    def _replace_classifier_head(self):
        """Replace pretrained ImageNet 1000-class head with clinical binary head."""
        if "resnet" in self.arch_key:
            in_features = self.backbone.fc.in_features
            self.classifier_module_name = "fc"
            self.backbone.fc = nn.Sequential(
                nn.Dropout(p=self.dropout_rate),
                nn.Linear(in_features, self.num_classes),
            )
        elif "densenet" in self.arch_key:
            in_features = self.backbone.classifier.in_features
            self.classifier_module_name = "classifier"
            self.backbone.classifier = nn.Sequential(
                nn.Dropout(p=self.dropout_rate),
                nn.Linear(in_features, self.num_classes),
            )
        elif "efficientnet" in self.arch_key:
            # EfficientNet classifier is nn.Sequential(Dropout, Linear)
            in_features = self.backbone.classifier[1].in_features
            self.classifier_module_name = "classifier"
            self.backbone.classifier = nn.Sequential(
                nn.Dropout(p=self.dropout_rate),
                nn.Linear(in_features, self.num_classes),
            )
        else:
            raise NotImplementedError(f"Head replacement not configured for {self.arch_key}")

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass generating raw logits (batch_size, num_classes)."""
        return self.backbone(x)

    def freeze_backbone(self):
        """Freeze all feature extractor layers, keeping only the classification head trainable."""
        for param in self.backbone.parameters():
            param.requires_grad = False

        # Unfreeze classifier head
        head = getattr(self.backbone, self.classifier_module_name)
        for param in head.parameters():
            param.requires_grad = True

        self.is_frozen = True
        logger.info(f"Backbone frozen for {self.arch_key}. Only classification head is trainable.")

    def unfreeze_backbone(self, num_layers: Optional[int] = None):
        """Unfreeze backbone parameters for fine-tuning.

        Args:
            num_layers: If None, unfreezes the entire model. If integer, unfreezes top N child blocks.
        """
        if num_layers is None:
            for param in self.backbone.parameters():
                param.requires_grad = True
            self.is_frozen = False
            logger.info(f"Entire backbone unfrozen for {self.arch_key}.")
        else:
            # Unfreeze only the last N top-level child modules
            children = list(self.backbone.children())
            total_children = len(children)
            unfreeze_from = max(0, total_children - num_layers)

            for i, child in enumerate(children):
                requires_grad = i >= unfreeze_from
                for param in child.parameters():
                    param.requires_grad = requires_grad

            self.is_frozen = False
            logger.info(
                f"Unfroze top {num_layers} blocks ({total_children - unfreeze_from}/{total_children}) for {self.arch_key}."
            )

    def get_target_layer_for_gradcam(self) -> nn.Module:
        """Return the optimal final convolutional layer for Grad-CAM visual heatmaps."""
        if "resnet" in self.arch_key:
            return self.backbone.layer4[-1]
        elif "densenet" in self.arch_key:
            return self.backbone.features.norm5
        elif "efficientnet" in self.arch_key:
            return self.backbone.features[-1]
        else:
            raise ValueError(f"Grad-CAM target layer not mapped for {self.arch_key}")

    def get_model_metadata(self) -> Dict[str, Any]:
        """Return comprehensive architectural parameter metadata and device mapping."""
        total_params = sum(p.numel() for p in self.parameters())
        trainable_params = sum(p.numel() for p in self.parameters() if p.requires_grad)
        frozen_params = total_params - trainable_params

        # Get device of first parameter
        param_device = next(self.parameters()).device.type

        return {
            "architecture": self.arch_key,
            "pretrained": self.pretrained,
            "num_classes": self.num_classes,
            "class_mapping": CLASS_TO_IDX,
            "dropout_rate": self.dropout_rate,
            "is_frozen": self.is_frozen,
            "total_parameters": total_params,
            "trainable_parameters": trainable_params,
            "frozen_parameters": frozen_params,
            "device": param_device,
            "classifier_module": self.classifier_module_name,
        }


def build_model(
    architecture: str = "resnet50",
    num_classes: int = 2,
    pretrained: bool = True,
    dropout: float = 0.3,
    freeze_backbone: bool = False,
    device: Optional[Union[str, torch.device]] = None,
) -> MedicalClassifier:
    """Factory function to instantiate, configure, and place a MedicalClassifier model on device.

    Args:
        architecture: Supported architecture key ('resnet50', 'densenet121', 'efficientnet_b0', etc.).
        num_classes: Output class count (default 2 for NORMAL vs PNEUMONIA).
        pretrained: Whether to load ImageNet weights.
        dropout: Classifier dropout probability.
        freeze_backbone: Initial freeze status of convolutional feature extractor.
        device: Target execution device. If None, auto-selects CUDA if available, else CPU.

    Returns:
        Configured MedicalClassifier model placed on target device.
    """
    model = MedicalClassifier(
        architecture=architecture,
        num_classes=num_classes,
        pretrained=pretrained,
        dropout=dropout,
        freeze_backbone=freeze_backbone,
    )

    target_device = torch.device(device) if device else get_device()
    model = model.to(target_device)
    return model


def save_model_checkpoint(
    model: MedicalClassifier,
    filepath: Union[str, Path],
    optimizer: Optional[torch.optim.Optimizer] = None,
    epoch: Optional[int] = None,
    metrics: Optional[Dict[str, Any]] = None,
    extra_config: Optional[Dict[str, Any]] = None,
) -> Path:
    """Save model state dictionary and architectural hyperparameters to disk.

    Args:
        model: MedicalClassifier instance.
        filepath: Destination path (.pth or .pt).
        optimizer: Optional optimizer state dictionary.
        epoch: Optional training epoch number.
        metrics: Optional validation metrics dictionary.
        extra_config: Additional metadata dictionary.

    Returns:
        Path object of saved checkpoint.
    """
    dest_path = Path(filepath)
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    metadata = model.get_model_metadata()

    checkpoint: Dict[str, Any] = {
        "model_state_dict": model.state_dict(),
        "metadata": metadata,
        "config": {
            "architecture": model.arch_key,
            "num_classes": model.num_classes,
            "pretrained": model.pretrained,
            "dropout": model.dropout_rate,
            **(extra_config or {}),
        },
        "epoch": epoch,
        "metrics": metrics or {},
    }

    if optimizer is not None:
        checkpoint["optimizer_state_dict"] = optimizer.state_dict()

    torch.save(checkpoint, dest_path)
    logger.info(f"Model checkpoint saved successfully to {dest_path}")
    return dest_path


def load_model_checkpoint(
    filepath: Union[str, Path],
    device: Optional[Union[str, torch.device]] = None,
) -> Tuple[MedicalClassifier, Dict[str, Any]]:
    """Load a saved model checkpoint and reconstruct the MedicalClassifier architecture.

    Args:
        filepath: Path to saved checkpoint file.
        device: Target device for loaded model weights.

    Returns:
        Tuple of (MedicalClassifier model, checkpoint dictionary).
    """
    ckpt_path = Path(filepath)
    if not ckpt_path.exists():
        raise FileNotFoundError(f"Checkpoint file not found: {ckpt_path.resolve()}")

    target_device = torch.device(device) if device else get_device()

    checkpoint = torch.load(ckpt_path, map_location=target_device)

    config = checkpoint.get("config", {})
    architecture = config.get("architecture", "resnet50")
    num_classes = config.get("num_classes", 2)
    dropout = config.get("dropout", 0.3)

    # Reconstruct architecture (pretrained=False since weights will be loaded from state_dict)
    model = MedicalClassifier(
        architecture=architecture,
        num_classes=num_classes,
        pretrained=False,
        dropout=dropout,
    )

    model.load_state_dict(checkpoint["model_state_dict"])
    model = model.to(target_device)
    model.eval()

    logger.info(f"Loaded {architecture} model from {ckpt_path} onto {target_device}")
    return model, checkpoint
