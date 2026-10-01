"""Real Grad-CAM smoke test runner on actual trained model and real dataset image."""
import sys
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.models.model import load_model_checkpoint
from src.explainability.gradcam import explain_medical_image, save_gradcam_artifacts

def run_gradcam_smoke_test():
    checkpoint_path = Path("backend/models/best_model.pth")
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")

    model, ckpt_dict = load_model_checkpoint(checkpoint_path, device="cpu")

    # Pick a real sample pneumonia scan from test set
    test_pneu_dir = Path("data/chest_xray/test/PNEUMONIA")
    sample_img_path = next(test_pneu_dir.glob("*.jpeg"))
    print(f"Selected study scan: {sample_img_path}")

    # Generate Grad-CAM explanation
    explanation = explain_medical_image(
        model=model,
        image_input=sample_img_path,
        target_class=1,  # PNEUMONIA
        device="cpu",
        alpha=0.45,
    )

    pred_name = explanation["predicted_class_name"]
    conf = explanation["confidence"]
    print(f"Predicted Diagnosis: {pred_name} (Confidence: {conf:.4f})")

    # Save artifacts
    out_dir = Path("reports/gradcam")
    saved_paths = save_gradcam_artifacts(
        explanation=explanation,
        output_dir=out_dir,
        prefix="real_smoke_test_pneumonia",
    )

    print("\nGenerated & Verified Files:")
    for key, path in saved_paths.items():
        with Image.open(path) as img:
            print(f"  - {key}: {path} (Dimensions: {img.size}, Mode: {img.mode})")

    return saved_paths

if __name__ == "__main__":
    run_gradcam_smoke_test()
