import { API_ENDPOINTS } from "./config";
import type {
  HealthResponse,
  SystemInfoResponse,
  PredictionResponse,
  ExplainResponse,
  AnalysisResponse,
  AnalysisHistoryResponse,
  AnalysisDetailResponse,
  ErrorResponse,
  UserPublic,
  AuthResponse,
  AdminUserListResponse,
  AdminStatsResponse,
} from "@/types/api";

export class ApiError extends Error {
  constructor(
    public status: number,
    public message: string,
    public code?: string,
    public details?: unknown
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/**
 * Helper to parse backend error responses safely without crashing.
 */
async function parseErrorResponse(res: Response): Promise<ApiError> {
  try {
    const data: ErrorResponse = await res.json();
    if (data && data.error) {
      return new ApiError(
        res.status,
        data.error.message || `Request failed with status ${res.status}`,
        data.error.code,
        data.error.details
      );
    }
  } catch {
    // Fallback if response body is not JSON
  }
  return new ApiError(res.status, `HTTP error ${res.status}: ${res.statusText}`);
}

// ---------------------------------------------------------------------------
// Authentication & Profile Endpoints (Task 19)
// ---------------------------------------------------------------------------

/**
 * Authenticate user with credentials and establish secure HTTP-only session cookie.
 * Endpoint: POST /auth/login
 */
export async function loginUser(
  credentials: { username: string; password: string },
  signal?: AbortSignal
): Promise<AuthResponse> {
  const res = await fetch(API_ENDPOINTS.AUTH_LOGIN, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Accept": "application/json",
    },
    body: JSON.stringify(credentials),
    credentials: "include",
    cache: "no-store",
    signal,
  });

  if (!res.ok) {
    throw await parseErrorResponse(res);
  }
  return await res.json();
}

/**
 * Register a new regular user account.
 * Endpoint: POST /auth/register
 */
export async function registerUser(
  credentials: { username: string; password: string },
  signal?: AbortSignal
): Promise<AuthResponse> {
  const res = await fetch(API_ENDPOINTS.AUTH_REGISTER, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Accept": "application/json",
    },
    body: JSON.stringify(credentials),
    credentials: "include",
    cache: "no-store",
    signal,
  });

  if (!res.ok) {
    throw await parseErrorResponse(res);
  }
  return await res.json();
}

/**
 * Log out and terminate the current user session.
 * Endpoint: POST /auth/logout
 */
export async function logoutUser(signal?: AbortSignal): Promise<{ message: string }> {
  const res = await fetch(API_ENDPOINTS.AUTH_LOGOUT, {
    method: "POST",
    headers: { "Accept": "application/json" },
    credentials: "include",
    cache: "no-store",
    signal,
  });

  if (!res.ok) {
    throw await parseErrorResponse(res);
  }
  return await res.json();
}

/**
 * Log out administrator and clear admin session cookie.
 * Endpoint: POST /auth/admin/logout
 */
export async function logoutAdmin(signal?: AbortSignal): Promise<{ message: string }> {
  const res = await fetch(API_ENDPOINTS.AUTH_ADMIN_LOGOUT, {
    method: "POST",
    headers: { "Accept": "application/json" },
    credentials: "include",
    cache: "no-store",
    signal,
  });

  if (!res.ok) {
    throw await parseErrorResponse(res);
  }
  return await res.json();
}

/**
 * Retrieve authenticated administrator profile if admin cookie is present.
 * Endpoint: GET /auth/admin/me
 */
export async function getAdminSession(signal?: AbortSignal): Promise<UserPublic> {
  const res = await fetch(API_ENDPOINTS.AUTH_ADMIN_ME, {
    method: "GET",
    headers: { "Accept": "application/json" },
    credentials: "include",
    cache: "no-store",
    signal,
  });

  if (!res.ok) {
    throw await parseErrorResponse(res);
  }
  return await res.json();
}

/**
 * Retrieve or automatically establish anonymous user session.
 * Endpoint: GET /auth/session
 */
export async function getUserSession(signal?: AbortSignal): Promise<UserPublic> {
  const res = await fetch(API_ENDPOINTS.AUTH_SESSION, {
    method: "GET",
    headers: { "Accept": "application/json" },
    credentials: "include",
    cache: "no-store",
    signal,
  });

  if (!res.ok) {
    throw await parseErrorResponse(res);
  }
  return await res.json();
}

/**
 * Invalidate current session and reset anonymous identity.
 * Endpoint: POST /auth/session/reset
 */
export async function resetSession(signal?: AbortSignal): Promise<{ message: string }> {
  const res = await fetch(API_ENDPOINTS.AUTH_RESET, {
    method: "POST",
    headers: { "Accept": "application/json" },
    credentials: "include",
    cache: "no-store",
    signal,
  });

  if (!res.ok) {
    throw await parseErrorResponse(res);
  }
  return await res.json();
}

