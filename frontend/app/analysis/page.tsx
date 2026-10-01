"use client";

import React, { useState, useEffect } from "react";
import {
  ScanLine,
  Play,
  Sliders,
} from "lucide-react";
import { analyzeXRay, ApiError } from "@/lib/api";
import type { AnalysisResponse } from "@/types/api";
import UploadDropzone from "@/components/UploadDropzone";
import ImagePreview from "@/components/ImagePreview";
import AnalysisResult from "@/components/AnalysisResult";
import LoadingState from "@/components/LoadingState";
import ErrorState from "@/components/ErrorState";
import Disclaimer from "@/components/Disclaimer";
import { useLanguage } from "@/lib/i18n";

export default function AnalysisPage() {
  const { t, isRTL } = useLanguage();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [alpha, setAlpha] = useState<number>(0.45);

  // Clean up object URLs on unmount or file change
  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  const handleFileSelected = (file: File) => {
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
    setSelectedFile(file);
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    setError(null);
    setResult(null);
  };

  const handleReset = () => {
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
    setSelectedFile(null);
    setPreviewUrl(null);
    setError(null);
    setResult(null);
  };

  const handleStartAnalysis = async () => {
    if (!selectedFile) return;

    setLoading(true);
    setError(null);

    try {
      const response = await analyzeXRay(selectedFile, { alpha });
      setResult(response);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError(t("analysis.failedGeneric"));
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* 1. Page Title Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <ScanLine className="w-6 h-6 text-medTeal-600" />
            <span>{t("analysis.pageTitle")}</span>
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            {t("analysis.pageDesc")}
          </p>
        </div>

        <Disclaimer variant="inline" />
      </div>

      {/* 2. Main Workflow State Machine */}
      {result ? (
        /* Result State */
        <AnalysisResult result={result} onReset={handleReset} />
      ) : loading ? (
        /* Loading State */
        <div className="py-12">
          <LoadingState />
        </div>
      ) : (
        /* Upload & Preview State */
        <div className="space-y-6">
          {!selectedFile ? (
            /* Upload Dropzone */
            <div className="space-y-4">
              <UploadDropzone onFileSelected={handleFileSelected} />

              <div className="bg-slate-50 border border-slate-200 rounded-2xl p-5 text-xs text-slate-600 space-y-2 shadow-xs">
                <div className="font-bold text-slate-800">{t("analysis.guidelinesTitle")}</div>
                <ul className="list-disc list-inside space-y-1 text-slate-600">
                  <li>{t("analysis.guideline1")}</li>
                  <li>{t("analysis.guideline2")}</li>
                  <li>{t("analysis.guideline3")}</li>
                </ul>
              </div>
            </div>
          ) : (
            /* Image Preview & Analyze Action */
            <div className="space-y-5">
              <ImagePreview
                file={selectedFile}
                previewUrl={previewUrl!}
                onReset={handleReset}
                disabled={loading}
              />

              {/* Explainability Settings (Alpha Overlay Transparency) */}
              <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4 flex flex-wrap items-center justify-between gap-4 shadow-xs">
                <div className="flex items-center gap-2 text-xs text-slate-800">
                  <Sliders className="w-4 h-4 text-medTeal-600" />
                  <span className="font-bold">{t("analysis.transparencyLabel")}</span>
                  <span className="font-mono text-medPink-600 font-bold">{alpha.toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min="0.1"
                  max="0.9"
                  step="0.05"
                  value={alpha}
                  onChange={(e) => setAlpha(parseFloat(e.target.value))}
                  disabled={loading}
                  className="w-48 accent-medPink-400 cursor-pointer"
                />
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  onClick={handleReset}
                  disabled={loading}
                  className="px-4 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs rounded-xl transition border border-slate-300 shadow-xs"
                >
                  {t("analysis.resetBtn")}
                </button>
                <button
                  onClick={handleStartAnalysis}
                  disabled={loading}
                  className="inline-flex items-center gap-2 px-6 py-2.5 bg-medPink-400 hover:bg-medPink-500 text-white font-bold text-xs sm:text-sm rounded-xl shadow-xs transition transform active:scale-95 disabled:opacity-50"
                >
                  <Play className={`w-4 h-4 fill-current ${isRTL ? "rotate-180" : ""}`} />
                  <span>{t("analysis.analyzeBtn")}</span>
                </button>
              </div>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <ErrorState
              title={t("analysis.failedTitle")}
              message={error}
              onRetry={selectedFile ? handleStartAnalysis : undefined}
            />
          )}

          {/* Persistent Disclaimer at Bottom */}
          <Disclaimer variant="card" />
        </div>
      )}
    </div>
  );
}
