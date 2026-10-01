"use client";

import React from "react";
import Link from "next/link";
import {
  BrainCircuit,
  Cpu,
  Clock,
  Fingerprint,
  Calendar,
  RotateCcw,
  History,
  Download,
} from "lucide-react";
import type { AnalysisResponse } from "@/types/api";
import ConfidenceDisplay from "./ConfidenceDisplay";
import ExplainabilityViewer from "./ExplainabilityViewer";
import Disclaimer from "./Disclaimer";
import { useLanguage } from "@/lib/i18n";

interface AnalysisResultProps {
  result: AnalysisResponse;
  onReset: () => void;
}

export default function AnalysisResult({ result, onReset }: AnalysisResultProps) {
  const { t, isRTL } = useLanguage();
  const isPneumonia = result.prediction.toUpperCase() === "PNEUMONIA";
  const displayPrediction = isPneumonia ? t("common.pneumonia") : t("common.normal");

  const formattedDate = new Date(result.created_at).toLocaleString(isRTL ? "ar-EG" : "en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  });

  const [downloading, setDownloading] = React.useState<boolean>(false);
  const [downloadError, setDownloadError] = React.useState<string | null>(null);

  const handleDownloadReport = async () => {
    if (!result?.analysis_id) return;
    setDownloading(true);
    setDownloadError(null);

    try {
      const { downloadAnalysisReport, triggerBlobDownload } = await import("@/lib/api");
      const blob = await downloadAnalysisReport(result.analysis_id);
      triggerBlobDownload(blob, `analysis_${result.analysis_id}.pdf`);
    } catch {
      setDownloadError(t("result.pdfError"));
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* 1. Medical Disclaimer Banner */}
      <Disclaimer variant="banner" />

      {/* Download Error Banner if any */}
      {downloadError && (
        <div className="bg-rose-50 border border-rose-200 text-rose-800 text-xs p-3.5 rounded-xl flex items-center justify-between shadow-xs">
          <span>{downloadError}</span>
          <button
            onClick={() => setDownloadError(null)}
            className="text-rose-600 hover:text-rose-800 text-xs underline font-semibold ml-4"
          >
            {t("common.dismiss")}
          </button>
        </div>
      )}

      {/* 2. Primary Diagnostic Result Card */}
      <div className="bg-white border border-slate-200 rounded-2xl p-5 sm:p-6 shadow-xs space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-4">
          <div>
            <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">
              {t("result.evaluationTitle")}
            </div>
            <div className="flex items-center gap-3">
              <span className="text-2xl sm:text-3xl font-black tracking-tight text-slate-900">
                {displayPrediction}
              </span>
              <span
                className={`px-3 py-1 rounded-full text-xs font-bold border ${
                  isPneumonia
                    ? "bg-amber-50 border-amber-200 text-amber-800"
                    : "bg-medTeal-50 border-medTeal-200 text-medTeal-800"
                }`}
              >
                {isPneumonia ? t("result.abnormalBadge") : t("result.normalBadge")}
              </span>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
            <button
              onClick={handleDownloadReport}
              disabled={downloading}
              className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-4 py-2.5 bg-medPink-400 hover:bg-medPink-500 text-white font-bold text-xs rounded-xl shadow-xs transition disabled:opacity-50 text-center"
              aria-label={t("result.downloadPdf")}
            >
              <Download className={`w-3.5 h-3.5 ${downloading ? "animate-bounce" : ""}`} />
              <span>{downloading ? t("result.generatingPdf") : t("result.downloadPdf")}</span>
            </button>
            <button
              onClick={onReset}
              className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-3.5 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs rounded-xl border border-slate-200 transition text-center"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>{t("result.analyzeAnother")}</span>
            </button>
            <Link
              href="/history"
              className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-3.5 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs rounded-xl border border-slate-200 transition text-center"
            >
              <History className="w-3.5 h-3.5 text-slate-500" />
              <span>{t("result.viewHistory")}</span>
            </Link>
          </div>
        </div>

        {/* 3. Metrics & Confidence Breakdown Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {/* Left: Confidence Progress Component */}
          <div className="lg:col-span-2">
            <ConfidenceDisplay
              prediction={result.prediction}
              confidence={result.confidence}
              probabilities={result.probabilities}
            />
          </div>

          {/* Right: Technical Metadata Card */}
          <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4 text-xs space-y-3">
            <div className="font-bold text-slate-800 border-b border-slate-200 pb-2">
              {t("result.metadataTitle")}
            </div>

            <div className="space-y-2 text-slate-600">
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <Fingerprint className="w-3.5 h-3.5 text-slate-400" />
                  <span>{t("result.analysisId")}</span>
                </span>
                <span className="font-mono text-slate-800 font-semibold text-[11px] truncate max-w-[120px]" title={result.analysis_id}>
                  {result.analysis_id.slice(0, 8)}...
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <Calendar className="w-3.5 h-3.5 text-slate-400" />
                  <span>{t("result.date")}</span>
                </span>
                <span className="text-slate-800 font-medium">{formattedDate}</span>
              </div>

              <div className="flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <BrainCircuit className="w-3.5 h-3.5 text-slate-400" />
                  <span>{t("result.model")}</span>
                </span>
                <span className="font-mono text-slate-800 font-semibold uppercase">
                  {result.architecture} (v{result.model_version})
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <Cpu className="w-3.5 h-3.5 text-slate-400" />
                  <span>{t("result.device")}</span>
                </span>
                <span className="font-mono text-slate-800 uppercase font-semibold">{result.device}</span>
              </div>

              <div className="flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-slate-400" />
                  <span>{t("result.latency")}</span>
                </span>
                <span className="font-mono text-slate-800 font-semibold">{result.inference_time_ms} ms</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 4. Visual Explainability Section */}
      <ExplainabilityViewer
        originalBase64={result.original_base64}
        heatmapBase64={result.heatmap_base64}
        overlayBase64={result.overlay_base64}
        originalDimensions={result.original_dimensions}
        targetClass={result.target_class}
        disclaimer={result.disclaimer}
      />

      {/* 5. Full Regulatory Disclaimer Card */}
      <Disclaimer variant="card" />
    </div>
  );
}
