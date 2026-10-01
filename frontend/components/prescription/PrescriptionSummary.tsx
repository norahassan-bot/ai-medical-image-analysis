"use client";

import React from "react";
import { Pill, Clock, CheckCircle2, AlertTriangle, Sparkles } from "lucide-react";
import type { PrescriptionUnderstandingResult } from "@/types/api";
import { useLanguage } from "@/lib/i18n";

interface PrescriptionSummaryProps {
  result: PrescriptionUnderstandingResult;
  createdAt?: string;
  className?: string;
}

export default function PrescriptionSummary({
  result,
  createdAt,
  className = "",
}: PrescriptionSummaryProps) {
  const { t, isRTL } = useLanguage();

  const totalMeds = result?.total_medications || result?.medications?.length || 0;
  const hasUncertain = result?.medications?.some(
    (m) => m.medication?.status === "uncertain" || (m.medication?.confidence < 0.50 && m.medication?.confidence > 0)
  );

  const formattedDate = createdAt
    ? new Date(createdAt).toLocaleDateString(isRTL ? "ar-EG" : "en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    : null;

  return (
    <div className={`bg-white rounded-3xl border border-slate-200/90 p-5 sm:p-6 shadow-xs space-y-4 ${className}`}>
      {/* Overview Stat Badges */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-medPink-500 to-medTeal-600 text-white flex items-center justify-center shadow-md">
            <Pill className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs font-bold text-slate-500 uppercase tracking-wider">
              {t("prescription.resultTitle")}
            </div>
            <div className="text-xl sm:text-2xl font-extrabold text-slate-900">
              {totalMeds === 1
                ? t("prescription.detectedMedsCountSingular")
                : t("prescription.detectedMedsCount").replace("{count}", String(totalMeds))}
            </div>
          </div>
        </div>

        {/* Telemetry info */}
        <div className="flex flex-wrap items-center gap-2 text-xs font-mono text-slate-500">
          {formattedDate && (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-slate-50 border border-slate-200 rounded-full">
              <Clock className="w-3.5 h-3.5 text-slate-400" />
              <span>{formattedDate}</span>
            </span>
          )}

          {result?.processing_time_ms !== undefined && (
            <span className="inline-flex items-center gap-1 px-3 py-1 bg-slate-50 border border-slate-200 rounded-full">
              <Sparkles className="w-3.5 h-3.5 text-medTeal-600" />
              <span>{result.processing_time_ms.toFixed(0)} ms</span>
            </span>
          )}
        </div>
      </div>

      {/* Uncertainty warning banner if needed */}
      {hasUncertain && (
        <div className="p-3.5 bg-amber-50 border border-amber-200 rounded-2xl flex items-start gap-2.5 text-xs text-amber-900 shadow-2xs">
          <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
          <div className="leading-relaxed">
            <span className="font-bold">{t("prescription.confidenceUncertain")}: </span>
            <span>{t("prescription.reviewOriginalNotice")}</span>
          </div>
        </div>
      )}
    </div>
  );
}
