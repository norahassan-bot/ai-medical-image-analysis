/**
 * Centralized API base URL and endpoints configuration.
 * Safely strips trailing slashes to prevent malformed double-slash URLs.
 */

const rawBaseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const API_BASE_URL = rawBaseUrl.replace(/\/+$/, "");

export const API_ENDPOINTS = {
  HEALTH: `${API_BASE_URL}/health`,
  API_V1_HEALTH: `${API_BASE_URL}/api/v1/health`,
  SYSTEM_INFO: `${API_BASE_URL}/api/v1/system/info`,
  PREDICT: `${API_BASE_URL}/predict`,
  EXPLAIN: `${API_BASE_URL}/explain`,
  ANALYZE: `${API_BASE_URL}/analyze`,
  HISTORY: `${API_BASE_URL}/history`,
  HISTORY_DETAIL: (id: string) => `${API_BASE_URL}/history/${encodeURIComponent(id)}`,
  REPORT: (id: string) => `${API_BASE_URL}/history/${encodeURIComponent(id)}/report`,
  ARTIFACT: (id: string, type: string) => `${API_BASE_URL}/history/${encodeURIComponent(id)}/artifacts/${encodeURIComponent(type)}`,
  DOCS: `${API_BASE_URL}/docs`,
  OPENAPI: `${API_BASE_URL}/openapi.json`,
  AUTH_LOGIN: `${API_BASE_URL}/auth/login`,
  AUTH_REGISTER: `${API_BASE_URL}/auth/register`,
  AUTH_LOGOUT: `${API_BASE_URL}/auth/logout`,
  AUTH_ADMIN_LOGOUT: `${API_BASE_URL}/auth/admin/logout`,
  AUTH_ADMIN_ME: `${API_BASE_URL}/auth/admin/me`,
  AUTH_SESSION: `${API_BASE_URL}/auth/session`,
  AUTH_RESET: `${API_BASE_URL}/auth/session/reset`,
  AUTH_ME: `${API_BASE_URL}/auth/me`,
  ADMIN_STATS: `${API_BASE_URL}/admin/statistics`,
  ADMIN_USERS: `${API_BASE_URL}/admin/users`,
  ADMIN_USER_STATUS: (id: string) => `${API_BASE_URL}/admin/users/${encodeURIComponent(id)}/status`,
  ADMIN_ANALYSES: `${API_BASE_URL}/admin/analyses`,
  ADMIN_SYSTEM: `${API_BASE_URL}/admin/system`,
} as const;

