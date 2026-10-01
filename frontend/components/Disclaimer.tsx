"use client";

import React from "react";
import { AlertTriangle, ShieldAlert } from "lucide-react";
import { useLanguage } from "@/lib/i18n";

interface DisclaimerProps {
  variant?: "banner" | "card" | "inline";
  className?: string;
}

export default function Disclaimer({ variant = "card", className = "" }: DisclaimerProps) {
  const { t } = useLanguage();

  if (variant === "inline") {
    return (
      <div className={`flex items-center gap-2 text-xs text-amber-800 bg-amber-50 border border-amber-200/70 px-3 py-1.5 rounded-lg shadow-xs ${className}`}>
        <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
        <span>{t("disclaimer.inline")}</span>
      </div>
    );
  }

  if (variant === "banner") {
    return (
      <div
        className={`bg-amber-50/80 border border-amber-200 rounded-xl px-4 py-3 text-amber-900 text-xs flex items-start gap-3 shadow-xs ${className}`}
      >
        <ShieldAlert className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
        <div className="leading-relaxed">
          <span className="font-bold text-amber-950">{t("disclaimer.regulatoryTitle")}{" "}</span>
          {t("disclaimer.standardText")}
        </div>
      </div>
    );
  }

  return (
    <div
      className={`bg-white border border-amber-200 rounded-2xl p-5 text-xs text-slate-700 space-y-2 shadow-xs ${className}`}
    >
      <div className="flex items-center gap-2 text-amber-900 font-bold text-sm">
        <ShieldAlert className="w-4 h-4 text-amber-600 shrink-0" />
        <span>{t("disclaimer.cardTitle")}</span>
      </div>
      <p className="text-slate-600 leading-relaxed">
        {t("disclaimer.cardBody")}
      </p>
    </div>
  );
}
