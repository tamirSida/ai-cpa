"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { ApiError } from "@/lib/apiClient";
import { messages, type Lang, type MsgKey } from "@/lib/messages";

export const DEFAULT_LANG: Lang = "en"; // English is the default language
const STORAGE_KEY = "lang";

type Vars = Record<string, string | number>;

interface I18nState {
  lang: Lang;
  setLang: (l: Lang) => void;
  t: (key: MsgKey, vars?: Vars) => string;
  /** Localized text for an unknown error: maps ApiError.code -> error.<code>, else falls
   *  back to the (possibly already-localized) backend message, else a generic line. */
  tError: (e: unknown) => string;
}

const I18nContext = createContext<I18nState>({
  lang: DEFAULT_LANG,
  setLang: () => {},
  t: (k) => k,
  tError: () => "",
});

function interpolate(s: string, vars?: Vars): string {
  if (!vars) return s;
  return Object.entries(vars).reduce((acc, [k, v]) => acc.replaceAll(`{${k}}`, String(v)), s);
}

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Lang>(DEFAULT_LANG);

  // Load the saved choice on mount (SSR renders the English default to avoid a hydration mismatch).
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === "he" || saved === "en") setLangState(saved);
  }, []);

  // Reflect language onto <html> so direction + screen-reader language follow the choice.
  useEffect(() => {
    document.documentElement.lang = lang;
    document.documentElement.dir = lang === "he" ? "rtl" : "ltr";
  }, [lang]);

  const setLang = useCallback((l: Lang) => {
    localStorage.setItem(STORAGE_KEY, l);
    setLangState(l);
  }, []);

  const t = useCallback(
    (key: MsgKey, vars?: Vars) => interpolate(messages[lang][key] ?? messages.en[key] ?? key, vars),
    [lang]
  );

  const tError = useCallback(
    (e: unknown): string => {
      if (e instanceof ApiError) {
        const key = `error.${e.code}` as MsgKey;
        if (key in messages.en) return t(key);
        return e.message || t("error.generic");
      }
      return t("error.generic");
    },
    [t]
  );

  return <I18nContext.Provider value={{ lang, setLang, t, tError }}>{children}</I18nContext.Provider>;
}

export const useI18n = () => useContext(I18nContext);
export const useT = () => useI18n().t;
