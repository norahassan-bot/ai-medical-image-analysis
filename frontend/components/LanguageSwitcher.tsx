"use client";

import React from "react";
import { Globe } from "lucide-react";
import { useLanguage } from "@/lib/i18n";

export default function LanguageSwitcher() {
  const { language, setLanguage, t } = useLanguage();

  return (
    <div
      className="inline-flex items-center bg-slate-100/90 border border-slate-200 rounded-xl p-0.5 sm:p-1 shadow-inner shrink-0"
      role="group"
      aria-label={t("lang.switcher")}
    >
      <div className="hidden xs:flex items-center px-1.5 text-slate-400">
        <Globe className="w-3.5 h-3.5 text-medTeal-500" />
      </div>

      <button
        type="button"
        onClick={() => setLanguage("ar")}
        className={`px-2 sm:px-2.5 py-0.5 sm:py-1 text-[11px] sm:text-xs font-semibold rounded-lg transition-all duration-200 ${
          language === "ar"
            ? "bg-medPink-400 text-white font-bold shadow-sm"
            : "text-slate-600 hover:text-slate-900 hover:bg-white/60"
        }`}
        aria-pressed={language === "ar"}
        aria-label="العربية"
      >
        العربية
      </button>

      <span className="text-slate-300 text-xs px-0.5 select-none">|</span>

      <button
        type="button"
        onClick={() => setLanguage("en")}
        className={`px-2 sm:px-2.5 py-0.5 sm:py-1 text-[11px] sm:text-xs font-semibold rounded-lg transition-all duration-200 ${
          language === "en"
            ? "bg-medPink-400 text-white font-bold shadow-sm"
            : "text-slate-600 hover:text-slate-900 hover:bg-white/60"
        }`}
        aria-pressed={language === "en"}
        aria-label="English"
      >
        English
      </button>
    </div>
  );
}
