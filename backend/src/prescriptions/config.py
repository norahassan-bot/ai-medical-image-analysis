"""Configuration module for Prescription Recognition and Layout Detection Pipeline."""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass
class PrescriptionConfig:
    """Master configuration for prescription ML pipeline."""
    
    # Base filesystem paths
    backend_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent)
    project_root: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent.parent)
    
    data_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent.parent / "data" / "prescriptions")
    models_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent.parent / "models")
    reports_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent.parent / "reports" / "prescription")
    
    # Checkpoint storage
    detection_checkpoint_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent.parent / "models" / "prescription_detection")
    recognition_checkpoint_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent.parent / "models" / "prescription_recognition")
    
    # Preprocessing parameters
    detection_input_size: Tuple[int, int] = (1024, 1024)
    handwriting_input_size: Tuple[int, int] = (64, 256)
    clahe_clip_limit: float = 2.0
    clahe_tile_grid_size: Tuple[int, int] = (8, 8)
    crop_padding_px: int = 8
    max_upscale_factor: float = 2.5
    
    # Medicine Region Detection parameters
    detector_backbone: str = "mobilenet_v3_large"
    num_detection_classes: int = 2  # Background (0), medicine_region (1)
    detection_score_threshold: float = 0.50
    detection_iou_threshold: float = 0.45
    detection_batch_size: int = 4
    detection_learning_rate: float = 1e-3
    detection_epochs: int = 15
    detection_random_seed: int = 42
    
    # Handwriting Recognition (CRNN + CTC) parameters
    recognition_vocab: str = " 0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ.,-+/%()[]#:*'\""
    blank_index: int = 0  # 0 is reserved for CTC blank
    crnn_cnn_out_channels: int = 512
    crnn_rnn_hidden_size: int = 256
    crnn_rnn_num_layers: int = 2
    crnn_rnn_dropout: float = 0.2
    recognition_batch_size: int = 16
    recognition_learning_rate: float = 5e-4
    recognition_epochs: int = 20
    recognition_random_seed: int = 42
    
    # Pipeline & Scoring thresholds
    uncertainty_confidence_threshold: float = 0.60
    top_k_alternatives: int = 3
    
    def __post_init__(self):
        """Ensure all required directories exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.detection_checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.recognition_checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        (self.reports_dir / "smoke_test").mkdir(parents=True, exist_ok=True)


# Global default configuration instance
default_config = PrescriptionConfig()
