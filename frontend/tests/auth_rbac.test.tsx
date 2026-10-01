import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import React from "react";
import LoginPage from "@/app/login/page";
import Sidebar from "@/components/Sidebar";
import Header from "@/components/Header";
import AdminDashboardPage from "@/app/admin/page";
import AdminUsersPage from "@/app/admin/users/page";
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
  useParams: () => ({}),
}));

// Mock API endpoints
vi.mock("@/lib/api", async (importOriginal) => {
  const actual: any = await importOriginal();
  return {
    ...actual,
    loginUser: vi.fn(),
    logoutUser: vi.fn(),
    logoutAdmin: vi.fn(),
    getAdminSession: vi.fn(),
    getUserSession: vi.fn(),
    getCurrentUser: vi.fn(),
    resetSession: vi.fn(),
    getAdminStatistics: vi.fn(),
    getAdminUsers: vi.fn(),
    updateUserStatus: vi.fn(),
    getAdminAnalyses: vi.fn(),
    getAdminSystemInfo: vi.fn(),
    getHealth: vi.fn().mockResolvedValue({ status: "healthy", model_loaded: true }),
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

describe("Frontend Auth & RBAC Test Suite (Task 19 & Task 21)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (api.getAdminSession as any).mockRejectedValue(new Error("No admin session"));
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
  });

  it("1. Admin Login page renders username, password and login button", async () => {
    renderWithProviders(<LoginPage />);
    expect(screen.getByLabelText(/اسم المستخدم|Username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/كلمة المرور|Password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /تسجيل الدخول|Sign In|Login/i })).toBeInTheDocument();
  });

  it("2. Admin login page has direct link to clinical portal without login", async () => {
    renderWithProviders(<LoginPage />);
    expect(screen.getByText(/الدخول المباشر إلى بوابة الفحص|Open Clinical User Portal/i)).toBeInTheDocument();
  });

  it("3. Successful Admin login calls API and redirects to /admin", async () => {
    (api.loginUser as any).mockResolvedValueOnce({
      user: { id: "admin-1", username: "admin", role: "ADMIN", is_active: true },
      message: "Success",
    });

    renderWithProviders(<LoginPage />);
    const usernameInput = screen.getByLabelText(/اسم المستخدم|Username/i);
    const passwordInput = screen.getByLabelText(/كلمة المرور|Password/i);
    const submitBtn = screen.getByRole("button", { name: /تسجيل الدخول|Sign In|Login/i });

    fireEvent.change(usernameInput, { target: { value: "admin" } });
    fireEvent.change(passwordInput, { target: { value: "AdminPass123!" } });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(api.loginUser).toHaveBeenCalledWith({
        username: "admin",
        password: "AdminPass123!",
      });
      expect(mockPush).toHaveBeenCalledWith("/admin");
    });
  });

  it("4. Invalid credentials display error alert", async () => {
    (api.loginUser as any).mockRejectedValueOnce(
      new api.ApiError(401, "Invalid administrator credentials.")
    );

    renderWithProviders(<LoginPage />);
    const usernameInput = screen.getByLabelText(/اسم المستخدم|Username/i);
    const passwordInput = screen.getByLabelText(/كلمة المرور|Password/i);
    const submitBtn = screen.getByRole("button", { name: /تسجيل الدخول|Sign In|Login/i });

    fireEvent.change(usernameInput, { target: { value: "wrongadmin" } });
    fireEvent.change(passwordInput, { target: { value: "wrongpass" } });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });
  });

  it("5. Admin Dashboard renders metrics for authenticated ADMIN", async () => {
    (api.getAdminSession as any).mockResolvedValue({
      id: "admin-1",
      username: "admin",
      role: "ADMIN",
      is_active: true,
    });
    (api.getUserSession as any).mockResolvedValue({
      id: "admin-1",
      username: "admin",
      role: "ADMIN",
      is_active: true,
    });
    (api.getAdminStatistics as any).mockResolvedValue({
      total_analyses: 42,
      normal_count: 20,
      pneumonia_count: 22,
      total_users: 10,
      active_users: 10,
      admin_users: 1,
      regular_users: 9,
      avg_confidence: 0.95,
      model_version: "1.0.0",
      architecture: "resnet18",
      environment: "test",
    });

    renderWithProviders(<AdminDashboardPage />);
    await waitFor(
      () => {
        expect(screen.getByText("42")).toBeInTheDocument();
      },
      { timeout: 5000 }
    );
  });

  it("6. Admin Users Page renders user accounts for authenticated ADMIN", async () => {
    (api.getAdminSession as any).mockResolvedValue({
      id: "admin-1",
      username: "admin",
      role: "ADMIN",
      is_active: true,
    });
    (api.getUserSession as any).mockResolvedValue({
      id: "admin-1",
      username: "admin",
      role: "ADMIN",
      is_active: true,
    });
    (api.getAdminUsers as any).mockResolvedValue({
      users: [
        {
          id: "u-1",
          username: "doctor_john",
          role: "USER",
          is_active: true,
          created_at: "2026-09-30T10:00:00Z",
          analysis_count: 15,
        },
      ],
      total: 1,
    });

    renderWithProviders(<AdminUsersPage />);
    await waitFor(
      () => {
        expect(screen.getAllByText("doctor_john").length).toBeGreaterThan(0);
        expect(screen.getAllByText("15").length).toBeGreaterThan(0);
      },
      { timeout: 5000 }
    );
  });

  it("7. Admin Users Page denies access to regular unprivileged USER", async () => {
    (api.getAdminSession as any).mockRejectedValue(new Error("Unauthorized"));
    (api.getUserSession as any).mockResolvedValue({
      id: "anon-u1",
      username: "anon_clinician",
      role: "USER",
      is_active: true,
    });

    renderWithProviders(<AdminUsersPage />);
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/login");
    });
  });
});
