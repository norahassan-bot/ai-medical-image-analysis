"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { RefreshCw, User, LogOut, LogIn, Shield, Menu, Activity } from "lucide-react";
import { getHealth } from "@/lib/api";
import type { HealthResponse } from "@/types/api";
import { useLanguage } from "@/lib/i18n";
import { useAuth } from "@/lib/auth/AuthContext";
import LanguageSwitcher from "./LanguageSwitcher";

interface HeaderProps {
  onToggleMobileSidebar?: () => void;
}

export default function Header({ onToggleMobileSidebar }: HeaderProps) {
  const pathname = usePathname();
  const { t, isRTL } = useLanguage();
  const { user, role, isAuthenticated, logout } = useAuth();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastChecked, setLastChecked] = useState<string>("");

  const isUserPortal = pathname?.startsWith("/user");
  const isAdminPortal = pathname?.startsWith("/admin");

  const checkStatus = async () => {
    setLoading(true);
    try {
      const data = await getHealth();
      setHealth(data);
      setLastChecked(new Date().toLocaleTimeString(isRTL ? "ar-EG" : "en-US"));
    } catch {
      setHealth({ status: "unreachable", model_loaded: false });
      setLastChecked(new Date().toLocaleTimeString(isRTL ? "ar-EG" : "en-US"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkStatus();
    const interval = setInterval(checkStatus, 30000);
    return () => clearInterval(interval);
  }, [isRTL]);

  const isHealthy = health?.status === "healthy";

  const getStatusDisplay = () => {
    if (!health) return t("header.checking");
    if (health.status === "healthy") return t("common.healthy");
    if (health.status === "unreachable") return t("common.unreachable");
    return health.status;
  };

  return (
    <header className="h-16 border-b border-slate-200/90 bg-white/95 backdrop-blur-md px-3 sm:px-6 flex items-center justify-between sticky top-0 z-30 shadow-xs">
      <div className="flex items-center gap-2 sm:gap-3 min-w-0 flex-1">
        {/* Mobile menu trigger */}
        <button
          onClick={onToggleMobileSidebar}
          aria-label="Open Navigation Menu"
          aria-controls="mobile-sidebar"
          className="p-2 -ms-1 sm:-ms-2 md:hidden text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition shrink-0"
        >
          <Menu className="w-5 h-5" />
        </button>

        <h1 className="text-xs sm:text-base font-bold text-slate-900 tracking-tight truncate max-w-[130px] sm:max-w-none">
          {t("app.headerTitle")}
        </h1>
        <span className="hidden lg:inline-block text-xs px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200 font-mono shrink-0">
          {t("app.stackBadge")}
        </span>
      </div>

      <div className="flex items-center gap-1.5 sm:gap-3 shrink-0">
        {/* Language Switcher */}
        <LanguageSwitcher />

        {/* Live Backend Connection Indicator */}
        <div
          className={`hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs ${
            isHealthy
              ? "bg-medTeal-50/80 border-medTeal-200 text-medTeal-800"
              : "bg-rose-50/80 border-rose-200 text-rose-800"
          }`}
        >
          <span className="relative flex h-2 w-2">
            <span
              className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                isHealthy ? "bg-medTeal-400" : "bg-rose-400"
              }`}
            ></span>
            <span
              className={`relative inline-flex rounded-full h-2 w-2 ${
                isHealthy ? "bg-medTeal-500" : "bg-rose-500"
              }`}
            ></span>
          </span>
          <span className="font-medium text-slate-700">
            {t("header.backend")}{" "}
            <span
              className={
                isHealthy ? "text-medTeal-700 font-semibold" : "text-rose-700 font-semibold"
              }
            >
              {getStatusDisplay()}
            </span>
          </span>
        </div>

        <button
          onClick={checkStatus}
          disabled={loading}
          title={t("header.refreshTitle")}
          aria-label={t("header.refreshTitle")}
          className="p-1.5 sm:p-2 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition disabled:opacity-50 shrink-0"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
        </button>

        {/* User Profile & Auth Badge */}
        {isAuthenticated && user ? (
          <div className="flex items-center gap-1 sm:gap-2 ps-1.5 sm:ps-2 border-s border-slate-200 shrink-0">
            <div className="flex items-center gap-1.5 sm:gap-2 bg-slate-50 border border-slate-200/80 rounded-full py-1 px-2 sm:px-2.5">
              <div
                className={`w-6 h-6 rounded-full flex items-center justify-center text-white text-[11px] font-bold shrink-0 ${
                  role === "ADMIN" ? "bg-medPink-600" : "bg-medTeal-600"
                }`}
              >
                {role === "ADMIN" ? <Shield className="w-3.5 h-3.5" /> : <User className="w-3.5 h-3.5" />}
              </div>
              <div className="hidden sm:flex flex-col text-start">
                <span className="text-xs font-semibold text-slate-800 leading-tight truncate max-w-[110px]">
                  {role === "ADMIN" ? user.username : (isRTL ? "مستخدم سريري" : "Clinical User")}
                </span>
                <span
                  className={`text-[10px] font-bold leading-none ${
                    role === "ADMIN" ? "text-medPink-600" : "text-medTeal-600"
                  }`}
                >
                  {role === "ADMIN" ? t("auth.adminRole") : (isRTL ? "جلسة مفعلة" : "Session Active")}
                </span>
              </div>
            </div>

            <button
              onClick={() => logout()}
              title={isUserPortal ? (isRTL ? "إنهاء الجلسة" : "End Session") : t("auth.logout")}
              aria-label={isUserPortal ? (isRTL ? "إنهاء الجلسة" : "End Session") : t("auth.logout")}
              className="p-1.5 sm:p-2 text-slate-500 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition shrink-0"
            >
              <LogOut className={`w-4 h-4 ${isRTL ? "rotate-180" : ""}`} />
            </button>
          </div>
        ) : isUserPortal ? (
          <div className="flex items-center gap-1.5 bg-medTeal-50 border border-medTeal-200/80 rounded-full py-1 px-2.5 text-medTeal-800 text-xs font-medium">
            <Activity className="w-3.5 h-3.5 text-medTeal-600" />
            <span className="hidden xs:inline">{isRTL ? "بوابة التحليل الإشعاعي" : "Clinical Session"}</span>
          </div>
        ) : (
          <Link
            href="/login"
            className="flex items-center gap-1.5 px-3 py-1.5 bg-medPink-600 hover:bg-medPink-700 text-white rounded-xl text-xs font-semibold shadow-xs transition shrink-0"
          >
            <LogIn className="w-3.5 h-3.5" />
            <span className="hidden xs:inline">{t("auth.adminLogin") || t("auth.login")}</span>
          </Link>
        )}
      </div>
    </header>
  );
}
