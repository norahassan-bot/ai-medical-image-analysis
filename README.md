# AI Medical Image Analysis & Clinical Decision Support Platform

An enterprise-grade, full-stack medical vision intelligence platform designed to assist healthcare providers and radiologists with automated binary chest radiograph diagnostics (`NORMAL` vs `PNEUMONIA`), visual explainability using **Grad-CAM** heatmaps, longitudinal study tracking in **SQLite**, and automated **Clinical PDF Report Generation**.

---

## 📑 Table of Contents

1. [Project Overview](#1-project-overview)
2. [Problem Statement](#2-problem-statement)
3. [System Objective](#3-system-objective)
4. [User Role & Clinical Workflow](#4-user-role--clinical-workflow)
5. [System Architecture](#5-system-architecture)
6. [Technology Stack](#6-technology-stack)
7. [Dataset Description](#7-dataset-description)
8. [Dataset Limitations & Demographic Warnings](#8-dataset-limitations--demographic-warnings)
9. [Exploratory Data Analysis (EDA)](#9-exploratory-data-analysis-eda)
10. [Data Preprocessing & Augmentation](#10-data-preprocessing--augmentation)
11. [Deep Learning Model Architectures](#11-deep-learning-model-architectures)
12. [Transfer Learning Strategy](#12-transfer-learning-strategy)
13. [Model Training Pipeline](#13-model-training-pipeline)
14. [Evaluation Protocol & Measured Performance](#14-evaluation-protocol--measured-performance)
15. [Confusion Matrices & Clinical Metrics](#15-confusion-matrices--clinical-metrics)
16. [Explainable AI with Grad-CAM](#16-explainable-ai-with-grad-cam)
17. [Production Inference Engine](#17-production-inference-engine)
18. [FastAPI REST Backend](#18-fastapi-rest-backend)
19. [Next.js Clinical Frontend](#19-nextjs-clinical-frontend)
20. [SQLite Persistence & History Audit](#20-sqlite-persistence--history-audit)
21. [Automated PDF Clinical Reports](#21-automated-pdf-clinical-reports)
22. [Security, Hardening & Sanitization](#22-security-hardening--sanitization)
23. [Automated Testing Strategy](#23-automated-testing-strategy)
24. [Docker & Docker Compose Containerization](#24-docker--docker-compose-containerization)
25. [Local Development Setup](#25-local-development-setup)
26. [Environment Variables](#26-environment-variables)
27. [Project Directory Structure](#27-project-directory-structure)
28. [System Limitations & Boundary Conditions](#28-system-limitations--boundary-conditions)
29. [Medical & Regulatory Disclaimer](#29-medical--regulatory-disclaimer)
30. [API Reference Documentation](#30-api-reference-documentation)

---

## 1. Project Overview

The **AI Medical Image Analysis & Clinical Decision Support Platform** is an end-to-end medical deep learning solution. It ingests anterior-posterior/posterior-anterior (AP/PA) chest radiographs, runs deep convolutional neural network inference using fine-tuned **ResNet18** weights, computes gradient-weighted class activation mapping (**Grad-CAM**) to provide visual interpretability for radiological review, persists diagnostic audit logs in a local **SQLite** database, and delivers structured **Clinical Decision-Support PDF Reports**.

---

## 2. Problem Statement

Pneumonia remains a leading cause of pediatric morbidity and mortality worldwide. Accurate radiological diagnosis requires rapid identification of subtle pulmonary consolidations, infiltrates, and air bronchograms on chest radiographs. In resource-constrained settings or during emergency triage, expert radiologist availability is limited. An automated, explainable, and secure decision-support platform can reduce diagnostic latency, provide secondary confirmation, and highlight suspected pathological lung zones for targeted clinical evaluation.

---

## 3. System Objective

- **High-Sensitivity Diagnostics**: Prioritize pneumonia detection to minimize false negatives (preventing missed infections).
- **Visual Explainability (XAI)**: Generate 2D activation heatmaps via Grad-CAM so clinicians can verify that the model attends to genuine lung field opacities rather than spurious artifacts (e.g. lead markers or borders).
- **Deterministic & Auditable Persistence**: Store all diagnostic sessions with unique UUIDs, timestamps, confidence scores, and artifact references.
- **Production-Ready Full-Stack Decoupling**: Isolate deep learning pipelines into modular FastAPI services accessible by a modern Next.js 14 client with strict security hardening.

---

## 4. User Role & Clinical Workflow

The platform serves **Radiologists, Pulmonologists, and General Practitioners** acting in a "human-in-the-loop" decision-support paradigm:

```
┌─────────────────┐     1. Upload DICOM/PNG/JPEG     ┌────────────────────────┐
│  Radiologist /  │ ───────────────────────────────> │  Next.js 14 Web Portal │
│   Practitioner  │ <─────────────────────────────── │  (Interactive Dashboard│
└─────────────────┘     4. Review Prediction & CAM   └───────────┬────────────┘
         │                                                       │ 2. POST /analyze
         │ 5. Download Official Clinical PDF                     ▼
         └────────────────────────────────────────── ┌────────────────────────┐
                                                     │  FastAPI Inference     │
                                                     │  & SQLite Persistence  │
                                                     └────────────────────────┘
```

1. **Intake**: Clinician uploads a chest radiograph.
2. **Analysis**: System runs image validation, model forward pass, and Grad-CAM extraction.
3. **Review**: Clinician inspects prediction confidence, class probabilities, and activation overlay.
4. **Audit**: Session is persisted in the historical audit log.
5. **Report**: Clinician generates and exports a signed clinical decision-support PDF.

---

## 5. System Architecture

```
┌────────────────────────────────────────────────────────┐
│                   Next.js 14 Frontend                  │
│       (TypeScript, App Router, Tailwind CSS)          │
│                http://localhost:3000                   │
└───────────────────────────┬────────────────────────────┘
                            │ REST / JSON (CORS)
                            ▼
┌────────────────────────────────────────────────────────┐
│                    FastAPI Backend                     │
│         (Uvicorn ASGI, Pydantic, OpenAPI /docs)        │
│                http://localhost:8000                   │
└─────────────┬──────────────────────────┬───────────────┘
              │                          │
              ▼                          ▼
┌───────────────────────────┐  ┌─────────────────────────┐
│     PyTorch AI Engine     │  │     SQLite Database     │
│ (ResNet18 / Grad-CAM)     │  │ (Audit Trail & Studies) │
└─────────────┬─────────────┘  └─────────────────────────┘
              ▼
┌───────────────────────────┐
│   Clinical PDF Reports    │
│  (ReportLab Generation)   │
└───────────────────────────┘
```

---

## 6. Technology Stack

- **Frontend Client**: Next.js 14 (App Router), TypeScript, React 18, Tailwind CSS, Lucide Icons.
- **Backend Framework**: Python 3.11, FastAPI, Uvicorn, Pydantic v2.
- **AI / Deep Learning**: PyTorch 2.x, Torchvision, Scikit-Learn, OpenCV (Headless), Pillow.
- **Data Persistence**: SQLite3 with WAL mode, parameterized queries.
- **Report Generation**: ReportLab 4.x / 5.x.
- **Testing Suites**: Pytest, Pytest-Asyncio, Vitest, Testing Library.
- **Containerization**: Docker, Docker Compose, Alpine & Slim multi-stage images.

---

## 7. Dataset Description

- **Dataset**: Kaggle Chest X-Ray Images (Pneumonia) (Kermany et al., 2018, *Cell*).
- **Total Samples**: 5,856 verified radiographs.
- **Partitioning**:
  - **Train**: 5,216 images (1,341 Normal, 3,875 Pneumonia) — 74.3% class imbalance.
  - **Validation**: 16 images (8 Normal, 8 Pneumonia) — balanced tuning set.
  - **Test (Strictly Isolated)**: 624 images (234 Normal, 390 Pneumonia) — held out exclusively for final evaluation.

---

## 8. Dataset Limitations & Demographic Warnings

> [!WARNING]
> **Pediatric Demographic Restriction**:
> The images in this dataset were acquired retrospectively from **pediatric patients aged 1 to 5 years** at Guangzhou Women and Children's Medical Center.
> **Generalizability Constraint**:
> Features learned by models trained on this dataset represent pediatric anatomy and pathology. **The model must NOT be deployed on adult, neonatal, or geriatric populations without external multi-center clinical validation.**

---

## 9. Exploratory Data Analysis (EDA)

Key statistical findings from [`backend/notebooks/01_eda.ipynb`](file:///e:/projects/AI%20Medical%20Image%20Analysis/backend/notebooks/01_eda.ipynb):
- **Image Formats**: 95.2% Grayscale (`L` mode), 4.8% RGB. Standardized to 3-channel RGB.
- **Spatial Resolution**: Width range `[384, 2916]` px, Height range `[127, 2713]` px.
- **Data Quality**: 0 corrupted or unreadable images across all 5,856 files.

---

## 10. Data Preprocessing & Augmentation

- **Deterministic Resizing**: Standardized to $224 \times 224$ pixels.
- **ImageNet Normalization**: Mean: `[0.485, 0.456, 0.406]`, Std: `[0.229, 0.224, 0.225]`.
- **Training Augmentations**: Random affine rotation ($\pm 10^\circ$), horizontal flip ($p=0.5$), slight brightness/contrast jittering.
- **Validation/Test Pipeline**: Pure deterministic resize + normalization (zero augmentation to prevent evaluation bias).

---

## 11. Deep Learning Model Architectures

The platform implements modular CNN backbones via [`src/models/model.py`](file:///e:/projects/AI%20Medical%20Image%20Analysis/backend/src/models/model.py):
- **ResNet Family**: ResNet-18 (11.18M parameters), ResNet-50 (23.51M parameters).
- **DenseNet Family**: DenseNet-121 (6.96M parameters).
- **EfficientNet Family**: EfficientNet-B0 (4.01M parameters).
- **Production Selection**: **ResNet-18** fine-tuned on pediatric radiographs for fast sub-50ms CPU inference latency.

---

## 12. Transfer Learning Strategy

1. **Pretrained Initialization**: Backbone initialized with ImageNet weights to leverage generalized visual edge/texture representations.
2. **Head Customization**: Replaced 1000-class ImageNet head with `Sequential(Dropout(0.3), Linear(512, 2))`.
3. **Fine-Tuning**: Trained end-to-end with Adam optimizer ($lr=1\times 10^{-4}$), Cross-Entropy loss with inverse class weighting to counter the 74.3% pneumonia imbalance.

---

## 13. Model Training Pipeline

- **Checkpoint**: Saved at [`backend/models/best_model.pth`](file:///e:/projects/AI%20Medical%20Image%20Analysis/backend/models/best_model.pth) (42.73 MB).
- **Early Stopping**: Monitored validation loss and ROC-AUC with patience = 5 epochs.
- **Weight Retention**: The checkpoint reflects real convergence on the training set.

---

## 14. Evaluation Protocol & Measured Performance

Evaluation was executed on the **held-out 624-image test set** (never seen during training or hyperparameter tuning).

### Actual Measured Results

| Metric | Validation Set (16 images) | Test Set (624 images) |
| :--- | :---: | :---: |
| **Accuracy** | **93.75%** | **87.50%** |
| **Precision (Pneumonia)** | **100.00%** | **95.09%** |
| **Recall / Sensitivity (Pneumonia)** | **87.50%** | **84.36%** |
| **Specificity (Normal)** | **100.00%** | **92.74%** |
| **F1-Score** | **93.33%** | **89.40%** |
| **ROC-AUC** | **0.9844** | **0.9538** |

---

## 15. Confusion Matrices & Clinical Metrics

### Test Set Confusion Matrix (624 Samples)

```
                     PREDICTED NORMAL    PREDICTED PNEUMONIA
ACTUAL NORMAL              217 (TN)            17 (FP)
ACTUAL PNEUMONIA            61 (FN)           329 (TP)
```

- **True Positives (TP)**: 329
- **True Negatives (TN)**: 217
- **False Positives (FP)**: 17
- **False Negatives (FN)**: 61

---

## 16. Explainable AI with Grad-CAM

Implemented via [`src/explainability/gradcam.py`](file:///e:/projects/AI%20Medical%20Image%20Analysis/backend/src/explainability/gradcam.py):
1. **Gradients**: Computes $\alpha_k^c = \frac{1}{Z} \sum_i \sum_j \frac{\partial Y^c}{\partial A_{i,j}^k}$ on `layer4[-1]`.
2. **ReLU Activation Map**: $L_{\text{Grad-CAM}}^c = \text{ReLU}\left(\sum_k \alpha_k^c A^k\right)$.
3. **Overlay**: Blends OpenCV `COLORMAP_JET` heatmap over original radiograph with $\alpha = 0.45$.

---

## 17. Production Inference Engine

The [`ChestXRayPredictor`](file:///e:/projects/AI%20Medical%20Image%20Analysis/backend/src/inference/predict.py) class coordinates:
- Input format verification (JPEG, PNG).
- Content-based Pillow validation (anti-malware & corruption rejection).
- Inference latency measurement.
- Direct base64 image encoding for single-trip HTTP payload responses.

---

## 18. FastAPI REST Backend

The REST service ([`backend/api/main.py`](file:///e:/projects/AI%20Medical%20Image%20Analysis/backend/api/main.py)) exposes standardized REST endpoints:
- Automatic OpenAPI 3.0 schema generation at `/docs` and `/redoc`.
- Centralized exception handlers for `400 Bad Request`, `413 File Too Large`, `422 Validation Error`, `500 Internal Server Error`, and `503 Service Unavailable`.

---

## 19. Next.js Clinical Frontend

Interactive React application ([`frontend/app`](file:///e:/projects/AI%20Medical%20Image%20Analysis/frontend/app)):
- **Dashboard (`/`)**: High-level platform KPIs, system status, quick actions.
- **Analysis Portal (`/analysis`)**: Drag-and-drop X-ray upload, real-time inference, dual Grad-CAM viewer.
- **History Audit (`/history`)**: Paginated diagnostic ledger.
- **Details (`/history/[analysisId]`)**: Comprehensive study view and instant PDF report download.
- **System Telemetry (`/system`)**: Hardware diagnostics, model versioning, API health monitor.

---

## 20. SQLite Persistence & History Audit

- **Zero-Dependency Persistence**: Uses standard library `sqlite3` in WAL mode with indexed UUID primary keys.
- **Storage Separation**: SQLite stores structured diagnostic metadata and probabilities; image artifacts are stored in `data/visualizations/`.
- **Query Safety**: 100% parameterized SQL queries protecting against SQL injection attacks.

---

## 21. Automated PDF Clinical Reports

Generated via [`backend/reports/report_generator.py`](file:///e:/projects/AI%20Medical%20Image%20Analysis/backend/reports/report_generator.py) using ReportLab:
- Standardized header with analysis UUID and UTC timestamp.
- Diagnostic prediction badge with confidence percentage.
- Side-by-side visualization table (Original X-Ray, Heatmap, Grad-CAM Overlay).
- Regulatory & Clinical Decision Support Disclaimer.
- On-disk caching to accelerate repeat downloads.

---

## 22. Security, Hardening & Sanitization

- **Path Traversal Shield**: Strict alphanumeric + UUID validation on all route parameters.
- **Sanitized Uploads**: User filenames are never used as on-disk paths.
- **Payload Limits**: Rejects payloads exceeding 15MB before inference (`HTTP 413`).
- **Error Sanitization**: Server exceptions omit internal filepaths, database details, or raw tracebacks.
- **CORS Protection**: Restricted strictly to configured frontend origins (`http://localhost:3000`).

---

## 23. Automated Testing Strategy

Complete multi-tiered automated test suite:

### 1. Backend Tests (Pytest)
```bash
cd backend
pytest tests/
```
**Results**: **133 / 133 Passed (100%)** across API contracts, database, evaluation, Grad-CAM, inference, reports, and security hardening.

### 2. Frontend Tests (Vitest)
```bash
cd frontend
npm test
```
**Results**: **13 / 13 Passed (100%)** across health monitoring, upload workflows, analysis loading states, and history navigation.

---

## 24. Docker & Docker Compose Containerization

Orchestrated with [`docker-compose.yml`](file:///e:/projects/AI%20Medical%20Image%20Analysis/docker-compose.yml):

```bash
# Build multi-stage containers
docker compose build

# Start services in background
docker compose up -d

# Inspect live logs
docker compose logs -f

# Teardown services (preserving SQLite and report volumes)
docker compose down
```

### Volume Persistence
- `medical_sqlite_data`: Mounts `/app/data` (persists `medical_ai.db` and visualizations across restarts).
- `medical_reports_data`: Mounts `/app/reports` (persists generated clinical PDF reports).
- `./backend/models`: Read-only host mount for model weights (`/app/models:ro`).

---

## 25. Local Development Setup

### 1. Backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate # Linux/macOS
pip install -r requirements.txt
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## 26. Environment Variables

### Backend Configuration (`backend/.env.example`)
```env
ENVIRONMENT=production
HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]
DATABASE_PATH=data/medical_ai.db
STORAGE_DIR=data/visualizations
PDF_REPORTS_DIR=../reports/pdf
MODEL_CHECKPOINT_PATH=models/best_model.pth
MODEL_VERSION=1.0.0
```

### Frontend Configuration (`frontend/.env.example`)
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
PORT=3000
HOSTNAME=0.0.0.0
```

---

## 27. Project Directory Structure

```
ai-medical-image-analysis/
│
├── frontend/                     # Next.js 14 Web Application
│   ├── app/                      # App router pages (dashboard, analysis, history, system)
│   ├── components/               # Header, Sidebar, Uploader, Grad-CAM viewers
│   ├── lib/                      # API client & configurations
│   ├── Dockerfile                # Multi-stage production container
│   ├── package.json              # Node dependencies
│   └── next.config.mjs           # Standalone compilation output
│
├── backend/                      # FastAPI Microservices
│   ├── api/                      # REST endpoints & Pydantic schemas
│   ├── src/                      # AI Core: datasets, models, evaluation, Grad-CAM, inference
│   ├── database/                 # SQLite persistence layer
│   ├── reports/                  # PDF report generation engine
│   ├── models/                   # Serialized model checkpoint (best_model.pth)
│   ├── tests/                    # 133 Pytest unit & regression tests
│   ├── Dockerfile                # Python 3.11 production container
│   └── requirements.txt          # Python dependencies
│
├── data/                         # Dataset root (data/chest_xray/)
├── reports/                      # Output PDFs, evaluation curves, Grad-CAM benchmarks
├── docker-compose.yml            # Multi-container orchestration
├── DATASET.md                    # Detailed dataset documentation & citations
├── SECURITY.md                   # Security policies & audit documentation
└── README.md                     # Master documentation
```

---

## 28. System Limitations & Boundary Conditions

1. **Binary Scope**: Classifies strictly between `NORMAL` and `PNEUMONIA`. Does not differentiate viral vs. bacterial pneumonia or detect pneumothorax, effusion, or cardiomegaly.
2. **Pediatric Restriction**: Validated exclusively on pediatric patients (1–5 years). Not clinically calibrated for adult populations.
3. **Single Projection**: Optimized for anterior-posterior / posterior-anterior radiographs; lateral projections are unsupported.

---

## 29. Medical & Regulatory Disclaimer

> [!IMPORTANT]
> **Clinical Decision Support Notice**:
> This artificial intelligence system is developed solely for **research, educational, and clinical decision-support purposes**. It does **NOT** constitute an autonomous medical device or a definitive diagnostic system. All predictions, confidence ratings, and Grad-CAM visualizations must be verified and corroborated by a licensed physician or board-certified radiologist alongside patient history and clinical laboratory findings.

---

## 30. API Reference Documentation

### `GET /health`
- **Purpose**: System and model operational readiness check.
- **Response**: `200 OK`
  ```json
  {
    "status": "healthy",
    "model_loaded": true,
    "model_version": "1.0.0",
    "architecture": "resnet18",
    "device": "cpu"
  }
  ```

### `POST /predict`
- **Purpose**: Fast forward-pass classification on uploaded radiograph.
- **Request**: `multipart/form-data` with `file: UploadFile` (PNG/JPEG).
- **Response**: `200 OK`
  ```json
  {
    "prediction": "PNEUMONIA",
    "predicted_index": 1,
    "confidence": 0.9842,
    "probabilities": { "NORMAL": 0.0158, "PNEUMONIA": 0.9842 },
    "model_version": "1.0.0",
    "architecture": "resnet18",
    "device": "cpu",
    "inference_time_ms": 42.15
  }
  ```
- **Errors**: `400 Bad Request` (invalid format/corrupted), `413 File Too Large`, `503 Service Unavailable`.

### `POST /explain`
- **Purpose**: Forward-pass inference with Grad-CAM heatmap & overlay generation.
- **Request**: `multipart/form-data` with `file: UploadFile`, optional `target_class: int`, `alpha: float`.
- **Response**: `200 OK` with base64 data URIs for original, heatmap, and overlay images.

### `POST /analyze`
- **Purpose**: Full diagnostic pipeline: prediction, Grad-CAM generation, artifact disk storage, and SQLite database persistence.
- **Request**: `multipart/form-data` with `file: UploadFile`.
- **Response**: `200 OK` returning `analysis_id` UUID, timestamp, probabilities, and visualization URIs.

### `GET /history`
- **Purpose**: Retrieve paginated list of past analyses ordered newest first.
- **Query Params**: `limit: int = 50`, `offset: int = 0`.
- **Response**: `200 OK` with array of historical records and total count.

### `GET /history/{analysis_id}`
- **Purpose**: Retrieve full details of a single past study by UUID.
- **Response**: `200 OK` or `404 Not Found`.

### `GET /history/{analysis_id}/report`
- **Purpose**: Download standardized clinical PDF report.
- **Response**: `200 OK` with `Content-Type: application/pdf` and `Content-Disposition: attachment`.

---

## 31. Authentication Architecture & Role Separation

The platform enforces zero-trust server-side authentication with strict separation between **Administrative Access** and **Clinical User Access**:

```
                    ┌────────────────────────────────────────────────────────┐
                    │               Client HTTP Request                      │
                    └───────────────────────────┬────────────────────────────┘
                                                │
                                    ┌───────────┴───────────┐
                                    ▼                       ▼
                         ┌────────────────────┐   ┌────────────────────┐
                         │   ADMIN PORTAL     │   │    USER PORTAL     │
                         │    /admin, /login  │   │    /user, /analyze │
                         └──────────┬─────────┘   └──────────┬─────────┘
                                    │                        │
                      Username / Password Login    Zero Login Screen Required
                      Bcrypt (12 rounds)           Python secrets.token_urlsafe(32)
                      Signed Admin JWT Cookie      SHA-256 Server Hash in SQLite
                      Brute-Force Throttling       HttpOnly Secure Session Cookie
                                    │                        │
                                    ▼                        ▼
                         Full Admin Supervisory   Anonymous Isolated Workspace
                         Access to All Analyses   Own Analyses & Reports Only
```

---

## 32. Task 21: Zero-Login Secure Token-Based User Identity

### Overview & Core Philosophy
Regular clinical users do **not** have username/password credentials, user registration forms, or login gates. When a clinician visits `/user` or initiates an analysis, the system automatically establishes a secure, browser-bound anonymous identity using high-entropy cryptographic tokens.

### 1. Cryptographically Secure Token Generation
- **Generator**: Uses Python's standard `secrets` module (`secrets.token_urlsafe(32)`), ensuring at least 256 bits of cryptographic entropy.
- **Forbidden Generators**: Never uses `random.random()`, timestamps, or sequential IDs.

### 2. Zero Raw-Token Database Storage
- **Token Hashing**: The raw token is **NEVER stored in SQLite**.
- **Hashing Algorithm**: Deterministic SHA-256 (`hashlib.sha256(raw_token.encode('utf-8')).hexdigest()`).
- **Lookup Flow**: Incoming cookie token is hashed server-side and matched against `users.token_hash`.

### 3. Cookie Security Model
- **Cookie Name**: `user_session_token` (and legacy `access_token` alias).
- **Attributes**: `HttpOnly=True`, `SameSite=Lax`, `Path=/`, `Secure=True` (in production).
- **JavaScript Inaccessibility**: Frontend JavaScript cannot access or read the raw token. It is never exposed in JSON API responses, React state, or URLs.

### 4. Analysis Ownership & Multi-Tenant Isolation
- **Server-Derived Ownership**: `owner_user_id` is assigned exclusively from the verified server-side session token.
- **Client Ownership Rejection**: Client-supplied `owner_user_id` or `role` fields in form bodies or query parameters are strictly ignored and overwritten.
- **Isolated History**: `GET /history` queries only records matching `owner_user_id == current_user.id`.
- **Protected Reports & Details**: `GET /history/{id}` and `GET /history/{id}/report` verify record ownership. Unauthorized access attempts return `HTTP 403 Forbidden`.

### 5. Session Expiration & Reset Lifecycle
- **Configurable Lifetime**: Default 30 days (`USER_SESSION_EXPIRE_DAYS=30`).
- **Auto-Invalidation**: Expired tokens are invalidated and automatically replaced with a new anonymous identity upon next request.
- **Reset / End Session Action**: Clinicians can reset their session via `/user/account` (`POST /auth/session/reset`). This clears the stored token hash in SQLite and purges the browser cookie.
- **Identity Scope & Limitation**: Anonymous user identities are browser/device-scoped. Clearing cookies, browsing in Incognito mode, or switching devices establishes a new anonymous identity without access to prior unlinked history.

### 6. Admin Authentication Preservation
- Administrators retain traditional username/password authentication via `/login` (`POST /auth/login`).
- Admin passwords remain securely hashed using bcrypt (12 rounds).
- Admin routes (`/admin/*`) strictly require role `ADMIN`; anonymous user tokens attempting to access admin endpoints receive `HTTP 403 Forbidden`.


