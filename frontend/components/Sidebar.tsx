"use client";

import React, { useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  ScanLine,
  History,
  Info,
  ExternalLink,
  ShieldCheck,
  BrainCircuit,
  ShieldAlert,
  Users,
  BarChart3,
  Pill,
  X,
} from "lucide-react";
import { API_ENDPOINTS } from "@/lib/config";
import { useLanguage } from "@/lib/i18n";
import { useAuth } from "@/lib/auth/AuthContext";

interface SidebarProps {
  mobileOpen?: boolean;
  onCloseMobile?: () => void;
}

export default function Sidebar({ mobileOpen = false, onCloseMobile }: SidebarProps) {
  const pathname = usePathname();
  const { t, isRTL } = useLanguage();
  const { role, isAuthenticated } = useAuth();

  const isUserPortal = pathname?.startsWith("/user");
  const isAdminPortal = pathname?.startsWith("/admin");
  const isAdmin = role === "ADMIN" || isAdminPortal;
  const isUser = isUserPortal || (isAuthenticated && role !== "ADMIN");

  // Close mobile sidebar on Escape key
  useEffect(() => {
    if (!mobileOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onCloseMobile?.();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [mobileOpen, onCloseMobile]);

  // Lock body scroll when mobile drawer is open
  useEffect(() => {
    if (mobileOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [mobileOpen]);

  // Dedicated Clinical User portal navigation
  const userNavigation = [
    {
      name: t("nav.dashboard"),
      href: "/",
      icon: Activity,
      badge: t("nav.dashboardBadge"),
    },
    {
      name: t("nav.analysis"),
      href: "/analysis",
      icon: ScanLine,
      badge: t("nav.analysisBadge"),
    },
    {
      name: t("nav.prescription"),
      href: "/user/prescription",
      icon: Pill,
      badge: t("nav.prescriptionBadge"),
    },
    {
      name: t("nav.myHistory"),
      href: "/history",
      icon: History,
      badge: t("nav.historyBadge"),
    },
    {
      name: t("nav.myAccount"),
      href: "/account",
      icon: Users,
      badge: t("nav.accountBadge"),
    },
  ];

  // Guest navigation (Unauthenticated overview)
  const guestNavigation = [
    {
      name: t("nav.dashboard"),
      href: "/",
      icon: Activity,
      badge: t("nav.dashboardBadge"),
    },
    {
      name: t("nav.analysis"),
      href: "/analysis",
      icon: ScanLine,
      badge: t("nav.analysisBadge"),
    },
    {
      name: t("nav.prescription"),
      href: "/user/prescription",
      icon: Pill,
      badge: t("nav.prescriptionBadge"),
    },
    {
      name: t("nav.history"),
      href: "/history",
      icon: History,
      badge: t("nav.historyBadge"),
    },
    {
      name: t("nav.system"),
      href: "/system",
      icon: Info,
      badge: t("nav.systemBadge"),
    },
  ];

  // Admin exclusive navigation
  const adminNavigation = [
    {
      name: t("nav.dashboard"),
      href: "/",
      icon: Activity,
      badge: t("nav.dashboardBadge"),
    },
    {
      name: t("nav.adminDashboard"),
      href: "/admin",
      icon: BarChart3,
      badge: t("nav.adminBadge"),
    },
    {
      name: t("nav.adminAnalyses"),
      href: "/admin/analyses",
      icon: History,
      badge: "All",
    },
    {
      name: t("nav.prescriptionHistory"),
      href: "/admin/prescriptions",
      icon: Pill,
      badge: "Rx",
    },
    {
      name: t("nav.adminUsers"),
      href: "/admin/users",
      icon: Users,
      badge: "Users",
    },
    {
      name: t("nav.analysis"),
      href: "/analysis",
      icon: ScanLine,
      badge: t("nav.analysisBadge"),
    },
    {
      name: t("nav.adminSystem"),
      href: "/admin/system",
      icon: ShieldAlert,
      badge: "Sys",
    },
  ];

  const navigationItems = isAdmin
    ? adminNavigation
    : isUser
    ? userNavigation
    : guestNavigation;

  const renderSidebarContent = (isMobileInstance: boolean = false) => (
    <div className="flex flex-col h-full bg-white">
      {/* Brand Header */}
      <div className="p-4 sm:p-5 border-b border-slate-200 flex items-center justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-medPink-400 via-medPink-300 to-medTeal-400 flex items-center justify-center shadow-sm shrink-0">
            <BrainCircuit className="w-5 h-5 text-white" />
          </div>
          <div className="min-w-0">
            <div className="text-sm font-bold tracking-tight text-slate-900 truncate">
              {t("app.shortTitle")}
            </div>
            <p className="text-[11px] text-medTeal-600 font-medium truncate">
              {isAdmin ? t("auth.adminRole") : t("app.subtitle")}
            </p>
          </div>
        </div>

        {isMobileInstance && onCloseMobile && (
          <button
            onClick={onCloseMobile}
            aria-label={t("common.close") || "Close Navigation"}
            className="p-2 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-xl transition shrink-0"
          >
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* Navigation Links */}
      <div className="px-3 py-4 flex-1 space-y-1.5 overflow-y-auto">
        <div className="px-3 pb-2 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
          {isAdmin ? t("nav.adminDashboard") : t("nav.platform")}
        </div>
        {navigationItems.map((item) => {
          const isActive =
            pathname === item.href ||
            (item.href === "/" && pathname === "/user") ||
            (item.href === "/analysis" && pathname === "/user/analysis") ||
            (item.href === "/history" && (pathname?.startsWith("/history") || pathname?.startsWith("/user/history"))) ||
            (item.href === "/account" && pathname === "/user/account");
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={isMobileInstance ? onCloseMobile : undefined}
              className={`flex items-center justify-between px-3 py-2.5 rounded-xl text-xs sm:text-sm font-medium transition-all ${
                isActive
                  ? "bg-medPink-50 text-medPink-700 border border-medPink-200 shadow-xs font-semibold"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
              }`}
            >
              <div className="flex items-center gap-3 min-w-0">
                <Icon
                  className={`w-4 h-4 shrink-0 ${
                    isActive ? "text-medPink-500" : "text-slate-400"
                  }`}
                />
                <span className="truncate">{item.name}</span>
              </div>
              <span
                className={`text-[10px] px-2 py-0.5 rounded-full font-medium shrink-0 ms-2 ${
                  isActive
                    ? "bg-medPink-100 text-medPink-700 font-semibold"
                    : "bg-slate-100 text-slate-500"
                }`}
              >
                {item.badge}
              </span>
            </Link>
          );
        })}
      </div>

      {/* Bottom External Resources & Compliance */}
      <div className="p-4 border-t border-slate-200 space-y-2 bg-slate-50/50">
        <a
          href={API_ENDPOINTS.DOCS}
          target="_blank"
          rel="noreferrer"
          className="flex items-center justify-between px-3 py-2 text-xs font-medium text-slate-700 bg-white rounded-xl border border-slate-200 hover:border-medTeal-300 hover:text-medTeal-700 transition shadow-xs"
        >
          <span className="truncate">{t("app.swaggerDocs")}</span>
          <ExternalLink className={`w-3.5 h-3.5 text-slate-400 shrink-0 ms-2 ${isRTL ? "rotate-180" : ""}`} />
        </a>

        <div className="flex items-center gap-2 px-3 py-2 bg-white rounded-xl border border-slate-200 text-[11px] text-slate-600 shadow-xs">
          <ShieldCheck className="w-4 h-4 text-medTeal-500 shrink-0" />
          <span className="truncate">{t("app.researchEngine")}</span>
        </div>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop Persistent Sidebar */}
      <aside className="hidden md:flex w-64 bg-white border-r rtl:border-r-0 rtl:border-l border-slate-200 flex-col shrink-0 min-h-screen shadow-xs">
        {renderSidebarContent(false)}
      </aside>

      {/* Mobile Off-canvas Drawer */}
      {mobileOpen && (
        <>
          <div
            className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs z-40 md:hidden transition-opacity"
            onClick={onCloseMobile}
            aria-hidden="true"
          />
          <aside
            role="dialog"
            aria-modal="true"
            aria-label="Mobile Navigation"
            id="mobile-sidebar"
            className={`fixed top-0 bottom-0 z-50 w-72 max-w-[calc(100vw-3rem)] bg-white shadow-2xl transition-transform duration-300 ease-in-out md:hidden ${
              isRTL ? "right-0 translate-x-0" : "left-0 translate-x-0"
            }`}
          >
            {renderSidebarContent(true)}
          </aside>
        </>
      )}
    </>
  );
}

