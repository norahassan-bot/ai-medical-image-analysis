"""Master script to train baseline prescription models, run evaluations, and generate smoke test reports."""

import os
import sys
import json
import time
from pathlib import Path
import numpy as np
import cv2
from PIL import Image

# Ensure backend/src is in Python path
backend_dir = Path(__file__).resolve().parent.parent
src_dir = backend_dir / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from prescriptions.config import PrescriptionConfig
from prescriptions.detection.train import train_detector
from prescriptions.handwriting.train import train_recognizer
from prescriptions.pipeline.prescription_pipeline import PrescriptionRecognitionPipeline


def run_baseline_and_smoke_tests():
    """Executes full training and smoke test pipeline."""
    print("=" * 70)
    print("TASK 23: PRESCRIPTION BASELINE MODEL TRAINING & SMOKE TEST")
    print("=" * 70)

    config = PrescriptionConfig()

    # 1. Train Medicine Region Detector
    print("\n[Step 1/3] Training Faster R-CNN Medicine Region Detector...")
    det_summary = train_detector(epochs=5, batch_size=2, config=config)

    # 2. Train CRNN Handwritten Text Recognizer
    print("\n[Step 2/3] Training CRNN + BiLSTM + CTC Handwriting Recognizer...")
    htr_summary = train_recognizer(epochs=10, batch_size=8, config=config)

    # 3. Save Experiment Master Configuration
    exp_config_file = config.reports_dir / "experiment_config.json"
    exp_meta = {
        "experiment_id": f"exp_prescription_baseline_{int(time.time())}",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "detector": {
            "model_name": "FasterRCNN-MobileNetV3",
            "weights": "best_detector.pt",
            "epochs": 5,
            "learning_rate": 1e-3,
            "mAP_50": det_summary["test_metrics"]["mAP_50"]
        },
        "recognizer": {
            "model_name": "CRNN-BiLSTM-CTC",
            "weights": "best_recognizer.pt",
            "epochs": 10,
            "learning_rate": 5e-4,
            "cer": htr_summary["test_metrics"]["character_error_rate_cer"],
            "wer": htr_summary["test_metrics"]["word_error_rate_wer"]
        },
        "datasets": {
            "layout_detection": "bangladesh_curated_prescriptions",
            "handwriting_recognition": "rxhandbd",
            "supplemental": "doctors_handwritten_bd, medical_prescription_ocr"
        },
        "safety_disclaimer": "RESEARCH BASELINE: No medical advice or dosage inference implemented."
    }
    with open(exp_config_file, "w", encoding="utf-8") as f:
        json.dump(exp_meta, f, indent=2)
    print(f"[+] Experiment config saved to: {exp_config_file}")

    # 4. End-to-End Real Sample Smoke Test
    print("\n[Step 3/3] Running End-to-End Inference Smoke Test on Real Samples...")
    pipeline = PrescriptionRecognitionPipeline(config=config)

    smoke_test_dir = config.reports_dir / "smoke_test"
    smoke_test_dir.mkdir(parents=True, exist_ok=True)

    # Find sample images
    sample_files = []
    full_presc_dir = config.data_dir / "raw" / "full_prescriptions"
    if full_presc_dir.exists():
        sample_files.extend(list(full_presc_dir.glob("*.png"))[:3])
        sample_files.extend(list(full_presc_dir.glob("*.jpg"))[:3])

    rxhand_dir = config.data_dir / "raw" / "rxhandbd"
    if rxhand_dir.exists():
        sample_files.extend(list(rxhand_dir.glob("*.png"))[:3])

    if not sample_files:
        # Create synthetic test prescription sheet if empty
        dummy_p = smoke_test_dir / "synthetic_smoke_rx.png"
        dummy_canvas = np.full((1200, 800, 3), 255, dtype=np.uint8)
        cv2.putText(dummy_canvas, "Dr. John Doe, MD", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (50, 50, 50), 2)
        cv2.putText(dummy_canvas, "Rx", (50, 250), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 180), 3)
        cv2.putText(dummy_canvas, "Augmentin 1g", (120, 350), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (20, 20, 20), 2)
        cv2.putText(dummy_canvas, "Paracetamol 500mg", (120, 480), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (20, 20, 20), 2)
        cv2.imwrite(str(dummy_p), dummy_canvas)
        sample_files.append(dummy_p)

    smoke_results = []

    for img_p in sample_files[:5]:
        result = pipeline.analyze(img_p)
        res_dict = result.model_dump()
        res_dict["source_file"] = img_p.name

        # Save annotated visualization
        orig_bgr = cv2.imread(str(img_p))
        if orig_bgr is not None:
            vis_canvas = orig_bgr.copy()
            for reg in result.regions:
                x1, y1, x2, y2 = reg.bbox
                cv2.rectangle(vis_canvas, (x1, y1), (x2, y2), (233, 139, 170), 2)
                lbl = f"{reg.normalized_text} ({reg.recognition_confidence:.2f})"
                cv2.putText(vis_canvas, lbl, (x1, max(20, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (43, 183, 169), 2)

            vis_out_path = smoke_test_dir / f"vis_{img_p.stem}.png"
            cv2.imwrite(str(vis_out_path), vis_canvas)
            res_dict["visualization_path"] = str(vis_out_path)

        smoke_results.append(res_dict)
        print(f"  [Sample: {img_p.name}] -> {result.total_regions_detected} regions detected, Latency: {result.processing_time_ms}ms")
        for reg in result.regions:
            print(f"    • Region '{reg.region_id}': Raw='{reg.raw_text}' -> Normalized='{reg.normalized_text}' (Conf: {reg.recognition_confidence}, Uncertain: {reg.uncertain})")

    # Save smoke test json
    smoke_json_path = smoke_test_dir / "smoke_test_predictions.json"
    with open(smoke_json_path, "w", encoding="utf-8") as f:
        json.dump(smoke_results, f, indent=2)

    print(f"\n[+] Smoke test complete! Results saved to: {smoke_json_path}")
    print("=" * 70)


if __name__ == "__main__":
    run_baseline_and_smoke_tests()
