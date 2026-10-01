"use client";

import React from "react";
import { AlertTriangle, Eye } from "lucide-react";
import { useLanguage } from "@/lib/i18n";

interface UncertaintyNoticeProps {
  rawText?: string;
  matchedName?: string | null;
  uncertainFields?: string[];
  className?: string;
}

export default function UncertaintyNotice({
  rawText,
  matchedName,
  uncertainFields = [],
  className = "",
}: UncertaintyNoticeProps) {
  const { t, isRTL } = useLanguage();

  return (
    <div
      className={`p-3.5 sm:p-4 bg-amber-50/90 border border-amber-200 rounded-2xl space-y-2 text-xs text-amber-950 shadow-2xs ${className}`}
      role="alert"
    >
      <div className="flex items-center gap-2 font-bold text-amber-900">
        <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
        <span>{t("prescription.confidenceUncertain")}</span>
      </div>

      <div className="space-y-1 text-slate-700 leading-relaxed">
        {rawText && (
          <div>
            <span className="font-semibold text-slate-900">{t("prescription.rawTextLabel")}</span>
            <code className="px-1.5 py-0.5 bg-white border border-amber-200/80 rounded font-mono text-[11px] text-amber-900">
              {rawText}
            </code>
          </div>
        )}
        {matchedName && (
          <div>
            <span className="font-semibold text-slate-900">{t("prescription.possibleMedLabel")}</span>
            <span className="font-bold text-slate-900">{matchedName}</span>
          </div>
        )}
        <div className="pt-1 flex items-center gap-1.5 text-amber-800 font-medium">
          <Eye className="w-3.5 h-3.5 shrink-0 text-amber-600" />
          <span>{t("prescription.reviewOriginalNotice")}</span>
        </div>
      </div>
    </div>
  );
}
