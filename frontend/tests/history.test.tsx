import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import HistoryPage from "@/app/history/page";
import AnalysisDetailPage from "@/app/history/[analysisId]/page";
import * as api from "@/lib/api";
import { LanguageProvider } from "@/lib/i18n";

vi.mock("next/navigation", () => ({
  useParams: () => ({ analysisId: "mock-uuid-test" }),
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    getHistory: vi.fn(),
    getAnalysisById: vi.fn(),
    downloadAnalysisReport: vi.fn(),
    triggerBlobDownload: vi.fn(),
  };
});

describe("History and Report Error States (Task 14)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("1. renders history error state cleanly when database is unreachable", async () => {
    vi.mocked(api.getHistory).mockRejectedValue(
      new api.ApiError(500, "Failed to load analysis history from SQLite database.")
    );

    render(
      <LanguageProvider>
        <HistoryPage />
      </LanguageProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/فشل تحميل السجل|Failed to Load History/i)).toBeInTheDocument();
      expect(
        screen.getByText(/Failed to load analysis history from SQLite database/i)
      ).toBeInTheDocument();
    });
  });

  it("2. renders missing analysis (404) state gracefully", async () => {
    vi.mocked(api.getAnalysisById).mockRejectedValue(
      new api.ApiError(404, "Analysis with ID 'mock-uuid-test' not found.")
    );

    render(
      <LanguageProvider>
        <AnalysisDetailPage />
      </LanguageProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/لم يتم العثور على سجل التحليل|Analysis Record Not Found/i)).toBeInTheDocument();
      expect(screen.getByText(/mock-uuid-test/i)).toBeInTheDocument();
    });
  });

  it("3. renders report download failure state cleanly", async () => {
    vi.mocked(api.getAnalysisById).mockResolvedValue({
      analysis_id: "mock-uuid-test",
      created_at: new Date().toISOString(),
      prediction: "NORMAL",
      predicted_index: 0,
      confidence: 0.98,
      probabilities: { NORMAL: 0.98, PNEUMONIA: 0.02 },
      model_version: "1.0.0",
      architecture: "resnet18",
      device: "cpu",
      inference_time_ms: 32.0,
      target_class: "NORMAL",
      status: "completed",
    });

    vi.mocked(api.downloadAnalysisReport).mockRejectedValue(
      new api.ApiError(500, "Failed to generate clinical PDF report.")
    );

    render(
      <LanguageProvider>
        <AnalysisDetailPage />
      </LanguageProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/تفاصيل التحليل|Analysis Details/i)).toBeInTheDocument();
    });

    const downloadBtn = screen.getByRole("button", { name: /تنزيل تقرير PDF|Download PDF Report/i });
    fireEvent.click(downloadBtn);

    await waitFor(() => {
      expect(screen.getByText(/Failed to generate clinical PDF report/i)).toBeInTheDocument();
    });
  });
});
