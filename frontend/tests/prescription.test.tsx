import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import PrescriptionSafetyDisclaimer from "../components/prescription/PrescriptionSafetyDisclaimer";
import ConfidenceBadge from "../components/prescription/ConfidenceBadge";
import UncertaintyNotice from "../components/prescription/UncertaintyNotice";
import MedicationInformation from "../components/prescription/MedicationInformation";
import PrescriptionInstructions from "../components/prescription/PrescriptionInstructions";
import PrescriptionUploader from "../components/prescription/PrescriptionUploader";
import PrescriptionPreview from "../components/prescription/PrescriptionPreview";
import PrescriptionHistoryTable from "../components/prescription/PrescriptionHistoryTable";
import { LanguageProvider } from "../lib/i18n";
import type {
  MedicationInformationData,
  ParsedPrescriptionInstructions,
  PrescriptionHistoryItem,
} from "../types/api";

const renderWithLang = (ui: React.ReactElement, initialLang: "ar" | "en" = "ar") => {
  localStorage.setItem("medvision_app_language", initialLang);
  return render(
    <LanguageProvider defaultLocale={initialLang}>
      {ui}
    </LanguageProvider>
  );
};

describe("Task 26 — Prescription Reader Frontend Component Suite", () => {
  // 1. Safety Disclaimer
  it("1. renders persistent non-prescribing safety disclaimer banner in Arabic and English", () => {
    const { unmount } = renderWithLang(<PrescriptionSafetyDisclaimer variant="banner" />, "ar");
    expect(screen.getByRole("region")).toBeDefined();
    expect(screen.getByText(/هذه الأداة تساعد في قراءة المعلومات المكتوبة في الروشتة/i)).toBeDefined();
    unmount();

    renderWithLang(<PrescriptionSafetyDisclaimer variant="banner" />, "en");
    expect(screen.getByText(/This tool assists with reading prescription information/i)).toBeDefined();
  });

  // 2. ConfidenceBadge
  it("2. renders accessible confidence badges across high, possible, uncertain, and unmatched states", () => {
    const { rerender } = renderWithLang(<ConfidenceBadge status="confirmed_candidate" confidence={0.95} />, "en");
    expect(screen.getByText(/Confirmed \/ High Confidence/i)).toBeDefined();
    expect(screen.getByText("(95%)")).toBeDefined();

    localStorage.setItem("medvision_app_language", "en");
    rerender(
      <LanguageProvider defaultLocale="en">
        <ConfidenceBadge status="uncertain" confidence={0.42} />
      </LanguageProvider>
    );
    expect(screen.getByText(/Needs Review \/ Unclear/i)).toBeDefined();
    expect(screen.getByText("(42%)")).toBeDefined();
  });

  // 3. Uncertainty Notice
  it("3. renders uncertainty notice with original prescription review advice", () => {
    renderWithLang(
      <UncertaintyNotice rawText="Augm..." matchedName="Augmentin" />,
      "ar"
    );
    expect(screen.getByText("Augm...")).toBeDefined();
    expect(screen.getByText("Augmentin")).toBeDefined();
    expect(screen.getByText(/يرجى مقارنة النتيجة بصورة الروشتة الأصلية/i)).toBeDefined();
  });

  // 4. Medication Information (Educational Facts Only)
  it("4. renders verified educational drug facts without prescribing or diagnostic claims", () => {
    const mockInfo: MedicationInformationData = {
      status: "verified",
      medication_name: "Augmentin",
      generic_name: "Amoxicillin / Clavulanic Acid",
      drug_class: "Antibacterial combination",
      active_ingredients: ["Amoxicillin", "Clavulanate potassium"],
      what_is_it: "Augmentin is an antibacterial combination medication.",
      what_is_it_ar: "أوجمنتين هو مضاد حيوي مركب لمكافحة البكتيريا.",
      general_uses: ["Bacterial respiratory infections"],
      general_uses_ar: ["التهابات الجهاز التنفسي البكتيرية"],
      source: {
        source_name: "RxNorm",
        source_id: "1114195",
      },
    };

    renderWithLang(<MedicationInformation info={mockInfo} />, "ar");
    expect(screen.getByText(/أوجمنتين هو مضاد حيوي مركب لمكافحة البكتيريا/i)).toBeDefined();
    expect(screen.getByText(/التهابات الجهاز التنفسي البكتيرية/i)).toBeDefined();
    expect(screen.getByText(/RxNorm/i)).toBeDefined();
  });

  // 5. Explicit Prescription Instructions Display
  it("5. renders explicit dose, frequency, duration, route, and meal timing directives", () => {
    const mockInstructions: ParsedPrescriptionInstructions = {
      dose: {
        value: 1,
        unit: "tablet",
        raw_text: "1 tab",
        confidence: 0.95,
        status: "parsed",
      },
      frequency: {
        frequency_type: "interval",
        times_per_day: 2,
        interval_hours: 12,
        raw_text: "every 12 hours",
        confidence: 0.94,
        status: "parsed",
      },
      duration: {
        value: 5,
        unit: "days",
        raw_text: "for 5 days",
        confidence: 0.92,
        status: "parsed",
      },
      food_timing: {
        timing: "after_food",
        raw_text: "after food",
        confidence: 0.90,
        status: "parsed",
      },
      prn: false,
      raw_instruction_text: "1 tab every 12 hours for 5 days after food",
    };

    renderWithLang(<PrescriptionInstructions instructions={mockInstructions} />, "ar");
    expect(screen.getByText(/1 قرص/i)).toBeDefined();
    expect(screen.getByText(/كل 12 ساعة/i)).toBeDefined();
    expect(screen.getByText(/لمدة 5 أيام/i)).toBeDefined();
    expect(screen.getByText(/بعد الأكل/i)).toBeDefined();
  });

  // 6. Missing Directives remain unknown
  it("6. renders clear unstated notices when dose or frequency are absent", () => {
    const emptyInstructions: ParsedPrescriptionInstructions = {
      dose: null,
      frequency: null,
      duration: null,
      food_timing: null,
    };

    renderWithLang(<PrescriptionInstructions instructions={emptyInstructions} />, "ar");
    expect(screen.getByText(/الجرعة: غير واضحة \/ غير موجودة في النص المقروء/i)).toBeDefined();
    expect(screen.getByText(/عدد مرات الاستخدام: غير واضح \/ غير مذكور/i)).toBeDefined();
    expect(screen.getByText(/المدة: غير واضحة \/ غير مذكورة/i)).toBeDefined();
  });

  // 7. Prescription Uploader File Validation
  it("7. validates accepted and rejected file types in uploader", () => {
    const onSelect = vi.fn();
    renderWithLang(<PrescriptionUploader onFileSelected={onSelect} />, "en");

    const input = document.getElementById("prescription-file-input") as HTMLInputElement;
    expect(input).toBeDefined();

    // Valid file
    const validFile = new File(["valid image"], "rx.png", { type: "image/png" });
    fireEvent.change(input, { target: { files: [validFile] } });
    expect(onSelect).toHaveBeenCalledWith(validFile);
  });

  // 8. Prescription Preview & Analyze CTA
  it("8. renders file preview with analyze CTA button", () => {
    const onRemove = vi.fn();
    const onAnalyze = vi.fn();
    const mockFile = new File(["dummy content"], "prescription_scan.jpg", { type: "image/jpeg" });

    // Mock URL.createObjectURL
    global.URL.createObjectURL = vi.fn(() => "blob:mock-preview-url");
    global.URL.revokeObjectURL = vi.fn();

    renderWithLang(
      <PrescriptionPreview
        file={mockFile}
        onRemove={onRemove}
        onAnalyze={onAnalyze}
      />,
      "ar"
    );

    expect(screen.getByText("prescription_scan.jpg")).toBeDefined();
    const analyzeBtn = screen.getByRole("button", { name: /تحليل الروشتة/i });
    fireEvent.click(analyzeBtn);
    expect(onAnalyze).toHaveBeenCalled();
  });

  // 9. Prescription History Table
  it("9. renders history table records and empty state cleanly", () => {
    const mockHistory: PrescriptionHistoryItem[] = [
      {
        analysis_id: "rx-uuid-001",
        created_at: new Date().toISOString(),
        filename: "doctor_prescription.png",
        total_medications: 2,
        status: "completed",
      },
    ];

    const { rerender } = renderWithLang(<PrescriptionHistoryTable items={mockHistory} />, "ar");
    expect(screen.getByText("doctor_prescription.png")).toBeDefined();
    expect(screen.getByText(/تم التعرف على 2 أدوية/i)).toBeDefined();

    rerender(
      <LanguageProvider initialLanguage="ar">
        <PrescriptionHistoryTable items={[]} />
      </LanguageProvider>
    );
    expect(screen.getByText(/لم يتم تسجيل أي روشتات حتى الآن/i)).toBeDefined();
  });
});
