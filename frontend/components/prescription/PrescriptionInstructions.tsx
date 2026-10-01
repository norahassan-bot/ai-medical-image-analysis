"use client";

import React from "react";
import { FileText, Clock, Calendar, Utensils, Compass, AlertCircle, CheckCircle2 } from "lucide-react";
import type { ParsedPrescriptionInstructions } from "@/types/api";
import { useLanguage } from "@/lib/i18n";

interface PrescriptionInstructionsProps {
  instructions?: ParsedPrescriptionInstructions | null;
  className?: string;
}

export default function PrescriptionInstructions({
  instructions,
  className = "",
}: PrescriptionInstructionsProps) {
  const { t, isRTL } = useLanguage();

  const dose = instructions?.dose;
  const frequency = instructions?.frequency;
  const duration = instructions?.duration;
  const route = instructions?.route;
  const foodTiming = instructions?.food_timing;
  const isPrn = instructions?.prn || frequency?.is_prn;

  // Helper for frequency display text
  const formatFrequency = () => {
    if (!frequency) return t("prescription.missingFrequency");
    if (frequency.status === "uncertain") return t("prescription.unclearField");
    if (frequency.frequency_type === "as_needed" || frequency.is_prn) {
      return t("prescription.prn");
    }
    if (frequency.interval_hours) {
      return isRTL ? `كل ${frequency.interval_hours} ساعة` : `Every ${frequency.interval_hours} hours`;
    }
    if (frequency.times_per_day) {
      if (frequency.times_per_day === 1) return isRTL ? "مرة واحدة يومياً" : "Once daily";
      if (frequency.times_per_day === 2) return isRTL ? "مرتين يومياً" : "Twice daily";
      if (frequency.times_per_day === 3) return isRTL ? "٣ مرات يومياً" : "3 times daily";
      return isRTL ? `${frequency.times_per_day} مرات يومياً` : `${frequency.times_per_day} times daily`;
    }
    return frequency.raw_text || t("prescription.missingFrequency");
  };

  // Helper for dose display text
  const formatDose = () => {
    if (!dose) return t("prescription.missingDose");
    if (dose.status === "uncertain") return t("prescription.unclearField");
    if (dose.value && dose.unit) {
      let unitLabel = dose.unit;
      if (isRTL) {
        if (dose.unit === "tablet") unitLabel = dose.value === 1 ? "قرص" : (dose.value === 2 ? "قرصين" : "أقراص");
        if (dose.unit === "spoon") unitLabel = dose.value === 1 ? "ملعقة" : "ملاعق";
        if (dose.unit === "ml") unitLabel = "مل";
        if (dose.unit === "drops") unitLabel = "نقط";
      }
      return `${dose.value} ${unitLabel}`;
    }
    return dose.raw_text || t("prescription.missingDose");
  };

  // Helper for duration display text
  const formatDuration = () => {
    if (!duration) return t("prescription.missingDuration");
    if (duration.status === "uncertain") return t("prescription.unclearField");
    if (duration.value && duration.unit) {
      let unitLabel = duration.unit;
      if (isRTL) {
        if (duration.unit === "days") unitLabel = duration.value === 1 ? "يوم" : (duration.value === 2 ? "يومين" : "أيام");
        if (duration.unit === "weeks") unitLabel = duration.value === 1 ? "أسبوع" : (duration.value === 2 ? "أسبوعين" : "أسابيع");
        if (duration.unit === "months") unitLabel = duration.value === 1 ? "شهر" : (duration.value === 2 ? "شهرين" : "شهور");
      }
      return isRTL ? `لمدة ${duration.value} ${unitLabel}` : `For ${duration.value} ${unitLabel}`;
    }
    return duration.raw_text || t("prescription.missingDuration");
  };

  // Helper for food timing
  const formatFoodTiming = () => {
    if (!foodTiming) return null;
    const map: Record<string, { ar: string; en: string }> = {
      before_food: { ar: "قبل الأكل", en: "Before food" },
      after_food: { ar: "بعد الأكل", en: "After food" },
      with_food: { ar: "مع الأكل", en: "With food" },
      empty_stomach: { ar: "على الريق", en: "On empty stomach" },
      before_breakfast: { ar: "قبل الإفطار", en: "Before breakfast" },
      bedtime: { ar: "قبل النوم", en: "At bedtime" },
    };
    const tEntry = map[foodTiming.timing];
    return tEntry ? (isRTL ? tEntry.ar : tEntry.en) : foodTiming.raw_text;
  };

  // Helper for route
  const formatRoute = () => {
    if (!route) return null;
    const map: Record<string, { ar: string; en: string }> = {
      oral: { ar: "عن طريق الفم", en: "Oral" },
      topical: { ar: "دهان موضعي", en: "Topical" },
      ophthalmic: { ar: "قطرة للعين", en: "Ophthalmic (Eye)" },
      otic: { ar: "قطرة للأذن", en: "Otic (Ear)" },
      nasal: { ar: "بخاخ للأنف", en: "Nasal" },
      inhalation: { ar: "استنشاق", en: "Inhalation" },
      intramuscular: { ar: "حقن عضلي (IM)", en: "Intramuscular (IM)" },
      intravenous: { ar: "حقن وريدي (IV)", en: "Intravenous (IV)" },
    };
    const rEntry = map[route.route];
    return rEntry ? (isRTL ? rEntry.ar : rEntry.en) : route.raw_text;
  };

  return (
    <div className={`p-4 sm:p-5 bg-gradient-to-br from-medPink-50/50 via-white to-rose-50/30 border border-medPink-200/80 rounded-2xl space-y-3.5 shadow-2xs ${className}`}>
      {/* Section Header */}
      <div className="flex items-center justify-between gap-2 pb-2.5 border-b border-medPink-100">
        <div className="flex items-center gap-2 text-xs font-extrabold text-slate-900">
          <FileText className="w-4 h-4 text-medPink-600" />
          <span>{t("prescription.writtenInstructions")}</span>
        </div>

        {isPrn && (
          <span className="px-2.5 py-0.5 rounded-full bg-medPink-100 border border-medPink-200 text-[11px] font-bold text-medPink-800">
            {t("prescription.prn")}
          </span>
        )}
      </div>

      {/* Grid of structured directives */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-xs">
        {/* Dose Directive */}
        <div className="p-3 bg-white border border-slate-200/80 rounded-xl space-y-1">
          <div className="text-slate-500 font-medium text-[11px] flex items-center justify-between">
            <span>{t("prescription.dose")}</span>
            {dose?.status === "parsed" && (
              <span className="text-emerald-600 font-mono text-[10px]">✓ {Math.round(dose.confidence * 100)}%</span>
            )}
          </div>
          <div className={`font-bold ${dose ? "text-slate-900 text-sm" : "text-slate-400 italic"}`}>
            {formatDose()}
          </div>
        </div>

        {/* Frequency Directive */}
        <div className="p-3 bg-white border border-slate-200/80 rounded-xl space-y-1">
          <div className="text-slate-500 font-medium text-[11px] flex items-center justify-between">
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3 text-medTeal-600" />
              <span>{t("prescription.frequency")}</span>
            </span>
            {frequency?.status === "parsed" && (
              <span className="text-emerald-600 font-mono text-[10px]">✓ {Math.round(frequency.confidence * 100)}%</span>
            )}
          </div>
          <div className={`font-bold ${frequency ? "text-slate-900 text-sm" : "text-slate-400 italic"}`}>
            {formatFrequency()}
          </div>
        </div>

        {/* Duration Directive */}
        <div className="p-3 bg-white border border-slate-200/80 rounded-xl space-y-1">
          <div className="text-slate-500 font-medium text-[11px] flex items-center justify-between">
            <span className="flex items-center gap-1">
              <Calendar className="w-3 h-3 text-medPink-600" />
              <span>{t("prescription.duration")}</span>
            </span>
            {duration?.status === "parsed" && (
              <span className="text-emerald-600 font-mono text-[10px]">✓ {Math.round(duration.confidence * 100)}%</span>
            )}
          </div>
          <div className={`font-bold ${duration ? "text-slate-900 text-sm" : "text-slate-400 italic"}`}>
            {formatDuration()}
          </div>
        </div>

        {/* Meal / Food Timing or Route */}
        <div className="p-3 bg-white border border-slate-200/80 rounded-xl space-y-1">
          <div className="text-slate-500 font-medium text-[11px] flex items-center gap-1">
            {foodTiming ? (
              <>
                <Utensils className="w-3 h-3 text-amber-600" />
                <span>{t("prescription.foodTiming")}</span>
              </>
            ) : (
              <>
                <Compass className="w-3 h-3 text-medTeal-600" />
                <span>{t("prescription.route")}</span>
              </>
            )}
          </div>
          <div className="font-bold text-slate-900 text-sm">
            {formatFoodTiming() || formatRoute() || t("prescription.missingFoodTiming")}
          </div>
        </div>
      </div>

      {/* Raw instruction text snippet */}
      {instructions?.raw_instruction_text && (
        <div className="p-2.5 bg-slate-50 rounded-xl border border-slate-200/70 text-[11px] text-slate-600 flex items-start gap-2">
          <span className="font-bold text-slate-800 shrink-0">{t("prescription.rawTextLabel")}</span>
          <span className="font-mono text-slate-700">{instructions.raw_instruction_text}</span>
        </div>
      )}
    </div>
  );
}
