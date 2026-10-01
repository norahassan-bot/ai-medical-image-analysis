# Dataset Documentation: Chest X-Ray Images (Pneumonia)

## 📌 Dataset Overview

- **Dataset Name**: Chest X-Ray Images (Pneumonia)
- **Source URL**: [https://www.kaggle.com/datasets/paultimothymooney/chest-xray-pneumonia](https://www.kaggle.com/datasets/paultimothymooney/chest-xray-pneumonia)
- **License**: Creative Commons Attribution 4.0 International (CC BY 4.0)
- **Original Source**: Guangzhou Women and Children's Medical Center, Guangzhou. Published in *Cell* (Kermany et al., 2018).
- **Total Verified Images**: 5,856
- **Corrupted / Unreadable Images**: 0 (100% valid and verified)

---

## ⚠️ Important Clinical & Demographic Warnings

> [!WARNING]
> **Pediatric Cohort Restriction**:
> The chest radiograph images in this dataset were selected from retrospective cohorts of **pediatric patients aged one to five years old** at Guangzhou Women and Children's Medical Center, Guangzhou.
>
> **Generalizability Limitation**:
> Models trained on this dataset reflect anatomical, developmental, and pathological characteristics specific to young children (1–5 years). **The results and predictions of models trained on this dataset must NOT be generalized to adult patient populations, neonates, or elderly demographics** without comprehensive external validation on representative clinical cohorts.

---

## 📂 Dataset Directory Structure

The dataset is located in the local directory `data/chest_xray/` (isolated from Git via `.gitignore`):

```
data/
└── chest_xray/
    ├── train/                    # 5,216 images (89.1% of dataset)
    │   ├── NORMAL/               # 1,341 images
    │   └── PNEUMONIA/            # 3,875 images (74.3% of train split)
    ├── val/                      # 16 images (0.3% of dataset)
    │   ├── NORMAL/               # 8 images
    │   └── PNEUMONIA/            # 8 images (50.0% of val split)
    └── test/                     # 624 images (10.6% of dataset) - STRICTLY ISOLATED
        ├── NORMAL/               # 234 images
        └── PNEUMONIA/            # 390 images (62.5% of test split)
```

---

## 📊 Real Dataset Verification & Statistical Profile

All values computed directly from physical image files on disk via [`backend/src/data/verify_dataset.py`](file:///e:/projects/AI%20Medical%20Image%20Analysis/backend/src/data/verify_dataset.py) and [`backend/notebooks/01_eda.ipynb`](file:///e:/projects/AI%20Medical%20Image%20Analysis/backend/notebooks/01_eda.ipynb):

### 1. Split & Class Distribution Table

| Split | NORMAL | PNEUMONIA | Total Split Images | Pneumonia Ratio (%) |
| :--- | :--- | :--- | :--- | :--- |
| **Train** | 1,341 | 3,875 | **5,216** | 74.3% |
| **Validation** | 8 | 8 | **16** | 50.0% |
| **Test (Isolated)** | 234 | 390 | **624** | 62.5% |
| **Total** | **1,583** | **4,273** | **5,856** | **73.0%** |

### 2. Spatial Dimension & Resolution Analysis

- **Width (Pixels)**:
  - Minimum: `384 px`
  - Maximum: `2,916 px`
  - Mean: `1,327.9 px` (Std: `363.5 px`)
- **Height (Pixels)**:
  - Minimum: `127 px`
  - Maximum: `2,713 px`
  - Mean: `970.7 px` (Std: `383.4 px`)
- **Color Channels**:
  - Grayscale (`L` mode): 5,573 images (95.2%)
  - RGB (`RGB` mode): 283 images (4.8%) — automatically standardized during tensor preprocessing.

---

## 🔒 Test Set Isolation Protocol

The `test/` partition (624 images) is strictly isolated:
- **No data leakage**: Never sampled, inspected, fitted, or normalized during training pipelines.
- **Pure Holdout**: Reserved exclusively for final unbiased clinical evaluation after model weights convergence.

---

## 📥 Reproduction & Verification Commands

```bash
# Verify dataset files and display summary metrics
python backend/src/data/verify_dataset.py

# Execute the full EDA notebook
jupyter nbconvert --to notebook --execute backend/notebooks/01_eda.ipynb
```

---

## 📚 Citation

```bibtex
@article{kermany2018identifying,
  title={Identifying Medical Diagnoses and Treatable Diseases by Image-Based Deep Learning},
  author={Kermany, Daniel S and Goldbaum, Michael and Cai, Wenjia and Valentim, Carolina CS and Liang, Huiying and Baxter, Sally L and McKeown, Alex and Yang, Ge and Xia, Xinxin and Zhou, Fan and others},
  journal={Cell},
  volume={173},
  number={5},
  pages={1122--1131},
  year={2018},
  publisher={Elsevier}
}
```
