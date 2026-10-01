"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ShieldAlert,
  Server,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  Cpu,
  Database,
  ExternalLink,
} from "lucide-react";
import { getAdminSystemInfo } from "@/lib/api";
import type { SystemInfoResponse } from "@/types/api";
import { useAuth } from "@/lib/auth/AuthContext";
import { useLanguage } from "@/lib/i18n";
import { API_ENDPOINTS } from "@/lib/config";

export default function AdminSystemPage() {
  const router = useRouter();
  const { isAdmin, role, isLoading: authLoading } = useAuth();
  const { t, isRTL } = useLanguage();

  const [sysInfo, setSysInfo] = useState<SystemInfoResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && !isAdmin) {
      router.push("/login");
    }
  }, [authLoading, isAdmin, router]);

  const loadSysInfo = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getAdminSystemInfo();
      setSysInfo(data);
    } catch (err: any) {
      setError(err?.message || "Failed to load system information.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isAdmin) {
      loadSysInfo();
    }
  }, [isAdmin]);

  if (authLoading || (loading && !sysInfo)) {
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
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-indigo-100/70 border border-indigo-200 rounded-full text-xs font-bold text-indigo-800 mb-2">
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>{t("nav.adminSystem")}</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
            {t("system.pageTitle")}
          </h1>
          <p className="text-xs sm:text-sm text-slate-600 mt-1 leading-relaxed">
            {t("system.pageDesc")}
          </p>
        </div>

        <button
          onClick={loadSysInfo}
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

      {/* Grid Diagnostic Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Backend & Environment */}
        <div className="p-6 bg-white rounded-3xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-medTeal-50 border border-medTeal-200 flex items-center justify-center text-medTeal-600">
              <Server className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-900">{t("system.fastapiAsgi")}</h2>
              <span className="text-[11px] text-medTeal-700 font-semibold">{t("system.healthyOnline")}</span>
            </div>
          </div>

          <div className="space-y-2.5 text-xs">
            <div className="flex justify-between py-2 border-b border-slate-100">
              <span className="text-slate-500">{t("health.env")}</span>
              <span className="font-semibold text-slate-800 capitalize">{sysInfo?.environment}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-slate-100">
              <span className="text-slate-500">{t("result.model")}</span>
              <span className="font-mono text-slate-800">v{sysInfo?.version}</span>
            </div>
            <div className="flex justify-between py-2">
              <span className="text-slate-500">{t("system.endpoint")}</span>
              <span className="font-mono text-[11px] text-slate-600">{sysInfo?.docs_url}</span>
            </div>
          </div>

          <a
            href={API_ENDPOINTS.DOCS}
            target="_blank"
            rel="noreferrer"
            className="w-full mt-2 py-2.5 px-4 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-xl text-xs font-semibold text-slate-700 flex items-center justify-center gap-2 transition"
          >
            <span>{t("system.openApiDocs")}</span>
            <ExternalLink className={`w-3.5 h-3.5 ${isRTL ? "rotate-180" : ""}`} />
          </a>
        </div>

        {/* Database & Persistence */}
        <div className="p-6 bg-white rounded-3xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-medPink-50 border border-medPink-200 flex items-center justify-center text-medPink-600">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-900">{t("system.storageEngine")}</h2>
              <span className="text-[11px] text-medPink-700 font-semibold">{t("system.sqliteActive")}</span>
            </div>
          </div>

          <div className="space-y-2.5 text-xs">
            <div className="flex justify-between py-2 border-b border-slate-100">
              <span className="text-slate-500">Database Engine</span>
              <span className="font-semibold text-slate-800">SQLite3 (WAL Mode)</span>
            </div>
            <div className="flex justify-between py-2 border-b border-slate-100">
              <span className="text-slate-500">Multi-tenant Privacy</span>
              <span className="font-semibold text-medTeal-700">Strict User Isolation</span>
            </div>
            <div className="flex justify-between py-2">
              <span className="text-slate-500">Authentication Scheme</span>
              <span className="font-semibold text-slate-800">Bcrypt + Signed JWT (HS256)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
