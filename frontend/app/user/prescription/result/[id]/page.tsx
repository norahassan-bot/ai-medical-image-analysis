"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  Pill,
  ArrowLeft,
  ArrowRight,
  RefreshCw,
  FileImage,
  History,
  AlertCircle,
  PlusCircle,
  FileSpreadsheet,
} from "lucide-react";
import { getPrescriptionDetail, getPrescriptionArtifactUrl } from "@/lib/api";
import type { PrescriptionAnalysisResponse } from "@/types/api";
import { useLanguage } from "@/lib/i18n";
import PrescriptionSummary from "@/components/prescription/PrescriptionSummary";
import PrescriptionMedicationCard from "@/components/prescription/PrescriptionMedicationCard";
import PrescriptionImageViewer from "@/components/prescription/PrescriptionImageViewer";
import PrescriptionSafetyDisclaimer from "@/components/prescription/PrescriptionSafetyDisclaimer";

export default function PrescriptionResultDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { t, isRTL } = useLanguage();

  const analysisId = params?.id as string;

  const [data, setData] = useState<PrescriptionAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!analysisId) return;

    let isMounted = true;
    setLoading(true);
    setError(null);

    getPrescriptionDetail(analysisId)
      .then((res) => {
        if (isMounted) {
          setData(res);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          console.error("Failed to fetch prescription analysis detail:", err);
          setError(
            err.message ||
              (isRTL
                ? "تعذر تحميل تفاصيل الروشتة. يرجى التحقق من المعرف والمحاولة مجددًا."
                : "Failed to load prescription details. Please verify the ID and try again.")
          );
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [analysisId, isRTL]);

  if (loading) {
    return (
      <div className="p-12 text-center bg-white rounded-3xl border border-slate-200 shadow-xs max-w-xl mx-auto space-y-3">
        <RefreshCw className="w-8 h-8 text-medTeal-600 animate-spin mx-auto" />
        <h3 className="text-sm sm:text-base font-bold text-slate-800">
          {t("common.loading")}
        </h3>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-8 sm:p-12 text-center bg-white rounded-3xl border border-rose-200 shadow-xs max-w-xl mx-auto space-y-4">
        <div className="w-12 h-12 rounded-2xl bg-rose-50 border border-rose-200 flex items-center justify-center mx-auto text-rose-600">
          <AlertCircle className="w-6 h-6" />
        </div>
        <div className="space-y-1">
          <h3 className="text-base font-bold text-slate-900">
            {isRTL ? "خطأ في تحميل الروشتة" : "Prescription Load Error"}
          </h3>
          <p className="text-xs text-slate-500">{error || "Record not found"}</p>
        </div>
        <div className="pt-2">
          <Link
            href="/user/prescription"
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-medTeal-600 text-white rounded-xl text-xs font-bold shadow-xs hover:bg-medTeal-700 transition"
          >
            <ArrowLeft className={`w-4 h-4 ${isRTL ? "rotate-180" : ""}`} />
            <span>{t("prescription.backToReader")}</span>
          </Link>
        </div>
      </div>
    );
  }

  const medications = data.result?.medications || [];
  const imageUrl = getPrescriptionArtifactUrl(data.analysis_id, "image");

  return (
    <div className="space-y-6 max-w-6xl mx-auto w-full">
      {/* 1. Header Navigation Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-1">
        <div className="flex items-center gap-3">
          <Link
            href="/user/prescription"
            className="p-2.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-2xl shadow-2xs transition"
            aria-label={t("prescription.backToReader")}
          >
            <ArrowLeft className={`w-4 h-4 ${isRTL ? "rotate-180" : ""}`} />
          </Link>
          <div>
            <h1 className="text-lg sm:text-2xl font-extrabold text-slate-900 tracking-tight">
              {t("prescription.resultTitle")}
            </h1>
            <p className="text-xs text-slate-500 font-mono">
              ID: {data.analysis_id}
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-2.5">
          <Link
            href="/user/prescription"
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-medPink-500 to-medTeal-600 hover:from-medPink-600 hover:to-medTeal-700 text-white rounded-xl text-xs font-bold shadow-2xs transition"
          >
            <PlusCircle className="w-4 h-4" />
            <span>{t("prescription.analyzeAnother")}</span>
          </Link>

          <Link
            href="/user/prescription/history"
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-xl text-xs font-bold shadow-2xs transition"
          >
            <History className="w-4 h-4 text-medTeal-600" />
            <span>{t("prescription.viewHistory")}</span>
          </Link>
        </div>
      </div>

      {/* 2. Persistent Safety Disclaimer */}
      <PrescriptionSafetyDisclaimer variant="banner" />

      {/* 3. Summary Statistics Card */}
      <PrescriptionSummary
        result={data.result}
        createdAt={data.created_at}
      />

      {/* 4. Main Two-Column Layout on Desktop */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Original Prescription Image Viewer */}
        <div className="lg:col-span-5 space-y-4 lg:sticky lg:top-6">
          <PrescriptionImageViewer
            imageUrl={imageUrl}
            filename={data.filename || "Prescription Scan"}
          />
        </div>

        {/* Right Column: Detected Medication Cards */}
        <div className="lg:col-span-7 space-y-5">
          {medications.length === 0 ? (
            <div className="p-8 text-center bg-white rounded-3xl border border-slate-200 shadow-xs space-y-2">
              <Pill className="w-8 h-8 text-slate-400 mx-auto" />
              <h3 className="text-sm font-bold text-slate-800">
                {t("prescription.noMedsDetected")}
              </h3>
            </div>
          ) : (
            medications.map((medItem, idx) => (
              <PrescriptionMedicationCard
                key={medItem.region_id || idx}
                item={medItem}
                index={idx}
              />
            ))
          )}
        </div>
      </div>
    </div>
  );
}
