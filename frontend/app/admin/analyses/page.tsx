"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  History,
  FileSpreadsheet,
  RefreshCw,
  AlertTriangle,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  Calendar,
  Eye,
} from "lucide-react";
import { getAdminAnalyses } from "@/lib/api";
import type { AnalysisHistoryItem } from "@/types/api";
import { useAuth } from "@/lib/auth/AuthContext";
import { useLanguage } from "@/lib/i18n";

export default function AdminAnalysesPage() {
  const router = useRouter();
  const { isAdmin, role, isLoading: authLoading } = useAuth();
  const { t, isRTL } = useLanguage();

  const [items, setItems] = useState<AnalysisHistoryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && !isAdmin) {
      router.push("/login");
    }
  }, [authLoading, isAdmin, router]);

  const loadAnalyses = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getAdminAnalyses(50, 0);
      setItems(res.items);
      setTotal(res.total);
    } catch (err: any) {
      setError(err?.message || "Failed to load platform analyses.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isAdmin) {
      loadAnalyses();
    }
  }, [isAdmin]);

  if (authLoading || (loading && items.length === 0)) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] space-y-3">
        <RefreshCw className="w-8 h-8 animate-spin text-medPink-600" />
        <p className="text-sm font-semibold text-slate-600">{t("common.loading")}</p>
      </div>
    );
  }

  if (!isAdmin || role !== "ADMIN") {
    return null;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="p-6 sm:p-8 bg-white rounded-3xl border border-slate-200 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-medPink-100/70 border border-medPink-200 rounded-full text-xs font-bold text-medPink-800 mb-2">
            <FileSpreadsheet className="w-3.5 h-3.5" />
            <span>{t("nav.adminAnalyses")}</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
            {t("admin.analysesTitle")}
          </h1>
          <p className="text-xs sm:text-sm text-slate-600 mt-1 leading-relaxed">
            {t("admin.analysesDesc")}
          </p>
        </div>

        <button
          onClick={loadAnalyses}
          disabled={loading}
          className="self-start md:self-auto inline-flex items-center gap-2 px-4 py-2 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-xl text-xs font-semibold text-slate-700 shadow-xs transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          <span>{t("system.refreshStatus")}</span>
        </button>
      </div>

      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 text-rose-800 rounded-2xl text-xs flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 text-rose-500 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Summary status */}
      <div className="flex items-center justify-between text-xs text-slate-500 px-1">
        <span>
          {t("history.showingCount")
            .replace("{count}", items.length.toString())
            .replace("{total}", total.toString())}
        </span>
        <span>{t("history.orderedNewest")}</span>
      </div>

      {/* Records Container */}
      <div className="bg-white rounded-3xl border border-slate-200 shadow-xs overflow-hidden">
        {items.length === 0 ? (
          <div className="p-12 text-center text-slate-400">
            <History className="w-12 h-12 mx-auto mb-3 opacity-40" />
            <p className="text-sm font-medium">{t("history.emptyTitle")}</p>
          </div>
        ) : (
          <>
            {/* Desktop Table */}
            <div className="hidden md:block overflow-x-auto">
              <table className="w-full text-left rtl:text-right border-collapse">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50/75 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                    <th className="py-3.5 px-6">{t("history.colId")}</th>
                    <th className="py-3.5 px-6">{t("history.colDate")}</th>
                    <th className="py-3.5 px-6">{t("history.colPrediction")}</th>
                    <th className="py-3.5 px-6">{t("history.colConfidence")}</th>
                    <th className="py-3.5 px-6">{t("history.colModel")}</th>
                    <th className="py-3.5 px-6 text-center">{t("history.colAction")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-xs">
                  {items.map((item) => {
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
                        <td className="py-4 px-6 text-slate-500 font-mono text-[11px]">
                          {item.model_version} ({item.architecture || "DenseNet"})
                        </td>
                        <td className="py-4 px-6 text-center">
                          <Link
                            href={`/history/${item.analysis_id}`}
                            className="inline-flex items-center gap-1.5 px-3 py-1 bg-medPink-50 text-medPink-700 hover:bg-medPink-100 border border-medPink-200 rounded-lg text-xs font-semibold transition"
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
              {items.map((item) => {
                const isPneumonia = item.prediction.toUpperCase() === "PNEUMONIA";
                return (
                  <div key={item.analysis_id} className="p-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs font-bold text-slate-700">
                        {item.analysis_id.slice(0, 8)}...
                      </span>
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
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
                      className="w-full mt-2 py-2 bg-medPink-50 text-medPink-700 hover:bg-medPink-100 border border-medPink-200 rounded-xl text-xs font-semibold transition flex items-center justify-center gap-1.5"
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
