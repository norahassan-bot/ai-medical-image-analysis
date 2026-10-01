"use client";

import React from "react";
import Link from "next/link";
import { Inbox, PlusCircle } from "lucide-react";
import { useLanguage } from "@/lib/i18n";

interface EmptyStateProps {
  title?: string;
  description?: string;
  actionText?: string;
  actionHref?: string;
  onAction?: () => void;
  icon?: React.ReactNode;
}

export default function EmptyState({
  title,
  description,
  actionText,
  actionHref = "/analysis",
  onAction,
  icon,
}: EmptyStateProps) {
  const { t } = useLanguage();

  const finalTitle = title || t("history.emptyTitle");
  const finalDescription = description || t("history.emptyDesc");
  const finalActionText = actionText || t("history.emptyAction");

  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-12 text-center flex flex-col items-center justify-center max-w-lg mx-auto space-y-4 shadow-xs">
      <div className="w-16 h-16 rounded-2xl bg-slate-50 border border-slate-200 flex items-center justify-center text-slate-400">
        {icon || <Inbox className="w-8 h-8 text-slate-400" />}
      </div>

      <h3 className="text-lg font-bold text-slate-900">{finalTitle}</h3>
      <p className="text-xs text-slate-500 leading-relaxed max-w-sm">{finalDescription}</p>

      {actionHref ? (
        <Link
          href={actionHref}
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-medPink-400 hover:bg-medPink-500 text-white font-bold text-xs rounded-xl shadow-xs transition"
        >
          <PlusCircle className="w-4 h-4" />
          <span>{finalActionText}</span>
        </Link>
      ) : onAction ? (
        <button
          onClick={onAction}
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-medPink-400 hover:bg-medPink-500 text-white font-bold text-xs rounded-xl shadow-xs transition"
        >
          <PlusCircle className="w-4 h-4" />
          <span>{finalActionText}</span>
        </button>
      ) : null}
    </div>
  );
}
