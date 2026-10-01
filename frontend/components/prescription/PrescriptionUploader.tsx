"use client";

import React, { useRef, useState } from "react";
import { UploadCloud, Camera, ImagePlus, AlertCircle } from "lucide-react";
import { useLanguage } from "@/lib/i18n";

const MAX_SIZE_BYTES = 10 * 1024 * 1024; // 10MB
const ALLOWED_MIME_TYPES = ["image/jpeg", "image/png", "image/webp", "image/jpg"];

interface PrescriptionUploaderProps {
  onFileSelected: (file: File) => void;
  disabled?: boolean;
  className?: string;
}

export default function PrescriptionUploader({
  onFileSelected,
  disabled = false,
  className = "",
}: PrescriptionUploaderProps) {
  const { t } = useLanguage();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  const validateAndSelect = (file: File) => {
    setValidationError(null);

    // 1. MIME type validation
    if (!ALLOWED_MIME_TYPES.includes(file.type.toLowerCase())) {
      const ext = file.name.split(".").pop()?.toLowerCase();
      if (!["jpg", "jpeg", "png", "webp"].includes(ext || "")) {
        setValidationError(t("prescription.unsupportedType"));
        return;
      }
    }

    // 2. File size validation
    if (file.size > MAX_SIZE_BYTES) {
      setValidationError(t("prescription.fileTooLarge"));
      return;
    }

    onFileSelected(file);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    if (!disabled) setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (disabled) return;

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndSelect(e.dataTransfer.files[0]);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndSelect(e.target.files[0]);
    }
  };

  return (
    <div className={`space-y-3 w-full ${className}`}>
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !disabled && fileInputRef.current?.click()}
        className={`relative cursor-pointer rounded-3xl border-2 border-dashed p-8 sm:p-12 text-center transition-all duration-200 flex flex-col items-center justify-center gap-4 ${
          isDragOver
            ? "border-medTeal-500 bg-medTeal-50/60 scale-[1.01]"
            : "border-slate-300 hover:border-medTeal-400 bg-slate-50/50 hover:bg-medTeal-50/20"
        } ${disabled ? "opacity-60 cursor-not-allowed" : ""}`}
        role="button"
        tabIndex={0}
        aria-label={t("prescription.dropzonePrompt")}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            if (!disabled) fileInputRef.current?.click();
          }
        }}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="image/png,image/jpeg,image/jpg,image/webp"
          onChange={handleInputChange}
          disabled={disabled}
          className="hidden"
          id="prescription-file-input"
          aria-describedby="prescription-upload-desc"
        />

        {/* Icon Circle */}
        <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-3xl bg-gradient-to-tr from-medPink-100 via-white to-medTeal-100 border border-slate-200 flex items-center justify-center text-medTeal-600 shadow-xs">
          <UploadCloud className="w-8 h-8 sm:w-10 sm:h-10 animate-pulse" />
        </div>

        {/* Prompt texts */}
        <div className="space-y-1 max-w-md">
          <p className="text-sm sm:text-base font-bold text-slate-800">
            {t("prescription.dropzonePrompt")}
          </p>
          <p id="prescription-upload-desc" className="text-xs text-slate-500">
            {t("prescription.supportedFormats")}
          </p>
        </div>

        {/* Mobile Camera / File button */}
        <div className="flex flex-wrap items-center justify-center gap-2 pt-2">
          <span className="inline-flex items-center gap-1.5 px-4 py-2 bg-white border border-slate-200 rounded-xl text-xs font-bold text-slate-700 shadow-2xs hover:bg-slate-50 transition">
            <Camera className="w-4 h-4 text-medPink-600" />
            <span>{t("prescription.takePhoto")}</span>
          </span>
        </div>
      </div>

      {/* Validation Error Alert */}
      {validationError && (
        <div
          className="p-3 bg-rose-50 border border-rose-200 rounded-xl flex items-center gap-2 text-xs font-semibold text-rose-800 shadow-2xs"
          role="alert"
        >
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{validationError}</span>
        </div>
      )}
    </div>
  );
}
