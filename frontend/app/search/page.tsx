"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import AppealForm from "@/components/AppealForm";
import AuthImage from "@/components/AuthImage";
import ConsentCheck from "@/components/ConsentCheck";
import Dropzone from "@/components/Dropzone";
import { getPolicy, getSearchCase, searchPhoto, type SearchCase } from "@/lib/api";
import { useSession } from "@/lib/session";
import { useT } from "@/lib/i18n";
import { BAND_LABEL, LIMITATIONS } from "@/lib/limitations";

const STATUS_TEXT: Record<string, string> = {
  pending_review: "Waiting for a human reviewer. Candidates are not shown until they are verified.",
  escalated: "Escalated to the Service Owner. Nothing is released yet.",
  completed: "Reviewed. Only matches a reviewer confirmed are shown.",
  no_match: "No candidates were confirmed.",
  stopped: "A reviewer stopped this search. No results will be released.",
};

export default function SearchPage() {
  const { ready, can, me } = useSession();
  const { t } = useT();
  // No purpose is pre-selected; only the two permitted purposes exist (ACC-03, ACC-07).
  const [purpose, setPurpose] = useState<"" | "self" | "consenting_person">("");
  const [busy, setBusy] = useState(false);
  const [res, setRes] = useState<SearchCase | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [consent, setConsent] = useState(false);
  const [minThreshold, setMinThreshold] = useState(0.35);
  const [threshold, setThreshold] = useState(0.35);
  const [appealFor, setAppealFor] = useState<string | null>(null);

  useEffect(() => {
    getPolicy()
      .then((p) => {
        setMinThreshold(p.search_min_threshold);
        setThreshold((t) => Math.max(t, p.search_min_threshold));
      })
      .catch(() => {});
  }, []);

  async function run(f: File) {
    setBusy(true);
    setErr(null);
    setRes(null);
    try {
      if (!purpose) return;
      const r = await searchPhoto(f, { limit: 40, threshold, consent, purpose });
      setRes(r);
    } catch (e: any) {
      setErr(e.message ?? "search failed");
    } finally {
      setBusy(false);
    }
  }

  async function refresh() {
    if (!res) return;
    try {
      setRes(await getSearchCase(res.case_id));
    } catch (e: any) {
      setErr(e.message ?? "refresh failed");
    }
  }

  return (
    <div className="space-y-6">
      <section className="glass rounded-2xl p-6 sm:p-8">
        <h1 className="text-3xl font-semibold tracking-tight mb-2">{t("search.title")}</h1>
        <p className="text-slate-200 mb-3 max-w-2xl">{t("search.lead")}</p>
        <details className="text-sm text-slate-300 mb-3 max-w-2xl">
          <summary className="cursor-pointer underline">{t("search.tech")}</summary>
          <p className="mt-1">{t("search.techBody")}</p>
        </details>
        <p className="text-sm mb-6">
          <Link href="/accessibility#support" className="underline text-slate-200">{t("search.human")}</Link>
        </p>
        {ready && !can("photos:search") ? (
          <div className="text-slate-300">
            <Link href="/signin" className="underline">{t("nav.signin")}</Link> · {t("search.signin")}
          </div>
        ) : (
          <>
            <label className="block text-sm text-slate-200 mb-4 max-w-2xl">
              <span className="block mb-1">{t("search.purpose")}</span>
              <select
                required
                className="w-full rounded-xl bg-black/30 border border-white/20 p-2"
                value={purpose}
                onChange={(e) => setPurpose(e.target.value as typeof purpose)}
              >
                <option value="" disabled>{t("search.purpose.choose")}</option>
                <option value="self">{t("search.purpose.self")}</option>
                <option value="consenting_person">{t("search.purpose.consenting")}</option>
              </select>
            </label>
            <ConsentCheck purpose="search" checked={consent} onChange={setConsent} />
            <Dropzone onFile={run} disabled={busy || !consent || !purpose} />
            <div className="flex items-center gap-3 mt-4 text-sm text-slate-300">
              <label>Threshold</label>
              <input
                type="range"
                min={minThreshold}
                max={0.9}
                step={0.01}
                value={threshold}
                onChange={(e) => setThreshold(parseFloat(e.target.value))}
                className="accent-accent"
              />
              <span className="chip">{threshold.toFixed(2)}</span>
              <span className="text-slate-500 text-xs">
                Minimum {minThreshold.toFixed(2)} is set by governance. Higher = fewer candidates.
              </span>
            </div>
          </>
        )}
        {busy && (
          <div className="mt-4 text-sm text-slate-400 animate-pulse">Searching…</div>
        )}
        {err && <div className="mt-4 text-sm text-red-300">{err}</div>}
      </section>

      {res && (
        <section className="space-y-4">
          <div className="glass rounded-2xl p-6 text-sm space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="chip">case · {res.case_id.slice(0, 8)}</span>
              <span className="chip">status · {res.status}</span>
              <span className="chip">threshold · {res.threshold_applied.toFixed(2)}</span>
              {res.candidate_count != null && <span className="chip">{res.candidate_count} candidate(s)</span>}
              <button className="btn-ghost" onClick={refresh}>Refresh</button>
              {can("review:decide") && res.status === "pending_review" && (
                <Link className="btn-ghost" href={`/review?case=${res.case_id}`}>
                  Open in review queue
                </Link>
              )}
            </div>
            <div className="text-slate-400">{STATUS_TEXT[res.status] ?? res.status}</div>
            <div className="text-slate-500 text-xs">{res.notice}</div>
            <details className="text-xs text-slate-400">
              <summary className="cursor-pointer">Limitations of these results</summary>
              <ul className="list-disc pl-5 mt-1 space-y-0.5">
                {(res.limitations?.length ? res.limitations : LIMITATIONS).map((l) => (
                  <li key={l}>{l}</li>
                ))}
              </ul>
            </details>
          </div>

          {res.matches.length > 0 && (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
              {res.matches.map((m) => (
                <div key={m.face_id} className="glass rounded-xl overflow-hidden border border-white/5">
                  <AuthImage photoId={m.photo_id} alt="confirmed match" className="aspect-square object-cover w-full" />
                  <div className="p-2 space-y-1 text-xs">
                    <div className={BAND_LABEL[m.confidence_band]?.tone} title={m.band_meaning}>
                      {BAND_LABEL[m.confidence_band]?.label}
                    </div>
                    <div className="flex items-center justify-between text-slate-400">
                      <span>{m.score != null ? `${(m.score * 100).toFixed(1)}% similar` : "added by reviewer"}</span>
                      <span title="verified by">✓ {m.reviewed_by}</span>
                    </div>
                    <button
                      className="text-slate-400 underline"
                      onClick={() => setAppealFor(appealFor === m.face_id ? null : m.face_id)}
                    >
                      Report incorrect match
                    </button>
                    {appealFor === m.face_id && (
                      <AppealForm compact photoId={m.photo_id} faceId={m.face_id} caseId={res.case_id} />
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
          {me && res.status === "completed" && res.matches.length === 0 && (
            <div className="glass rounded-2xl p-8 text-center text-slate-400">
              The reviewer did not confirm any candidate.
            </div>
          )}
        </section>
      )}
    </div>
  );
}
