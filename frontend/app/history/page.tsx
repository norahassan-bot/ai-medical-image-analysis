"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { History, RefreshCw, PlusCircle } from "lucide-react";
import { getHistory, ApiError } from "@/lib/api";
import type { AnalysisHistoryItem } from "@/types/api";
import HistoryTable from "@/components/HistoryTable";
import EmptyState from "@/components/EmptyState";
import ErrorState from "@/components/ErrorState";
import LoadingState from "@/components/LoadingState";
import Disclaimer from "@/components/Disclaimer";
import { useLanguage } from "@/lib/i18n";

export default function HistoryPage() {
  const { t } = useLanguage();
  const [items, setItems] = useState<AnalysisHistoryItem[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadHistory = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getHistory(50, 0);
      setItems(data.items);
      setTotal(data.total);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError(t("history.failedTitle"));
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* 1. Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <History className="w-6 h-6 text-medTeal-600" />
            <span>{t("history.pageTitle")}</span>
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            {t("history.pageDesc")}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={loadHistory}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-2 bg-slate-100 hover:bg-slate-200 border border-slate-300 rounded-xl text-xs text-slate-700 font-semibold transition disabled:opacity-50 shadow-xs"
            title={t("health.refreshBtn")}
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin text-medTeal-500" : ""}`} />
            <span>{t("health.refreshBtn")}</span>
          </button>

          <Link
            href="/analysis"
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-medPink-400 hover:bg-medPink-500 text-white font-bold text-xs rounded-xl shadow-xs transition"
          >
            <PlusCircle className="w-3.5 h-3.5" />
            <span>{t("history.newAnalysisBtn")}</span>
          </Link>
        </div>
      </div>

      {/* 2. Content State Machine */}
      {loading ? (
        <div className="py-12">
          <LoadingState
            message={t("history.loadingMsg")}
            subMessage={t("history.loadingSub")}
          />
        </div>
      ) : error ? (
        <ErrorState
          title={t("history.failedTitle")}
          message={error}
          onRetry={loadHistory}
        />
      ) : items.length === 0 ? (
        <EmptyState
          title={t("history.emptyTitle")}
          description={t("history.emptyDesc")}
          actionText={t("history.emptyAction")}
          actionHref="/analysis"
        />
      ) : (
        <div className="space-y-6">
          <div className="text-xs text-slate-500 flex items-center justify-between">
            <span>
              {t("history.showingCount", { count: items.length, total: total })}
            </span>
            <span className="text-[11px] font-mono text-slate-400">
              {t("history.orderedNewest")}
            </span>
          </div>

          <HistoryTable items={items} />

          <Disclaimer variant="banner" />
        </div>
      )}
    </div>
  );
}
