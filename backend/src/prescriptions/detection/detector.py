"""Medicine region detection and cropping modules for prescription layouts."""

import os
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Union
import numpy as np
import cv2
from PIL import Image
import torch
import torch.nn as nn
import torchvision
from torchvision.models.detection import fasterrcnn_mobilenet_v3_large_320_fpn, FasterRCNN_MobileNet_V3_Large_320_FPN_Weights
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor

from ..config import PrescriptionConfig, default_config
from ..preprocessing.image_preprocessor import PrescriptionImagePreprocessor
from ..schemas.prediction import MedicineCropInfo


class MedicineRegionCropper:
    """Safely extracts, pads, and normalizes medicine region crops from prescription sheets."""

    def __init__(self, config: Optional[PrescriptionConfig] = None):
        self.config = config or default_config
        self.padding = self.config.crop_padding_px
        self.max_upscale = self.config.max_upscale_factor

    def crop_regions(
        self,
        image_input: Union[str, Path, np.ndarray, Image.Image],
        bounding_boxes: List[Union[List[int], Dict[str, Any]]],
        save_dir: Optional[Union[str, Path]] = None
    ) -> List[Dict[str, Any]]:
        """Extracts bounding box regions from the prescription image.
        
        Args:
            image_input: Raw image array, PIL Image, or file path.
            bounding_boxes: List of [x1, y1, x2, y2] or dicts containing 'bbox' and 'confidence'.
            save_dir: Optional directory to save cropped PNG images.
            
        Returns:
            List of crop metadata dicts containing:
                - 'region_id': str
                - 'bbox': [x1, y1, x2, y2]
                - 'confidence': float
                - 'crop_bgr': np.ndarray
                - 'crop_rgb': np.ndarray
                - 'crop_path': Optional[str]
        """
        # Load image array
        if isinstance(image_input, (str, Path)):
            bgr = cv2.imread(str(image_input))
            if bgr is None:
                raise FileNotFoundError(f"Could not load image from {image_input}")
        elif isinstance(image_input, Image.Image):
            rgb = np.array(image_input.convert("RGB"))
            bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        elif isinstance(image_input, np.ndarray):
            bgr = image_input.copy()
            if bgr.ndim == 2:
                bgr = cv2.cvtColor(bgr, cv2.COLOR_GRAY2BGR)
        else:
            raise TypeError(f"Unsupported image input type: {type(image_input)}")

        img_h, img_w = bgr.shape[:2]
        crops = []
        
        if save_dir:
            save_path = Path(save_dir)
            save_path.mkdir(parents=True, exist_ok=True)
        else:
            save_path = None

        for idx, item in enumerate(bounding_boxes):
            if isinstance(item, dict):
                raw_bbox = item.get("bbox", [0, 0, 0, 0])
                conf = float(item.get("confidence", item.get("score", 1.0)))
                reg_id = item.get("region_id", f"medicine_{idx + 1}")
            elif isinstance(item, (list, tuple)) and len(item) >= 4:
                raw_bbox = item[:4]
                conf = 1.0
                reg_id = f"medicine_{idx + 1}"
            else:
                continue

            # Support both [x1, y1, x2, y2] and [x, y, w, h]
            x1, y1, c3, c4 = raw_bbox
            if c3 > x1 and c4 > y1:
                x2, y2 = c3, c4
            elif c3 <= 0 or c4 <= 0 or (c3 == x1 and c4 == y1):
                # Zero-area or inverted box
                continue
            else:
                # [x, y, w, h] format
                x2, y2 = x1 + c3, y1 + c4

            # Check raw unpadded area
            if (x2 - x1) <= 2 or (y2 - y1) <= 2:
                continue

            # Add padding
            px1 = max(0, int(x1) - self.padding)
            py1 = max(0, int(y1) - self.padding)
            px2 = min(img_w, int(x2) + self.padding)
            py2 = min(img_h, int(y2) + self.padding)

            # Drop zero-area or inverted boxes
            crop_w = px2 - px1
            crop_h = py2 - py1
            if crop_w <= 2 or crop_h <= 2:
                continue

            crop_bgr = bgr[py1:py2, px1:px2].copy()
            crop_rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)

            file_saved_path = None
            if save_path:
                file_name = f"{reg_id}_{px1}_{py1}_{px2}_{py2}.png"
                full_save = save_path / file_name
                cv2.imwrite(str(full_save), crop_bgr)
                file_saved_path = str(full_save)

            crops.append({
                "region_id": reg_id,
                "bbox": [px1, py1, px2, py2],
                "confidence": round(conf, 4),
                "crop_bgr": crop_bgr,
                "crop_rgb": crop_rgb,
                "crop_path": file_saved_path
            })

        return crops


