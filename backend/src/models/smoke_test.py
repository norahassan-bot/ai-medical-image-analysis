import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import torch
from src.models.model import build_model, get_device, CLASS_TO_IDX

def run_smoke_test():
    device = get_device()
    cuda_status = "AVAILABLE" if torch.cuda.is_available() else "NOT AVAILABLE (CPU in use)"
    print(f"Device: {device} | CUDA Status: {cuda_status}")

    architectures = ["resnet50", "densenet121", "efficientnet_b0"]
    synthetic_batch = torch.randn(4, 3, 224, 224, device=device)

    print("\n--- Model Smoke Tests ---")
    for arch in architectures:
        model = build_model(
            architecture=arch,
            num_classes=2,
            pretrained=False,
            device=device
        )
        model.eval()
        with torch.no_grad():
            logits = model(synthetic_batch)

        meta = model.get_model_metadata()
        total_p = meta["total_parameters"]
        train_p = meta["trainable_parameters"]
        print(f"[{arch.upper()}] Input: {list(synthetic_batch.shape)} -> Output: {list(logits.shape)}")
        print(f"  Total Params: {total_p:,} | Trainable: {train_p:,} | Head: {meta['classifier_module']}")

    print(f"\nClass Mapping: {CLASS_TO_IDX}")
    print("All smoke tests passed successfully.")

if __name__ == "__main__":
    run_smoke_test()
