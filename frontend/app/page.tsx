"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  ScanLine,
  History,
  BrainCircuit,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  Clock,
  Sparkles,
  Server,
  PlusCircle,
  User as UserIcon,
  Activity,
  FileSpreadsheet,
  Eye,
  RefreshCw,
  Pill,
} from "lucide-react";
import { getHealth, getHistory, getSystemInfo } from "@/lib/api";
import type { HealthResponse, AnalysisHistoryItem, SystemInfoResponse } from "@/types/api";
import Disclaimer from "@/components/Disclaimer";
import { useLanguage } from "@/lib/i18n";
import { useAuth } from "@/lib/auth/AuthContext";

export default function ClinicalDashboardPage() {
  const { t, isRTL } = useLanguage();
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();

  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [systemInfo, setSystemInfo] = useState<SystemInfoResponse | null>(null);
  const [recentAnalyses, setRecentAnalyses] = useState<AnalysisHistoryItem[]>([]);
  const [totalAnalyses, setTotalAnalyses] = useState<number>(0);
  const [loading, setLoading] = useState(true);

  const loadDashboardData = async () => {
    setLoading(true);
    try {
      const [healthData, sysData, historyData] = await Promise.allSettled([
        getHealth(),
        getSystemInfo(),
        getHistory(5, 0),
      ]);

      if (healthData.status === "fulfilled") setHealth(healthData.value);
      if (sysData.status === "fulfilled") setSystemInfo(sysData.value);
      if (historyData.status === "fulfilled") {
        setRecentAnalyses(historyData.value.items);
        setTotalAnalyses(historyData.value.total);
      }
    } catch (err) {
      console.error("Dashboard data load error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  const isHealthy = health?.status === "healthy";
  const isModelLoaded = health?.model_loaded === true;

  const normalCount = recentAnalyses.filter((i) => i.prediction.toUpperCase() === "NORMAL").length;
  const pneumoniaCount = recentAnalyses.filter((i) => i.prediction.toUpperCase() === "PNEUMONIA").length;

  return (
    <div className="space-y-6 max-w-6xl mx-auto w-full">
      {/* 1. Header Hero Banner */}
      <div className="p-5 sm:p-8 bg-gradient-to-r from-medPink-50 via-white to-medTeal-50 rounded-3xl border border-slate-200 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-5 sm:gap-6 relative overflow-hidden">
        <div className="space-y-2 relative z-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-medTeal-100/80 border border-medTeal-200 rounded-full text-xs font-bold text-medTeal-800">
            <Activity className="w-3.5 h-3.5" />
            <span>{t("user.dashboardTitle")}</span>
          </div>

          <h1 className="text-xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            {isRTL ? "منظومة التحليل الإشعاعي بالذكاء الاصطناعي" : "Pediatric Chest X-Ray AI Analysis"}
          </h1>
          <p className="text-xs sm:text-sm text-slate-600 max-w-2xl leading-relaxed">
            {t("user.dashboardSubtitle")}
          </p>
        </div>

        {/* Quick Action Buttons */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5 sm:gap-3 w-full sm:w-auto relative z-10">
          <Link
            href="/analysis"
            className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-gradient-to-r from-medPink-500 to-medTeal-600 hover:from-medPink-600 hover:to-medTeal-700 text-white rounded-xl text-xs sm:text-sm font-bold shadow-md hover:shadow-lg transition-all text-center"
          >
            <PlusCircle className="w-4 h-4" />
            <span>{t("dashboard.startAnalysis")}</span>
          </Link>

          <Link
            href="/account"
            className="inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 rounded-xl text-xs sm:text-sm font-semibold shadow-xs transition text-center"
          >
            <UserIcon className="w-4 h-4 text-slate-500" />
            <span>{t("nav.myAccount")}</span>
          </Link>
        </div>
      </div>

      {/* 2. Medical Disclaimer */}
      <Disclaimer variant="banner" />

      {/* 3. Telemetry Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        {/* Total Studies */}
        <div className="p-4 sm:p-5 bg-white rounded-2xl border border-slate-200 shadow-xs flex items-center justify-between">
          <div>
            <div className="text-xs font-medium text-slate-500">{t("user.totalCompleted")}</div>
            <div className="text-2xl font-bold text-slate-900 mt-1">
              {loading ? "..." : totalAnalyses}
            </div>
            <div className="text-[11px] text-slate-400 mt-1">{t("dashboard.sqlitePersistent")}</div>
          </div>
          <div className="w-11 h-11 sm:w-12 sm:h-12 rounded-xl bg-medTeal-50 border border-medTeal-200 flex items-center justify-center text-medTeal-600 shrink-0 ms-2">
            <FileSpreadsheet className="w-5 h-5 sm:w-6 sm:h-6" />
          </div>
        </div>

        {/* Normal Radiographs */}
        <div className="p-4 sm:p-5 bg-white rounded-2xl border border-slate-200 shadow-xs flex items-center justify-between">
          <div>
            <div className="text-xs font-medium text-slate-500">{t("user.normalCount")}</div>
            <div className="text-2xl font-bold text-medTeal-700 mt-1">
              {loading ? "..." : normalCount}
            </div>
            <div className="text-[11px] text-medTeal-600 font-medium mt-1">
              {t("common.normalDisplay")}
            </div>
          </div>
          <div className="w-11 h-11 sm:w-12 sm:h-12 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-600 shrink-0 ms-2">
            <CheckCircle2 className="w-5 h-5 sm:w-6 sm:h-6" />
          </div>
        </div>

        {/* Pneumonia Cases Detected */}
        <div className="p-4 sm:p-5 bg-white rounded-2xl border border-slate-200 shadow-xs flex items-center justify-between">
          <div>
            <div className="text-xs font-medium text-slate-500">{t("user.pneumoniaCount")}</div>
            <div className="text-2xl font-bold text-rose-700 mt-1">
              {loading ? "..." : pneumoniaCount}
            </div>
            <div className="text-[11px] text-rose-600 font-medium mt-1">
              {t("common.pneumoniaDisplay")}
            </div>
          </div>
          <div className="w-11 h-11 sm:w-12 sm:h-12 rounded-xl bg-rose-50 border border-rose-200 flex items-center justify-center text-rose-600 shrink-0 ms-2">
            <AlertCircle className="w-5 h-5 sm:w-6 sm:h-6" />
          </div>
        </div>

        {/* AI Engine Status */}
        <div className="p-4 sm:p-5 bg-white rounded-2xl border border-slate-200 shadow-xs flex items-center justify-between">
          <div>
            <div className="text-xs font-medium text-slate-500">{t("dashboard.aiEngine")}</div>
            <div className="text-sm font-bold text-slate-900 mt-1 flex items-center gap-1.5">
              <span
                className={`w-2.5 h-2.5 rounded-full ${
                  isHealthy ? "bg-medTeal-500 animate-pulse" : "bg-rose-500"
                }`}
              />
              {loading
                ? t("common.checking")
                : isModelLoaded
                ? t("dashboard.weightsLoaded")
                : t("dashboard.uninitialized")}
            </div>
            <div className="text-[11px] text-slate-400 font-mono mt-1">
              {health?.architecture ? `Arch: ${health.architecture.toUpperCase()}` : "PyTorch ResNet-18"}
            </div>
          </div>
          <div className="w-11 h-11 sm:w-12 sm:h-12 rounded-xl bg-medPink-50 border border-medPink-200 flex items-center justify-center text-medPink-600 shrink-0 ms-2">
            <BrainCircuit className="w-5 h-5 sm:w-6 sm:h-6" />
          </div>
        </div>
      </div>

      {/* 4. Primary Clinical AI Tools Suite */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
        {/* Tool 1: Chest X-Ray AI Analysis */}
        <div className="p-6 bg-gradient-to-br from-white via-medPink-50/20 to-medPink-50/50 rounded-3xl border border-slate-200/90 shadow-xs flex flex-col justify-between space-y-4 hover:shadow-md transition">
          <div className="space-y-3">
            <div className="w-12 h-12 rounded-2xl bg-medPink-500 text-white flex items-center justify-center shadow-sm">
              <ScanLine className="w-6 h-6" />
            </div>
            <div className="space-y-1">
              <h3 className="text-base sm:text-lg font-extrabold text-slate-900">
                {t("nav.analysis")}
              </h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                {t("user.quickAnalysisDesc")}
              </p>
            </div>
          </div>
          <div className="pt-2">
            <Link
              href="/analysis"
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-slate-900 hover:bg-slate-800 text-white rounded-xl text-xs font-bold shadow-xs transition"
            >
              <span>{t("dashboard.startAnalysis")}</span>
              <ArrowRight className={`w-3.5 h-3.5 ${isRTL ? "rotate-180" : ""}`} />
            </Link>
          </div>
        </div>

        {/* Tool 2: Prescription Reader */}
        <div className="p-6 bg-gradient-to-br from-white via-medTeal-50/20 to-medTeal-50/50 rounded-3xl border border-slate-200/90 shadow-xs flex flex-col justify-between space-y-4 hover:shadow-md transition">
          <div className="space-y-3">
            <div className="w-12 h-12 rounded-2xl bg-medTeal-600 text-white flex items-center justify-center shadow-sm">
              <Pill className="w-6 h-6" />
            </div>
            <div className="space-y-1">
              <h3 className="text-base sm:text-lg font-extrabold text-slate-900">
                {t("dashboard.prescriptionCardTitle")}
              </h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                {t("dashboard.prescriptionCardDesc")}
              </p>
            </div>
          </div>
          <div className="pt-2">
            <Link
              href="/user/prescription"
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-medPink-500 to-medTeal-600 hover:from-medPink-600 hover:to-medTeal-700 text-white rounded-xl text-xs font-bold shadow-xs transition"
            >
              <span>{t("dashboard.startPrescription")}</span>
              <ArrowRight className={`w-3.5 h-3.5 ${isRTL ? "rotate-180" : ""}`} />
            </Link>
          </div>
        </div>
      </div>

      {/* 5. Recent Analyses Section */}
      <div className="bg-white rounded-3xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-4 sm:p-6 border-b border-slate-200 flex flex-col xs:flex-row xs:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <History className="w-5 h-5 text-medTeal-600" />
            <h2 className="text-sm sm:text-base font-bold text-slate-900">{t("user.recentAnalyses")}</h2>
          </div>

          {totalAnalyses > 0 && (
            <Link
              href="/history"
              className="inline-flex items-center gap-1.5 text-xs font-bold text-medPink-600 hover:text-medPink-700 transition"
            >
              <span>{t("user.viewAllHistory")}</span>
              <ArrowRight className={`w-3.5 h-3.5 ${isRTL ? "rotate-180" : ""}`} />
            </Link>
          )}
        </div>

        {loading ? (
          <div className="p-8 text-center text-slate-400">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-medTeal-500" />
            <p className="text-xs">{t("common.loading")}</p>
          </div>
        ) : recentAnalyses.length === 0 ? (
          <div className="p-8 sm:p-10 text-center space-y-3">
            <div className="w-12 h-12 rounded-2xl bg-slate-100 border border-slate-200 flex items-center justify-center mx-auto text-slate-400">
              <ScanLine className="w-6 h-6" />
            </div>
            <h3 className="text-sm font-bold text-slate-800">{t("dashboard.noAnalysesYet")}</h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              {t("user.quickAnalysisDesc")}
            </p>
            <div className="pt-2">
              <Link
                href="/analysis"
                className="inline-flex items-center gap-2 px-4 py-2.5 bg-medPink-600 hover:bg-medPink-700 text-white text-xs font-bold rounded-xl shadow-xs transition"
              >
                <PlusCircle className="w-3.5 h-3.5" />
                <span>{t("dashboard.performFirst")}</span>
              </Link>
            </div>
          </div>
        ) : (
          <>
            {/* Desktop Table */}
            <div className="hidden md:block overflow-x-auto">
              <table className="w-full text-left rtl:text-right border-collapse text-xs">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50/75 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                    <th className="py-3.5 px-6">{t("history.colId")}</th>
                    <th className="py-3.5 px-6">{t("history.colDate")}</th>
                    <th className="py-3.5 px-6">{t("history.colPrediction")}</th>
                    <th className="py-3.5 px-6">{t("history.colConfidence")}</th>
                    <th className="py-3.5 px-6 text-center">{t("history.colAction")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {recentAnalyses.map((item) => {
                    const isPneumonia = item.prediction.toUpperCase() === "PNEUMONIA";
                    return (
                      <tr key={item.analysis_id} className="hover:bg-slate-50/50 transition">
                        <td className="py-4 px-6 font-mono font-medium text-slate-700">
                          {item.analysis_id.slice(0, 8)}...
                        </td>
                        <td className="py-4 px-6 text-slate-500 font-mono text-[11px]">
                          {item.created_at ? new Date(item.created_at).toLocaleString() : "—"}
                        </td>
                        <td className="py-4 px-6">
                          <span
                            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold ${
                              isPneumonia
                                ? "bg-rose-50 text-rose-700 border border-rose-200"
                                : "bg-medTeal-50 text-medTeal-700 border border-medTeal-200"
                            }`}
                          >
                            {isPneumonia ? t("common.pneumoniaDisplay") : t("common.normalDisplay")}
                          </span>
                        </td>
                        <td className="py-4 px-6 font-bold text-slate-800">
                          {(item.confidence * 100).toFixed(1)}%
                        </td>
                        <td className="py-4 px-6 text-center">
                          <Link
                            href={`/history/${item.analysis_id}`}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-medPink-50 text-medPink-700 hover:bg-medPink-100 border border-medPink-200 rounded-lg text-xs font-semibold transition"
                          >
                            <Eye className="w-3.5 h-3.5" />
                            <span>{t("history.viewAction")}</span>
                          </Link>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Mobile Cards */}
            <div className="md:hidden divide-y divide-slate-100">
              {recentAnalyses.map((item) => {
                const isPneumonia = item.prediction.toUpperCase() === "PNEUMONIA";
                return (
                  <div key={item.analysis_id} className="p-4 space-y-3">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-mono text-xs font-bold text-slate-700 truncate">
                        {item.analysis_id.slice(0, 8)}...
                      </span>
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold shrink-0 ${
                          isPneumonia
                            ? "bg-rose-50 text-rose-700 border border-rose-200"
                            : "bg-medTeal-50 text-medTeal-700 border border-medTeal-200"
                        }`}
                      >
                        {isPneumonia ? t("common.pneumoniaDisplay") : t("common.normalDisplay")}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-xs text-slate-600">
                      <div>
                        <span className="text-slate-400 block text-[10px]">{t("history.colConfidence")}</span>
                        <span className="font-bold text-slate-800">
                          {(item.confidence * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-400 block text-[10px]">{t("history.colDate")}</span>
                        <span className="text-[11px] font-mono">
                          {item.created_at ? new Date(item.created_at).toLocaleDateString() : "—"}
                        </span>
                      </div>
                    </div>

                    <Link
                      href={`/history/${item.analysis_id}`}
                      className="w-full mt-2 py-2.5 bg-medPink-50 text-medPink-700 hover:bg-medPink-100 border border-medPink-200 rounded-xl text-xs font-semibold transition flex items-center justify-center gap-1.5 shadow-xs"
                    >
                      <Eye className="w-3.5 h-3.5" />
                      <span>{t("history.viewAction")}</span>
                    </Link>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
