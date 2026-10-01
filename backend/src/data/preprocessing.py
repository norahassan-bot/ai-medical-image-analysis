"""Clinical image preprocessing and augmentation pipelines for medical vision models.

Architectural Rationale:
------------------------
1. Why Resizing is Required:
   Deep convolutional neural networks (e.g., ResNet-50, DenseNet-121) rely on fixed-dimensional
   spatial tensors (C, H, W) to perform parallel matrix multiplications across mini-batches.
   Medical radiographs vary substantially in raw resolution and aspect ratio (e.g. 384px to 2916px).
   Standardizing spatial dimensions (default 224x224) ensures consistent kernel receptive fields
   and uniform batch processing.

2. Why Normalization is Required:
   Raw pixel intensities [0, 255] are scaled to [0.0, 1.0] and normalized with channel-wise
   mean and standard deviation (ImageNet standard: mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]).
   This centers input distributions around zero, aligns inputs with pretrained transfer learning weight
   expectations, mitigates vanishing/exploding gradients, and accelerates optimization convergence.

3. Why Augmentation is Training-Only:
   Stochastic perturbations (e.g., random rotation ±10°, slight horizontal flipping, subtle contrast shifts)
   are applied exclusively during training to artificially expand phenotypic variety and regularize
   the network against overfitting. It prevents the model from memorizing anatomical orientations
   or idiosyncratic imaging artifacts.

4. Why Validation & Test Preprocessing Must Remain Deterministic:
   Evaluation datasets (validation and test) must measure objective, unbiased diagnostic accuracy on true
   unaltered patient studies. Stochastic transformations during validation or testing would introduce random
   variance into clinical metrics (e.g., sensitivity, specificity, AUC) and corrupt benchmark validity.

5. Inference Compatibility:
   The evaluation preprocessing pipeline (`get_eval_transforms` / `get_transforms("inference")`) is 100%
   deterministic and directly exportable to live FastAPI inference endpoints for single-scan analysis.
"""

from typing import Tuple, Optional
from torchvision import transforms

# Standard ImageNet distribution constants
DEFAULT_IMAGENET_MEAN = (0.485, 0.456, 0.406)
DEFAULT_IMAGENET_STD = (0.229, 0.224, 0.225)
DEFAULT_IMAGE_SIZE = (224, 224)


def get_train_transforms(
    image_size: Tuple[int, int] = DEFAULT_IMAGE_SIZE,
    mean: Tuple[float, float, float] = DEFAULT_IMAGENET_MEAN,
    std: Tuple[float, float, float] = DEFAULT_IMAGENET_STD,
    rotation_degrees: int = 10,
    horizontal_flip_prob: float = 0.5,
) -> transforms.Compose:
    """Build stochastic clinical augmentation pipeline for the training partition.

    Args:
        image_size: Target spatial dimensions (H, W).
        mean: Normalization channel means.
        std: Normalization channel standard deviations.
        rotation_degrees: Maximum degree of random rotation.
        horizontal_flip_prob: Probability of horizontal flip.

    Returns:
        torchvision.transforms.Compose pipeline.
    """
    return transforms.Compose([
        transforms.Resize(image_size),
        transforms.RandomHorizontalFlip(p=horizontal_flip_prob),
        transforms.RandomRotation(degrees=rotation_degrees),
        transforms.ColorJitter(brightness=0.1, contrast=0.1),
        transforms.ToTensor(),
        transforms.Normalize(mean=list(mean), std=list(std)),
    ])


def get_eval_transforms(
    image_size: Tuple[int, int] = DEFAULT_IMAGE_SIZE,
    mean: Tuple[float, float, float] = DEFAULT_IMAGENET_MEAN,
    std: Tuple[float, float, float] = DEFAULT_IMAGENET_STD,
) -> transforms.Compose:
    """Build deterministic preprocessing pipeline for validation, test, and live inference.

    Args:
        image_size: Target spatial dimensions (H, W).
        mean: Normalization channel means.
        std: Normalization channel standard deviations.

    Returns:
        Deterministic torchvision.transforms.Compose pipeline.
    """
    return transforms.Compose([
        transforms.Resize(image_size),
        transforms.ToTensor(),
        transforms.Normalize(mean=list(mean), std=list(std)),
    ])


def get_transforms(
    split: str = "train",
    image_size: Tuple[int, int] = DEFAULT_IMAGE_SIZE,
    mean: Tuple[float, float, float] = DEFAULT_IMAGENET_MEAN,
    std: Tuple[float, float, float] = DEFAULT_IMAGENET_STD,
    **kwargs
) -> transforms.Compose:
    """Factory function to retrieve appropriate transform pipeline by split name.

    Args:
        split: One of 'train', 'val', 'validation', 'test', 'inference'.
        image_size: Target spatial dimensions (H, W).
        mean: Channel means for normalization.
        std: Channel std deviations for normalization.

    Returns:
        torchvision.transforms.Compose pipeline.
    """
    normalized_split = split.lower().strip()
    if normalized_split == "train":
        return get_train_transforms(image_size=image_size, mean=mean, std=std, **kwargs)
    elif normalized_split in ("val", "validation", "test", "inference", "eval"):
        return get_eval_transforms(image_size=image_size, mean=mean, std=std)
    else:
        raise ValueError(
            f"Unsupported split '{split}'. Expected one of: 'train', 'val', 'validation', 'test', 'inference'."
        )
