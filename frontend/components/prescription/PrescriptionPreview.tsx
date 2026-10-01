"use client";

import React, { useState, useEffect } from "react";
import { Sparkles, RefreshCw, Trash2, FileImage, Layers } from "lucide-react";
import { useLanguage } from "@/lib/i18n";

interface PrescriptionPreviewProps {
  file: File;
  onRemove: () => void;
  onAnalyze: () => void;
  isAnalyzing?: boolean;
  className?: string;
}

export default function PrescriptionPreview({
  file,
  onRemove,
  onAnalyze,
  isAnalyzing = false,
  className = "",
}: PrescriptionPreviewProps) {
  const { t, isRTL } = useLanguage();
  const [previewUrl, setPreviewUrl] = useState<string>("");
  const [dimensions, setDimensions] = useState<{ width: number; height: number } | null>(null);

  useEffect(() => {
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);

    const img = new Image();
    img.onload = () => {
      setDimensions({ width: img.naturalWidth, height: img.naturalHeight });
    };
    img.src = url;

    return () => {
      URL.revokeObjectURL(url);
    };
  }, [file]);

  const formatFileSize = (bytes: number) => {
    if (bytes >= 1024 * 1024) {
      return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    }
    return `${(bytes / 1024).toFixed(1)} KB`;
  };

  return (
    <div className={`bg-white rounded-3xl border border-slate-200/90 shadow-sm p-5 sm:p-6 space-y-5 ${className}`}>
      {/* 1. Header Metadata Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-100">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-10 h-10 rounded-xl bg-medTeal-50 border border-medTeal-200 flex items-center justify-center text-medTeal-600 shrink-0">
            <FileImage className="w-5 h-5" />
          </div>
          <div className="min-w-0">
            <h4 className="text-xs sm:text-sm font-bold text-slate-900 truncate">
              {file.name}
            </h4>
            <div className="flex items-center gap-2 text-[11px] text-slate-500 font-mono">
              <span>{formatFileSize(file.size)}</span>
              {dimensions && (
                <>
                  <span>•</span>
                  <span>{dimensions.width} × {dimensions.height} px</span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Remove Button */}
        <button
          type="button"
          onClick={onRemove}
          disabled={isAnalyzing}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-rose-200 bg-rose-50/80 hover:bg-rose-100 text-rose-700 text-xs font-bold transition disabled:opacity-50"
          aria-label={t("prescription.removeImage")}
        >
          <Trash2 className="w-3.5 h-3.5" />
          <span>{t("prescription.removeImage")}</span>
        </button>
      </div>

      {/* 2. Image Viewport */}
      <div className="relative w-full aspect-4/3 sm:aspect-16/10 bg-slate-900/5 rounded-2xl overflow-hidden flex items-center justify-center border border-slate-200/70">
        {previewUrl && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={previewUrl}
            alt={file.name}
            className="max-h-full max-w-full object-contain rounded-xl"
          />
        )}
      </div>

      {/* 3. Analyze Action CTA Button */}
      <div className="pt-2">
        <button
          type="button"
          onClick={onAnalyze}
          disabled={isAnalyzing}
          className="w-full inline-flex items-center justify-center gap-2 px-6 py-3.5 rounded-2xl bg-gradient-to-r from-medPink-500 via-medPink-600 to-medTeal-600 hover:from-medPink-600 hover:to-medTeal-700 text-white font-bold text-sm sm:text-base shadow-md hover:shadow-lg transition-all disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {isAnalyzing ? (
            <>
              <RefreshCw className="w-5 h-5 animate-spin" />
              <span>{t("prescription.analyzingBtn")}</span>
            </>
          ) : (
            <>
              <Sparkles className="w-5 h-5" />
              <span>{t("prescription.analyzeBtn")}</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
}
