"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Pill, Activity, ArrowRight, History, Sparkles, AlertCircle } from "lucide-react";
import { analyzePrescription } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import PrescriptionUploader from "@/components/prescription/PrescriptionUploader";
import PrescriptionPreview from "@/components/prescription/PrescriptionPreview";
import PrescriptionProcessing from "@/components/prescription/PrescriptionProcessing";
import PrescriptionSafetyDisclaimer from "@/components/prescription/PrescriptionSafetyDisclaimer";

export default function PrescriptionReaderPage() {
  const router = useRouter();
  const { t, isRTL } = useLanguage();

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleFileSelected = (file: File) => {
    setSelectedFile(file);
    setErrorMessage(null);
  };

  const handleRemoveFile = () => {
    setSelectedFile(null);
    setErrorMessage(null);
  };

  const handleAnalyze = async () => {
    if (!selectedFile || isAnalyzing) return;

    setIsAnalyzing(true);
    setErrorMessage(null);

    try {
      const response = await analyzePrescription(selectedFile);
      if (response && response.analysis_id) {
        router.push(`/user/prescription/result/${response.analysis_id}`);
      } else {
        throw new Error("Invalid response format from prescription analysis service.");
      }
    } catch (err: any) {
      console.error("Prescription analysis failed:", err);
      setErrorMessage(
        err.message ||
          (isRTL
            ? "تعذر تحليل الروشتة حاليًا. يرجى التأكد من وضوح الصورة والمحاولة مرة أخرى."
            : "Unable to analyze the prescription right now. Please verify image clarity and try again.")
      );
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto w-full">
      {/* 1. Header Banner */}
      <div className="p-5 sm:p-8 bg-gradient-to-r from-medPink-50 via-white to-medTeal-50 rounded-3xl border border-slate-200 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-5 relative overflow-hidden">
        <div className="space-y-2 relative z-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-medPink-100/80 border border-medPink-200 rounded-full text-xs font-bold text-medPink-900">
            <Pill className="w-3.5 h-3.5" />
            <span>{t("nav.prescription")}</span>
          </div>

          <h1 className="text-xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            {t("prescription.uploadTitle")}
          </h1>
          <p className="text-xs sm:text-sm text-slate-600 max-w-2xl leading-relaxed">
            {t("prescription.uploadSubtitle")}
          </p>
        </div>

        {/* Quick link to history */}
        <div className="flex items-center gap-2 relative z-10 shrink-0">
          <Link
            href="/user/prescription/history"
            className="inline-flex items-center gap-1.5 px-4 py-2.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-xl text-xs font-bold shadow-2xs transition"
          >
            <History className="w-4 h-4 text-medTeal-600" />
            <span>{t("prescription.viewHistory")}</span>
          </Link>
        </div>
      </div>

      {/* 2. Persistent Non-Prescribing Safety Disclaimer */}
      <PrescriptionSafetyDisclaimer variant="banner" />

      {/* 3. Error Alert if analysis failed */}
      {errorMessage && (
        <div
          className="p-4 bg-rose-50 border border-rose-200 rounded-2xl flex items-start gap-3 text-xs text-rose-900 shadow-2xs"
          role="alert"
        >
          <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <div className="font-bold">
              {isRTL ? "فشل تحليل الروشتة" : "Prescription Analysis Error"}
            </div>
            <p>{errorMessage}</p>
          </div>
        </div>
      )}

      {/* 4. Processing State OR Upload / Preview Screen */}
      {isAnalyzing ? (
        <PrescriptionProcessing />
      ) : selectedFile ? (
        <PrescriptionPreview
          file={selectedFile}
          onRemove={handleRemoveFile}
          onAnalyze={handleAnalyze}
          isAnalyzing={isAnalyzing}
        />
      ) : (
        <PrescriptionUploader onFileSelected={handleFileSelected} />
      )}
    </div>
  );
}
