"use client";

import React, { useState } from "react";
import { ZoomIn, ZoomOut, RotateCcw, Maximize2, X, FileImage } from "lucide-react";
import { useLanguage } from "@/lib/i18n";

interface PrescriptionImageViewerProps {
  imageUrl: string;
  filename?: string;
  className?: string;
}

export default function PrescriptionImageViewer({
  imageUrl,
  filename = "Prescription",
  className = "",
}: PrescriptionImageViewerProps) {
  const { t } = useLanguage();
  const [zoomLevel, setZoomLevel] = useState(1);
  const [modalOpen, setModalOpen] = useState(false);

  const handleZoomIn = () => setZoomLevel((prev) => Math.min(prev + 0.25, 3.0));
  const handleZoomOut = () => setZoomLevel((prev) => Math.max(prev - 0.25, 0.75));
  const handleResetZoom = () => setZoomLevel(1);

  return (
    <>
      <div className={`bg-white rounded-3xl border border-slate-200/90 overflow-hidden shadow-xs space-y-3 p-4 sm:p-5 ${className}`}>
        {/* Header with Title & Zoom Actions */}
        <div className="flex items-center justify-between gap-2 pb-2 border-b border-slate-100">
          <div className="flex items-center gap-2 text-xs font-bold text-slate-800 truncate">
            <FileImage className="w-4 h-4 text-medTeal-600 shrink-0" />
            <span className="truncate">{filename || t("prescription.originalImage")}</span>
          </div>

          <div className="flex items-center gap-1 shrink-0">
            <button
              type="button"
              onClick={handleZoomIn}
              className="p-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 transition"
              title="Zoom in"
              aria-label="Zoom in"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={handleZoomOut}
              className="p-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 transition"
              title="Zoom out"
              aria-label="Zoom out"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={handleResetZoom}
              className="p-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 transition"
              title="Reset zoom"
              aria-label="Reset zoom"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={() => setModalOpen(true)}
              className="p-1.5 rounded-lg bg-medTeal-50 hover:bg-medTeal-100 text-medTeal-700 transition ms-1"
              title="Fullscreen"
              aria-label="Fullscreen viewer"
            >
              <Maximize2 className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Image viewport */}
        <div className="relative w-full aspect-4/3 sm:aspect-16/10 bg-slate-900/5 rounded-2xl overflow-hidden flex items-center justify-center border border-slate-200/60">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={imageUrl}
            alt={filename || "Prescription Image"}
            style={{ transform: `scale(${zoomLevel})` }}
            className="max-h-full max-w-full object-contain transition-transform duration-200 ease-out cursor-zoom-in"
            onClick={() => setModalOpen(true)}
          />
        </div>

        <div className="text-[11px] text-slate-400 text-center">
          {t("prescription.imageViewerZoom")}
        </div>
      </div>

      {/* Fullscreen Modal View */}
      {modalOpen && (
        <div
          className="fixed inset-0 z-50 bg-slate-950/90 backdrop-blur-md flex flex-col p-4 sm:p-8"
          role="dialog"
          aria-modal="true"
        >
          <div className="flex items-center justify-between text-white pb-4">
            <span className="text-sm font-bold truncate">{filename}</span>
            <button
              type="button"
              onClick={() => setModalOpen(false)}
              className="p-2 rounded-xl bg-white/10 hover:bg-white/20 text-white transition"
              aria-label="Close fullscreen modal"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="flex-1 w-full flex items-center justify-center overflow-auto">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={imageUrl}
              alt={filename || "Prescription Image"}
              className="max-h-full max-w-full object-contain rounded-xl shadow-2xl"
            />
          </div>
        </div>
      )}
    </>
  );
}
