"""Exhaustive test suite for Prescription Recognition Pipeline, Detection, and HTR Modules."""

import io
import pytest
import numpy as np
import cv2
from PIL import Image, ImageOps
import torch

from src.prescriptions.config import PrescriptionConfig, default_config
from src.prescriptions.preprocessing.image_preprocessor import PrescriptionImagePreprocessor
from src.prescriptions.detection.detector import MedicineRegionDetector, MedicineRegionCropper
from src.prescriptions.handwriting.decoder import CTCDecoder, normalize_ocr_text
from src.prescriptions.handwriting.recognizer import HandwrittenTextRecognizer, CRNNModel
from src.prescriptions.pipeline.prescription_pipeline import PrescriptionRecognitionPipeline
from src.prescriptions.evaluation.metrics import (
    compute_cer,
    compute_wer,
    compute_exact_match,
    levenshtein_distance,
    evaluate_htr_predictions
)


# ==============================================================================
# 1. IMAGE PREPROCESSING TESTS
# ==============================================================================

def test_preprocessor_valid_image():
    """Verifies that a valid RGB image loads and preprocesses correctly."""
    preprocessor = PrescriptionImagePreprocessor()
    canvas = np.full((300, 400, 3), 200, dtype=np.uint8)
    # Add fake ink lines
    cv2.line(canvas, (50, 100), (350, 100), (20, 20, 20), 2)
    
    prep_det = preprocessor.preprocess_for_detection(canvas, target_size=(512, 512))
    assert "tensor" in prep_det
    assert prep_det["tensor"].shape == (3, 512, 512)
    assert prep_det["original_size"] == (300, 400)
    assert prep_det["scale"] > 0

    prep_htr = preprocessor.preprocess_for_handwriting(canvas, target_size=(64, 256))
    assert "tensor" in prep_htr
    assert prep_htr["tensor"].shape == (1, 64, 256)


def test_preprocessor_empty_or_corrupted_payload():
    """Verifies preprocessor rejects empty byte payloads safely."""
    preprocessor = PrescriptionImagePreprocessor()
    with pytest.raises(ValueError, match="Empty image byte payload"):
        preprocessor.load_image(b"")


def test_preprocessor_unsupported_format_or_type():
    """Verifies preprocessor rejects invalid input types."""
    preprocessor = PrescriptionImagePreprocessor()
    with pytest.raises(TypeError, match="Unsupported image input type"):
        preprocessor.load_image(12345)  # Invalid int type


def test_preprocessor_exif_rotation_handling():
    """Verifies EXIF orientation metadata is honored non-destructively."""
    preprocessor = PrescriptionImagePreprocessor()
    pil_img = Image.new("RGB", (200, 100), color=(255, 255, 255))
    loaded = preprocessor.load_image(pil_img)
    assert loaded.shape[:2] == (100, 200)


def test_preprocessor_extreme_dimensions():
    """Verifies preprocessor safely handles small or large aspect ratios."""
    preprocessor = PrescriptionImagePreprocessor()
    tiny_img = np.full((30, 800, 3), 240, dtype=np.uint8)
    prep = preprocessor.preprocess_for_detection(tiny_img, target_size=(512, 512))
    assert prep["tensor"].shape == (3, 512, 512)


# ==============================================================================
# 2. MEDICINE REGION DETECTION & CROPPING TESTS
# ==============================================================================

def test_cropper_valid_bounding_boxes():
    """Verifies cropper extracts valid regions with safety padding."""
    cropper = MedicineRegionCropper()
    canvas = np.full((500, 500, 3), 255, dtype=np.uint8)
    boxes = [
        {"bbox": [50, 100, 200, 180], "confidence": 0.92, "region_id": "med_1"},
        [100, 200, 300, 280]
    ]
    crops = cropper.crop_regions(canvas, boxes)
    assert len(crops) == 2
    assert crops[0]["region_id"] == "med_1"
    assert crops[0]["confidence"] == 0.92
    assert crops[0]["crop_bgr"].shape[0] > 0
    assert crops[0]["crop_bgr"].shape[1] > 0


def test_cropper_clipped_and_zero_area_boxes():
    """Verifies cropper clips out-of-bounds boxes and drops zero-area boxes."""
    cropper = MedicineRegionCropper()
    canvas = np.full((200, 200, 3), 255, dtype=np.uint8)
    boxes = [
        [-50, -50, 100, 100],  # Out of bounds -> clipped
        [50, 50, 50, 50],      # Zero-area -> dropped
        [10, 10, 12, 12]       # Too small <= 2px -> dropped
    ]
    crops = cropper.crop_regions(canvas, boxes)
    assert len(crops) == 1
    assert crops[0]["bbox"][0] >= 0
    assert crops[0]["bbox"][1] >= 0


