"use client";

import React from "react";
import { ShieldAlert, AlertTriangle } from "lucide-react";
import { useLanguage } from "@/lib/i18n";

interface PrescriptionSafetyDisclaimerProps {
  variant?: "banner" | "card" | "compact";
  className?: string;
}

export default function PrescriptionSafetyDisclaimer({
  variant = "card",
  className = "",
}: PrescriptionSafetyDisclaimerProps) {
  const { t, isRTL } = useLanguage();

  if (variant === "compact") {
    return (
      <div
        className={`flex items-center gap-2 text-xs text-amber-900 bg-amber-50/90 border border-amber-200/80 px-3 py-2 rounded-xl shadow-xs ${className}`}
        role="note"
        aria-label={t("prescription.safetyDisclaimerTitle")}
      >
        <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
        <p className="leading-relaxed">{t("prescription.safetyDisclaimer")}</p>
      </div>
    );
  }

  if (variant === "banner") {
    return (
      <div
        className={`bg-amber-50/90 border border-amber-200 rounded-2xl p-4 text-amber-950 text-xs flex items-start gap-3 shadow-xs ${className}`}
        role="region"
        aria-label={t("prescription.safetyDisclaimerTitle")}
      >
        <ShieldAlert className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
        <div className="space-y-1 leading-relaxed">
          <div className="font-bold text-amber-900 text-sm">
            {t("prescription.safetyDisclaimerTitle")}
          </div>
          <p className="text-amber-800">{t("prescription.safetyDisclaimer")}</p>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`bg-gradient-to-r from-amber-50/80 via-white to-amber-50/60 border border-amber-200/90 rounded-2xl p-5 text-xs text-slate-700 space-y-2 shadow-xs ${className}`}
      role="region"
      aria-label={t("prescription.safetyDisclaimerTitle")}
    >
      <div className="flex items-center gap-2 text-amber-950 font-bold text-sm">
        <ShieldAlert className="w-4 h-4 text-amber-600 shrink-0" />
        <span>{t("prescription.safetyDisclaimerTitle")}</span>
      </div>
      <p className="text-slate-600 leading-relaxed">
        {t("prescription.safetyDisclaimer")}
      </p>
    </div>
  );
}
