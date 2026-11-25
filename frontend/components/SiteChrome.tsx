"use client";

import Link from "next/link";
import { Icon } from "@/components/ui";
import { useT } from "@/lib/i18n";

/** Skip link for keyboard and screen-reader users (ACC-01). */
export function SkipLink() {
  const { t } = useT();
  return (
    <a href="#main" className="skip-link">
      {t("skip")}
    </a>
  );
}

/** Persistent, plain-language AI disclosure (TRAN-01, ACC-07: not misleading). */
export function AiNotice() {
  const { t } = useT();
  return (
    <div role="note" className="mb-8 flex items-start gap-3 rounded-xl border border-warning/30 bg-warning/5 px-4 py-3 text-sm">
      <span className="badge badge-warning mt-px">AI</span>
      <p className="leading-relaxed text-muted">
        <strong className="font-semibold text-fg">{t("banner.title")}</strong> {t("banner.body")}{" "}
        <Link href="/privacy" className="link">{t("banner.privacy")}</Link>
        <span aria-hidden className="mx-1.5 text-subtle">·</span>
        <Link href="/appeal" className="link">{t("banner.challenge")}</Link>
      </p>
    </div>
  );
}

export function SiteFooter() {
  const { t } = useT();
  return (
    <footer className="mt-16 border-t border-line">
      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-8 text-sm text-muted sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <span>{t("footer.free")}</span>
        <nav aria-label="Footer" className="flex flex-wrap gap-x-5 gap-y-2">
          {[
            ["/accessibility", t("footer.accessibility")],
            ["/transparency", t("footer.transparency")],
            ["/appeal", t("nav.appeal")],
          ].map(([href, label]) => (
            <Link key={href} href={href} className="underline decoration-line-strong underline-offset-4 hover:text-fg hover:decoration-fg">
              {label}
            </Link>
          ))}
        </nav>
      </div>
    </footer>
  );
}
