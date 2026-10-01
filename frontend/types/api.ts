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

// ============================================================================
// Prescription Understanding & Reader Interfaces (Task 25 & Task 26)
// ============================================================================

export interface DoseInstruction {
  value: number;
  unit: string;
  raw_text: string;
  confidence: number;
  status: string;
}

export interface FrequencyInstruction {
  frequency_type: string;
  times_per_day?: number | null;
  interval_hours?: number | null;
  specific_timing?: string | null;
  is_prn?: boolean;
  raw_text: string;
  confidence: number;
  status: string;
}

export interface DurationInstruction {
  value: number;
  unit: string;
  raw_text: string;
  confidence: number;
  status: string;
}

export interface RouteInstruction {
  route: string;
  raw_text: string;
  confidence: number;
  status: string;
}

export interface FoodTimingInstruction {
  timing: string;
  raw_text: string;
  confidence: number;
  status: string;
}

export interface ParsedPrescriptionInstructions {
  dose?: DoseInstruction | null;
  frequency?: FrequencyInstruction | null;
  duration?: DurationInstruction | null;
  route?: RouteInstruction | null;
  food_timing?: FoodTimingInstruction | null;
  prn?: boolean;
  special_instructions?: string[];
  raw_instruction_text?: string;
  overall_confidence?: number;
  uncertain_fields?: string[];
}

export interface MedicationSummary {
  matched_name?: string | null;
  generic_name?: string | null;
  brand_name?: string | null;
  source?: string | null;
  confidence: number;
  status: string;
}

export interface StrengthInfo {
  value: number;
  unit: string;
  raw_text?: string;
}

export interface DosageFormInfo {
  form: string;
  raw_text?: string;
}

export interface MedicationInformationData {
  status: "verified" | "unverified" | "provider_unavailable" | string;
  medication_name?: string;
  generic_name?: string;
  brand_name?: string;
  active_ingredients?: string[];
  drug_class?: string;
  what_is_it?: string;
  what_is_it_ar?: string;
  general_uses?: string[];
  general_uses_ar?: string[];
  route?: string;
  source?: {
    source_name?: string;
    source_id?: string;
    retrieved_at?: string;
    provider_version?: string;
  };
}

export interface PrescriptionMedicationItem {
  region_id: string;
  raw_text: string;
  normalized_text: string;
  ocr_confidence?: number;
  medication: MedicationSummary;
  strength?: StrengthInfo | null;
  dosage_form?: DosageFormInfo | null;
  instructions: ParsedPrescriptionInstructions;
  medication_information: MedicationInformationData;
  association_confidence?: number;
  association_uncertain?: boolean;
}

export interface PrescriptionUnderstandingResult {
  analysis_type: string;
  status: string;
  parser_version?: string;
  total_medications: number;
  medications: PrescriptionMedicationItem[];
  processing_time_ms: number;
  disclaimer_en?: string;
  disclaimer_ar?: string;
}

export interface PrescriptionAnalysisResponse {
  analysis_id: string;
  created_at: string;
  filename?: string;
  image_reference?: string;
  status: string;
  total_medications: number;
  processing_time_ms: number;
  result: PrescriptionUnderstandingResult;
}

export interface PrescriptionHistoryItem {
  id?: number;
  analysis_id: string;
  owner_user_id?: string;
  created_at: string;
  filename?: string;
  total_medications: number;
  status: string;
  image_reference?: string;
  processing_time_ms?: number;
  result?: PrescriptionUnderstandingResult;
}

export interface PrescriptionHistoryResponse {
  items: PrescriptionHistoryItem[];
  total: number;
  limit: number;
  offset: number;
}

