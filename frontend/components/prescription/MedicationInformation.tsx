"use client";

import React from "react";
import { BookOpen, ShieldCheck, AlertCircle, ExternalLink, Pill, Activity } from "lucide-react";
import type { MedicationInformationData } from "@/types/api";
import { useLanguage } from "@/lib/i18n";

interface MedicationInformationProps {
  info: MedicationInformationData;
  className?: string;
}

export default function MedicationInformation({ info, className = "" }: MedicationInformationProps) {
  const { t, isRTL } = useLanguage();

  const isVerified = info?.status === "verified";
  const isUnavailable = info?.status === "provider_unavailable";

  if (!info || (!isVerified && isUnavailable)) {
    return (
      <div className={`p-4 bg-slate-50 border border-slate-200 rounded-2xl text-xs text-slate-600 flex items-start gap-2.5 ${className}`}>
        <AlertCircle className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
        <div>
          <div className="font-bold text-slate-700">{t("prescription.aboutMedication")}</div>
          <p className="mt-0.5 text-slate-500">{t("prescription.providerUnavailable")}</p>
        </div>
      </div>
    );
  }

  if (!isVerified) {
    return (
      <div className={`p-4 bg-slate-50 border border-slate-200 rounded-2xl text-xs text-slate-600 flex items-start gap-2.5 ${className}`}>
        <AlertCircle className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
        <div>
          <div className="font-bold text-slate-700">{t("prescription.aboutMedication")}</div>
          <p className="mt-0.5 text-slate-500">{t("prescription.unverifiedInfo")}</p>
        </div>
      </div>
    );
  }

  const whatIsItText = isRTL ? (info.what_is_it_ar || info.what_is_it) : (info.what_is_it || info.what_is_it_ar);
  const generalUsesList = isRTL ? (info.general_uses_ar?.length ? info.general_uses_ar : info.general_uses) : (info.general_uses?.length ? info.general_uses : info.general_uses_ar);

  return (
    <div className={`p-4 sm:p-5 bg-gradient-to-br from-medTeal-50/60 via-white to-sky-50/40 border border-medTeal-200/80 rounded-2xl space-y-3.5 shadow-2xs ${className}`}>
      {/* Header with Verified Badge & Source */}
      <div className="flex flex-wrap items-center justify-between gap-2 pb-2.5 border-b border-medTeal-100">
        <div className="flex items-center gap-2 text-xs font-extrabold text-medTeal-900">
          <BookOpen className="w-4 h-4 text-medTeal-600" />
          <span>{t("prescription.aboutMedication")}</span>
        </div>

        <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-medTeal-100/80 border border-medTeal-200 text-[11px] font-bold text-medTeal-800">
          <ShieldCheck className="w-3.5 h-3.5 text-medTeal-600" />
          <span>{info.source?.source_name || t("prescription.verifiedInfo")}</span>
          {info.source?.source_id && (
            <span className="font-mono text-[10px] text-medTeal-600">#{info.source.source_id}</span>
          )}
        </div>
      </div>

      {/* Drug Class & Active Ingredients */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
        {info.drug_class && (
          <div className="p-2.5 bg-white/90 border border-slate-200/70 rounded-xl">
            <span className="text-slate-500 block text-[11px] font-medium">{isRTL ? "الفئة الدوائية" : "Drug Class"}</span>
            <span className="font-bold text-slate-800">{info.drug_class}</span>
          </div>
        )}

        {info.active_ingredients && info.active_ingredients.length > 0 && (
          <div className="p-2.5 bg-white/90 border border-slate-200/70 rounded-xl">
            <span className="text-slate-500 block text-[11px] font-medium">{t("prescription.genericName")}</span>
            <span className="font-bold text-slate-800">{info.active_ingredients.join(" + ")}</span>
          </div>
        )}
      </div>

      {/* What is this medication */}
      {whatIsItText && (
        <div className="space-y-1">
          <div className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
            <Pill className="w-3.5 h-3.5 text-medPink-600" />
            <span>{t("prescription.whatIsIt")}</span>
          </div>
          <p className="text-xs text-slate-600 leading-relaxed bg-white/80 p-3 rounded-xl border border-slate-200/60">
            {whatIsItText}
          </p>
        </div>
      )}

      {/* General uses */}
      {generalUsesList && generalUsesList.length > 0 && (
        <div className="space-y-1.5 pt-1">
          <div className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
            <Activity className="w-3.5 h-3.5 text-medTeal-600" />
            <span>{t("prescription.generalUses")}</span>
          </div>
          <p className="text-[11px] text-slate-500 italic">
            {t("prescription.generalUsesPrefix")}
          </p>
          <ul className="space-y-1 text-xs text-slate-700 bg-white/80 p-3 rounded-xl border border-slate-200/60">
            {generalUsesList.map((useStr, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-medTeal-500 mt-1.5 shrink-0" />
                <span className="leading-relaxed">{useStr}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
