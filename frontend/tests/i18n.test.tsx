import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { LanguageProvider, useLanguage } from "@/lib/i18n";
import LanguageSwitcher from "@/components/LanguageSwitcher";
import Disclaimer from "@/components/Disclaimer";
import ConfidenceDisplay from "@/components/ConfidenceDisplay";
import Header from "@/components/Header";
import Sidebar from "@/components/Sidebar";
import UploadDropzone from "@/components/UploadDropzone";
import EmptyState from "@/components/EmptyState";
import ErrorState from "@/components/ErrorState";
import LoadingState from "@/components/LoadingState";
import { en } from "@/lib/i18n/locales/en";
import { ar } from "@/lib/i18n/locales/ar";

// Helper component for testing context hooks
function TestConsumer() {
  const { language, direction, isRTL, setLanguage, t } = useLanguage();
  return (
    <div>
      <span data-testid="current-lang">{language}</span>
      <span data-testid="current-dir">{direction}</span>
      <span data-testid="is-rtl">{isRTL ? "true" : "false"}</span>
      <span data-testid="translated-title">{t("app.title")}</span>
      <span data-testid="translated-prediction">{t("common.pneumonia")}</span>
      <span data-testid="disclaimer">{t("disclaimer.standardText")}</span>
      <button onClick={() => setLanguage("en")}>Set English</button>
      <button onClick={() => setLanguage("ar")}>Set Arabic</button>
    </div>
  );
}

describe("Task 17 — Bilingual Localization & RTL Verification", () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.lang = "ar";
    document.documentElement.dir = "rtl";
  });

  it("1. Arabic is the default locale", () => {
    render(
      <LanguageProvider>
        <TestConsumer />
      </LanguageProvider>
    );

    expect(screen.getByTestId("current-lang").textContent).toBe("ar");
  });

  it("2. English can be selected and switches state", () => {
    render(
      <LanguageProvider>
        <TestConsumer />
      </LanguageProvider>
    );

    fireEvent.click(screen.getByText("Set English"));
    expect(screen.getByTestId("current-lang").textContent).toBe("en");
  });

  it("3. Arabic sets dir='rtl' and lang='ar' on documentElement", () => {
    render(
      <LanguageProvider>
        <TestConsumer />
      </LanguageProvider>
    );

    expect(screen.getByTestId("current-dir").textContent).toBe("rtl");
    expect(screen.getByTestId("is-rtl").textContent).toBe("true");
    expect(document.documentElement.dir).toBe("rtl");
    expect(document.documentElement.lang).toBe("ar");
  });

  it("4. English sets dir='ltr' and lang='en' on documentElement", () => {
    render(
      <LanguageProvider>
        <TestConsumer />
      </LanguageProvider>
    );

    fireEvent.click(screen.getByText("Set English"));
    expect(screen.getByTestId("current-dir").textContent).toBe("ltr");
    expect(screen.getByTestId("is-rtl").textContent).toBe("false");
    expect(document.documentElement.dir).toBe("ltr");
    expect(document.documentElement.lang).toBe("en");
  });

  it("5. LanguageSwitcher toggles between Arabic and English seamlessly", () => {
    render(
      <LanguageProvider>
        <LanguageSwitcher />
        <TestConsumer />
      </LanguageProvider>
    );

    expect(screen.getByTestId("current-lang").textContent).toBe("ar");

    const enBtn = screen.getByRole("button", { name: "English" });
    fireEvent.click(enBtn);

    expect(screen.getByTestId("current-lang").textContent).toBe("en");
    expect(screen.getByTestId("translated-title").textContent).toBe(en["app.title"]);

    const arBtn = screen.getByRole("button", { name: "العربية" });
    fireEvent.click(arBtn);

    expect(screen.getByTestId("current-lang").textContent).toBe("ar");
    expect(screen.getByTestId("translated-title").textContent).toBe(ar["app.title"]);
  });

  it("6. Medical Disclaimer matches exact regulatory Arabic & English texts", () => {
    const { rerender } = render(
      <LanguageProvider>
        <Disclaimer variant="banner" />
      </LanguageProvider>
    );

    // Default Arabic
    expect(
      screen.getByText(/هذه النتيجة مولدة بواسطة نظام ذكاء اصطناعي، ولا تُعد تشخيصًا طبيًا/i)
    ).toBeInTheDocument();

    // Switch to English
    rerender(
      <LanguageProvider>
        <LanguageSwitcher />
        <Disclaimer variant="banner" />
      </LanguageProvider>
    );

    fireEvent.click(screen.getByRole("button", { name: "English" }));

    expect(
      screen.getByText(/This result is AI-generated and is not a medical diagnosis/i)
    ).toBeInTheDocument();
  });

  it("7. Prediction labels are localized while keeping backend values untouched", () => {
    const { rerender } = render(
      <LanguageProvider>
        <ConfidenceDisplay
          prediction="PNEUMONIA"
          confidence={0.94}
          probabilities={{ NORMAL: 0.06, PNEUMONIA: 0.94 }}
        />
      </LanguageProvider>
    );

    // In Arabic default
    expect(screen.getAllByText("التهاب رئوي").length).toBeGreaterThan(0);
    expect(screen.getByText("طبيعي")).toBeInTheDocument();
    expect(screen.getByText("94%")).toBeInTheDocument();

    // In English
    rerender(
      <LanguageProvider>
        <LanguageSwitcher />
        <ConfidenceDisplay
          prediction="PNEUMONIA"
          confidence={0.94}
          probabilities={{ NORMAL: 0.06, PNEUMONIA: 0.94 }}
        />
      </LanguageProvider>
    );

    fireEvent.click(screen.getByRole("button", { name: "English" }));

    expect(screen.getAllByText("PNEUMONIA").length).toBeGreaterThan(0);
    expect(screen.getByText("NORMAL")).toBeInTheDocument();
  });

  it("8. Sidebar navigation labels and headers translate properly", () => {
    render(
      <LanguageProvider>
        <Sidebar />
      </LanguageProvider>
    );

    expect(screen.getByText("لوحة التحكم")).toBeInTheDocument();
    expect(screen.getByText("تحليل الصور الطبية بالذكاء الاصطناعي")).toBeInTheDocument();
    expect(screen.getByText("سجل التحليلات")).toBeInTheDocument();
    expect(screen.getByText("معلومات النظام")).toBeInTheDocument();
  });

  it("9. Upload validation errors translate properly", () => {
    const onFileSelected = vi.fn();
    const { container } = render(
      <LanguageProvider>
        <UploadDropzone onFileSelected={onFileSelected} />
      </LanguageProvider>
    );

    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;
    const invalidFile = new File(["dummy content"], "report.pdf", { type: "application/pdf" });

    fireEvent.change(fileInput, { target: { files: [invalidFile] } });

    expect(
      screen.getByText(/تنسيق الملف غير مدعوم/i)
    ).toBeInTheDocument();
  });

  it("10. Translation coverage: every key in en exists in ar", () => {
    const enKeys = Object.keys(en);
    const arKeys = Object.keys(ar);

    expect(arKeys.length).toBe(enKeys.length);
    enKeys.forEach((key) => {
      expect(ar[key as keyof typeof en]).toBeDefined();
      expect(ar[key as keyof typeof en].length).toBeGreaterThan(0);
    });
  });
});