/**
 * Retrieve the currently authenticated user profile.
 * Endpoint: GET /auth/me
 */
export async function getCurrentUser(signal?: AbortSignal): Promise<UserPublic> {
  const res = await fetch(API_ENDPOINTS.AUTH_ME, {
    method: "GET",
    headers: { "Accept": "application/json" },
    credentials: "include",
    cache: "no-store",
    signal,
  });

  if (!res.ok) {
    throw await parseErrorResponse(res);
  }
  return await res.json();
}

// ---------------------------------------------------------------------------
// Admin Management Endpoints (Task 19 RBAC)
// ---------------------------------------------------------------------------

/**
 * Fetch aggregated administrative statistics.
 * Endpoint: GET /admin/statistics
 */
export async function getAdminStatistics(signal?: AbortSignal): Promise<AdminStatsResponse> {
  const res = await fetch(API_ENDPOINTS.ADMIN_STATS, {
    method: "GET",
    headers: { "Accept": "application/json" },
    credentials: "include",
    cache: "no-store",
    signal,
  });

  if (!res.ok) {
    throw await parseErrorResponse(res);
  }
  return await res.json();
}

/**
 * List all users across the platform for administrative management.
 * Endpoint: GET /admin/users
 */
export async function getAdminUsers(
  limit: number = 100,
  offset: number = 0,
  signal?: AbortSignal
): Promise<AdminUserListResponse> {
  const url = `${API_ENDPOINTS.ADMIN_USERS}?limit=${limit}&offset=${offset}`;
  const res = await fetch(url, {
    method: "GET",
    headers: { "Accept": "application/json" },
    credentials: "include",
    cache: "no-store",
    signal,
  });

  if (!res.ok) {
    throw await parseErrorResponse(res);
  }
  return await res.json();
}

/**
 * Toggle active / deactivated status for a user account.
 * Endpoint: POST /admin/users/{id}/status
 */
export async function updateUserStatus(
  userId: string,
  isActive: boolean,
  signal?: AbortSignal
): Promise<{ id: string; username: string; is_active: boolean; message: string }> {
  const url = API_ENDPOINTS.ADMIN_USER_STATUS(userId);
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Accept": "application/json",
    },
    body: JSON.stringify({ is_active: isActive }),
    credentials: "include",
    cache: "no-store",
    signal,
  });

  if (!res.ok) {
    throw await parseErrorResponse(res);
  }
  return await res.json();
}

/**
 * Retrieve all clinical analyses across all users for admin review.
 * Endpoint: GET /admin/analyses
 */
export async function getAdminAnalyses(
  limit: number = 50,
  offset: number = 0,
  signal?: AbortSignal
): Promise<AnalysisHistoryResponse> {
  const url = `${API_ENDPOINTS.ADMIN_ANALYSES}?limit=${limit}&offset=${offset}`;
  const res = await fetch(url, {
    method: "GET",
    headers: { "Accept": "application/json" },
    credentials: "include",
    cache: "no-store",
    signal,
  });

  if (!res.ok) {
    throw await parseErrorResponse(res);
  }
  return await res.json();
}

/**
 * Retrieve detailed system diagnostic metadata for admin.
 * Endpoint: GET /admin/system
 */
export async function getAdminSystemInfo(signal?: AbortSignal): Promise<SystemInfoResponse> {
  const res = await fetch(API_ENDPOINTS.ADMIN_SYSTEM, {
    method: "GET",
    headers: { "Accept": "application/json" },
    credentials: "include",
    cache: "no-store",
    signal,
  });

  if (!res.ok) {
    throw await parseErrorResponse(res);
  }
  return await res.json();
}

// ---------------------------------------------------------------------------
// Core Clinical & Analysis Endpoints
// ---------------------------------------------------------------------------

/**
 * Fetch health status from FastAPI backend.
 * Endpoint: GET /health
 */
export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 8000);

  const effectiveSignal = signal || controller.signal;

  try {
    const res = await fetch(API_ENDPOINTS.HEALTH, {
      method: "GET",
      headers: { "Accept": "application/json" },
      cache: "no-store",
      credentials: "include",
      signal: effectiveSignal,
    });
    clearTimeout(timeoutId);

    if (!res.ok) {
      throw await parseErrorResponse(res);
    }
    return await res.json();
  } catch (err: unknown) {
    clearTimeout(timeoutId);
    if (err instanceof ApiError) throw err;
    if (err && typeof err === "object" && "name" in err && err.name === "AbortError") {
      throw new ApiError(408, "Health check request timed out after 8 seconds");
    }
    const msg = err instanceof Error ? err.message : "Unable to connect to FastAPI backend";
    throw new ApiError(0, msg);
  }
}

/**
 * Fetch system and environment metadata.
 * Endpoint: GET /api/v1/system/info
 */
