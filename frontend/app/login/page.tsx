"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { BrainCircuit, Lock, User, AlertCircle, ArrowRight, ShieldCheck, LogIn, Sparkles } from "lucide-react";
import { useAuth } from "@/lib/auth/AuthContext";
import { useLanguage } from "@/lib/i18n";

export default function AdminLoginPage() {
  const router = useRouter();
  const { login, isAdmin, isLoading: authLoading } = useAuth();
  const { t, isRTL } = useLanguage();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // If already authenticated as ADMIN, redirect to /admin
  useEffect(() => {
    if (!authLoading && isAdmin) {
      router.push("/admin");
    }
  }, [isAdmin, authLoading, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password) {
      setError(t("auth.invalidCredentials"));
      return;
    }

    setError(null);
    setSubmitting(true);

    try {
      const user = await login({ username: username.trim(), password });
      if (user.role === "ADMIN") {
        router.push("/admin");
      } else {
        router.push("/");
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError(t("auth.invalidCredentials"));
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-[80vh] flex flex-col items-center justify-center px-4 py-8">
      <div className="w-full max-w-md bg-white rounded-3xl border border-slate-200 shadow-xl overflow-hidden">
        {/* Top Gradient Header */}
        <div className="bg-gradient-to-r from-medPink-600 via-medPink-500 to-medTeal-600 p-8 text-white text-center relative overflow-hidden">
          <div className="relative z-10 flex flex-col items-center">
            <div className="w-14 h-14 rounded-2xl bg-white/20 backdrop-blur-md flex items-center justify-center mb-3 shadow-inner">
              <BrainCircuit className="w-8 h-8 text-white" />
            </div>
            <h2 className="text-xl font-bold tracking-tight">
              {t("auth.loginTitle")}
            </h2>
            <p className="text-xs text-white/90 mt-1 max-w-xs leading-relaxed">
              {t("auth.loginSubtitle")}
            </p>
          </div>
        </div>

        {/* Form Body */}
        <div className="p-6 sm:p-8 space-y-6">
          {error && (
            <div
              role="alert"
              className="flex items-start gap-3 p-3.5 bg-rose-50 border border-rose-200 text-rose-800 rounded-xl text-xs"
            >
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-500 mt-0.5" />
              <div className="flex-1 leading-relaxed">{error}</div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="username-input"
                className="block text-xs font-semibold text-slate-700 mb-1.5"
              >
                {t("auth.username")}
              </label>
              <div className="relative rounded-xl shadow-2xs">
                <div className="absolute inset-y-0 left-0 rtl:left-auto rtl:right-0 pl-3.5 rtl:pl-0 rtl:pr-3.5 flex items-center pointer-events-none text-slate-400">
                  <User className="w-4 h-4" />
                </div>
                <input
                  id="username-input"
                  type="text"
                  required
                  autoComplete="username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder={t("auth.usernamePlaceholder")}
                  className="block w-full pl-10 rtl:pl-3.5 rtl:pr-10 pr-3.5 py-2.5 text-sm bg-slate-50 border border-slate-200 rounded-xl text-slate-900 placeholder:text-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-medPink-500/30 focus:border-medPink-500 transition"
                />
              </div>
            </div>

            <div>
              <label
                htmlFor="password-input"
                className="block text-xs font-semibold text-slate-700 mb-1.5"
              >
                {t("auth.password")}
              </label>
              <div className="relative rounded-xl shadow-2xs">
                <div className="absolute inset-y-0 left-0 rtl:left-auto rtl:right-0 pl-3.5 rtl:pl-0 rtl:pr-3.5 flex items-center pointer-events-none text-slate-400">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  id="password-input"
                  type="password"
                  required
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder={t("auth.passwordPlaceholder")}
                  className="block w-full pl-10 rtl:pl-3.5 rtl:pr-10 pr-3.5 py-2.5 text-sm bg-slate-50 border border-slate-200 rounded-xl text-slate-900 placeholder:text-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-medPink-500/30 focus:border-medPink-500 transition"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full mt-2 py-3 px-4 bg-gradient-to-r from-medPink-600 to-medTeal-600 hover:from-medPink-700 hover:to-medTeal-700 text-white rounded-xl text-sm font-semibold shadow-md hover:shadow-lg transition-all flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {submitting ? (
                <span>{t("auth.loggingIn")}</span>
              ) : (
                <>
                  <LogIn className="w-4 h-4" />
                  <span>{t("auth.login")}</span>
                  <ArrowRight className={`w-4 h-4 ${isRTL ? "rotate-180" : ""}`} />
                </>
              )}
            </button>
          </form>

          {/* User Portal Link (Zero Login Required) */}
          <div className="pt-3 border-t border-slate-100 text-center space-y-2">
            <Link
              href="/"
              className="inline-flex items-center justify-center gap-1.5 text-xs font-semibold text-medTeal-700 hover:text-medTeal-800 bg-medTeal-50 hover:bg-medTeal-100 border border-medTeal-200 py-2 px-3 rounded-xl transition w-full"
            >
              <Sparkles className="w-3.5 h-3.5 text-medTeal-600" />
              <span>{isRTL ? "الدخول المباشر إلى بوابة الفحص السريري (بدون تسجيل)" : "Open Clinical User Portal (No Login Required)"}</span>
            </Link>
          </div>

          <div className="flex items-center justify-center gap-2 text-[11px] text-slate-400">
            <ShieldCheck className="w-3.5 h-3.5 text-medTeal-500" />
            <span>{t("disclaimer.inline")}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
