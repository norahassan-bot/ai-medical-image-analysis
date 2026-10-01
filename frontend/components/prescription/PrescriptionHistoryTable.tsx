"use client";

import React from "react";
import Link from "next/link";
import { Pill, Clock, ArrowRight, CheckCircle2, AlertTriangle, Eye, FileSpreadsheet } from "lucide-react";
import type { PrescriptionHistoryItem } from "@/types/api";
import { useLanguage } from "@/lib/i18n";

interface PrescriptionHistoryTableProps {
  items: PrescriptionHistoryItem[];
  isAdminView?: boolean;
  className?: string;
}

export default function PrescriptionHistoryTable({
  items,
  isAdminView = false,
  className = "",
}: PrescriptionHistoryTableProps) {
  const { t, isRTL } = useLanguage();

  if (!items || items.length === 0) {
    return (
      <div className={`p-8 sm:p-12 text-center bg-white rounded-3xl border border-slate-200 shadow-xs space-y-3 ${className}`}>
        <div className="w-14 h-14 rounded-2xl bg-slate-100 border border-slate-200 flex items-center justify-center mx-auto text-slate-400">
          <FileSpreadsheet className="w-7 h-7" />
        </div>
        <h3 className="text-sm sm:text-base font-bold text-slate-800">
          {t("prescription.noHistory")}
        </h3>
        <p className="text-xs text-slate-500 max-w-sm mx-auto">
          {t("prescription.uploadSubtitle")}
        </p>
        <div className="pt-2">
          <Link
            href="/user/prescription"
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-medPink-500 to-medTeal-600 text-white rounded-xl text-xs font-bold shadow-sm hover:shadow-md transition"
          >
            <Pill className="w-4 h-4" />
            <span>{t("dashboard.startPrescription")}</span>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white rounded-3xl border border-slate-200/90 shadow-xs overflow-hidden ${className}`}>
      <div className="divide-y divide-slate-100">
        {items.map((item, idx) => {
          const formattedDate = new Date(item.created_at).toLocaleDateString(isRTL ? "ar-EG" : "en-US", {
            year: "numeric",
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
          });

          const totalMeds = item.total_medications || item.result?.total_medications || item.result?.medications?.length || 0;
          const hasUncertain = item.result?.medications?.some(
            (m) => m.medication?.status === "uncertain" || (m.medication?.confidence < 0.50 && m.medication?.confidence > 0)
          );

          const resultLink = `/user/prescription/result/${item.analysis_id}`;

          return (
            <div
              key={item.analysis_id || idx}
              className="p-4 sm:p-5 hover:bg-slate-50/70 transition flex flex-col sm:flex-row sm:items-center justify-between gap-4"
            >
              {/* Left Column: Icon & Metadata */}
              <div className="flex items-center gap-3.5 min-w-0">
                <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-2xl bg-gradient-to-tr from-medPink-50 via-white to-medTeal-50 border border-slate-200 flex items-center justify-center text-medTeal-600 shrink-0 shadow-2xs">
                  <Pill className="w-5 h-5 sm:w-6 sm:h-6" />
                </div>

                <div className="min-w-0 space-y-0.5">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-xs sm:text-sm font-extrabold text-slate-900 truncate">
                      {item.filename || `Prescription #${item.analysis_id.slice(0, 8)}`}
                    </span>
                    {hasUncertain ? (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-amber-50 border border-amber-200 text-amber-800 text-[10px] font-bold">
                        <AlertTriangle className="w-3 h-3 text-amber-600" />
                        <span>{t("prescription.confidenceUncertain")}</span>
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-emerald-50 border border-emerald-200 text-emerald-800 text-[10px] font-bold">
                        <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                        <span>{t("prescription.confidenceHigh")}</span>
                      </span>
                    )}
                  </div>

                  <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500 font-mono">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3 text-slate-400" />
                      <span>{formattedDate}</span>
                    </span>
                    <span>•</span>
                    <span className="font-bold text-slate-700">
                      {totalMeds === 1
                        ? t("prescription.detectedMedsCountSingular")
                        : t("prescription.detectedMedsCount").replace("{count}", String(totalMeds))}
                    </span>
                  </div>
                </div>
              </div>

              {/* Right Column: Details CTA Action */}
              <div className="flex items-center gap-2 self-end sm:self-auto shrink-0">
                <Link
                  href={resultLink}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-medTeal-50 hover:bg-medTeal-100 text-medTeal-800 text-xs font-bold border border-medTeal-200/80 transition shadow-2xs"
                >
                  <Eye className="w-3.5 h-3.5" />
                  <span>{isRTL ? "عرض التفاصيل" : "View Details"}</span>
                  <ArrowRight className={`w-3.5 h-3.5 ${isRTL ? "rotate-180" : ""}`} />
                </Link>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
