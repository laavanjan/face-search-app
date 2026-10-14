"use client";

import Link from "next/link";
import { setAccessKey } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { useSession } from "@/lib/session";

export default function NavAuth() {
  const { me, ready, can } = useSession();
  const { t } = useT();

  return (
    <nav aria-label="Main" className="flex flex-wrap items-center gap-2 text-sm">
      {can("photos:write") && <Link className="btn-ghost" href="/">{t("nav.index")}</Link>}
      {can("photos:search") && <Link className="btn-ghost" href="/search">{t("nav.search")}</Link>}
      {can("photos:read") && <Link className="btn-ghost" href="/gallery">{t("nav.gallery")}</Link>}
      {can("review:decide") && <Link className="btn-ghost" href="/review">{t("nav.review")}</Link>}
      {can("system:control") && <Link className="btn-ghost" href="/admin">{t("nav.admin")}</Link>}
      <Link className="btn-ghost" href="/appeal">{t("nav.appeal")}</Link>
      <Link className="btn-ghost" href="/privacy">{t("nav.privacy")}</Link>
      {ready &&
        (me ? (
          <button
            className="btn-ghost"
            onClick={() => setAccessKey(null)}
            title={`Roles: ${me.roles.join(", ")}`}
            aria-label={`Sign out ${me.name}`}
          >
            {me.name} · {t("nav.signout")}
          </button>
        ) : (
          <Link className="btn" href="/signin">{t("nav.signin")}</Link>
        ))}
    </nav>
  );
}
