# Security, Input Validation & Automated Testing Documentation (Task 14)

## 1. Overview & Threat Model

The AI Medical Image Analysis Platform implements defense-in-depth security principles to safeguard medical imaging data, prevent unauthorized filesystem access, sanitize error disclosures, and protect the integrity of automated clinical decision-support predictions.

---

## 2. File & Image Validation

### Supported File Formats
- **Formats Allowed**: `PNG`, `JPG`, `JPEG` (case-insensitive extension and MIME verification).
- **MIME Types Accepted**: `image/png`, `image/jpeg`, `image/jpg`.

### Multi-Stage Content Validation Pipeline
1. **Request Presence Check**: Ensures the multipart payload contains a non-empty image file.
2. **Zero-Byte File Rejection**: 0-byte uploads are rejected with HTTP 400 (`INVALID_IMAGE`).
3. **Client-Side Pre-Validation**: The Next.js upload dropzone uses the browser File API to reject invalid types and oversized files before dispatch.
4. **Server-Side Content Decoding**: The backend uses Pillow and OpenCV to decode image bytes:
   - `PIL.Image.verify()` validates image integrity, preventing truncated, corrupt, or disguised executables/documents.
   - Decompression bomb protection (`MAX_IMAGE_PIXELS`) prevents memory-exhaustion denial of service.
5. **Spatial Dimension Validation**: Images must have spatial resolution between $32 \times 32$ and $10,000 \times 10,000$ pixels. Zero/negative dimensions and tiny images are rejected.

---

## 3. Upload Size Limit

- **Configurable Limit**: Set via `MAX_UPLOAD_SIZE_MB` (default: 15 MB) or `MAX_FILE_SIZE_BYTES`.
- **Enforcement**: Strictly enforced server-side before running preprocessing or model inference.
- **HTTP Status**: HTTP 413 (`Payload Too Large`) with structured error code `FILE_TOO_LARGE`.
- **No Binary Logging**: Uploaded binary payloads are never logged to console or logs.

---

## 4. Safe File Handling & Path Traversal Prevention

- **Untrusted User Filenames**: User-provided filenames are never concatenated into local server filepaths.
- **Server-Generated Unique Filenames**: Stored under `STORAGE_DIR/{analysis_id}/original{ext}`.
- **Strict Path Resolution**:
  - `resolve_safe_image_path()` verifies that canonical resolved paths reside strictly within the configured storage directory.
  - `get_report_path()` sanitizes analysis UUIDs and rejects path traversal sequences (`../`, `..\`, absolute paths).
  - Malicious path traversal attempts (e.g. `../../secret.txt`, `/etc/passwd`, `C:\Windows\System32\...`) are blocked with HTTP 400 / HTTP 404.

---

## 5. Centralized Error Handling & Information Disclosure Prevention

### Standardized JSON Error Structure
```json
{
  "error": {
    "code": "INVALID_IMAGE",
    "message": "The uploaded file could not be processed as a valid image.",
    "details": null
  }
}
```

### Sanitized Error Codes
| Exception | HTTP Status | Error Code | Sanitization |
|---|---|---|---|
| `FileTooLargeError` | 413 | `FILE_TOO_LARGE` | Client-friendly size limit message |
| `UnsupportedFormatError` | 400 | `UNSUPPORTED_FORMAT` | Clear allowed formats list |
| `ImageValidationError` | 400 | `INVALID_IMAGE` | Sanitized validation failure reason |
| `RequestValidationError` | 422 | `VALIDATION_ERROR` | Schema field violation list |
| `ModelNotLoadedError` | 503 | `MODEL_NOT_AVAILABLE` | Clean availability status |
| `InferenceError` | 500 | `INFERENCE_ERROR` | Sanitized inference failure message |
| `HTTPException (404)` | 404 | `NOT_FOUND` | "Analysis with ID '...' not found" |
| `Unhandled Exception` | 500 | `INTERNAL_SERVER_ERROR` | Generic safe message; stack traces logged server-side only |

### Information Leakage Prevention
- No Python tracebacks, SQLite syntax, table structures, internal server filepaths, credentials, or environment variables are ever leaked to API clients.

---

## 6. CORS Policy & Origins

- **Default Allowed Origins**: `http://localhost:3000`, `http://127.0.0.1:3000`.
- **Configurable**: Environment variable `CORS_ORIGINS` (JSON list or comma-separated string).
- **Wildcard Policy**: Wildcard origins (`*`) are disallowed for production security.
- **Credentials Policy**: Credentials disabled (`allow_credentials=False`) unless authenticated session management is explicitly integrated.

---

## 7. Database Safety & Test Isolation

- **Parameterized Queries**: 100% of SQLite database queries use parameterized SQL (`?` placeholders) to prevent SQL injection.
- **UUID Validation**: Analysis IDs are validated against strict alphanumeric and hyphen/underscore formats before queries.
- **Automated Test Isolation**: Automated tests execute strictly against isolated temporary SQLite database files created in temporary directories (`tmp_path` / `.test_tmp`) and automatically clean up after execution. The production database (`medical_ai.db`) is never used in tests.

---

## 8. Medical Data Handling & Privacy

- **Minimal Data Retention**: Only diagnostic predictions, confidence probabilities, inference timing, and Grad-CAM visualization artifacts are recorded.
- **No Unnecessary PHI**: No patient identifiers (names, SSNs, MRNs) are stored in the database.
- **Static Access Control**: Medical images are not exposed via arbitrary public static web directories; access requires specific analysis UUID lookup with path containment checks.

---

## 9. Automated Testing Strategy

### Backend Test Suite (`backend/tests/`)
- **Framework**: Pytest with FastAPI `TestClient`.
- **Coverage**:
  - `test_api.py`: Endpoint contracts, HTTP status codes, schema validation.
  - `test_security.py`: Path traversal regressions, disguised executables, oversized payloads, SQL injection, CORS origin checks, error sanitization.
  - `test_inference.py`: Image validation, edge-case dimensions, format checking, model inference.
  - `test_database.py`: Parameterized queries, schema migrations, CRUD, concurrency.
  - `test_report.py`: PDF report generation, caching, traversal prevention.
  - `test_health.py`: Telemetry, system information, model readiness.

### Frontend Test Suite (`frontend/tests/`)
- **Framework**: Vitest with React Testing Library and jsdom.
- **Coverage**:
  - `upload.test.tsx`: Render, invalid extension rejection, oversized file rejection, 0-byte file rejection, valid file selection.
  - `analysis.test.tsx`: Loading spinner, successful result rendering, backend error sanitization, duplicate click prevention.
  - `history.test.tsx`: Database unavailable state, 404 missing analysis state, PDF download error handling.
  - `health.test.tsx`: Health card rendering across online, offline, and uninitialized states.

---

## 10. Known Security Limitations & Clinical Disclaimer

> **IMPORTANT CLINICAL & REGULATORY NOTICE**:
> This platform is an educational and research prototype developed for automated chest radiograph classification and Explainable AI (Grad-CAM). 
>
> 1. **Not a Medical Device**: This software has NOT received FDA, CE-IVD, or other regulatory clearance for autonomous clinical diagnosis.
> 2. **Clinical Verification Required**: All AI-generated predictions and visual heatmaps must be reviewed and verified by a licensed radiologist or healthcare provider.
> 3. **Production Healthcare Compliance**: Deploying this software into a clinical healthcare environment requires implementing HIPAA / GDPR compliance, role-based access control (RBAC), end-to-end TLS encryption, DICOM/PACS integration (DIMSE/DICOMweb), audit logging compliant with medical records standards, and clinical validation across diverse multi-center patient populations.
