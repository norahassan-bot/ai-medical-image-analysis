"use client";

import React, { useState } from "react";
import { Layers, ZoomIn, Info } from "lucide-react";
import { useLanguage } from "@/lib/i18n";

interface ExplainabilityViewerProps {
  originalBase64?: string;
  heatmapBase64?: string;
  overlayBase64?: string;
  originalDimensions?: [number, number];
  targetClass?: string;
  disclaimer?: string;
  className?: string;
}

export default function ExplainabilityViewer({
  originalBase64,
  heatmapBase64,
  overlayBase64,
  originalDimensions,
  targetClass = "NORMAL",
  className = "",
}: ExplainabilityViewerProps) {
  const { t } = useLanguage();
  const [activeTab, setActiveTab] = useState<"overlay" | "heatmap" | "original" | "grid">("overlay");
  const [zoomedImage, setZoomedImage] = useState<string | null>(null);

  const hasVisuals = originalBase64 || heatmapBase64 || overlayBase64;

  if (!hasVisuals) {
    return (
      <div className="bg-white border border-slate-200 rounded-2xl p-6 text-center text-slate-500 text-sm shadow-xs">
        {t("explain.noVisuals")}
      </div>
    );
  }

  const targetClassStr = typeof targetClass === "string" ? targetClass : String(targetClass || "");
  const displayTarget = targetClassStr.toUpperCase() === "PNEUMONIA" || targetClassStr === "1"
    ? t("common.pneumonia")
    : t("common.normal");

  return (
    <div className={`bg-white border border-slate-200 rounded-2xl p-5 space-y-4 shadow-xs ${className}`}>
      {/* Visual Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200 pb-3">
        <div className="flex items-center gap-2 flex-wrap">
          <Layers className="w-4 h-4 text-medTeal-600 shrink-0" />
          <h3 className="text-sm font-bold text-slate-800">
            {t("explain.title")}
          </h3>
          {targetClass && (
            <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-medTeal-50 border border-medTeal-200 text-medTeal-800 font-mono font-semibold">
              {t("explain.target", { targetClass: displayTarget })}
            </span>
          )}
        </div>

        {/* View Mode Buttons */}
        <div className="flex items-center bg-slate-100 rounded-xl p-0.5 sm:p-1 border border-slate-200 text-xs overflow-x-auto max-w-full">
          <button
            onClick={() => setActiveTab("overlay")}
            className={`px-2.5 sm:px-3 py-1 text-[11px] sm:text-xs rounded-lg font-semibold transition whitespace-nowrap ${
              activeTab === "overlay"
                ? "bg-medPink-400 text-white shadow-xs"
                : "text-slate-600 hover:text-slate-900 hover:bg-white/60"
            }`}
          >
            {t("explain.tabOverlay")}
          </button>
          <button
            onClick={() => setActiveTab("heatmap")}
            className={`px-2.5 sm:px-3 py-1 text-[11px] sm:text-xs rounded-lg font-semibold transition whitespace-nowrap ${
              activeTab === "heatmap"
                ? "bg-medPink-400 text-white shadow-xs"
                : "text-slate-600 hover:text-slate-900 hover:bg-white/60"
            }`}
          >
            {t("explain.tabHeatmap")}
          </button>
          <button
            onClick={() => setActiveTab("original")}
            className={`px-2.5 sm:px-3 py-1 text-[11px] sm:text-xs rounded-lg font-semibold transition whitespace-nowrap ${
              activeTab === "original"
                ? "bg-medPink-400 text-white shadow-xs"
                : "text-slate-600 hover:text-slate-900 hover:bg-white/60"
            }`}
          >
            {t("explain.tabOriginal")}
          </button>
          <button
            onClick={() => setActiveTab("grid")}
            className={`px-2.5 sm:px-3 py-1 text-[11px] sm:text-xs rounded-lg font-semibold transition whitespace-nowrap ${
              activeTab === "grid"
                ? "bg-medPink-400 text-white shadow-xs"
                : "text-slate-600 hover:text-slate-900 hover:bg-white/60"
            }`}
          >
            {t("explain.tabGrid")}
          </button>
        </div>
      </div>

      {/* Primary Display Area */}
      {activeTab === "grid" ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {originalBase64 && (
            <div className="space-y-1.5">
              <div className="text-xs font-semibold text-slate-600 flex items-center justify-between">
                <span>{t("explain.origTitle")}</span>
                <button
                  onClick={() => setZoomedImage(originalBase64)}
                  className="text-slate-400 hover:text-medTeal-600 transition"
                  title={t("explain.expand")}
                >
                  <ZoomIn className="w-3.5 h-3.5" />
                </button>
              </div>
              <div className="bg-slate-50 rounded-xl overflow-hidden border border-slate-200 aspect-square flex items-center justify-center p-2 shadow-inner">
                <img
                  src={originalBase64}
                  alt={t("explain.origTitle")}
                  className="max-h-full max-w-full object-contain rounded-lg shadow-xs"
                />
              </div>
            </div>
          )}

          {heatmapBase64 && (
            <div className="space-y-1.5">
              <div className="text-xs font-semibold text-slate-600 flex items-center justify-between">
                <span>{t("explain.heatTitle")}</span>
                <button
                  onClick={() => setZoomedImage(heatmapBase64)}
                  className="text-slate-400 hover:text-medTeal-600 transition"
                  title={t("explain.expand")}
                >
                  <ZoomIn className="w-3.5 h-3.5" />
                </button>
              </div>
              <div className="bg-slate-50 rounded-xl overflow-hidden border border-slate-200 aspect-square flex items-center justify-center p-2 shadow-inner">
                <img
                  src={heatmapBase64}
                  alt={t("explain.heatTitle")}
                  className="max-h-full max-w-full object-contain rounded-lg shadow-xs"
                />
              </div>
            </div>
          )}

          {overlayBase64 && (
            <div className="space-y-1.5">
              <div className="text-xs font-semibold text-slate-600 flex items-center justify-between">
                <span>{t("explain.overTitle")}</span>
                <button
                  onClick={() => setZoomedImage(overlayBase64)}
                  className="text-slate-400 hover:text-medTeal-600 transition"
                  title={t("explain.expand")}
                >
                  <ZoomIn className="w-3.5 h-3.5" />
                </button>
              </div>
              <div className="bg-slate-50 rounded-xl overflow-hidden border border-slate-200 aspect-square flex items-center justify-center p-2 shadow-inner">
                <img
                  src={overlayBase64}
                  alt={t("explain.overTitle")}
                  className="max-h-full max-w-full object-contain rounded-lg shadow-xs"
                />
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="relative bg-slate-50 rounded-2xl overflow-hidden border border-slate-200 flex items-center justify-center min-h-[360px] p-4 shadow-inner">
          {activeTab === "overlay" && overlayBase64 && (
            <img
              src={overlayBase64}
              alt={t("explain.overTitle")}
              className="max-h-[460px] max-w-full object-contain rounded-xl shadow-xs transition-transform duration-300"
            />
          )}
          {activeTab === "heatmap" && heatmapBase64 && (
            <img
              src={heatmapBase64}
              alt={t("explain.heatTitle")}
              className="max-h-[460px] max-w-full object-contain rounded-xl shadow-xs"
            />
          )}
          {activeTab === "original" && originalBase64 && (
            <img
              src={originalBase64}
              alt={t("explain.origTitle")}
              className="max-h-[460px] max-w-full object-contain rounded-xl shadow-xs"
            />
          )}

          {/* Quick Overlay Label */}
          <div className="absolute top-3 start-3 px-3 py-1 rounded-xl bg-white/95 backdrop-blur border border-slate-200 text-xs text-slate-700 font-semibold shadow-xs">
            {activeTab === "overlay" && t("explain.overTitle")}
            {activeTab === "heatmap" && t("explain.heatTitle")}
            {activeTab === "original" && t("explain.origTitle")}
            {originalDimensions && ` (${originalDimensions[0]}×${originalDimensions[1]}px)`}
          </div>
        </div>
      )}

      {/* Explanatory Note */}
      <div className="bg-medTeal-50/70 border border-medTeal-200 rounded-xl p-3 text-xs text-slate-700 flex items-start gap-2.5">
        <Info className="w-4 h-4 text-medTeal-600 shrink-0 mt-0.5" />
        <p className="leading-relaxed">
          {t("explain.infoNote")}
        </p>
      </div>

      {/* Modal Zoom View */}
      {zoomedImage && (
        <div
          className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-6"
          onClick={() => setZoomedImage(null)}
        >
          <div className="relative max-w-4xl max-h-[90vh] bg-white p-3 rounded-2xl border border-slate-200 shadow-2xl">
            <img
              src={zoomedImage}
              alt={t("explain.expand")}
              className="max-h-[80vh] max-w-full object-contain rounded-xl"
            />
            <div className="p-2 text-center text-xs text-slate-500 font-medium">{t("explain.closeModal")}</div>
          </div>
        </div>
      )}
    </div>
  );
}
