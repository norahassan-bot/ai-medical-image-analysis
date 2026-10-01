"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ArrowLeft,
  Calendar,
  Fingerprint,
  BrainCircuit,
  Cpu,
  Clock,
  Download,
  AlertTriangle,
} from "lucide-react";
import {
  getAnalysisById,
  downloadAnalysisReport,
  triggerBlobDownload,
  getArtifactUrl,
  ApiError,
} from "@/lib/api";
import type { AnalysisDetailResponse } from "@/types/api";
import ConfidenceDisplay from "@/components/ConfidenceDisplay";
import ExplainabilityViewer from "@/components/ExplainabilityViewer";
import LoadingState from "@/components/LoadingState";
import ErrorState from "@/components/ErrorState";
import Disclaimer from "@/components/Disclaimer";
import { useLanguage } from "@/lib/i18n";

export default function AnalysisDetailPage() {
  const { t, isRTL } = useLanguage();
  const params = useParams();
  const analysisId = params?.analysisId as string;

  const [detail, setDetail] = useState<AnalysisDetailResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState<boolean>(false);

  // PDF Download state
  const [downloading, setDownloading] = useState<boolean>(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const loadDetail = async () => {
    if (!analysisId) return;

    setLoading(true);
    setError(null);
    setNotFound(false);

    try {
      const data = await getAnalysisById(analysisId);
      setDetail(data);
    } catch (err: unknown) {
      if (err instanceof ApiError && err.status === 404) {
        setNotFound(true);
      } else if (err instanceof ApiError && err.status === 403) {
        setError(t("auth.accessDenied"));
      } else if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError(t("detail.failedTitle"));
      }
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadReport = async () => {
    if (!analysisId) return;
    setDownloading(true);
    setDownloadError(null);

    try {
      const blob = await downloadAnalysisReport(analysisId);
      triggerBlobDownload(blob, `analysis_${analysisId}.pdf`);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setDownloadError(err.message);
      } else {
        setDownloadError(t("result.pdfError"));
      }
    } finally {
      setDownloading(false);
    }
  };

  useEffect(() => {
    loadDetail();
  }, [analysisId]);

  if (notFound) {
    return (
      <div className="max-w-xl mx-auto py-12 text-center space-y-4">
        <div className="w-16 h-16 rounded-2xl bg-amber-50 border border-amber-200 flex items-center justify-center mx-auto text-amber-600 shadow-xs">
          <AlertTriangle className="w-8 h-8" />
        </div>
        <h2 className="text-xl font-bold text-slate-900">{t("detail.notFoundTitle")}</h2>
        <p className="text-xs text-slate-500">
          {t("detail.notFoundDesc", { id: analysisId })}
        </p>
        <div className="pt-2">
          <Link
            href="/history"
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-semibold rounded-xl border border-slate-300 transition shadow-xs"
          >
            <ArrowLeft className={`w-4 h-4 ${isRTL ? "rotate-180" : ""}`} />
            <span>{t("detail.backToHistory")}</span>
          </Link>
        </div>
      </div>
    );
  }

  const isPneumonia = detail?.prediction.toUpperCase() === "PNEUMONIA";
  const displayPrediction = detail
    ? isPneumonia
      ? t("common.pneumonia")
      : t("common.normal")
    : "";

  const formattedDate = detail?.created_at
    ? new Date(detail.created_at).toLocaleString(isRTL ? "ar-EG" : "en-US", {
        dateStyle: "medium",
        timeStyle: "short",
      })
    : "";

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* 1. Header Navigation & Actions */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div className="flex items-center gap-3">
          <Link
            href="/history"
            className="p-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl border border-slate-300 transition shadow-xs"
            title={t("detail.backToHistory")}
            aria-label={t("detail.backToHistory")}
          >
            <ArrowLeft className={`w-4 h-4 ${isRTL ? "rotate-180" : ""}`} />
          </Link>
          <div>
            <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
              <span>{t("detail.pageTitle")}</span>
            </h1>
            <p className="text-xs text-slate-500 font-mono mt-0.5">
              {t("detail.idPrefix", { id: analysisId })}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleDownloadReport}
            disabled={downloading || loading || !detail}
            className="flex items-center gap-2 px-4 py-2.5 bg-medPink-400 hover:bg-medPink-500 text-white font-bold text-xs rounded-xl shadow-xs transition disabled:opacity-50"
            aria-label={t("result.downloadPdf")}
          >
            <Download className={`w-3.5 h-3.5 ${downloading ? "animate-bounce" : ""}`} />
            <span>{downloading ? t("result.generatingPdf") : t("result.downloadPdf")}</span>
          </button>

          <Link
            href="/history"
            className="px-3.5 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-xl border border-slate-300 transition shadow-xs"
          >
            {t("detail.backToHistory")}
          </Link>
        </div>
      </div>

      {/* Download Error Alert */}
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

      {/* 2. Content State Machine */}
      {loading ? (
        <div className="py-12">
          <LoadingState
            message={t("detail.loadingMsg")}
            subMessage={t("detail.loadingSub")}
          />
        </div>
      ) : error ? (
        <ErrorState
          title={t("detail.failedTitle")}
          message={error}
          onRetry={loadDetail}
        />
      ) : detail ? (
        <div className="space-y-6 animate-fadeIn">
          {/* Disclaimer Banner */}
          <Disclaimer variant="banner" />

          {/* Diagnosis & Metadata Card */}
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs space-y-6">
            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 pb-4">
              <div>
                <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">
                  {t("detail.recordedPredTitle")}
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

              {detail.filename && (
                <div className={isRTL ? "text-left" : "text-right"}>
                  <span className="text-[11px] text-slate-500 block">{t("detail.uploadedScan")}</span>
                  <span className="font-mono text-xs text-slate-800 font-bold">
                    {detail.filename}
                  </span>
                </div>
              )}
            </div>

            {/* Confidence & Metadata Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
              <div className="lg:col-span-2">
                <ConfidenceDisplay
                  prediction={detail.prediction}
                  confidence={detail.confidence}
                  probabilities={detail.probabilities}
                />
              </div>

              <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4 text-xs space-y-3">
                <div className="font-bold text-slate-800 border-b border-slate-200 pb-2">
                  {t("detail.recordMetadata")}
                </div>

                <div className="space-y-2 text-slate-600">
                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-1.5">
                      <Fingerprint className="w-3.5 h-3.5 text-slate-400" />
                      <span>{t("result.analysisId")}</span>
                    </span>
                    <span className="font-mono text-slate-800 font-semibold text-[11px]" title={detail.analysis_id}>
                      {detail.analysis_id.slice(0, 10)}...
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
                      {detail.architecture} (v{detail.model_version})
                    </span>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-1.5">
                      <Cpu className="w-3.5 h-3.5 text-slate-400" />
                      <span>{t("result.device")}</span>
                    </span>
                    <span className="font-mono text-slate-800 uppercase font-semibold">{detail.device}</span>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-1.5">
                      <Clock className="w-3.5 h-3.5 text-slate-400" />
                      <span>{t("result.latency")}</span>
                    </span>
                    <span className="font-mono text-slate-800 font-semibold">{detail.inference_time_ms} ms</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Explainability Visuals */}
          <ExplainabilityViewer
            originalBase64={detail.image_reference ? getArtifactUrl(detail.analysis_id, "original") : undefined}
            heatmapBase64={detail.heatmap_reference ? getArtifactUrl(detail.analysis_id, "heatmap") : undefined}
            overlayBase64={detail.overlay_reference ? getArtifactUrl(detail.analysis_id, "overlay") : undefined}
            targetClass={detail.target_class}
            originalDimensions={detail.original_dimensions}
          />

          <Disclaimer variant="card" />
        </div>
      ) : null}
    </div>
  );
}
