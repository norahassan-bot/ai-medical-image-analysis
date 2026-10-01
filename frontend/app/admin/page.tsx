"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  BarChart3,
  Users,
  Activity,
  ShieldCheck,
  ScanLine,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  Server,
  FileSpreadsheet,
} from "lucide-react";
import { getAdminStatistics, ApiError } from "@/lib/api";
import type { AdminStatsResponse } from "@/types/api";
import { useAuth } from "@/lib/auth/AuthContext";
import { useLanguage } from "@/lib/i18n";

export default function AdminDashboardPage() {
  const router = useRouter();
  const { isAdmin, role, isLoading: authLoading } = useAuth();
  const { t } = useLanguage();

  const [stats, setStats] = useState<AdminStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && !isAdmin) {
      router.push("/login");
    }
  }, [authLoading, isAdmin, router]);

  const loadStats = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getAdminStatistics();
      setStats(data);
    } catch (err: any) {
      if (err instanceof ApiError && err.status === 403) {
        setError(t("auth.adminOnly"));
      } else {
        setError(err?.message || "Failed to load admin statistics.");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isAdmin) {
      loadStats();
    }
  }, [isAdmin]);

  if (authLoading || (loading && !stats)) {
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
      {/* Top Header Card */}
      <div className="p-6 sm:p-8 bg-gradient-to-r from-medPink-50 via-white to-medTeal-50 rounded-3xl border border-slate-200 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-medPink-100/70 border border-medPink-200 rounded-full text-xs font-bold text-medPink-800 mb-2">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>{t("nav.adminDashboard")}</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
            {t("admin.statsTitle")}
          </h1>
          <p className="text-xs sm:text-sm text-slate-600 mt-1 max-w-2xl leading-relaxed">
            {t("admin.statsDesc")}
          </p>
        </div>

        <button
          onClick={loadStats}
          disabled={loading}
          className="self-start md:self-auto inline-flex items-center gap-2 px-4 py-2 bg-white hover:bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-700 shadow-xs transition"
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

      {/* Metrics Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Analyses */}
        <div className="p-5 bg-white rounded-2xl border border-slate-200 shadow-xs flex items-center justify-between">
          <div>
            <div className="text-xs font-medium text-slate-500">{t("admin.totalAnalyses")}</div>
            <div className="text-2xl font-bold text-slate-900 mt-1">
              {stats?.total_analyses ?? 0}
            </div>
            <div className="text-[11px] text-medTeal-600 font-medium mt-1">
              {stats?.normal_count ?? 0} {t("common.normal")} / {stats?.pneumonia_count ?? 0}{" "}
              {t("common.pneumonia")}
            </div>
          </div>
          <div className="w-12 h-12 rounded-xl bg-medTeal-50 border border-medTeal-200 flex items-center justify-center text-medTeal-600">
            <BarChart3 className="w-6 h-6" />
          </div>
        </div>

        {/* Total Users */}
        <div className="p-5 bg-white rounded-2xl border border-slate-200 shadow-xs flex items-center justify-between">
          <div>
            <div className="text-xs font-medium text-slate-500">{t("admin.totalUsers")}</div>
            <div className="text-2xl font-bold text-slate-900 mt-1">
              {stats?.total_users ?? 0}
            </div>
            <div className="text-[11px] text-medPink-600 font-medium mt-1">
              {stats?.active_users ?? 0} {t("admin.statusActive")} / {stats?.admin_users ?? 0}{" "}
              {t("admin.adminUsers")}
            </div>
          </div>
          <div className="w-12 h-12 rounded-xl bg-medPink-50 border border-medPink-200 flex items-center justify-center text-medPink-600">
            <Users className="w-6 h-6" />
          </div>
        </div>

        {/* Avg Confidence */}
        <div className="p-5 bg-white rounded-2xl border border-slate-200 shadow-xs flex items-center justify-between">
          <div>
            <div className="text-xs font-medium text-slate-500">{t("admin.avgConfidence")}</div>
            <div className="text-2xl font-bold text-slate-900 mt-1">
              {stats?.avg_confidence ? `${(stats.avg_confidence * 100).toFixed(1)}%` : "N/A"}
            </div>
            <div className="text-[11px] text-slate-500 font-medium mt-1">
              {stats?.architecture ?? "DenseNet-121"}
            </div>
          </div>
          <div className="w-12 h-12 rounded-xl bg-indigo-50 border border-indigo-200 flex items-center justify-center text-indigo-600">
            <Activity className="w-6 h-6" />
          </div>
        </div>

        {/* System Environment */}
        <div className="p-5 bg-white rounded-2xl border border-slate-200 shadow-xs flex items-center justify-between">
          <div>
            <div className="text-xs font-medium text-slate-500">{t("health.env")}</div>
            <div className="text-xl font-bold text-slate-900 mt-1 capitalize">
              {stats?.environment ?? "development"}
            </div>
            <div className="text-[11px] text-medTeal-600 font-semibold mt-1 flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>v{stats?.model_version ?? "1.0.0"}</span>
            </div>
          </div>
          <div className="w-12 h-12 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-center text-slate-600">
            <Server className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* Admin Quick Action Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
        <Link
          href="/admin/analyses"
          className="p-6 bg-white rounded-2xl border border-slate-200 hover:border-medPink-300 hover:shadow-md transition-all group"
        >
          <div className="w-10 h-10 rounded-xl bg-medPink-50 text-medPink-600 flex items-center justify-center mb-3 group-hover:scale-105 transition-transform">
            <FileSpreadsheet className="w-5 h-5" />
          </div>
          <h3 className="text-sm font-bold text-slate-900">{t("nav.adminAnalyses")}</h3>
          <p className="text-xs text-slate-500 mt-1 leading-relaxed">{t("admin.analysesDesc")}</p>
        </Link>

        <Link
          href="/admin/users"
          className="p-6 bg-white rounded-2xl border border-slate-200 hover:border-medTeal-300 hover:shadow-md transition-all group"
        >
          <div className="w-10 h-10 rounded-xl bg-medTeal-50 text-medTeal-600 flex items-center justify-center mb-3 group-hover:scale-105 transition-transform">
            <Users className="w-5 h-5" />
          </div>
          <h3 className="text-sm font-bold text-slate-900">{t("nav.adminUsers")}</h3>
          <p className="text-xs text-slate-500 mt-1 leading-relaxed">{t("admin.usersDesc")}</p>
        </Link>

        <Link
          href="/admin/system"
          className="p-6 bg-white rounded-2xl border border-slate-200 hover:border-indigo-300 hover:shadow-md transition-all group"
        >
          <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center mb-3 group-hover:scale-105 transition-transform">
            <Server className="w-5 h-5" />
          </div>
          <h3 className="text-sm font-bold text-slate-900">{t("nav.adminSystem")}</h3>
          <p className="text-xs text-slate-500 mt-1 leading-relaxed">
            {t("system.pageDesc")}
          </p>
        </Link>
      </div>
    </div>
  );
}
