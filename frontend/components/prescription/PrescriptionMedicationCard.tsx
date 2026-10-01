"use client";

import React, { useState } from "react";
import { Pill, ChevronDown, ChevronUp, Sparkles, Tag, Layers } from "lucide-react";
import type { PrescriptionMedicationItem } from "@/types/api";
import { useLanguage } from "@/lib/i18n";
import ConfidenceBadge from "./ConfidenceBadge";
import UncertaintyNotice from "./UncertaintyNotice";
import MedicationInformation from "./MedicationInformation";
import PrescriptionInstructions from "./PrescriptionInstructions";

interface PrescriptionMedicationCardProps {
  item: PrescriptionMedicationItem;
  index: number;
  className?: string;
}

export default function PrescriptionMedicationCard({
  item,
  index,
  className = "",
}: PrescriptionMedicationCardProps) {
  const { t, isRTL } = useLanguage();
  const [detailsExpanded, setDetailsExpanded] = useState(false);

  const medName = item.medication?.matched_name || item.raw_text;
  const genericName = item.medication?.generic_name;
  const brandName = item.medication?.brand_name;
  const isUncertain = item.medication?.status === "uncertain" || (item.medication?.confidence < 0.50 && item.medication?.confidence > 0);

  return (
    <article
      className={`bg-white rounded-3xl border border-slate-200/90 shadow-sm overflow-hidden transition-all duration-200 hover:shadow-md ${className}`}
      aria-labelledby={`med-card-title-${index}`}
    >
      {/* 1. Header Banner */}
      <div className="p-5 sm:p-6 bg-gradient-to-r from-slate-50 via-white to-medTeal-50/30 border-b border-slate-200/80 space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex items-start gap-3 min-w-0">
            <div className="w-11 h-11 rounded-2xl bg-gradient-to-tr from-medPink-500 to-medTeal-600 text-white flex items-center justify-center font-bold text-sm shadow-sm shrink-0">
              <Pill className="w-5 h-5" />
            </div>

            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-bold px-2 py-0.5 rounded-md bg-slate-100 text-slate-600 font-mono">
                  #{index + 1}
                </span>
                <h3
                  id={`med-card-title-${index}`}
                  className="text-base sm:text-lg font-extrabold text-slate-900 tracking-tight truncate"
                >
                  {medName}
                </h3>
              </div>

              {genericName && (
                <div className="text-xs text-slate-500 mt-0.5 font-medium">
                  <span className="font-semibold text-slate-700">{t("prescription.genericName")}: </span>
                  <span>{genericName}</span>
                </div>
              )}
            </div>
          </div>

          <ConfidenceBadge
            status={item.medication?.status}
            confidence={item.medication?.confidence}
          />
        </div>

        {/* Strength & Dosage Form Badges */}
        <div className="flex flex-wrap items-center gap-2 pt-1 text-xs">
          {item.strength && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-slate-100/80 border border-slate-200 text-slate-700 font-semibold text-[11px]">
              <Tag className="w-3 h-3 text-medTeal-600" />
              <span>{t("prescription.strength")}: {item.strength.value} {item.strength.unit}</span>
            </span>
          )}

          {item.dosage_form && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-slate-100/80 border border-slate-200 text-slate-700 font-semibold text-[11px]">
              <Layers className="w-3 h-3 text-medPink-600" />
              <span>{t("prescription.dosageForm")}: {item.dosage_form.form}</span>
            </span>
          )}

          {brandName && brandName !== medName && (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-xl bg-sky-50 border border-sky-200 text-sky-800 text-[11px] font-medium">
              <span>{t("prescription.brandName")}:</span>
              <span className="font-bold">{brandName}</span>
            </span>
          )}
        </div>
      </div>

      {/* 2. Uncertainty Notice if applicable */}
      {isUncertain && (
        <div className="p-4 sm:p-5 pb-0">
          <UncertaintyNotice
            rawText={item.raw_text}
            matchedName={medName}
            uncertainFields={item.instructions?.uncertain_fields}
          />
        </div>
      )}

      {/* 3. Main Content: Separate Educational Info & Explicit Instructions */}
      <div className="p-4 sm:p-6 space-y-4">
        {/* Section A: Verified Medication Facts */}
        <MedicationInformation info={item.medication_information} />

        {/* Section B: Explicit Prescription Instructions */}
        <PrescriptionInstructions instructions={item.instructions} />
      </div>

      {/* 4. Collapsible Advanced Analysis Details */}
      <div className="border-t border-slate-100 bg-slate-50/60 p-3 sm:px-6">
        <button
          type="button"
          onClick={() => setDetailsExpanded(!detailsExpanded)}
          className="w-full flex items-center justify-between text-xs font-semibold text-slate-600 hover:text-slate-900 transition py-1"
          aria-expanded={detailsExpanded}
        >
          <span className="flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-medTeal-600" />
            <span>{t("prescription.analysisDetails")}</span>
          </span>
          {detailsExpanded ? (
            <ChevronUp className="w-4 h-4 text-slate-400" />
          ) : (
            <ChevronDown className="w-4 h-4 text-slate-400" />
          )}
        </button>

        {detailsExpanded && (
          <div className="mt-3 p-3 bg-white border border-slate-200/80 rounded-xl space-y-2 text-[11px] text-slate-600 font-mono">
            <div className="flex justify-between">
              <span className="text-slate-400">{t("prescription.rawTextLabel")}</span>
              <span className="text-slate-800 font-bold">{item.raw_text}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Normalized Query:</span>
              <span className="text-slate-800">{item.normalized_text}</span>
            </div>
            {item.ocr_confidence !== undefined && (
              <div className="flex justify-between">
                <span className="text-slate-400">OCR Confidence:</span>
                <span className="text-slate-800">{Math.round(item.ocr_confidence * 100)}%</span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-slate-400">Source:</span>
              <span className="text-slate-800">{item.medication?.source || "Internal Engine"}</span>
            </div>
          </div>
        )}
      </div>
    </article>
  );
}
