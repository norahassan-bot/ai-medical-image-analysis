"use client";

import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from "react";
import type { Language, Direction, LanguageContextType } from "./types";
import { en, TranslationKey } from "./locales/en";
import { ar } from "./locales/ar";

const LANGUAGE_STORAGE_KEY = "medvision_app_language";

const dictionaries: Record<Language, Record<TranslationKey, string>> = {
  ar,
  en,
};

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export function LanguageProvider({
  children,
  defaultLocale = "ar",
}: {
  children: React.ReactNode;
  defaultLocale?: Language;
}) {
  // Arabic is the DEFAULT and PRIMARY language unless defaultLocale is passed
  const [language, setLanguageState] = useState<Language>(defaultLocale);

  // Initialize language from localStorage on client mount if saved
  useEffect(() => {
    try {
      const savedLang = localStorage.getItem(LANGUAGE_STORAGE_KEY) as Language | null;
      if (savedLang && (savedLang === "en" || savedLang === "ar")) {
        setLanguageState(savedLang);
      }
    } catch {
      // Ignore localStorage access restrictions
    }
  }, []);

  // Update document root attributes whenever language changes
  useEffect(() => {
    const dir: Direction = language === "ar" ? "rtl" : "ltr";
    document.documentElement.lang = language;
    document.documentElement.dir = dir;
  }, [language]);

  const setLanguage = useCallback((newLang: Language) => {
    setLanguageState(newLang);
    try {
      localStorage.setItem(LANGUAGE_STORAGE_KEY, newLang);
    } catch {
      // Ignore storage errors
    }
  }, []);

  const direction: Direction = useMemo(() => (language === "ar" ? "rtl" : "ltr"), [language]);
  const isRTL = useMemo(() => language === "ar", [language]);

  const t = useCallback(
    (key: string, params?: Record<string, string | number>): string => {
      const currentDict = dictionaries[language] || dictionaries.ar;
      let text = (currentDict as Record<string, string>)[key] || (ar as Record<string, string>)[key] || (en as Record<string, string>)[key] || key;

      if (params) {
        Object.entries(params).forEach(([paramKey, paramValue]) => {
          text = text.replace(new RegExp(`\\{${paramKey}\\}`, "g"), String(paramValue));
        });
      }

      return text;
    },
    [language]
  );

  const contextValue = useMemo(
    () => ({
      language,
      direction,
      isRTL,
      setLanguage,
      t,
    }),
    [language, direction, isRTL, setLanguage, t]
  );

  return (
    <LanguageContext.Provider value={contextValue}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage(): LanguageContextType {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error("useLanguage must be used within a LanguageProvider");
  }
  return context;
}