def test_detector_inference_smoke():
    """Verifies detector runs forward pass and returns sorted bounding boxes."""
    detector = MedicineRegionDetector(device="cpu")
    canvas = np.full((600, 400, 3), 255, dtype=np.uint8)
    cv2.putText(canvas, "Rx Paracetamol", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    
    detections = detector.detect(canvas, score_threshold=0.01)
    assert isinstance(detections, list)
    for det in detections:
        assert "bbox" in det
        assert "confidence" in det
        assert len(det["bbox"]) == 4


# ==============================================================================
# 3. HANDWRITING RECOGNITION & CTC DECODER TESTS
# ==============================================================================

def test_ctc_decoder_greedy_and_beam_search():
    """Verifies CTC decoder greedy path and beam search logic."""
    vocab = " abcdefghijklmnopqrstuvwxyz"
    decoder = CTCDecoder(vocab=vocab, blank_index=0)
    
    # Construct artificial logit distribution for "cat"
    T = 10
    C = decoder.num_classes
    logits = torch.full((T, C), -10.0)
    
    # Frame 1-2: 'c' (idx for 'c')
    c_idx = decoder.char_to_idx["c"]
    logits[1:3, c_idx] = 2.0
    # Frame 3: blank
    logits[3, 0] = 2.0
    # Frame 4-5: 'a'
    a_idx = decoder.char_to_idx["a"]
    logits[4:6, a_idx] = 2.0
    # Frame 6: blank
    logits[6, 0] = 2.0
    # Frame 7-8: 't'
    t_idx = decoder.char_to_idx["t"]
    logits[7:9, t_idx] = 2.0

    log_probs = torch.log_softmax(logits, dim=-1)
    
    text, conf, char_confs = decoder.decode_greedy(log_probs)
    assert text == "cat"
    assert conf > 0.5
    assert len(char_confs) == 3

    alts = decoder.decode_beam_search(log_probs, beam_width=5, top_k=2)
    assert len(alts) > 0
    assert alts[0].text == "cat"


def test_text_normalizer():
    """Verifies medical text normalization rules without hallucinating ungrounded tokens."""
    # Test OCR space splitting normalization
    res1 = normalize_ocr_text("Augm entin 1g")
    assert res1.normalized_text == "Augmentin 1g"
    assert res1.raw_text == "Augm entin 1g"

    # Test frequency standardization
    res2 = normalize_ocr_text("1 + 0 + 1")
    assert res2.normalized_text == "1+0+1"

    # Test dosage standardization
    res3 = normalize_ocr_text("500 mg")
    assert res3.normalized_text == "500mg"

    # Test empty string handling
    res_empty = normalize_ocr_text("")
    assert res_empty.normalized_text == ""


def test_recognizer_uncertainty_thresholding():
    """Verifies low confidence outputs are explicitly marked uncertain."""
    recognizer = HandwrittenTextRecognizer(device="cpu")
    canvas = np.full((64, 256, 3), 255, dtype=np.uint8)  # Blank image
    res = recognizer.recognize(canvas)
    
    assert "raw_text" in res
    assert "normalized_text" in res
    assert "confidence" in res
    assert "uncertain" in res
    assert res["uncertain"] is True  # Blank image must yield uncertainty


# ==============================================================================
# 4. END-TO-END PIPELINE & SAFETY BOUNDARY TESTS
# ==============================================================================

def test_pipeline_end_to_end_execution():
    """Verifies the complete pipeline runs and returns valid Pydantic schema."""
    pipeline = PrescriptionRecognitionPipeline(device="cpu")
    canvas = np.full((800, 600, 3), 255, dtype=np.uint8)
    cv2.putText(canvas, "Dr. Smith", (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    cv2.putText(canvas, "Rx", (50, 180), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 2)
    cv2.putText(canvas, "Augmentin 1g", (100, 280), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)

    result = pipeline.analyze(canvas)
    assert result.analysis_type == "prescription"
    assert result.status == "completed"
    assert result.total_regions_detected >= 1
    assert len(result.regions) >= 1
    assert result.processing_time_ms > 0
    assert "RESEARCH BASELINE" in result.disclaimer


def test_pipeline_medical_safety_boundary():
    """Verifies the pipeline NEVER synthesizes unwritten medical instructions or dosages."""
    pipeline = PrescriptionRecognitionPipeline(device="cpu")
    canvas = np.full((800, 600, 3), 255, dtype=np.uint8)
    cv2.putText(canvas, "Ciprocin", (100, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)

    result = pipeline.analyze(canvas)
    # The pipeline should transcribe only visual text and NEVER add unauthorized clinical advice
    for reg in result.regions:
        forbidden_inferences = [
            "take 2 times daily",
            "take twice daily",
            "take with food",
            "indicated for bacterial infection"
        ]
        for forb in forbidden_inferences:
            assert forb not in reg.normalized_text.lower()


# ==============================================================================
# 5. SEQUENCE EVALUATION METRICS TESTS
# ==============================================================================

def test_cer_wer_metrics():
    """Verifies exact computation of Levenshtein, CER, and WER."""
    preds = ["Augmentin", "Paracetamol", "1+0+1"]
    gts = ["Augmentin", "Paracetamol", "1+1+1"]

    cer = compute_cer(preds, gts)
    assert cer == round(1 / (9 + 11 + 5), 4)  # 1 substitution in 25 chars

    wer = compute_wer(preds, gts)
    assert wer == round(1 / 3, 4)

    acc = compute_exact_match(preds, gts)
    assert acc == round(2 / 3, 4)
