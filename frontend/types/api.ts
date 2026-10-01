/**
 * Frontend TypeScript interfaces matching the FastAPI backend response contracts.
 */

export interface HealthResponse {
  status: "healthy" | "unhealthy" | string;
  model_loaded: boolean;
  model_version?: string;
  architecture?: string;
  device?: string;
}

export interface SystemInfoResponse {
  app_name: string;
  version: string;
  environment: string;
  docs_url: string;
  cors_allowed_origins: string[];
}

export interface PredictionResponse {
  prediction: "NORMAL" | "PNEUMONIA" | string;
  predicted_index: number;
  confidence: number;
  probabilities: Record<string, number>;
  model_version: string;
  architecture: string;
  device: string;
  inference_time_ms: number;
  class_mapping: Record<string, number>;
  disclaimer: string;
}

export interface ExplainResponse {
  prediction: "NORMAL" | "PNEUMONIA" | string;
  predicted_index: number;
  confidence: number;
  probabilities: Record<string, number>;
  model_version: string;
  architecture: string;
  device: string;
  inference_time_ms: number;
  target_class: string;
  original_base64?: string;
  heatmap_base64?: string;
  overlay_base64?: string;
  original_dimensions?: [number, number];
  disclaimer: string;
}

export interface AnalysisResponse {
  analysis_id: string;
  created_at: string;
  filename?: string;
  prediction: "NORMAL" | "PNEUMONIA" | string;
  predicted_index: number;
  confidence: number;
  probabilities: Record<string, number>;
  model_version: string;
  architecture: string;
  device: string;
  inference_time_ms: number;
  target_class: string;
  image_reference?: string;
  heatmap_reference?: string;
  overlay_reference?: string;
  original_base64?: string;
  heatmap_base64?: string;
  overlay_base64?: string;
  original_dimensions?: [number, number];
  class_mapping: Record<string, number>;
  disclaimer: string;
}

export interface AnalysisHistoryItem {
  analysis_id: string;
  created_at: string;
  filename?: string;
  prediction: "NORMAL" | "PNEUMONIA" | string;
  confidence: number;
  model_version: string;
  architecture?: string;
  image_reference?: string;
  overlay_reference?: string;
  status?: string;
}

export interface AnalysisHistoryResponse {
  items: AnalysisHistoryItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface AnalysisDetailResponse {
  analysis_id: string;
  created_at: string;
  filename?: string;
  prediction: "NORMAL" | "PNEUMONIA" | string;
  predicted_index: number;
  confidence: number;
  probabilities: Record<string, number>;
  model_version: string;
  architecture: string;
  device: string;
  inference_time_ms: number;
  target_class: string;
  image_reference?: string;
  heatmap_reference?: string;
  overlay_reference?: string;
  original_dimensions?: [number, number];
  status: string;
}

export interface ErrorDetail {
  code: string;
  message: string;
  details?: unknown;
}

export interface ErrorResponse {
  error: ErrorDetail;
}

export interface UserPublic {
  id: string;
  username: string;
  role: "ADMIN" | "USER" | string;
  is_active: boolean;
  created_at?: string;
}

export interface AuthResponse {
  user: UserPublic;
  message: string;
}

export interface AdminUserItem {
  id: string;
  username: string;
  role: string;
  is_active: boolean;
  created_at: string;
  analysis_count?: number;
}

export interface AdminUserListResponse {
  users: AdminUserItem[];
  total: number;
}

export interface AdminStatsResponse {
  total_analyses: number;
  normal_count: number;
  pneumonia_count: number;
  total_users: number;
  active_users: number;
  admin_users: number;
  regular_users: number;
  avg_confidence: number;
  model_version: string;
  architecture: string;
  environment: string;
}

