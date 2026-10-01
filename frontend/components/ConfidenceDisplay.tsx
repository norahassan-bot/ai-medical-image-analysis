"use client";

import React from "react";
import { Percent, CheckCircle2, AlertCircle } from "lucide-react";
import { useLanguage } from "@/lib/i18n";

interface ConfidenceDisplayProps {
  prediction: string;
  confidence: number;
  probabilities?: Record<string, number>;
  className?: string;
}

export default function ConfidenceDisplay({
  prediction,
  confidence,
  probabilities,
  className = "",
}: ConfidenceDisplayProps) {
  const { t } = useLanguage();
  const percent = Math.round(confidence * 100);
  const isPneumonia = prediction.toUpperCase() === "PNEUMONIA";

  const normalProb = probabilities?.NORMAL ?? (isPneumonia ? 1 - confidence : confidence);
  const pneuProb = probabilities?.PNEUMONIA ?? (isPneumonia ? confidence : 1 - confidence);

  return (
    <div className={`bg-white border border-slate-200 rounded-2xl p-5 space-y-4 shadow-xs ${className}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-slate-800 font-bold text-sm">
          <Percent className="w-4 h-4 text-medTeal-600" />
          <span>{t("confidence.title")}</span>
        </div>
        <span className="text-xl font-black font-mono text-slate-900">
          {percent}%
        </span>
      </div>

      {/* Main Confidence Bar */}
      <div className="w-full bg-slate-100 rounded-full h-3 overflow-hidden border border-slate-200">
        <div
          className={`h-full transition-all duration-700 rounded-full ${
            isPneumonia
              ? "bg-gradient-to-r from-medTeal-400 to-medPink-400"
              : "bg-gradient-to-r from-medTeal-300 to-medTeal-500"
          }`}
          style={{ width: `${percent}%` }}
        />
      </div>

      {/* Probability Distribution Breakdown */}
      <div className="pt-2 border-t border-slate-200 grid grid-cols-2 gap-3 text-xs">
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-3 flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-slate-600 font-medium">
            <CheckCircle2 className="w-3.5 h-3.5 text-medTeal-600 shrink-0" />
            <span>{t("confidence.normal")}</span>
          </div>
          <span className="font-mono font-bold text-slate-800">
            {(normalProb * 100).toFixed(1)}%
          </span>
        </div>

        <div className="bg-slate-50 border border-slate-200 rounded-xl p-3 flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-slate-600 font-medium">
            <AlertCircle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
            <span>{t("confidence.pneumonia")}</span>
          </div>
          <span className="font-mono font-bold text-slate-800">
            {(pneuProb * 100).toFixed(1)}%
          </span>
        </div>
      </div>
    </div>
  );
}
