"use client";

// Language support (ACC-01, SOC-08). Strings live in /locales/*.json; English is
// the fallback for any missing key. The choice is remembered in this browser
// and sets <html lang> so screen readers use the right voice.
import { useCallback, useEffect, useState } from "react";
import en from "@/locales/en.json";
import es from "@/locales/es.json";

export const LOCALES = { en, es } as const;
export type Locale = keyof typeof LOCALES;
const KEY = "fsa.locale";
const EVENT = "fsa-locale";

function readLocale(): Locale {
  try {
    const v = window.localStorage.getItem(KEY);
    if (v && v in LOCALES) return v as Locale;
    const nav = navigator.language?.slice(0, 2);
    if (nav && nav in LOCALES) return nav as Locale;
  } catch {
    /* storage unavailable */
  }
  return "en";
}

export function setLocale(l: Locale) {
  try {
    window.localStorage.setItem(KEY, l);
  } catch {
    /* ignore */
  }
  window.dispatchEvent(new Event(EVENT));
}

export function useT() {
  const [locale, setL] = useState<Locale>("en");
  useEffect(() => {
    const sync = () => {
      const l = readLocale();
      setL(l);
      document.documentElement.lang = l;
    };
    sync();
    window.addEventListener(EVENT, sync);
    return () => window.removeEventListener(EVENT, sync);
  }, []);
  const t = useCallback(
    (key: string, vars?: Record<string, string>) => {
      const dict = LOCALES[locale] as Record<string, string>;
      let s = dict[key] ?? (en as Record<string, string>)[key] ?? key;
      for (const [k, v] of Object.entries(vars ?? {})) s = s.replace(`{${k}}`, v);
      return s;
    },
    [locale]
  );
  return { t, locale };
}
