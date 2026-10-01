"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Pill, PlusCircle, RefreshCw, History, FileSpreadsheet } from "lucide-react";
import { getPrescriptionHistory } from "@/lib/api";
import type { PrescriptionHistoryItem } from "@/types/api";
import { useLanguage } from "@/lib/i18n";
import PrescriptionHistoryTable from "@/components/prescription/PrescriptionHistoryTable";
import PrescriptionSafetyDisclaimer from "@/components/prescription/PrescriptionSafetyDisclaimer";

export default function UserPrescriptionHistoryPage() {
  const { t, isRTL } = useLanguage();

  const [items, setItems] = useState<PrescriptionHistoryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  const loadHistory = async () => {
    setLoading(true);
    try {
      const res = await getPrescriptionHistory(50, 0);
      setItems(res.items || []);
      setTotal(res.total || 0);
    } catch (err) {
      console.error("Failed to load prescription history:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  return (
    <div className="space-y-6 max-w-5xl mx-auto w-full">
      {/* Header Banner */}
      <div className="p-5 sm:p-8 bg-gradient-to-r from-medPink-50 via-white to-medTeal-50 rounded-3xl border border-slate-200 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-5 relative overflow-hidden">
        <div className="space-y-2 relative z-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-medTeal-100/80 border border-medTeal-200 rounded-full text-xs font-bold text-medTeal-800">
            <History className="w-3.5 h-3.5" />
            <span>{t("nav.prescriptionHistory")}</span>
          </div>

          <h1 className="text-xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            {t("prescription.historyTitle")}
          </h1>
          <p className="text-xs sm:text-sm text-slate-600 max-w-2xl leading-relaxed">
            {t("prescription.historySubtitle")}
          </p>
        </div>

        {/* Start New Prescription CTA */}
        <div className="flex items-center gap-2 relative z-10 shrink-0">
          <Link
            href="/user/prescription"
            className="inline-flex items-center gap-1.5 px-5 py-2.5 bg-gradient-to-r from-medPink-500 to-medTeal-600 hover:from-medPink-600 hover:to-medTeal-700 text-white rounded-xl text-xs sm:text-sm font-bold shadow-xs hover:shadow-md transition"
          >
            <PlusCircle className="w-4 h-4" />
            <span>{t("dashboard.startPrescription")}</span>
          </Link>
        </div>
      </div>

      <PrescriptionSafetyDisclaimer variant="compact" />

      {/* Content Table / Loading / Empty */}
      {loading ? (
        <div className="p-12 text-center bg-white rounded-3xl border border-slate-200 shadow-xs space-y-3">
          <RefreshCw className="w-8 h-8 text-medTeal-600 animate-spin mx-auto" />
          <h3 className="text-sm font-bold text-slate-800">{t("common.loading")}</h3>
        </div>
      ) : (
        <PrescriptionHistoryTable items={items} />
      )}
    </div>
  );
}
