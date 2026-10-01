"use client";

import React from "react";
import Link from "next/link";
import { ChevronRight } from "lucide-react";
import type { AnalysisHistoryItem } from "@/types/api";
import { useLanguage } from "@/lib/i18n";

interface HistoryTableProps {
  items: AnalysisHistoryItem[];
}

export default function HistoryTable({ items }: HistoryTableProps) {
  const { t, isRTL } = useLanguage();

  if (items.length === 0) {
    return null;
  }

  return (
    <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-xs">
      {/* Desktop Table View */}
      <div className="hidden md:block overflow-x-auto">
        <table className="w-full text-start border-collapse">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50/90 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
              <th className="py-3.5 px-5 text-start">{t("history.colId")}</th>
              <th className="py-3.5 px-5 text-start">{t("history.colDate")}</th>
              <th className="py-3.5 px-5 text-start">{t("history.colPrediction")}</th>
              <th className="py-3.5 px-5 text-start">{t("history.colConfidence")}</th>
              <th className="py-3.5 px-5 text-start">{t("history.colModel")}</th>
              <th className="py-3.5 px-5 text-end">{t("history.colAction")}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 text-xs">
            {items.map((item) => {
              const isPneumonia = item.prediction.toUpperCase() === "PNEUMONIA";
              const displayPrediction = isPneumonia ? t("common.pneumonia") : t("common.normal");
              const dateStr = new Date(item.created_at).toLocaleString(isRTL ? "ar-EG" : "en-US", {
                dateStyle: "short",
                timeStyle: "short",
              });

              return (
                <tr
                  key={item.analysis_id}
                  className="hover:bg-slate-50 transition group"
                >
                  <td className="py-4 px-5 font-mono text-slate-800 font-semibold text-start">
                    <span title={item.analysis_id}>
                      {item.analysis_id.slice(0, 8)}...
                    </span>
                  </td>
                  <td className="py-4 px-5 text-slate-500 text-start">{dateStr}</td>
                  <td className="py-4 px-5 text-start">
                    <span
                      className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold border ${
                        isPneumonia
                          ? "bg-amber-50 border-amber-200 text-amber-800"
                          : "bg-medTeal-50 border-medTeal-200 text-medTeal-800"
                      }`}
                    >
                      {displayPrediction}
                    </span>
                  </td>
                  <td className="py-4 px-5 font-mono font-bold text-slate-800 text-start">
                    {(item.confidence * 100).toFixed(1)}%
                  </td>
                  <td className="py-4 px-5 text-slate-500 font-mono text-[11px] text-start">
                    v{item.model_version} {item.architecture && `(${item.architecture})`}
                  </td>
                  <td className="py-4 px-5 text-end">
                    <Link
                      href={`/history/${item.analysis_id}`}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 hover:bg-medPink-400 hover:text-white rounded-xl text-slate-700 font-semibold text-xs transition border border-slate-200 shadow-xs"
                      aria-label={`${t("history.viewAction")} ${item.analysis_id}`}
                    >
                      <span>{t("history.viewAction")}</span>
                      <ChevronRight className={`w-3.5 h-3.5 ${isRTL ? "rotate-180" : ""}`} />
                    </Link>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Mobile Card List View */}
      <div className="md:hidden divide-y divide-slate-100">
        {items.map((item) => {
          const isPneumonia = item.prediction.toUpperCase() === "PNEUMONIA";
          const displayPrediction = isPneumonia ? t("common.pneumonia") : t("common.normal");
          const dateStr = new Date(item.created_at).toLocaleString(isRTL ? "ar-EG" : "en-US", {
            dateStyle: "short",
            timeStyle: "short",
          });

          return (
            <Link
              key={item.analysis_id}
              href={`/history/${item.analysis_id}`}
              className="block p-4 hover:bg-slate-50 transition space-y-2"
            >
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs text-slate-900 font-bold">
                  {item.analysis_id.slice(0, 8)}...
                </span>
                <span
                  className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                    isPneumonia
                      ? "bg-amber-50 border-amber-200 text-amber-800"
                      : "bg-medTeal-50 border-medTeal-200 text-medTeal-800"
                  }`}
                >
                  {displayPrediction}
                </span>
              </div>

              <div className="flex items-center justify-between text-xs text-slate-500">
                <span>{dateStr}</span>
                <span className="font-mono font-bold text-slate-800">
                  {t("history.confidenceLabel", { confidence: (item.confidence * 100).toFixed(1) })}
                </span>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
