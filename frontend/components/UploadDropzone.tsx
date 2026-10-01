"use client";

import React, { useState, useRef, DragEvent, ChangeEvent } from "react";
import { UploadCloud, AlertCircle } from "lucide-react";
import { useLanguage } from "@/lib/i18n";

const ALLOWED_MIME_TYPES = ["image/jpeg", "image/png", "image/jpg"];
const ALLOWED_EXTENSIONS = ["jpg", "jpeg", "png"];
const MAX_SIZE_BYTES = 15 * 1024 * 1024; // 15MB

interface UploadDropzoneProps {
  onFileSelected: (file: File) => void;
  disabled?: boolean;
}

export default function UploadDropzone({ onFileSelected, disabled = false }: UploadDropzoneProps) {
  const { t } = useLanguage();
  const [isDragging, setIsDragging] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateAndProcessFile = (file: File) => {
    setValidationError(null);

    // Validate type and extension
    const ext = file.name.split(".").pop()?.toLowerCase();
    const isAllowedExt = !!ext && ALLOWED_EXTENSIONS.includes(ext);
    const isAllowedMime = !file.type || ALLOWED_MIME_TYPES.includes(file.type.toLowerCase());

    if (!isAllowedExt || !isAllowedMime) {
      setValidationError(t("upload.errUnsupported"));
      return;
    }

    // Validate empty file
    if (file.size === 0) {
      setValidationError(t("upload.errEmpty"));
      return;
    }

    // Validate size
    if (file.size > MAX_SIZE_BYTES) {
      setValidationError(t("upload.errTooLarge"));
      return;
    }

    onFileSelected(file);
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (disabled) return;
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    if (disabled) return;

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndProcessFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndProcessFile(e.target.files[0]);
    }
  };

  return (
    <div className="space-y-3">
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !disabled && fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all duration-200 flex flex-col items-center justify-center min-h-[260px] ${
          isDragging
            ? "border-medPink-400 bg-medPink-50/50 scale-[1.01]"
            : "border-slate-300 bg-white hover:border-medPink-300 hover:bg-slate-50/70 shadow-xs"
        } ${disabled ? "opacity-50 cursor-not-allowed pointer-events-none" : ""}`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".png,.jpg,.jpeg,image/png,image/jpeg"
          onChange={handleFileInputChange}
          className="hidden"
          disabled={disabled}
        />

        <div className="w-14 h-14 rounded-2xl bg-medTeal-50 border border-medTeal-200 flex items-center justify-center mb-4 text-medTeal-600 shadow-xs">
          <UploadCloud className="w-7 h-7" />
        </div>

        <h3 className="text-base font-bold text-slate-900 mb-1">
          {t("upload.title")}
        </h3>
        <p className="text-xs text-slate-500 max-w-sm mb-4">
          {t("upload.desc")}
        </p>

        <button
          type="button"
          disabled={disabled}
          className="px-4 py-2 bg-slate-100 hover:bg-slate-200 border border-slate-300 text-slate-800 text-xs font-bold rounded-xl shadow-xs transition"
        >
          {t("upload.browse")}
        </button>
      </div>

      {validationError && (
        <div className="flex items-center gap-2 p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-xs shadow-xs">
          <AlertCircle className="w-4 h-4 text-rose-500 shrink-0" />
          <span>{validationError}</span>
        </div>
      )}
    </div>
  );
}
