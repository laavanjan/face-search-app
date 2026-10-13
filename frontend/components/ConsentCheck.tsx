"use client";

import Link from "next/link";

type Props = { checked: boolean; onChange: (v: boolean) => void; purpose: "index" | "search" };

/** Unchecked by default. The backend rejects the request without it when the
 * configured legal basis is consent, and audit-logs each confirmation. */
export default function ConsentCheck({ checked, onChange, purpose }: Props) {
  return (
    <label className="flex items-start gap-3 text-sm text-slate-300 mb-4 max-w-2xl">
      <input
        type="checkbox"
        className="mt-1 accent-accent"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
      />
      <span>
        {purpose === "index"
          ? "I confirm everyone identifiable in this photo has consented to having their face analysed and indexed, and that I am authorised to upload it."
          : "I confirm the person in this reference photo has consented to this search (or I am that person), and I will treat results as unverified until a reviewer confirms them."}{" "}
        <Link href="/privacy" className="underline text-slate-200">How the data is used</Link>.
      </span>
    </label>
  );
}
