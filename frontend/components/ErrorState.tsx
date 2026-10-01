"use client";

import React from "react";
import { AlertCircle, RefreshCw } from "lucide-react";
import { useLanguage } from "@/lib/i18n";

interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  className?: string;
}

export default function ErrorState({
  title,
  message,
  onRetry,
  className = "",
}: ErrorStateProps) {
  const { t } = useLanguage();
  const finalTitle = title || t("common.error");

  return (
    <div
      className={`bg-rose-50 border border-rose-200 rounded-2xl p-6 text-slate-800 space-y-3 max-w-xl mx-auto shadow-xs ${className}`}
    >
      <div className="flex items-center gap-3 text-rose-700 font-bold text-sm">
        <AlertCircle className="w-5 h-5 shrink-0" />
        <span>{finalTitle}</span>
      </div>

      <p className="text-xs text-rose-950 leading-relaxed bg-white p-3 rounded-xl border border-rose-200 font-mono shadow-inner">
        {message}
      </p>

      {onRetry && (
        <div className="pt-2 flex justify-end">
          <button
            onClick={onRetry}
            className="inline-flex items-center gap-2 px-4 py-2 bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 rounded-xl text-xs font-semibold transition shadow-xs"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>{t("common.tryAgain")}</span>
          </button>
        </div>
      )}
    </div>
  );
}
