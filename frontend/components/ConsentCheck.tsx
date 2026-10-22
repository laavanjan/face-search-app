"use client";

import Link from "next/link";
import { useT } from "@/lib/i18n";

type Props = { checked: boolean; onChange: (v: boolean) => void; purpose: "index" | "search" };

/** Consent design (ACC-07): never pre-ticked (callers start with `false`, and
 * tests/test_inclusion.py fails on any pre-checked box or `true` initial state),
 * plain wording, one purpose per box, nothing bundled. Declining simply means
 * the photo is not processed. The backend refuses the request without it and
 * audit-logs each confirmation. */
export default function ConsentCheck({ checked, onChange, purpose }: Props) {
  const { t } = useT();
  return (
    <label className="choice">
      <input type="checkbox" className="mt-0.5" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span className="leading-relaxed">
        {purpose === "index" ? t("consent.index") : t("consent.search")}{" "}
        <Link href="/privacy" className="link">{t("consent.link")}</Link>.
      </span>
    </label>
  );
}
