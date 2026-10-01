import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import React from "react";
import Sidebar from "@/components/Sidebar";
import ClinicalDashboardPage from "@/app/page";
import AnalysisPage from "@/app/analysis/page";
import HistoryPage from "@/app/history/page";
import AnalysisDetailPage from "@/app/history/[analysisId]/page";
import AccountPage from "@/app/account/page";
import UserDashboardPage from "@/app/user/page";
import UserAnalysisPage from "@/app/user/analysis/page";
import UserHistoryPage from "@/app/user/history/page";
import UserAccountPage from "@/app/user/account/page";
import UserAnalysisDetailPage from "@/app/user/history/[analysisId]/page";
import { LanguageProvider } from "@/lib/i18n";
import { AuthProvider } from "@/lib/auth/AuthContext";
import * as api from "@/lib/api";

// Mock Next.js navigation
const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
    replace: vi.fn(),
    prefetch: vi.fn(),
  }),
  usePathname: () => "/",
  useParams: () => ({ analysisId: "test-uuid-12345" }),
}));

// Mock API endpoints
vi.mock("@/lib/api", async (importOriginal) => {
  const actual: any = await importOriginal();
  return {
    ...actual,
    loginUser: vi.fn(),
    logoutUser: vi.fn(),
    getUserSession: vi.fn(),
    getCurrentUser: vi.fn(),
    resetSession: vi.fn(),
    getHistory: vi.fn(),
    getAnalysisHistory: vi.fn(),
    getAnalysisById: vi.fn(),
    downloadAnalysisReport: vi.fn(),
    triggerBlobDownload: vi.fn(),
    analyzeImage: vi.fn(),
    analyzeXRay: vi.fn(),
    getHealth: vi.fn().mockResolvedValue({ status: "healthy", model_loaded: true }),
    getSystemInfo: vi.fn().mockResolvedValue({ environment: "development", device: "cpu" }),
  };
});

function renderWithProviders(ui: React.ReactNode, { lang = "ar" }: { lang?: "ar" | "en" } = {}) {
  if (typeof window !== "undefined") {
    window.localStorage.setItem("medvision_lang", lang);
  }
  return render(
    <LanguageProvider defaultLocale={lang}>
      <AuthProvider>{ui}</AuthProvider>
    </LanguageProvider>
  );
}

