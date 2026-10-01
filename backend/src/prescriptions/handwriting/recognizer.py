"""Handwritten Text Recognition (HTR) model using CRNN + BiLSTM + CTC Decoder."""

import os
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Union
import numpy as np
import cv2
from PIL import Image
import torch
import torch.nn as nn
import torch.nn.functional as F

from ..config import PrescriptionConfig, default_config
from ..preprocessing.image_preprocessor import PrescriptionImagePreprocessor
from .decoder import CTCDecoder, normalize_ocr_text
from ..schemas.prediction import AlternativeCandidate, NormalizedTextResult


class CRNNModel(nn.Module):
    """Convolutional Recurrent Neural Network (CRNN) for handwritten text transcription."""

    def __init__(
        self,
        img_h: int = 64,
        in_channels: int = 1,
        num_classes: int = 80,
        rnn_hidden: int = 256,
        rnn_layers: int = 2,
        dropout: float = 0.2
    ):
        super().__init__()
        self.img_h = img_h
        self.num_classes = num_classes

        # 1. Feature Extractor (CNN)
        self.cnn = nn.Sequential(
            # Stage 1: (1, 64, W) -> (64, 32, W/2)
            nn.Conv2d(in_channels, 64, kernel_size=3, stride=1, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2, stride=2),

            # Stage 2: (64, 32, W/2) -> (128, 16, W/4)
            nn.Conv2d(64, 128, kernel_size=3, stride=1, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2, stride=2),

            # Stage 3: (128, 16, W/4) -> (256, 8, W/4)
            nn.Conv2d(128, 256, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            nn.Conv2d(256, 256, kernel_size=3, stride=1, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=(2, 2), stride=(2, 1), padding=(0, 1)),

            # Stage 4: (256, 8, W/4) -> (512, 4, W/4)
            nn.Conv2d(256, 512, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(512),
            nn.ReLU(inplace=True),
            nn.Conv2d(512, 512, kernel_size=3, stride=1, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=(2, 2), stride=(2, 1), padding=(0, 1)),

            # Stage 5: Collapse height to 1: (512, 4, W/4) -> (512, 1, W/4)
            nn.Conv2d(512, 512, kernel_size=(4, 1), stride=1, padding=0),
            nn.BatchNorm2d(512),
            nn.ReLU(inplace=True)
        )

        # 2. Sequence Modeling (Bidirectional LSTM)
        self.rnn = nn.LSTM(
            input_size=512,
            hidden_size=rnn_hidden,
            num_layers=rnn_layers,
            bidirectional=True,
            dropout=dropout if rnn_layers > 1 else 0.0,
            batch_first=False
        )

        # 3. Transcription Layer (Linear + LogSoftmax for CTC)
        self.fc = nn.Linear(rnn_hidden * 2, num_classes)
        self.log_softmax = nn.LogSoftmax(dim=2)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass.
        
        Args:
            x: (B, 1, 64, W) image tensor.
            
        Returns:
            (T, B, num_classes) log-probabilities tensor for CTCLoss.
        """
        features = self.cnn(x)  # (B, 512, 1, T)
        b, c, h, t = features.size()
        assert h == 1, f"Expected height after CNN to be 1, got {h}"

        features = features.squeeze(2)  # (B, 512, T)
        features = features.permute(2, 0, 1)  # (T, B, 512)

        rnn_out, _ = self.rnn(features)  # (T, B, 2 * hidden)
        logits = self.fc(rnn_out)  # (T, B, num_classes)
        log_probs = self.log_softmax(logits)  # (T, B, num_classes)
        return log_probs


class HandwrittenTextRecognizer:
    """Clinical Handwritten Text Recognizer with CTC Decoding and Medication Text Normalization."""

    def __init__(
        self,
        model_path: Optional[Union[str, Path]] = None,
        config: Optional[PrescriptionConfig] = None,
        device: Optional[str] = None
    ):
        self.config = config or default_config
        self.device = torch.device(device if device else ("cuda" if torch.cuda.is_available() else "cpu"))
        self.preprocessor = PrescriptionImagePreprocessor(self.config)
        self.decoder = CTCDecoder(vocab=self.config.recognition_vocab, blank_index=self.config.blank_index)
        self.version = "1.0.0-crnn-bilstm-ctc"

        # Build CRNN model
        self.model = CRNNModel(
            img_h=self.config.handwriting_input_size[0],
            in_channels=1,
            num_classes=self.decoder.num_classes,
            rnn_hidden=self.config.crnn_rnn_hidden_size,
            rnn_layers=self.config.crnn_rnn_num_layers,
            dropout=self.config.crnn_rnn_dropout
        )
        self.model.to(self.device)
        self.model_path = model_path

        if model_path and Path(model_path).exists():
            self.load_weights(model_path)
        else:
            default_ckpt = self.config.recognition_checkpoint_dir / "best_recognizer.pt"
            if default_ckpt.exists():
                self.load_weights(default_ckpt)
            else:
                self.model.eval()

    def load_weights(self, checkpoint_path: Union[str, Path]):
        """Loads weights from checkpoint."""
        p = Path(checkpoint_path)
        if not p.exists():
            raise FileNotFoundError(f"HTR checkpoint not found at {checkpoint_path}")

        ckpt = torch.load(p, map_location=self.device)
        if isinstance(ckpt, dict) and "model_state_dict" in ckpt:
            self.model.load_state_dict(ckpt["model_state_dict"])
            self.version = ckpt.get("version", self.version)
        else:
            self.model.load_state_dict(ckpt)

        self.model.eval()
        self.model_path = str(p)

    def recognize(
        self,
        crop_input: Union[str, Path, np.ndarray, Image.Image],
        top_k: int = 3
    ) -> Dict[str, Any]:
        """Runs handwriting transcription on a single cropped medicine token."""
        # Preprocess handwriting crop
        prep = self.preprocessor.preprocess_for_handwriting(crop_input)
        tensor_chw = prep["tensor"]  # (1, 64, 256)

        img_tensor = torch.from_numpy(tensor_chw).float().to(self.device).unsqueeze(0)  # (1, 1, 64, 256)

        self.model.eval()
        with torch.no_grad():
            log_probs = self.model(img_tensor)  # (T, 1, C)

        # Squeeze batch dimension for decoder: (T, C)
        single_log_probs = log_probs[:, 0, :]

        # 1. Greedy path decoding
        raw_text, confidence, char_confs = self.decoder.decode_greedy(single_log_probs)

        # 2. Top-k beam search for alternative candidates
        alternatives = self.decoder.decode_beam_search(
            single_log_probs,
            beam_width=5,
            top_k=top_k
        )

        # 3. Medical token normalization
        norm_result = normalize_ocr_text(raw_text)

        # 4. Uncertainty classification
        uncertain = bool(confidence < self.config.uncertainty_confidence_threshold or len(raw_text.strip()) == 0)

        return {
            "raw_text": raw_text,
            "normalized_text": norm_result.normalized_text,
            "confidence": round(confidence, 4),
            "uncertain": uncertain,
            "alternatives": [alt.model_dump() for alt in alternatives],
            "character_confidences": char_confs,
            "model_version": self.version
        }
