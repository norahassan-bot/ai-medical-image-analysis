"use client";

import React, { useEffect, useState } from "react";
import { CheckCircle2, XCircle, RefreshCw, Server, Cpu, Database } from "lucide-react";
import { getHealth, getSystemInfo } from "@/lib/api";
import { API_ENDPOINTS } from "@/lib/config";
import type { HealthResponse, SystemInfoResponse } from "@/types/api";
import { useLanguage } from "@/lib/i18n";

export default function HealthStatusCard() {
  const { t } = useLanguage();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [systemInfo, setSystemInfo] = useState<SystemInfoResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [hData, sData] = await Promise.allSettled([
        getHealth(),
        getSystemInfo(),
      ]);

      if (hData.status === "fulfilled") {
        setHealth(hData.value);
      } else {
        setError(hData.reason?.message || t("health.offlineFallback"));
        setHealth({ status: "offline", model_loaded: false });
      }

      if (sData.status === "fulfilled") {
        setSystemInfo(sData.value);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const isHealthy = health?.status === "healthy";

  return (
    <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-5">
      <div className="flex items-center justify-between pb-4 border-b border-slate-200">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-medTeal-50 border border-medTeal-200 text-medTeal-600">
            <Server className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-bold text-slate-900 text-base">
              {t("health.cardTitle")}
            </h3>
            <p className="text-xs text-slate-500">
              {t("health.cardDesc")}
            </p>
          </div>
        </div>

        <button
          onClick={loadData}
          disabled={loading}
          className="flex items-center gap-2 text-xs font-semibold px-3 py-1.5 rounded-xl bg-slate-100 text-slate-700 hover:bg-slate-200 hover:text-slate-900 transition disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin text-medTeal-500" : ""}`} />
          <span>{t("health.refreshBtn")}</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Backend Endpoint Status */}
        <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/90 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-slate-500 font-medium">
            <span>{t("dashboard.fastapiServer")}</span>
            <span className="font-mono text-[10px] text-slate-400">GET /health</span>
          </div>
          <div className="my-2.5 flex items-center gap-2">
            {isHealthy ? (
              <>
                <CheckCircle2 className="w-5 h-5 text-medTeal-500 shrink-0" />
                <span className="font-bold text-medTeal-700 text-lg">{t("health.healthy200")}</span>
              </>
            ) : (
              <>
                <XCircle className="w-5 h-5 text-rose-500 shrink-0" />
                <span className="font-bold text-rose-700 text-lg">
                  {loading ? t("header.checking") : t("health.offlineUnreachable")}
                </span>
              </>
            )}
          </div>
          <p className="text-[11px] text-slate-500">
            {isHealthy
              ? t("health.healthyDesc")
              : error || t("health.offlineFallback")}
          </p>
        </div>

        {/* Model Inference Engine Status */}
        <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/90 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-slate-500 font-medium">
            <span>{t("health.modelEngine")}</span>
            <Cpu className="w-4 h-4 text-medTeal-600" />
          </div>
          <div className="my-2.5 flex items-center gap-2">
            <span
              className={`px-2.5 py-1 rounded-full text-xs font-semibold ${
                health?.model_loaded
                  ? "bg-medTeal-50 text-medTeal-700 border border-medTeal-200"
                  : "bg-amber-50 text-amber-700 border border-amber-200"
              }`}
            >
              {health?.model_loaded ? t("health.modelReady") : t("health.awaitingWeights")}
            </span>
          </div>
          <p className="text-[11px] text-slate-500">
            {t("health.modelEngineDesc")}
          </p>
        </div>

        {/* Database Foundation */}
        <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/90 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-slate-500 font-medium">
            <span>{t("health.clinicalStorage")}</span>
            <Database className="w-4 h-4 text-medTeal-600" />
          </div>
          <div className="my-2.5 flex items-center gap-2">
            <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-200/70 text-slate-700 border border-slate-300">
              {t("health.sqliteDb")}
            </span>
          </div>
          <p className="text-[11px] text-slate-500">
            {t("health.storageDesc")}
          </p>
        </div>
      </div>

      {/* Raw Response inspection */}
      <div className="pt-3 border-t border-slate-200 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
        <div className="flex items-center gap-2">
          <span className="font-mono text-slate-400">{t("health.apiResponse")}</span>
          <code className="bg-slate-100 px-2 py-0.5 rounded text-slate-700 font-mono text-[11px] border border-slate-200">
            {JSON.stringify(health || { status: "pending" })}
          </code>
        </div>
        {systemInfo && (
          <span className="text-[11px] text-slate-500">
            {t("health.env")}{" "}
            <span className="text-slate-700 font-semibold">{systemInfo.environment}</span> |{" "}
            {t("health.docs")}{" "}
            <a
              href={API_ENDPOINTS.DOCS}
              target="_blank"
              rel="noreferrer"
              className="text-medTeal-600 font-semibold underline hover:text-medTeal-700"
            >
              /docs
            </a>
          </span>
        )}
      </div>
    </div>
  );
}
