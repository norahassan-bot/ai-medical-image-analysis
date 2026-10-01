"""Script to verify Chest X-Ray dataset on disk and compute exact statistics."""
from pathlib import Path
from PIL import Image
import numpy as np
import pandas as pd

def verify_dataset(dataset_path: str = "data/chest_xray"):
    dataset_root = Path(dataset_path)
    splits = ["train", "val", "test"]
    classes = ["NORMAL", "PNEUMONIA"]
    supported_exts = {".jpg", ".jpeg", ".png"}

    counts = {s: {c: 0 for c in classes} for s in splits}
    corrupted = []
    unsupported = []
    records = []

    for split in splits:
        for cls in classes:
            cls_dir = dataset_root / split / cls
            if not cls_dir.exists():
                print(f"Directory not found: {cls_dir}")
                continue
            for file in cls_dir.iterdir():
                if not file.is_file():
                    continue
                ext = file.suffix.lower()
                if ext not in supported_exts:
                    unsupported.append(str(file))
                    continue
                try:
                    with Image.open(file) as img:
                        img.verify()
                    with Image.open(file) as img:
                        w, h = img.size
                        mode = img.mode
                    counts[split][cls] += 1
                    records.append({
                        "split": split,
                        "class": cls,
                        "path": str(file),
                        "width": w,
                        "height": h,
                        "mode": mode,
                    })
                except Exception as e:
                    corrupted.append((str(file), str(e)))

    df = pd.DataFrame(records)

    print("=== DATASET VERIFICATION RESULTS ===")
    print(f"Dataset Path: {dataset_root.resolve()}")
    print("\nImage Counts per Split & Class:")
    for split in splits:
        tot = sum(counts[split].values())
        norm = counts[split]["NORMAL"]
        pneu = counts[split]["PNEUMONIA"]
        pct_pneu = (pneu / tot * 100) if tot > 0 else 0
        print(f"  {split.upper()}: Total={tot} | NORMAL={norm} | PNEUMONIA={pneu} ({pct_pneu:.1f}% Pneumonia)")

    total_images = len(df)
    total_normal = sum(counts[s]["NORMAL"] for s in splits)
    total_pneumonia = sum(counts[s]["PNEUMONIA"] for s in splits)

    print(f"\nTotal Dataset Images: {total_images}")
    print(f"Total NORMAL: {total_normal}")
    print(f"Total PNEUMONIA: {total_pneumonia}")
    print(f"Corrupted Images: {len(corrupted)}")
    print(f"Unreadable Images: {len(corrupted)}")
    print(f"Unsupported Files: {len(unsupported)}")

    if not df.empty:
        print("\nDimension Summary (Width x Height):")
        print(f"  Width:  min={df['width'].min()}, max={df['width'].max()}, mean={df['width'].mean():.1f}, std={df['width'].std():.1f}")
        print(f"  Height: min={df['height'].min()}, max={df['height'].max()}, mean={df['height'].mean():.1f}, std={df['height'].std():.1f}")
        print("\nColor Modes:", df["mode"].value_counts().to_dict())

    return counts, corrupted, unsupported, df

if __name__ == "__main__":
    verify_dataset()
