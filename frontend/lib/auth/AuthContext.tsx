"use client";

import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { getUserSession, getAdminSession, loginUser, logoutUser, logoutAdmin, resetSession, ApiError } from "@/lib/api";
import type { UserPublic } from "@/types/api";

interface AuthContextType {
  user: UserPublic | null;
  adminUser: UserPublic | null;
  role: "ADMIN" | "USER" | null;
  isAdmin: boolean;
  isUser: boolean;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (credentials: { username: string; password: string }) => Promise<UserPublic>;
  logout: () => Promise<void>;
  resetUserSession: () => Promise<void>;
  refreshUser: () => Promise<void>;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserPublic | null>(null);
  const [adminUser, setAdminUser] = useState<UserPublic | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const refreshUser = useCallback(async () => {
    try {
      setIsLoading(true);

      // 1. Establish or retrieve anonymous USER session
      try {
        const userProfile = await getUserSession();
        setUser(userProfile);
        if (userProfile && userProfile.role === "ADMIN") {
          setAdminUser(userProfile);
        }
      } catch (err: unknown) {
        console.warn("Could not retrieve user backend session, using active anonymous fallback:", err);
        setUser({
          id: "anon_user",
          username: "anon_clinician",
          role: "USER",
          is_active: true,
        });
      }

      // 2. Check if active ADMIN session exists
      try {
        const adminProfile = await getAdminSession();
        if (adminProfile && adminProfile.role === "ADMIN") {
          setAdminUser(adminProfile);
        }
      } catch {
        // Normal state when not logged in as admin
      }

      setError(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const login = useCallback(
    async (credentials: { username: string; password: string }): Promise<UserPublic> => {
      try {
        setIsLoading(true);
        setError(null);
        const res = await loginUser(credentials);
        if (res.user && res.user.role === "ADMIN") {
          setAdminUser(res.user);
        }
        return res.user;
      } catch (err: unknown) {
        let msg = "Invalid administrator credentials.";
        if (err instanceof ApiError) {
          msg = err.message;
        } else if (err instanceof Error) {
          msg = err.message;
        }
        setError(msg);
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  const logout = useCallback(async () => {
    try {
      setIsLoading(true);
      await logoutAdmin();
      setAdminUser(null);
    } catch {
      setAdminUser(null);
    } finally {
      setError(null);
      setIsLoading(false);
    }
  }, []);

  const resetUserSession = useCallback(async () => {
    try {
      setIsLoading(true);
      await resetSession();
      // Provision a fresh anonymous USER session
      const freshUser = await getUserSession();
      setUser(freshUser);
    } catch {
      // User session fallback
      setUser({
        id: "anon_user",
        username: "anon_clinician",
        role: "USER",
        is_active: true,
      });
    } finally {
      setError(null);
      setIsLoading(false);
    }
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const isAdmin = adminUser !== null && adminUser.role === "ADMIN";
  const isUser = user !== null;
  const role = isAdmin ? "ADMIN" : isUser ? "USER" : null;
  const isAuthenticated = isAdmin || isUser;

  return (
    <AuthContext.Provider
      value={{
        user: isAdmin ? adminUser : user,
        adminUser,
        role,
        isAdmin,
        isUser,
        isAuthenticated,
        isLoading,
        error,
        login,
        logout,
        resetUserSession,
        refreshUser,
        clearError,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

const defaultAuthContext: AuthContextType = {
  user: null,
  adminUser: null,
  role: null,
  isAdmin: false,
  isUser: false,
  isAuthenticated: false,
  isLoading: false,
  error: null,
  login: async () => {
    throw new Error("AuthProvider not found");
  },
  logout: async () => {},
  resetUserSession: async () => {},
  refreshUser: async () => {},
  clearError: () => {},
};

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  return context || defaultAuthContext;
}
