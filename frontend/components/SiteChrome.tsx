"use client";

import Link from "next/link";
import { LOCALES, setLocale, useT, type Locale } from "@/lib/i18n";

/** Skip link for keyboard and screen-reader users (ACC-01). */
export function SkipLink() {
  const { t } = useT();
  return (
    <a href="#main" className="skip-link">
      {t("skip")}
    </a>
  );
}

export function LanguageSelect() {
  const { t, locale } = useT();
  return (
    <label className="flex items-center gap-2 text-xs text-slate-300">
      <span>{t("lang.label")}</span>
      <select
        className="rounded-lg bg-black/30 border border-white/20 p-1"
        value={locale}
        onChange={(e) => setLocale(e.target.value as Locale)}
      >
        {(Object.keys(LOCALES) as Locale[]).map((l) => (
          <option key={l} value={l} lang={l}>
            {(LOCALES[l] as Record<string, string>)["lang.name"]}
          </option>
        ))}
      </select>
    </label>
  );
}

/** Persistent, plain-language AI disclosure (TRAN-01, ACC-07: not misleading). */
export function AiNotice() {
  const { t } = useT();
  return (
    <div role="note" className="mb-8 rounded-xl border border-amber-300/30 bg-amber-300/10 px-4 py-2 text-sm text-amber-50">
      <strong>{t("banner.title")}</strong> {t("banner.body")}{" "}
      <Link href="/privacy" className="underline">{t("banner.privacy")}</Link> ·{" "}
      <Link href="/appeal" className="underline">{t("banner.challenge")}</Link>
    </div>
  );
}

export function SiteFooter() {
  const { t } = useT();
  return (
    <footer className="mt-16 border-t border-white/10 pt-6 text-sm text-slate-300 flex flex-wrap gap-4 justify-between">
      <span>{t("footer.free")}</span>
      <nav aria-label="Footer" className="flex gap-4">
        <Link href="/accessibility" className="underline">{t("footer.accessibility")}</Link>
        <Link href="/transparency" className="underline">{t("footer.transparency")}</Link>
        <Link href="/appeal" className="underline">{t("nav.appeal")}</Link>
      </nav>
    </footer>
  );
}
