"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Pill, RefreshCw, ShieldAlert, ArrowLeft, History, Users, Eye } from "lucide-react";
import { getAdminPrescriptions } from "@/lib/api";
import type { PrescriptionHistoryItem } from "@/types/api";
import { useLanguage } from "@/lib/i18n";
import { useAuth } from "@/lib/auth/AuthContext";
import PrescriptionHistoryTable from "@/components/prescription/PrescriptionHistoryTable";

export default function AdminPrescriptionsPage() {
  const { t, isRTL } = useLanguage();
  const { user, role, isAuthenticated, isLoading: authLoading } = useAuth();

  const [items, setItems] = useState<PrescriptionHistoryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  const isAdmin = role === "ADMIN";

  const loadAdminPrescriptions = async () => {
    setLoading(true);
    try {
      const res = await getAdminPrescriptions(100, 0);
      setItems(res.items || []);
      setTotal(res.total || 0);
    } catch (err) {
      console.error("Failed to load admin prescriptions:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isAdmin) {
      loadAdminPrescriptions();
    }
  }, [isAdmin]);

  if (authLoading) {
    return (
      <div className="p-12 text-center bg-white rounded-3xl border border-slate-200 shadow-xs max-w-md mx-auto space-y-3">
        <RefreshCw className="w-8 h-8 text-medTeal-600 animate-spin mx-auto" />
        <p className="text-xs text-slate-500">{t("common.loading")}</p>
      </div>
    );
  }

  if (!isAdmin) {
    return (
      <div className="p-8 sm:p-12 text-center bg-white rounded-3xl border border-rose-200 shadow-xs max-w-md mx-auto space-y-4">
        <div className="w-12 h-12 rounded-2xl bg-rose-50 border border-rose-200 flex items-center justify-center mx-auto text-rose-600">
          <ShieldAlert className="w-6 h-6" />
        </div>
        <div className="space-y-1">
          <h3 className="text-base font-bold text-slate-900">{t("auth.accessDenied")}</h3>
          <p className="text-xs text-slate-500">{t("auth.adminOnlyDescription")}</p>
        </div>
        <div className="pt-2">
          <Link
            href="/"
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-slate-900 text-white rounded-xl text-xs font-bold shadow-xs hover:bg-slate-800 transition"
          >
            <ArrowLeft className={`w-4 h-4 ${isRTL ? "rotate-180" : ""}`} />
            <span>{t("auth.backToClinicalPortal")}</span>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-6xl mx-auto w-full">
      {/* Header Banner */}
      <div className="p-5 sm:p-8 bg-gradient-to-r from-slate-900 via-slate-800 to-medTeal-950 text-white rounded-3xl shadow-md flex flex-col md:flex-row md:items-center justify-between gap-5 relative overflow-hidden">
        <div className="space-y-2 relative z-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-medTeal-500/20 border border-medTeal-400/30 rounded-full text-xs font-bold text-medTeal-300">
            <Pill className="w-3.5 h-3.5 text-medTeal-400" />
            <span>{t("auth.adminRole")}</span>
          </div>

          <h1 className="text-xl sm:text-3xl font-extrabold tracking-tight">
            {t("prescription.adminHistoryTitle")}
          </h1>
          <p className="text-xs sm:text-sm text-slate-300 max-w-2xl leading-relaxed">
            {t("prescription.adminHistoryDesc")}
          </p>
        </div>

        {/* Stats count badge */}
        <div className="flex items-center gap-3 p-3.5 rounded-2xl bg-white/10 border border-white/10 backdrop-blur-md shrink-0">
          <History className="w-6 h-6 text-medTeal-400" />
          <div>
            <div className="text-[11px] text-slate-300 font-medium">{t("dashboard.totalRecorded")}</div>
            <div className="text-xl font-extrabold text-white">{total}</div>
          </div>
        </div>
      </div>

      {/* Prescription List Table */}
      {loading ? (
        <div className="p-12 text-center bg-white rounded-3xl border border-slate-200 shadow-xs space-y-3">
          <RefreshCw className="w-8 h-8 text-medTeal-600 animate-spin mx-auto" />
          <p className="text-xs text-slate-500">{t("common.loading")}</p>
        </div>
      ) : (
        <PrescriptionHistoryTable items={items} isAdminView={true} />
      )}
    </div>
  );
}
