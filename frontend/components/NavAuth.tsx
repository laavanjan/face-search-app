"use client";

import Link from "next/link";
import { setAccessKey } from "@/lib/api";
import { useSession } from "@/lib/session";

export default function NavAuth() {
  const { me, ready, can } = useSession();

  return (
    <nav className="flex flex-wrap items-center gap-2 text-sm">
      {can("photos:write") && <Link className="btn-ghost" href="/">Index</Link>}
      {can("photos:search") && <Link className="btn-ghost" href="/search">Search</Link>}
      {can("photos:read") && <Link className="btn-ghost" href="/gallery">Gallery</Link>}
      {can("review:decide") && <Link className="btn-ghost" href="/review">Review</Link>}
      {can("system:control") && <Link className="btn-ghost" href="/admin">Admin</Link>}
      <Link className="btn-ghost" href="/appeal">Appeal</Link>
      <Link className="btn-ghost" href="/privacy">Privacy &amp; AI use</Link>
      {ready &&
        (me ? (
          <button
            className="btn-ghost"
            onClick={() => setAccessKey(null)}
            title={`Roles: ${me.roles.join(", ")}`}
            aria-label={`Sign out ${me.name}`}
          >
            {me.name} · sign out
          </button>
        ) : (
          <Link className="btn" href="/signin">Sign in</Link>
        ))}
    </nav>
  );
}
