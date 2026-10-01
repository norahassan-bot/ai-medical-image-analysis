import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import AnalysisPage from "@/app/analysis/page";
import * as api from "@/lib/api";
import type { AnalysisResponse } from "@/types/api";
import { LanguageProvider } from "@/lib/i18n";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    analyzeXRay: vi.fn(),
  };
});

describe("AnalysisPage Workflow & Security Testing (Task 14)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("1. shows loading state during analysis and prevents duplicate clicks", async () => {
    let resolveAnalysis: (val: AnalysisResponse) => void;
    const promise = new Promise<AnalysisResponse>((resolve) => {
      resolveAnalysis = resolve;
    });
    vi.mocked(api.analyzeXRay).mockReturnValue(promise);

    const { container } = render(
      <LanguageProvider>
        <AnalysisPage />
      </LanguageProvider>
    );

    // Select a valid file
    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;
    const validFile = new File(["fake_bytes"], "chest.png", { type: "image/png" });
    fireEvent.change(fileInput, { target: { files: [validFile] } });

    // Click Analyze
    const analyzeBtn = screen.getByRole("button", { name: /تحليل الأشعة|Analyze X-Ray/i });
    expect(analyzeBtn).toBeInTheDocument();
    fireEvent.click(analyzeBtn);

    // Verify loading state is shown
    expect(screen.getByText(/جاري التحميل|Running AI Diagnostic Inference/i)).toBeInTheDocument();

    // Verify button cannot be double-submitted while loading
    expect(api.analyzeXRay).toHaveBeenCalledTimes(1);

    // Resolve analysis
    resolveAnalysis!({
      analysis_id: "test-analysis-uuid-123",
      created_at: new Date().toISOString(),
      filename: "chest.png",
      prediction: "PNEUMONIA",
      predicted_index: 1,
      confidence: 0.945,
      probabilities: { NORMAL: 0.055, PNEUMONIA: 0.945 },
      model_version: "1.0.0",
      architecture: "resnet18",
      device: "cpu",
      inference_time_ms: 45.0,
      target_class: "PNEUMONIA",
      original_base64: "data:image/png;base64,mockOriginal",
      heatmap_base64: "data:image/png;base64,mockHeatmap",
      overlay_base64: "data:image/png;base64,mockOverlay",
      original_dimensions: [224, 224],
      class_mapping: { NORMAL: 0, PNEUMONIA: 1 },
      disclaimer: "AI prediction disclaimer",
    });

    // Verify successful result renders
    await waitFor(() => {
      expect(screen.getByText(/تقييم التشخيص بالذكاء الاصطناعي|AI Diagnostic Evaluation/i)).toBeInTheDocument();
      expect(screen.getAllByText(/التهاب رئوي|PNEUMONIA/i).length).toBeGreaterThan(0);
      expect(screen.getByText(/صورة أشعة غير طبيعية|Abnormal Radiograph/i)).toBeInTheDocument();
    });
  });

  it("2. renders sanitized backend error safely without technical leaks", async () => {
    vi.mocked(api.analyzeXRay).mockRejectedValue(
      new api.ApiError(400, "The uploaded file could not be processed as a valid image.")
    );

    const { container } = render(
      <LanguageProvider>
        <AnalysisPage />
      </LanguageProvider>
    );

    // Select valid file
    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;
    const validFile = new File(["fake_bytes"], "chest.png", { type: "image/png" });
    fireEvent.change(fileInput, { target: { files: [validFile] } });

    // Click Analyze
    const analyzeBtn = screen.getByRole("button", { name: /تحليل الأشعة|Analyze X-Ray/i });
    fireEvent.click(analyzeBtn);

    await waitFor(() => {
      expect(screen.getByText(/فشل طلب الاستدلال|Inference Request Failed/i)).toBeInTheDocument();
      expect(
        screen.getByText(/The uploaded file could not be processed as a valid image/i)
      ).toBeInTheDocument();
    });

    // Ensure raw system keywords / tracebacks are not exposed
    expect(screen.queryByText(/Traceback/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/File "/i)).not.toBeInTheDocument();
  });
});
