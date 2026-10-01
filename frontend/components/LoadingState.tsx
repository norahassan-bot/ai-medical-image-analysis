"use client";

import React from "react";
import { Loader2, BrainCircuit } from "lucide-react";
import { useLanguage } from "@/lib/i18n";

interface LoadingStateProps {
  message?: string;
  subMessage?: string;
  className?: string;
}

export default function LoadingState({
  message,
  subMessage,
  className = "",
}: LoadingStateProps) {
  const { t } = useLanguage();
  const finalMessage = message || t("common.loading");

  return (
    <div
      className={`bg-white border border-slate-200 rounded-2xl p-10 text-center flex flex-col items-center justify-center space-y-4 max-w-md mx-auto shadow-xs ${className}`}
    >
      <div className="relative">
        <div className="w-16 h-16 rounded-2xl bg-medPink-50 border border-medPink-200 flex items-center justify-center text-medPink-500 shadow-xs">
          <BrainCircuit className="w-8 h-8 animate-pulse" />
        </div>
        <Loader2 className="w-6 h-6 text-medTeal-500 animate-spin absolute -top-2 -right-2 rtl:-right-auto rtl:-left-2" />
      </div>

      <div className="space-y-1">
        <h4 className="text-sm font-bold text-slate-900">{finalMessage}</h4>
        {subMessage && (
          <p className="text-xs text-slate-500 max-w-xs">{subMessage}</p>
        )}
      </div>

      {/* Indeterminate loader bar */}
      <div className="w-48 bg-slate-100 rounded-full h-1.5 overflow-hidden border border-slate-200">
        <div className="h-full bg-gradient-to-r from-medPink-400 to-medTeal-400 rounded-full animate-pulse w-2/3 mx-auto" />
      </div>
    </div>
  );
}