class MedicineRegionDetector:
    """Lightweight deep learning object detector for medicine region proposals in prescriptions."""

    def __init__(
        self,
        model_path: Optional[Union[str, Path]] = None,
        config: Optional[PrescriptionConfig] = None,
        device: Optional[str] = None
    ):
        self.config = config or default_config
        self.device = torch.device(device if device else ("cuda" if torch.cuda.is_available() else "cpu"))
        self.preprocessor = PrescriptionImagePreprocessor(self.config)
        self.cropper = MedicineRegionCropper(self.config)
        self.version = "1.0.0-mobilenetv3-fasterrcnn"
        
        # Build model architecture
        self.model = self._build_model()
        self.model_path = model_path
        
        if model_path and Path(model_path).exists():
            self.load_weights(model_path)
        else:
            # Check default checkpoint location
            default_ckpt = self.config.detection_checkpoint_dir / "best_detector.pt"
            if default_ckpt.exists():
                self.load_weights(default_ckpt)
            else:
                self.model.eval()

    def _build_model(self) -> nn.Module:
        """Constructs Faster R-CNN with MobileNetV3-Large 320 FPN backbone offline."""
        model = fasterrcnn_mobilenet_v3_large_320_fpn(
            weights=None,
            weights_backbone=None,
            num_classes=self.config.num_detection_classes
        )
        model.to(self.device)
        return model

    def load_weights(self, checkpoint_path: Union[str, Path]):
        """Loads model weights from checkpoint."""
        p = Path(checkpoint_path)
        if not p.exists():
            raise FileNotFoundError(f"Detector checkpoint not found at {checkpoint_path}")
            
        ckpt = torch.load(p, map_location=self.device)
        if isinstance(ckpt, dict) and "model_state_dict" in ckpt:
            self.model.load_state_dict(ckpt["model_state_dict"])
            self.version = ckpt.get("version", self.version)
        else:
            self.model.load_state_dict(ckpt)
            
        self.model.eval()
        self.model_path = str(p)

    def detect(
        self,
        image_input: Union[str, Path, np.ndarray, Image.Image],
        score_threshold: Optional[float] = None,
        iou_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Runs medicine region inference on a prescription image.
        
        Returns:
            List of detected regions: [{'bbox': [x1, y1, x2, y2], 'confidence': float, 'class_name': 'medicine_region'}]
        """
        score_thresh = score_threshold or self.config.detection_score_threshold
        iou_thresh = iou_threshold or self.config.detection_iou_threshold

        # Preprocess full prescription sheet
        prep_data = self.preprocessor.preprocess_for_detection(image_input)
        tensor_chw = prep_data["tensor"]  # (3, H, W)
        scale = prep_data["scale"]
        pad_x, pad_y = prep_data["padding"]
        orig_h, orig_w = prep_data["original_size"]

        img_tensor = torch.from_numpy(tensor_chw).float().to(self.device).unsqueeze(0)  # (1, 3, H, W)

        self.model.eval()
        with torch.no_grad():
            predictions = self.model(img_tensor)

        detections = []
        if predictions and len(predictions) > 0:
            pred = predictions[0]
            boxes = pred.get("boxes", torch.empty((0, 4))).cpu().numpy()
            scores = pred.get("scores", torch.empty((0,))).cpu().numpy()
            labels = pred.get("labels", torch.empty((0,))).cpu().numpy()

            for box, score, lbl in zip(boxes, scores, labels):
                if score < score_thresh:
                    continue
                if lbl != 1:  # 1 is medicine_region
                    continue

                bx1, by1, bx2, by2 = box
                # Invert letterbox padding and scaling back to original image space
                orig_x1 = max(0, min(orig_w, int((bx1 - pad_x) / scale)))
                orig_y1 = max(0, min(orig_h, int((by1 - pad_y) / scale)))
                orig_x2 = max(0, min(orig_w, int((bx2 - pad_x) / scale)))
                orig_y2 = max(0, min(orig_h, int((by2 - pad_y) / scale)))

                if (orig_x2 - orig_x1) > 10 and (orig_y2 - orig_y1) > 10:
                    detections.append({
                        "bbox": [orig_x1, orig_y1, orig_x2, orig_y2],
                        "confidence": float(score),
                        "class_name": "medicine_region"
                    })

        # Apply Non-Maximum Suppression (NMS) if multiple overlapping boxes
        if len(detections) > 1:
            box_tensor = torch.tensor([d["bbox"] for d in detections], dtype=torch.float32)
            score_tensor = torch.tensor([d["confidence"] for d in detections], dtype=torch.float32)
            keep_indices = torchvision.ops.nms(box_tensor, score_tensor, iou_thresh).tolist()
            detections = [detections[i] for i in keep_indices]

        # Sort detections top-to-bottom as typical in prescriptions
        detections.sort(key=lambda d: (d["bbox"][1], d["bbox"][0]))
        return detections
