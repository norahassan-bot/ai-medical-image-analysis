import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import HealthStatusCard from "@/components/HealthStatusCard";
import * as api from "@/lib/api";
import { LanguageProvider } from "@/lib/i18n";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    getHealth: vi.fn(),
    getSystemInfo: vi.fn(),
  };
});

describe("HealthStatusCard Display (Task 14)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("1. displays healthy and model ready status correctly", async () => {
    vi.mocked(api.getHealth).mockResolvedValue({
      status: "healthy",
      model_loaded: true,
      model_version: "1.0.0",
      architecture: "resnet18",
      device: "cpu",
    });
    vi.mocked(api.getSystemInfo).mockResolvedValue({
      app_name: "AI Medical Platform",
      version: "1.0.0",
      environment: "development",
      docs_url: "/docs",
      cors_allowed_origins: ["http://localhost:3000"],
    });

    render(
      <LanguageProvider>
        <HealthStatusCard />
      </LanguageProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/200 OK/i)).toBeInTheDocument();
      expect(screen.getByText(/النموذج جاهز|Model Ready/i)).toBeInTheDocument();
      expect(screen.getByText(/SQLite \(medical_ai\.db\)/i)).toBeInTheDocument();
    });
  });

  it("2. displays uninitialized status when model weights are not loaded", async () => {
    vi.mocked(api.getHealth).mockResolvedValue({
      status: "healthy",
      model_loaded: false,
    });
    vi.mocked(api.getSystemInfo).mockResolvedValue({
      app_name: "AI Medical Platform",
      version: "1.0.0",
      environment: "development",
      docs_url: "/docs",
      cors_allowed_origins: ["http://localhost:3000"],
    });

    render(
      <LanguageProvider>
        <HealthStatusCard />
      </LanguageProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/200 OK/i)).toBeInTheDocument();
      expect(screen.getByText(/في انتظار الأوزان|Awaiting Weights/i)).toBeInTheDocument();
    });
  });

  it("3. displays offline when backend is unreachable", async () => {
    vi.mocked(api.getHealth).mockRejectedValue(
      new Error("Unable to connect to FastAPI backend")
    );
    vi.mocked(api.getSystemInfo).mockRejectedValue(
      new Error("System info fetch failed")
    );

    render(
      <LanguageProvider>
        <HealthStatusCard />
      </LanguageProvider>
    );

    await waitFor(() => {
      expect(
        screen.getByText(/غير متصل \/ تعذر الوصول|Offline \/ Unreachable/i)
      ).toBeInTheDocument();
    });
  });
});
