"use client";

import React, { useState } from "react";
import {
  User,
  ShieldCheck,
  CheckCircle2,
  Calendar,
  RotateCcw,
  Shield,
  Key,
  Clock,
  Sparkles,
  AlertTriangle,
} from "lucide-react";
import { useAuth } from "@/lib/auth/AuthContext";
import { useLanguage } from "@/lib/i18n";
import LoadingState from "@/components/LoadingState";

export default function AccountPage() {
  const { user, isLoading, resetUserSession } = useAuth();
  const { t, isRTL } = useLanguage();
  const [resetting, setResetting] = useState(false);
  const [resetNotice, setResetNotice] = useState(false);

  if (isLoading || !user) {
    return (
      <div className="py-12">
        <LoadingState message={t("common.loading")} />
      </div>
    );
  }

  const handleResetSession = async () => {
    setResetting(true);
    try {
      await resetUserSession();
      setResetNotice(true);
      setTimeout(() => setResetNotice(false), 6000);
    } catch {
      // Handled in context
    } finally {
      setResetting(false);
    }
  };

  const memberSinceFormatted = user?.created_at
    ? new Date(user.created_at).toLocaleDateString(isRTL ? "ar-EG" : "en-US", {
        year: "numeric",
        month: "long",
        day: "numeric",
      })
    : "—";

  return (
    <div className="space-y-6 max-w-4xl mx-auto w-full">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4 border-b border-slate-200 pb-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <User className="w-5 h-5 sm:w-6 sm:h-6 text-medTeal-600 shrink-0" />
            <span>{t("user.accountTitle")}</span>
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            {t("user.accountDesc")}
          </p>
        </div>

        <button
          onClick={handleResetSession}
          disabled={resetting}
          className="flex items-center justify-center gap-2 px-4 py-2.5 bg-rose-50 hover:bg-rose-100 text-rose-700 font-bold text-xs rounded-xl border border-rose-200 shadow-xs transition w-full sm:w-auto disabled:opacity-50"
          aria-label={isRTL ? "إنهاء الجلسة / إعادة تعيين الهوية" : "End Session / Reset Identity"}
        >
          <RotateCcw className={`w-4 h-4 ${resetting ? "animate-spin" : ""}`} />
          <span>{resetting ? t("common.loading") : isRTL ? "إنهاء الجلسة" : "End Session"}</span>
        </button>
      </div>

      {resetNotice && (
        <div
          role="alert"
          className="flex items-start gap-3 p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-2xl text-xs shadow-xs"
        >
          <Sparkles className="w-4 h-4 shrink-0 text-emerald-600 mt-0.5" />
          <div className="leading-relaxed font-medium">
            {isRTL
              ? "تم إنهاء الجلسة وإنشاء هوية مستخدم مجهولة جديدة بنجاح. التحليلات السابقة معزولة بأمان."
              : "Session successfully reset. A fresh anonymous user identity has been established. Previous analyses remain isolated."}
          </div>
        </div>
      )}

      {/* Account Info Profile Card */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 sm:gap-6">
        {/* Left Column: Profile Summary */}
        <div className="bg-white border border-slate-200 rounded-2xl p-5 sm:p-6 shadow-xs flex flex-col items-center text-center space-y-4">
          <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-full bg-gradient-to-tr from-medTeal-100 to-medPink-100 border-2 border-medTeal-300 flex items-center justify-center text-medTeal-800 shadow-inner shrink-0">
            <User className="w-8 h-8 sm:w-10 sm:h-10" />
          </div>
          <div>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 truncate max-w-[200px]">
              {isRTL ? "مستخدم سريري (هوية مؤمنة)" : "Clinical User (Secure Session)"}
            </h2>
            <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold bg-medTeal-50 text-medTeal-700 border border-medTeal-200 mt-1">
              <ShieldCheck className="w-3.5 h-3.5 shrink-0" />
              <span>{user?.role === "USER" ? t("auth.userRole") : user?.role}</span>
            </div>
          </div>

          <div className="w-full pt-3 border-t border-slate-100 text-xs text-slate-500 space-y-2">
            <div className="flex justify-between items-center">
              <span>{t("user.accountStatus")}:</span>
              <span className="font-semibold text-emerald-600 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" />
                {t("user.activeStatus")}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span>{t("user.sessionStatus")}:</span>
              <span className="font-semibold text-slate-700">{t("user.authenticated")}</span>
            </div>
          </div>
        </div>

        {/* Right Column: Account Details */}
        <div className="md:col-span-2 bg-white border border-slate-200 rounded-2xl p-5 sm:p-6 shadow-xs space-y-5 sm:space-y-6">
          <h3 className="text-sm font-bold text-slate-900 border-b border-slate-100 pb-3 flex items-center gap-2">
            <Shield className="w-4 h-4 text-medPink-500 shrink-0" />
            <span>{t("user.accountInfoSection")}</span>
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4 text-xs">
            <div className="p-3.5 sm:p-4 bg-slate-50 rounded-xl border border-slate-200/70 space-y-1">
              <span className="text-slate-500 text-[11px] block">{isRTL ? "نوع الحساب" : "Account Type"}</span>
              <span className="text-slate-900 font-bold text-sm block">
                {isRTL ? "مستخدم سريري موثق (USER)" : "Authenticated Clinical User (USER)"}
              </span>
            </div>

            <div className="p-3.5 sm:p-4 bg-slate-50 rounded-xl border border-slate-200/70 space-y-1">
              <span className="text-slate-500 text-[11px] block">{t("auth.role")}</span>
              <span className="text-slate-900 font-bold text-sm block">
                {user?.role === "USER" ? t("auth.userRole") : user?.role}
              </span>
            </div>

            <div className="p-3.5 sm:p-4 bg-slate-50 rounded-xl border border-slate-200/70 space-y-1">
              <span className="text-slate-500 text-[11px] block flex items-center gap-1">
                <Calendar className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                <span>{t("user.memberSince")}</span>
              </span>
              <span className="text-slate-900 font-semibold truncate block">{memberSinceFormatted}</span>
            </div>

            <div className="p-3.5 sm:p-4 bg-slate-50 rounded-xl border border-slate-200/70 space-y-1">
              <span className="text-slate-500 text-[11px] block flex items-center gap-1">
                <Clock className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                <span>{t("user.lastLogin")}</span>
              </span>
              <span className="text-slate-900 font-semibold truncate block">
                {isRTL ? "الجلسة مفعلة (HttpOnly)" : "Session Active (HttpOnly)"}
              </span>
            </div>
          </div>

          {/* Privacy & Session Isolation Information */}
          <div className="p-4 rounded-xl bg-sky-50 border border-sky-200 text-sky-900 text-xs space-y-2">
            <div className="font-bold flex items-center gap-1.5">
              <Key className="w-3.5 h-3.5 text-sky-600 shrink-0" />
              <span>{t("user.securityPrivacyNotice")}</span>
            </div>
            <p className="text-sky-800 text-[11px] leading-relaxed">
              {t("user.privacyExplanation")}
            </p>
          </div>

          {/* End Session Warning Note */}
          <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs space-y-1.5">
            <div className="font-bold flex items-center gap-1.5 text-amber-800">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
              <span>{isRTL ? "إعادة تعيين الجلسة والخصوصية" : "Session Reset & Isolation"}</span>
            </div>
            <p className="text-amber-800 text-[11px] leading-relaxed">
              {isRTL
                ? "عند الضغط على «إنهاء الجلسة»، يتم إبطال الرمز المميز الحالي والبدء بهوية سريرية مجهولة جديدة عند زيارتك التالية. الفحوصات والتقارير المرتبطة بالجلسة السابقة لن تظهر في الهوية الجديدة لضمان أقصى درجات الخصوصية."
                : "Ending or resetting your session invalidates the active cryptographic token. A new anonymous session will be established on your next action, ensuring your historical data remains completely isolated."}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