export async function getSystemInfo(signal?: AbortSignal): Promise<SystemInfoResponse> {
  const res = await fetch(API_ENDPOINTS.SYSTEM_INFO, {
    method: "GET",
    headers: { "Accept": "application/json" },
    cache: "no-store",
    credentials: "include",
    signal,
  });
  if (!res.ok) {
    throw await parseErrorResponse(res);
  }
  return await res.json();
}

/**
 * Send chest radiograph for full AI analysis, Grad-CAM overlays, and persistent storage.
 * Endpoint: POST /analyze
 */
export async function analyzeXRay(
  file: File,
  options?: { targetClass?: number; alpha?: number },
  signal?: AbortSignal
): Promise<AnalysisResponse> {
  const formData = new FormData();
  formData.append("file", file);
  if (options?.targetClass !== undefined) {
    formData.append("target_class", options.targetClass.toString());
  }
  if (options?.alpha !== undefined) {
    formData.append("alpha", options.alpha.toString());
  }

  const res = await fetch(API_ENDPOINTS.ANALYZE, {
    method: "POST",
    body: formData,
    credentials: "include",
    signal,
  });

  if (!res.ok) {
    throw await parseErrorResponse(res);
  }
  return await res.json();
}

/**
 * Send chest radiograph for fast standard prediction.
 * Endpoint: POST /predict
 */
export async function predictXRay(file: File, signal?: AbortSignal): Promise<PredictionResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(API_ENDPOINTS.PREDICT, {
    method: "POST",
    body: formData,
    credentials: "include",
    signal,
  });

  if (!res.ok) {
    throw await parseErrorResponse(res);
  }
  return await res.json();
}

/**
 * Send chest radiograph for Grad-CAM explainability visualization only.
 * Endpoint: POST /explain
 */
export async function explainXRay(
  file: File,
  options?: { targetClass?: number; alpha?: number },
  signal?: AbortSignal
): Promise<ExplainResponse> {
  const formData = new FormData();
  formData.append("file", file);
  if (options?.targetClass !== undefined) {
    formData.append("target_class", options.targetClass.toString());
  }
  if (options?.alpha !== undefined) {
    formData.append("alpha", options.alpha.toString());
  }

  const res = await fetch(API_ENDPOINTS.EXPLAIN, {
    method: "POST",
    body: formData,
    credentials: "include",
    signal,
  });

  if (!res.ok) {
    throw await parseErrorResponse(res);
  }
  return await res.json();
}

/**
 * Fetch paginated analysis history from SQLite.
 * Endpoint: GET /history
 */
export async function getHistory(
  limit: number = 50,
  offset: number = 0,
  signal?: AbortSignal
): Promise<AnalysisHistoryResponse> {
  const url = `${API_ENDPOINTS.HISTORY}?limit=${limit}&offset=${offset}`;
  const res = await fetch(url, {
    method: "GET",
    headers: { "Accept": "application/json" },
    cache: "no-store",
    credentials: "include",
    signal,
  });

  if (!res.ok) {
    throw await parseErrorResponse(res);
  }
  return await res.json();
}

/**
 * Fetch a single stored analysis record by ID.
 * Endpoint: GET /history/{analysis_id}
 */
export async function getAnalysisById(
  analysisId: string,
  signal?: AbortSignal
): Promise<AnalysisDetailResponse> {
  const url = API_ENDPOINTS.HISTORY_DETAIL(analysisId);
  const res = await fetch(url, {
    method: "GET",
    headers: { "Accept": "application/json" },
    cache: "no-store",
    credentials: "include",
    signal,
  });

  if (!res.ok) {
    throw await parseErrorResponse(res);
  }
  return await res.json();
}

/**
 * Download clinical PDF report for a stored analysis.
 * Endpoint: GET /history/{analysis_id}/report
 * Returns a Blob representing the PDF file.
 */
export async function downloadAnalysisReport(
  analysisId: string,
  signal?: AbortSignal
): Promise<Blob> {
  const url = API_ENDPOINTS.REPORT(analysisId);
  const res = await fetch(url, {
    method: "GET",
    headers: { Accept: "application/pdf" },
    credentials: "include",
    signal,
  });

  if (!res.ok) {
    throw await parseErrorResponse(res);
  }
  return await res.blob();
}

/**
 * Trigger native browser file download of a Blob.
 */
export function triggerBlobDownload(blob: Blob, filename: string): void {
  const blobUrl = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = blobUrl;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  setTimeout(() => window.URL.revokeObjectURL(blobUrl), 1000);
}

/**
 * Get direct artifact URL for stored image/heatmap/overlay.
 */
export function getArtifactUrl(analysisId: string, artifactType: "image" | "heatmap" | "overlay" | "original"): string {
  return API_ENDPOINTS.ARTIFACT(analysisId, artifactType);
}

// Backward compatibility alias
export const fetchHealth = getHealth;
export const fetchSystemInfo = getSystemInfo;
