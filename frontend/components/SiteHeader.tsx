"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LanguageSelect } from "@/components/SiteChrome";
import { Icon, type IconName } from "@/components/ui";
import { setAccessKey } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { useSession } from "@/lib/session";

type NavItem = { href: string; key: string; icon: IconName; perm?: string };

// Workspace links appear by permission; appeal and privacy are always visible
// so people without an account can find them.
const NAV: NavItem[] = [
  { href: "/", key: "nav.index", icon: "upload", perm: "photos:write" },
  { href: "/search", key: "nav.search", icon: "search", perm: "photos:search" },
  { href: "/gallery", key: "nav.gallery", icon: "image", perm: "photos:read" },
  { href: "/review", key: "nav.review", icon: "shield", perm: "review:decide" },
  { href: "/admin", key: "nav.admin", icon: "sliders", perm: "system:control" },
  { href: "/appeal", key: "nav.appeal", icon: "flag" },
  { href: "/privacy", key: "nav.privacy", icon: "lock" },
];

export default function SiteHeader() {
  const { me, ready, can } = useSession();
  const { t } = useT();
  const path = usePathname();
  const items = NAV.filter((n) => !n.perm || can(n.perm));
  const isActive = (href: string) => (href === "/" ? path === "/" : path.startsWith(href));

  return (
    <header className="sticky top-0 z-30 border-b border-line bg-surface/90 backdrop-blur supports-[backdrop-filter]:bg-surface/75">
      <div className="mx-auto flex h-16 max-w-6xl items-center gap-3 px-4 sm:px-6">
        <Link href="/" className="flex items-center gap-2.5">
          <span aria-hidden className="flex h-9 w-9 items-center justify-center rounded-xl bg-accent text-accent-fg shadow-sm">
            <Icon name="scan" className="h-5 w-5" />
          </span>
          <span className="leading-tight">
            <span className="block font-semibold tracking-tight text-fg">Face Search</span>
            <span className="hidden text-xs text-subtle sm:block">InsightFace + Qdrant · local-first</span>
          </span>
        </Link>
        <div className="ml-auto flex items-center gap-2">
          <LanguageSelect />
          {ready &&
            (me ? (
              <div className="flex items-center gap-1 rounded-xl border border-line bg-surface py-1 pl-1 pr-1 shadow-sm">
                <span
                  aria-hidden
                  className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent/10 text-sm font-semibold uppercase text-accent"
                >
                  {me.name.charAt(0)}
                </span>
                <span className="hidden px-1.5 leading-tight sm:block">
                  <span className="block text-sm font-medium text-fg">{me.name}</span>
                  <span className="block text-xs capitalize text-subtle">{me.roles.join(", ")}</span>
                </span>
                <button
                  className="btn-ghost !px-3"
                  onClick={() => setAccessKey(null)}
                  title={`Roles: ${me.roles.join(", ")}`}
                  aria-label={`${t("nav.signout")} (${me.name})`}
                >
                  <Icon name="logout" />
                  <span className="hidden md:inline">{t("nav.signout")}</span>
                </button>
              </div>
            ) : (
              <Link className="btn" href="/signin">
                {t("nav.signin")}
              </Link>
            ))}
        </div>
      </div>
      <nav aria-label="Main" className="mx-auto max-w-6xl px-2 sm:px-4">
        <ul className="-mb-px flex gap-1 overflow-x-auto [scrollbar-width:thin]">
          {items.map((n) => {
            const active = isActive(n.href);
            return (
              <li key={n.href} className="shrink-0">
                <Link
                  href={n.href}
                  aria-current={active ? "page" : undefined}
                  className={`flex min-h-[44px] items-center gap-2 whitespace-nowrap rounded-t-lg border-b-2 px-3 text-sm transition-colors ${
                    active
                      ? "border-accent font-medium text-fg"
                      : "border-transparent text-muted hover:border-line-strong hover:text-fg"
                  }`}
                >
                  <Icon name={n.icon} className={`h-4 w-4 ${active ? "text-accent" : ""}`} />
                  {t(n.key)}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </header>
  );
}