describe("Clinical User Portal at Root Route / & Zero-Login Test Suite", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (api.getUserSession as any).mockResolvedValue({
      id: "anon-u1",
      username: "anon_e4bf5262",
      role: "USER",
      is_active: true,
      created_at: "2026-09-30T10:00:00Z",
    });
    (api.getCurrentUser as any).mockResolvedValue({
      id: "anon-u1",
      username: "anon_e4bf5262",
      role: "USER",
      is_active: true,
      created_at: "2026-09-30T10:00:00Z",
    });
    (api.getHistory as any).mockResolvedValue({
      items: [],
      total: 0,
    });
  });

  it("1. Root / renders clinical dashboard without requiring login", async () => {
    const historyData = {
      items: [
        {
          analysis_id: "ana-001",
          created_at: "2026-09-30T12:00:00Z",
          prediction: "NORMAL",
          confidence: 0.98,
          model_version: "1.0.0",
        },
      ],
      total: 1,
    };
    (api.getHistory as any).mockResolvedValue(historyData);

    renderWithProviders(<ClinicalDashboardPage />);
    await waitFor(() => {
      expect(mockPush).not.toHaveBeenCalledWith("/login");
      expect(screen.getAllByText(/منظومة التحليل الإشعاعي|Pediatric Chest X-Ray AI Analysis/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/ana-001/i).length).toBeGreaterThan(0);
    });
  });

  it("2. /analysis renders without login requirement", async () => {
    renderWithProviders(<AnalysisPage />);
    await waitFor(() => {
      expect(mockPush).not.toHaveBeenCalledWith("/login");
      expect(screen.getAllByText(/تحليل صورة أشعة الصدر|رفع صورة|اسحب وأفلت|Upload|Chest X-ray/i).length).toBeGreaterThan(0);
    });
  });

  it("3. /history renders without login requirement", async () => {
    (api.getHistory as any).mockResolvedValue({
      items: [
        {
          analysis_id: "ana-002",
          created_at: "2026-09-30T12:00:00Z",
          prediction: "PNEUMONIA",
          confidence: 0.94,
          model_version: "1.0.0",
        },
      ],
      total: 1,
    });

    renderWithProviders(<HistoryPage />);
    await waitFor(() => {
      expect(mockPush).not.toHaveBeenCalledWith("/login");
      expect(screen.getAllByText(/ana-002/i).length).toBeGreaterThan(0);
    });
  });

  it("4. /account renders active session telemetry without login fields", async () => {
    renderWithProviders(<AccountPage />);
    await waitFor(() => {
      expect(screen.getAllByText(/مستخدم سريري|Clinical User/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/نشط وموثق|Active/i).length).toBeGreaterThan(0);
      expect(screen.getByRole("button", { name: /إنهاء الجلسة|End Session/i })).toBeInTheDocument();
    });
  });

  it("5. End Session / Reset button triggers session reset", async () => {
    (api.resetSession as any).mockResolvedValueOnce({ message: "Session reset" });
    (api.getUserSession as any).mockResolvedValueOnce({
      id: "anon-u2",
      username: "anon_99999999",
      role: "USER",
      is_active: true,
      created_at: "2026-09-30T12:30:00Z",
    });

    renderWithProviders(<AccountPage />);
    const resetBtn = await screen.findByRole("button", { name: /إنهاء الجلسة|End Session/i });
    fireEvent.click(resetBtn);

    await waitFor(() => {
      expect(api.resetSession).toHaveBeenCalled();
    });
  });

  it("6. Analysis Detail page loads and displays medical report actions", async () => {
    (api.getAnalysisById as any).mockResolvedValueOnce({
      analysis_id: "test-uuid-12345",
      created_at: "2026-09-30T12:00:00Z",
      filename: "test_xray.png",
      prediction: "NORMAL",
      predicted_index: 0,
      confidence: 0.975,
      probabilities: { NORMAL: 0.975, PNEUMONIA: 0.025 },
      model_version: "1.0.0",
      architecture: "resnet18",
      device: "cpu",
      inference_time_ms: 18.2,
      target_class: "NORMAL",
      status: "completed",
    });

    renderWithProviders(<AnalysisDetailPage />);
    await waitFor(() => {
      expect(screen.getAllByText(/test-uuid-12345/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/تنزيل تقرير PDF|تحميل تقرير PDF|Download/i).length).toBeGreaterThan(0);
    });
  });

  it("7. Clinical user navigation renders user-only navigation items", async () => {
    renderWithProviders(<Sidebar />);
    await waitFor(() => {
      expect(screen.getAllByText(/لوحة التحكم|الرئيسية|Dashboard/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/تحليل الصور الطبية|تحليل الأشعة|AI Analysis/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/سجل تحليلاتي|سجل الفحوصات|My Analyses/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/حسابي الشخصي|My Account/i).length).toBeGreaterThan(0);
    });
  });

  it("8. /user route renders UserDashboardPage with complete UI and zero login", async () => {
    (api.getHistory as any).mockResolvedValue({
      items: [
        {
          analysis_id: "ana-user",
          created_at: "2026-09-30T12:00:00Z",
          prediction: "NORMAL",
          confidence: 0.96,
          model_version: "1.0.0",
        },
      ],
      total: 1,
    });

    renderWithProviders(<UserDashboardPage />);
    await waitFor(() => {
      expect(mockPush).not.toHaveBeenCalledWith("/login");
      expect(screen.getAllByText(/منظومة التحليل الإشعاعي|Pediatric Chest X-Ray AI Analysis/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/ana-user/i).length).toBeGreaterThan(0);
    });
  });

  it("9. /user/analysis route renders UserAnalysisPage with dropzone", async () => {
    renderWithProviders(<UserAnalysisPage />);
    await waitFor(() => {
      expect(mockPush).not.toHaveBeenCalledWith("/login");
      expect(screen.getAllByText(/تحليل صورة أشعة الصدر|رفع صورة|اسحب وأفلت|Upload|Chest X-ray/i).length).toBeGreaterThan(0);
    });
  });
});
