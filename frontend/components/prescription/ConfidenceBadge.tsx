"use client";

import React from "react";
import { CheckCircle2, AlertTriangle, HelpCircle, Info } from "lucide-react";
import { useLanguage } from "@/lib/i18n";

interface ConfidenceBadgeProps {
  status?: string;
  confidence?: number;
  className?: string;
}

export default function ConfidenceBadge({
  status = "confirmed_candidate",
  confidence,
  className = "",
}: ConfidenceBadgeProps) {
  const { t } = useLanguage();

  const isConfirmed = status === "confirmed_candidate" || (confidence !== undefined && confidence >= 0.75);
  const isPossible = status === "possible_candidate" || (confidence !== undefined && confidence >= 0.50 && confidence < 0.75);
  const isUncertain = status === "uncertain" || (confidence !== undefined && confidence < 0.50 && confidence > 0);
  const isUnmatched = status === "unmatched" || status === "unverified" || (confidence !== undefined && confidence === 0);

  if (isConfirmed) {
    return (
      <span
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-50 border border-emerald-200 text-emerald-800 shadow-2xs ${className}`}
        role="status"
        aria-label={t("prescription.confidenceHigh")}
      >
        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
        <span>{t("prescription.confidenceHigh")}</span>
        {confidence !== undefined && (
          <span className="font-mono text-[10px] text-emerald-600">({Math.round(confidence * 100)}%)</span>
        )}
      </span>
    );
  }

  if (isPossible) {
    return (
      <span
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-sky-50 border border-sky-200 text-sky-800 shadow-2xs ${className}`}
        role="status"
        aria-label={t("prescription.confidencePossible")}
      >
        <Info className="w-3.5 h-3.5 text-sky-600" />
        <span>{t("prescription.confidencePossible")}</span>
        {confidence !== undefined && (
          <span className="font-mono text-[10px] text-sky-600">({Math.round(confidence * 100)}%)</span>
        )}
      </span>
    );
  }

  if (isUncertain) {
    return (
      <span
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-amber-50 border border-amber-200 text-amber-800 shadow-2xs ${className}`}
        role="status"
        aria-label={t("prescription.confidenceUncertain")}
      >
        <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
        <span>{t("prescription.confidenceUncertain")}</span>
        {confidence !== undefined && (
          <span className="font-mono text-[10px] text-amber-600">({Math.round(confidence * 100)}%)</span>
        )}
      </span>
    );
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-slate-100 border border-slate-200 text-slate-700 shadow-2xs ${className}`}
      role="status"
      aria-label={t("prescription.confidenceUnmatched")}
    >
      <HelpCircle className="w-3.5 h-3.5 text-slate-500" />
      <span>{t("prescription.confidenceUnmatched")}</span>
    </span>
  );
}
