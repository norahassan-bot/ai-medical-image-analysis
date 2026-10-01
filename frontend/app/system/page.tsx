"use client";

import React, { useEffect, useState } from "react";
import {
  Server,
  Activity,
  BrainCircuit,
  ExternalLink,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Code2,
  Database,
} from "lucide-react";
import { getHealth, getSystemInfo, ApiError } from "@/lib/api";
import { API_BASE_URL, API_ENDPOINTS } from "@/lib/config";
import type { HealthResponse, SystemInfoResponse } from "@/types/api";
import Disclaimer from "@/components/Disclaimer";
import ErrorState from "@/components/ErrorState";
import { useLanguage } from "@/lib/i18n";

export default function SystemInfoPage() {
  const { t, isRTL } = useLanguage();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [, setSystemInfo] = useState<SystemInfoResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastChecked, setLastChecked] = useState<string>("");

  const loadSystemData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [healthData, infoData] = await Promise.all([
        getHealth(),
        getSystemInfo().catch(() => null),
      ]);
      setHealth(healthData);
      setSystemInfo(infoData);
      setLastChecked(new Date().toLocaleTimeString(isRTL ? "ar-EG" : "en-US"));
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError(t("system.backendFailedTitle"));
      }
      setHealth({ status: "unreachable", model_loaded: false });
      setLastChecked(new Date().toLocaleTimeString(isRTL ? "ar-EG" : "en-US"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSystemData();
  }, []);

  const isHealthy = health?.status === "healthy";
  const isModelLoaded = health?.model_loaded === true;

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* 1. Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <Server className="w-6 h-6 text-medTeal-600" />
            <span>{t("system.pageTitle")}</span>
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            {t("system.pageDesc")}
          </p>
        </div>

        <button
          onClick={loadSystemData}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-2 bg-slate-100 hover:bg-slate-200 border border-slate-300 rounded-xl text-xs text-slate-700 font-semibold transition disabled:opacity-50 shadow-xs"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin text-medTeal-500" : ""}`} />
          <span>{t("system.refreshStatus")}</span>
        </button>
      </div>

      {error && !health && (
        <ErrorState
          title={t("system.backendFailedTitle")}
          message={error}
          onRetry={loadSystemData}
        />
      )}

      {/* 2. Core Service Status Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Backend REST API */}
        <div className="bg-white border border-slate-200 rounded-2xl p-5 space-y-3 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 text-xs font-semibold">
            <span>{t("system.fastapiAsgi")}</span>
            <Activity className="w-4 h-4 text-medTeal-600" />
          </div>

          <div className="flex items-center gap-2.5">
            <span
              className={`w-3 h-3 rounded-full ${
                isHealthy ? "bg-medTeal-500 animate-pulse" : "bg-rose-500"
              }`}
            />
            <span className="text-lg font-bold text-slate-900">
              {isHealthy ? t("system.healthyOnline") : t("system.serviceUnavailable")}
            </span>
          </div>

          <div className="text-xs text-slate-500 space-y-1 pt-2 border-t border-slate-100">
            <div className="flex justify-between">
              <span>{t("system.endpoint")}</span>
              <span className="font-mono text-slate-800 font-semibold">{API_BASE_URL}</span>
            </div>
            {lastChecked && (
              <div className="flex justify-between">
                <span>{t("system.lastPolled")}</span>
                <span className="font-mono text-slate-800">{lastChecked}</span>
              </div>
            )}
          </div>
        </div>

        {/* AI Model Runtime */}
        <div className="bg-white border border-slate-200 rounded-2xl p-5 space-y-3 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 text-xs font-semibold">
            <span>{t("system.pytorchClassifier")}</span>
            <BrainCircuit className="w-4 h-4 text-medTeal-600" />
          </div>

          <div className="flex items-center gap-2.5">
            {isModelLoaded ? (
              <CheckCircle2 className="w-5 h-5 text-medTeal-500 shrink-0" />
            ) : (
              <AlertCircle className="w-5 h-5 text-amber-500 shrink-0" />
            )}
            <span className="text-lg font-bold text-slate-900">
              {isModelLoaded ? t("system.weightsActive") : t("system.unloaded")}
            </span>
          </div>

          <div className="text-xs text-slate-500 space-y-1 pt-2 border-t border-slate-100">
            <div className="flex justify-between">
              <span>{t("system.architecture")}</span>
              <span className="font-mono text-slate-800 font-semibold uppercase">
                {health?.architecture || "ResNet-18"}
              </span>
            </div>
            <div className="flex justify-between">
              <span>{t("system.modelVersion")}</span>
              <span className="font-mono text-slate-800 font-semibold">
                v{health?.model_version || "1.0.0"}
              </span>
            </div>
          </div>
        </div>

        {/* Persistence Layer */}
        <div className="bg-white border border-slate-200 rounded-2xl p-5 space-y-3 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 text-xs font-semibold">
            <span>{t("system.storageEngine")}</span>
            <Database className="w-4 h-4 text-medTeal-600" />
          </div>

          <div className="flex items-center gap-2.5">
            <CheckCircle2 className="w-5 h-5 text-medTeal-500 shrink-0" />
            <span className="text-lg font-bold text-slate-900">{t("system.sqliteActive")}</span>
          </div>

          <div className="text-xs text-slate-500 space-y-1 pt-2 border-t border-slate-100">
            <div className="flex justify-between">
              <span>{t("system.executionDevice")}</span>
              <span className="font-mono text-slate-800 font-semibold uppercase">
                {health?.device || "CPU"}
              </span>
            </div>
            <div className="flex justify-between">
              <span>{t("system.explainability")}</span>
              <span className="font-mono text-medTeal-700 font-semibold">{t("system.gradcamHook")}</span>
            </div>
          </div>
        </div>
      </div>

      {/* 3. API Endpoints Reference Card */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b border-slate-200 pb-3">
          <div className="flex items-center gap-2 text-sm font-bold text-slate-900">
            <Code2 className="w-4 h-4 text-medTeal-600" />
            <span>{t("system.apiSurfaceTitle")}</span>
          </div>
          <a
            href={API_ENDPOINTS.DOCS}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 rounded-xl text-xs font-semibold text-slate-800 border border-slate-300 transition shadow-xs"
          >
            <span>{t("system.openApiDocs")}</span>
            <ExternalLink className={`w-3.5 h-3.5 text-slate-500 ${isRTL ? "rotate-180" : ""}`} />
          </a>
        </div>

        <div className="divide-y divide-slate-100 text-xs font-mono">
          <div className="py-2.5 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="px-2.5 py-0.5 rounded-full bg-medTeal-50 border border-medTeal-200 text-medTeal-800 font-bold text-[10px]">
                GET
              </span>
              <span className="text-slate-900 font-bold">/health</span>
            </div>
            <span className="text-slate-500 text-[11px] font-sans">
              {t("system.endpointHealthDesc")}
            </span>
          </div>

          <div className="py-2.5 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="px-2.5 py-0.5 rounded-full bg-medPink-50 border border-medPink-200 text-medPink-800 font-bold text-[10px]">
                POST
              </span>
              <span className="text-slate-900 font-bold">/analyze</span>
            </div>
            <span className="text-slate-500 text-[11px] font-sans">
              {t("system.endpointAnalyzeDesc")}
            </span>
          </div>

          <div className="py-2.5 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="px-2.5 py-0.5 rounded-full bg-medPink-50 border border-medPink-200 text-medPink-800 font-bold text-[10px]">
                POST
              </span>
              <span className="text-slate-900 font-bold">/predict</span>
            </div>
            <span className="text-slate-500 text-[11px] font-sans">
              {t("system.endpointPredictDesc")}
            </span>
          </div>

          <div className="py-2.5 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="px-2.5 py-0.5 rounded-full bg-medPink-50 border border-medPink-200 text-medPink-800 font-bold text-[10px]">
                POST
              </span>
              <span className="text-slate-900 font-bold">/explain</span>
            </div>
            <span className="text-slate-500 text-[11px] font-sans">
              {t("system.endpointExplainDesc")}
            </span>
          </div>

          <div className="py-2.5 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="px-2.5 py-0.5 rounded-full bg-medTeal-50 border border-medTeal-200 text-medTeal-800 font-bold text-[10px]">
                GET
              </span>
              <span className="text-slate-900 font-bold">/history</span>
            </div>
            <span className="text-slate-500 text-[11px] font-sans">
              {t("system.endpointHistoryDesc")}
            </span>
          </div>

          <div className="py-2.5 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="px-2.5 py-0.5 rounded-full bg-medTeal-50 border border-medTeal-200 text-medTeal-800 font-bold text-[10px]">
                GET
              </span>
              <span className="text-slate-900 font-bold">/history/&#123;analysis_id&#125;</span>
            </div>
            <span className="text-slate-500 text-[11px] font-sans">
              {t("system.endpointDetailDesc")}
            </span>
          </div>
        </div>
      </div>

      <Disclaimer variant="card" />
    </div>
  );
}
