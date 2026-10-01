"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Users,
  Shield,
  UserCheck,
  UserX,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  Calendar,
  Activity,
} from "lucide-react";
import { getAdminUsers, updateUserStatus, ApiError } from "@/lib/api";
import type { AdminUserItem } from "@/types/api";
import { useAuth } from "@/lib/auth/AuthContext";
import { useLanguage } from "@/lib/i18n";

export default function AdminUsersPage() {
  const router = useRouter();
  const { adminUser: currentUser, isAdmin, role, isLoading: authLoading } = useAuth();
  const { t } = useLanguage();

  const [users, setUsers] = useState<AdminUserItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && !isAdmin) {
      router.push("/login");
    }
  }, [authLoading, isAdmin, router]);

  const loadUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getAdminUsers();
      setUsers(res.users);
      setTotal(res.total);
    } catch (err: any) {
      setError(err?.message || "Failed to load users list.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isAdmin) {
      loadUsers();
    }
  }, [isAdmin]);

  const handleToggleStatus = async (targetUser: AdminUserItem) => {
    if (targetUser.id === currentUser?.id) {
      return;
    }
    setActionLoading(targetUser.id);
    try {
      const newStatus = !targetUser.is_active;
      await updateUserStatus(targetUser.id, newStatus);
      setUsers((prev) =>
        prev.map((u) => (u.id === targetUser.id ? { ...u, is_active: newStatus } : u))
      );
    } catch (err: any) {
      alert(err?.message || "Failed to update user status.");
    } finally {
      setActionLoading(null);
    }
  };

  if (authLoading || (loading && users.length === 0)) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] space-y-3">
        <RefreshCw className="w-8 h-8 animate-spin text-medPink-600" />
        <p className="text-sm font-semibold text-slate-600">{t("common.loading")}</p>
      </div>
    );
  }

  if (!isAdmin || role !== "ADMIN") {
    return (
      <div className="p-8 text-center bg-white rounded-3xl border border-rose-200 shadow-sm max-w-lg mx-auto">
        <AlertTriangle className="w-12 h-12 text-rose-500 mx-auto mb-3" />
        <h2 className="text-lg font-bold text-slate-900">{t("auth.accessDenied")}</h2>
        <p className="text-xs text-slate-500 mt-1">{t("auth.adminOnly")}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="p-6 sm:p-8 bg-white rounded-3xl border border-slate-200 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-medTeal-100/70 border border-medTeal-200 rounded-full text-xs font-bold text-medTeal-800 mb-2">
            <Users className="w-3.5 h-3.5" />
            <span>{t("nav.adminUsers")}</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
            {t("admin.usersTitle")}
          </h1>
          <p className="text-xs sm:text-sm text-slate-600 mt-1 leading-relaxed">
            {t("admin.usersDesc")}
          </p>
        </div>

        <button
          onClick={loadUsers}
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

      {/* Users Responsive Cards & Table Container */}
      <div className="bg-white rounded-3xl border border-slate-200 shadow-xs overflow-hidden">
        {/* Desktop Data Table */}
        <div className="hidden md:block overflow-x-auto">
          <table className="w-full text-left rtl:text-right border-collapse">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/75 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                <th className="py-3.5 px-6">{t("admin.colUsername")}</th>
                <th className="py-3.5 px-6">{t("admin.colRole")}</th>
                <th className="py-3.5 px-6">{t("admin.colStatus")}</th>
                <th className="py-3.5 px-6">{t("admin.colCreated")}</th>
                <th className="py-3.5 px-6">{t("admin.colAnalyses")}</th>
                <th className="py-3.5 px-6 text-center">{t("admin.colActions")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs">
              {users.map((u) => {
                const isCurrent = u.id === currentUser?.id;
                return (
                  <tr key={u.id} className="hover:bg-slate-50/50 transition">
                    <td className="py-4 px-6 font-bold text-slate-900 flex items-center gap-2">
                      <div className="w-8 h-8 rounded-full bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-700 font-semibold text-xs">
                        {u.username.charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <div>{u.username}</div>
                        {isCurrent && (
                          <span className="text-[10px] text-medPink-600 font-semibold">
                            ({t("auth.signedInAs")})
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-4 px-6">
                      <span
                        className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                          u.role === "ADMIN"
                            ? "bg-medPink-100 text-medPink-800 border border-medPink-200"
                            : "bg-medTeal-100 text-medTeal-800 border border-medTeal-200"
                        }`}
                      >
                        {u.role === "ADMIN" ? (
                          <Shield className="w-3 h-3" />
                        ) : (
                          <Users className="w-3 h-3" />
                        )}
                        <span>{u.role}</span>
                      </span>
                    </td>
                    <td className="py-4 px-6">
                      <span
                        className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold ${
                          u.is_active
                            ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                            : "bg-slate-100 text-slate-600 border border-slate-200"
                        }`}
                      >
                        {u.is_active ? t("admin.statusActive") : t("admin.statusInactive")}
                      </span>
                    </td>
                    <td className="py-4 px-6 text-slate-500 font-mono text-[11px]">
                      {u.created_at ? new Date(u.created_at).toLocaleDateString() : "—"}
                    </td>
                    <td className="py-4 px-6 font-semibold text-slate-700">
                      {u.analysis_count ?? 0}
                    </td>
                    <td className="py-4 px-6 text-center">
                      <button
                        onClick={() => handleToggleStatus(u)}
                        disabled={isCurrent || actionLoading === u.id}
                        className={`px-3 py-1 rounded-lg text-xs font-semibold transition shadow-2xs disabled:opacity-40 ${
                          u.is_active
                            ? "bg-rose-50 text-rose-700 border border-rose-200 hover:bg-rose-100"
                            : "bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100"
                        }`}
                      >
                        {actionLoading === u.id
                          ? t("common.loading")
                          : u.is_active
                          ? t("admin.deactivateBtn")
                          : t("admin.activateBtn")}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Mobile Responsive Cards */}
        <div className="md:hidden divide-y divide-slate-100">
          {users.map((u) => {
            const isCurrent = u.id === currentUser?.id;
            return (
              <div key={u.id} className="p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-full bg-slate-100 border border-slate-200 flex items-center justify-center font-bold text-xs text-slate-700">
                      {u.username.charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <div className="text-sm font-bold text-slate-900">{u.username}</div>
                      {isCurrent && (
                        <span className="text-[10px] text-medPink-600 font-semibold">
                          ({t("auth.signedInAs")})
                        </span>
                      )}
                    </div>
                  </div>
                  <span
                    className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                      u.role === "ADMIN"
                        ? "bg-medPink-100 text-medPink-800 border border-medPink-200"
                        : "bg-medTeal-100 text-medTeal-800 border border-medTeal-200"
                    }`}
                  >
                    {u.role}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs text-slate-600 pt-1">
                  <div>
                    <span className="text-slate-400 block text-[10px]">{t("admin.colStatus")}</span>
                    <span
                      className={`inline-block px-2 py-0.5 rounded text-[10px] font-semibold mt-0.5 ${
                        u.is_active
                          ? "bg-emerald-50 text-emerald-700"
                          : "bg-slate-100 text-slate-600"
                      }`}
                    >
                      {u.is_active ? t("admin.statusActive") : t("admin.statusInactive")}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px]">{t("admin.colAnalyses")}</span>
                    <span className="font-semibold text-slate-800">{u.analysis_count ?? 0}</span>
                  </div>
                </div>

                <div className="pt-2">
                  <button
                    onClick={() => handleToggleStatus(u)}
                    disabled={isCurrent || actionLoading === u.id}
                    className={`w-full py-2 rounded-xl text-xs font-semibold transition disabled:opacity-40 ${
                      u.is_active
                        ? "bg-rose-50 text-rose-700 border border-rose-200 hover:bg-rose-100"
                        : "bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100"
                    }`}
                  >
                    {actionLoading === u.id
                      ? t("common.loading")
                      : u.is_active
                      ? t("admin.deactivateBtn")
                      : t("admin.activateBtn")}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
