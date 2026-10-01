"use client";

import React, { useState, useEffect } from "react";
import { RefreshCw, ScanLine, BrainCircuit, Pill, FileText, CheckCircle2 } from "lucide-react";
import { useLanguage } from "@/lib/i18n";

interface PrescriptionProcessingProps {
  className?: string;
}

export default function PrescriptionProcessing({ className = "" }: PrescriptionProcessingProps) {
  const { t } = useLanguage();
  const [currentStep, setCurrentStep] = useState(0);

  const stages = [
    { key: "prescription.stagePreparing", icon: ScanLine },
    { key: "prescription.stageReading", icon: BrainCircuit },
    { key: "prescription.stageDetecting", icon: Pill },
    { key: "prescription.stageMatching", icon: BrainCircuit },
    { key: "prescription.stageInstructions", icon: FileText },
  ];

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentStep((prev) => (prev < stages.length - 1 ? prev + 1 : prev));
    }, 700);

    return () => clearInterval(interval);
  }, [stages.length]);

  return (
    <div
      className={`bg-white rounded-3xl border border-slate-200/90 p-8 sm:p-12 shadow-sm text-center space-y-6 max-w-xl mx-auto ${className}`}
      role="status"
      aria-live="polite"
    >
      {/* Spinning Center Icon */}
      <div className="relative w-20 h-20 sm:w-24 sm:h-24 mx-auto flex items-center justify-center">
        <div className="absolute inset-0 rounded-full border-4 border-medTeal-100 border-t-medTeal-600 animate-spin" />
        <div className="w-14 h-14 sm:w-16 sm:h-16 rounded-2xl bg-gradient-to-tr from-medPink-500 to-medTeal-600 text-white flex items-center justify-center shadow-md">
          <Pill className="w-7 h-7 sm:w-8 sm:h-8 animate-pulse" />
        </div>
      </div>

      {/* Main Title & Subtitle */}
      <div className="space-y-1.5">
        <h3 className="text-base sm:text-lg font-extrabold text-slate-900">
          {t("prescription.analyzingBtn")}
        </h3>
        <p className="text-xs text-slate-500">
          {t("prescription.uploadSubtitle")}
        </p>
      </div>

      {/* Progressive Stage Stepper */}
      <div className="space-y-2.5 max-w-md mx-auto text-left pt-2">
        {stages.map((stage, idx) => {
          const Icon = stage.icon;
          const isDone = idx < currentStep;
          const isActive = idx === currentStep;

          return (
            <div
              key={idx}
              className={`p-2.5 rounded-xl border flex items-center gap-3 transition-all duration-300 ${
                isActive
                  ? "bg-medTeal-50 border-medTeal-300 text-medTeal-950 font-bold scale-[1.02]"
                  : isDone
                  ? "bg-slate-50 border-slate-200 text-slate-700"
                  : "bg-transparent border-transparent text-slate-400 opacity-60"
              }`}
            >
              <div className="shrink-0">
                {isDone ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                ) : isActive ? (
                  <RefreshCw className="w-4 h-4 text-medTeal-600 animate-spin" />
                ) : (
                  <Icon className="w-4 h-4 text-slate-400" />
                )}
              </div>
              <span className="text-xs">{t(stage.key as any)}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
