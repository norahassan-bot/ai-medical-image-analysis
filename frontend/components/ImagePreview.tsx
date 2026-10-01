"use client";

import React from "react";
import { X, CheckCircle2 } from "lucide-react";
import { useLanguage } from "@/lib/i18n";

interface ImagePreviewProps {
  file: File;
  previewUrl: string;
  onReset: () => void;
  disabled?: boolean;
}

export default function ImagePreview({
  file,
  previewUrl,
  onReset,
  disabled = false,
}: ImagePreviewProps) {
  const { t } = useLanguage();

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-5 space-y-4 shadow-xs">
      <div className="flex items-center justify-between border-b border-slate-200 pb-3">
        <div className="flex items-center gap-2 text-sm font-bold text-slate-800">
          <CheckCircle2 className="w-4 h-4 text-medTeal-500" />
          <span>{t("preview.title")}</span>
        </div>
        <button
          onClick={onReset}
          disabled={disabled}
          className="flex items-center gap-1 text-xs text-slate-500 hover:text-rose-600 p-1.5 rounded-lg hover:bg-slate-100 transition disabled:opacity-50 font-medium"
          title={t("preview.change")}
        >
          <X className="w-4 h-4" />
          <span className="hidden sm:inline">{t("preview.change")}</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5 items-center">
        {/* Preview Frame */}
        <div className="bg-slate-50 rounded-xl border border-slate-200 aspect-square max-h-[320px] flex items-center justify-center p-2 overflow-hidden shadow-inner">
          <img
            src={previewUrl}
            alt={t("preview.title")}
            className="max-h-full max-w-full object-contain rounded-lg shadow-sm"
          />
        </div>

        {/* File Metadata Details */}
        <div className="space-y-3 text-xs">
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 space-y-2">
            <div>
              <span className="text-slate-500 font-medium block">{t("preview.filename")}</span>
              <span className="text-slate-900 font-mono font-bold break-all">
                {file.name}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-200">
              <div>
                <span className="text-slate-500 font-medium block">{t("preview.fileSize")}</span>
                <span className="text-slate-800 font-mono font-semibold">
                  {formatBytes(file.size)}
                </span>
              </div>
              <div>
                <span className="text-slate-500 font-medium block">{t("preview.mimeType")}</span>
                <span className="text-slate-800 font-mono font-semibold">
                  {file.type || "image/jpeg"}
                </span>
              </div>
            </div>
          </div>

          <div className="p-3 bg-medTeal-50 border border-medTeal-200 rounded-xl text-medTeal-900 text-[11px] leading-relaxed font-medium">
            {t("preview.readyNote")}
          </div>
        </div>
      </div>
    </div>
  );
}
