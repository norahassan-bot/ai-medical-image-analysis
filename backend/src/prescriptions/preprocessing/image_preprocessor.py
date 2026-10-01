"""Image preprocessor for prescription sheets and cropped handwriting tokens."""

import io
from pathlib import Path
from typing import Union, Tuple, Dict, Any, Optional
import numpy as np
import cv2
from PIL import Image, ImageOps

from ..config import PrescriptionConfig, default_config


class PrescriptionImagePreprocessor:
    """Deterministic, non-destructive image preprocessor for prescription pipelines."""

    def __init__(self, config: Optional[PrescriptionConfig] = None):
        self.config = config or default_config
        self.clahe = cv2.createCLAHE(
            clipLimit=self.config.clahe_clip_limit,
            tileGridSize=self.config.clahe_tile_grid_size
        )

    def load_image(self, image_input: Union[str, Path, bytes, Image.Image, np.ndarray]) -> np.ndarray:
        """Loads and standardizes input to a BGR numpy uint8 image array."""
        if isinstance(image_input, (str, Path)):
            p = Path(image_input)
            if not p.exists():
                raise FileNotFoundError(f"Prescription image not found at: {image_input}")
            # Use PIL to read with EXIF orientation correction
            with Image.open(p) as pil_img:
                pil_img = ImageOps.exif_transpose(pil_img)
                if pil_img.mode != "RGB":
                    pil_img = pil_img.convert("RGB")
                np_img = np.array(pil_img)
                # Convert RGB to BGR for OpenCV standard
                return cv2.cvtColor(np_img, cv2.COLOR_RGB2BGR)

        elif isinstance(image_input, bytes):
            if len(image_input) == 0:
                raise ValueError("Empty image byte payload provided.")
            with Image.open(io.BytesIO(image_input)) as pil_img:
                pil_img = ImageOps.exif_transpose(pil_img)
                if pil_img.mode != "RGB":
                    pil_img = pil_img.convert("RGB")
                np_img = np.array(pil_img)
                return cv2.cvtColor(np_img, cv2.COLOR_RGB2BGR)

        elif isinstance(image_input, Image.Image):
            pil_img = ImageOps.exif_transpose(image_input)
            if pil_img.mode != "RGB":
                pil_img = pil_img.convert("RGB")
            np_img = np.array(pil_img)
            return cv2.cvtColor(np_img, cv2.COLOR_RGB2BGR)

        elif isinstance(image_input, np.ndarray):
            # Non-destructive copy
            img_copy = image_input.copy()
            if img_copy.ndim == 2:
                return cv2.cvtColor(img_copy, cv2.COLOR_GRAY2BGR)
            elif img_copy.ndim == 3 and img_copy.shape[2] == 4:
                return cv2.cvtColor(img_copy, cv2.COLOR_BGRA2BGR)
            elif img_copy.ndim == 3 and img_copy.shape[2] == 3:
                return img_copy
            else:
                raise ValueError(f"Unsupported numpy image shape: {img_copy.shape}")
        else:
            raise TypeError(f"Unsupported image input type: {type(image_input)}")

    def correct_shadows_and_illumination(self, bgr_image: np.ndarray) -> np.ndarray:
        """Reduces shadows and non-uniform lighting via morphological background estimation."""
        gray = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2GRAY)
        # Dilate then median blur to estimate background illumination surface
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (19, 19))
        dilated = cv2.dilate(gray, kernel)
        bg = cv2.medianBlur(dilated, 21)
        
        # Difference from background surface + 255 offset
        diff = 255 - cv2.absdiff(gray, bg)
        norm = cv2.normalize(diff, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8UC1)
        return cv2.cvtColor(norm, cv2.COLOR_GRAY2BGR)

    def deskew_image(self, bgr_image: np.ndarray, max_skew_angle: float = 15.0) -> Tuple[np.ndarray, float]:
        """Detects and corrects document skew using Hough Line transform / minAreaRect."""
        gray = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100, minLineLength=100, maxLineGap=10)
        
        angle = 0.0
        if lines is not None:
            angles = []
            for line in lines:
                pts = np.asarray(line).reshape(-1)
                if len(pts) >= 4:
                    x1, y1, x2, y2 = pts[:4]
                    rad = np.arctan2(float(y2 - y1), float(x2 - x1))
                    deg = np.degrees(rad)
                    if abs(deg) < max_skew_angle:
                        angles.append(deg)
            if angles:
                angle = float(np.median(angles))
                
        if abs(angle) > 0.5:
            h, w = bgr_image.shape[:2]
            center = (w // 2, h // 2)
            rot_mat = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(bgr_image, rot_mat, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
            return rotated, angle
        return bgr_image, 0.0

    def enhance_contrast(self, bgr_image: np.ndarray) -> np.ndarray:
        """Applies CLAHE on the L channel of LAB color space to boost ink legibility."""
        lab = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2LAB)
        l_chan, a_chan, b_chan = cv2.split(lab)
        enhanced_l = self.clahe.apply(l_chan)
        merged = cv2.merge([enhanced_l, a_chan, b_chan])
        return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)

    def preprocess(self, image_input: Union[str, Path, bytes, Image.Image, np.ndarray]) -> np.ndarray:
        """Standard full preprocessing: EXIF fix, shadow correction, deskew, and contrast enhancement."""
        bgr = self.load_image(image_input)
        shadow_free = self.correct_shadows_and_illumination(bgr)
        deskewed, _ = self.deskew_image(shadow_free)
        enhanced = self.enhance_contrast(deskewed)
        return enhanced

    def preprocess_for_detection(
        self,
        image_input: Union[str, Path, bytes, Image.Image, np.ndarray],
        target_size: Optional[Tuple[int, int]] = None
    ) -> Dict[str, Any]:
        """Prepares a full prescription sheet for the region detector.
        
        Returns:
            Dict containing:
                - 'image': (3, H, W) normalized float tensor / RGB array
                - 'original_size': (orig_h, orig_w)
                - 'scale': float scaling factor
                - 'padding': (pad_x, pad_y)
                - 'rgb_image': (H, W, 3) uint8 numpy array for visualization
        """
        bgr = self.load_image(image_input)
        deskewed, _ = self.deskew_image(bgr)
        enhanced = self.enhance_contrast(deskewed)
        rgb = cv2.cvtColor(enhanced, cv2.COLOR_BGR2RGB)
        
        target_w, target_h = target_size or self.config.detection_input_size
        orig_h, orig_w = rgb.shape[:2]
        
        # Scale while preserving aspect ratio
        scale = min(target_w / orig_w, target_h / orig_h)
        new_w, new_h = int(orig_w * scale), int(orig_h * scale)
        resized = cv2.resize(rgb, (new_w, new_h), interpolation=cv2.INTER_AREA)
        
        # Letterbox padding with neutral gray (114, 114, 114)
        canvas = np.full((target_h, target_w, 3), 114, dtype=np.uint8)
        pad_x = (target_w - new_w) // 2
        pad_y = (target_h - new_h) // 2
        canvas[pad_y:pad_y + new_h, pad_x:pad_x + new_w] = resized
        
        # Float32 normalized to [0, 1]
        norm_tensor = canvas.astype(np.float32) / 255.0
        # Transpose to (C, H, W)
        tensor_chw = np.transpose(norm_tensor, (2, 0, 1))
        
        return {
            "tensor": tensor_chw,
            "canvas_rgb": canvas,
            "original_size": (orig_h, orig_w),
            "scale": scale,
            "padding": (pad_x, pad_y),
            "processed_bgr": enhanced
        }

    def preprocess_for_handwriting(
        self,
        crop_input: Union[str, Path, bytes, Image.Image, np.ndarray],
        target_size: Optional[Tuple[int, int]] = None
    ) -> Dict[str, Any]:
        """Prepares a cropped handwriting medicine token for CRNN/HTR recognition.
        
        Returns:
            Dict containing:
                - 'tensor': (1, H, W) normalized float32 tensor
                - 'original_size': (orig_h, orig_w)
                - 'crop_rgb': visualization array
        """
        bgr = self.load_image(crop_input)
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        
        # Apply CLAHE to grayscale crop
        enhanced_gray = self.clahe.apply(gray)
        
        target_h, target_w = target_size or self.config.handwriting_input_size
        orig_h, orig_w = enhanced_gray.shape[:2]
        
        # Prevent division by zero on corrupted crops
        if orig_h == 0 or orig_w == 0:
            raise ValueError(f"Invalid crop dimensions: {orig_w}x{orig_h}")
            
        # Scale to target height, preserving aspect ratio up to target_w
        scale = target_h / orig_h
        new_w = min(int(orig_w * scale), target_w)
        resized = cv2.resize(enhanced_gray, (new_w, target_h), interpolation=cv2.INTER_AREA)
        
        # Pad right side with white (255) background
        canvas = np.full((target_h, target_w), 255, dtype=np.uint8)
        canvas[:, :new_w] = resized
        
        # Normalize to [-1.0, 1.0] standard for CRNN
        norm_tensor = (canvas.astype(np.float32) / 127.5) - 1.0
        tensor_chw = np.expand_dims(norm_tensor, axis=0)  # (1, H, W)
        
        return {
            "tensor": tensor_chw,
            "canvas_gray": canvas,
            "original_size": (orig_h, orig_w),
            "valid_width": new_w,
            "crop_rgb": cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        }
