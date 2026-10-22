"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import AppealForm from "@/components/AppealForm";
import AuthImage from "@/components/AuthImage";
import ConsentCheck from "@/components/ConsentCheck";
import Dropzone from "@/components/Dropzone";
import { Alert, EmptyState, Icon, PageHeader, Spinner, StatusBadge } from "@/components/ui";
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

/** Where a case is in its journey: submitted -> human review -> outcome. */
function CaseProgress({ status }: { status: string }) {
  const closed = !["pending_review", "escalated"].includes(status);
  const last =
    status === "stopped" ? "Stopped" : status === "no_match" ? "No match" : closed ? "Released" : "Release";
  const steps = [
    { label: "Submitted", state: "done" },
    { label: status === "escalated" ? "Escalated" : "Human review", state: closed ? "done" : "current" },
    { label: last, state: closed ? (status === "stopped" ? "stopped" : "done") : "todo" },
  ];
  return (
    <ol className="flex items-center gap-2 text-xs sm:gap-3" aria-label="Case progress">
      {steps.map((s, i) => (
        <li key={s.label} className="flex items-center gap-2 sm:gap-3">
          <span
            aria-current={s.state === "current" ? "step" : undefined}
            className={`flex items-center gap-1.5 font-medium ${
              s.state === "done" ? "text-success" : s.state === "current" ? "text-accent" : s.state === "stopped" ? "text-danger" : "text-subtle"
            }`}
          >
            <span
              aria-hidden
              className={`flex h-5 w-5 items-center justify-center rounded-full ring-1 ring-inset ${
                s.state === "done"
                  ? "bg-success/10 ring-success/30"
                  : s.state === "current"
                    ? "bg-accent/10 ring-accent/30"
                    : s.state === "stopped"
                      ? "bg-danger/10 ring-danger/30"
                      : "ring-line-strong"
              }`}
            >
              {s.state === "done" ? (
                <Icon name="check" className="h-3 w-3" />
              ) : s.state === "stopped" ? (
                <Icon name="x" className="h-3 w-3" />
              ) : s.state === "current" ? (
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current" />
              ) : null}
            </span>
            {s.label}
          </span>
          {i < steps.length - 1 && <span aria-hidden className="h-px w-4 bg-line-strong sm:w-8" />}
        </li>
      ))}
    </ol>
  );
}

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

  const done = (b: boolean, n: number) => (
    <span className={`step-num ${b ? "done" : ""}`}>{b ? <Icon name="check" className="h-3.5 w-3.5" /> : n}</span>
  );

  return (
    <div className="space-y-6">
      <PageHeader title={t("search.title")} description={t("search.lead")} />
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_300px]">
        <section className="card p-5 sm:p-6">
          {ready && !can("photos:search") ? (
            <div className="flex flex-col items-center py-10 text-center">
              <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-sunken text-subtle">
                <Icon name="lock" className="h-5 w-5" />
              </div>
              <p className="text-muted">{t("search.signin")}</p>
              <Link href="/signin" className="btn mt-4">{t("nav.signin")}</Link>
            </div>
          ) : (
            <ol className="space-y-6">
              <li className="flex gap-4">
                {done(!!purpose, 1)}
                <div className="min-w-0 flex-1">
                  <label htmlFor="search-purpose" className="label pt-1">{t("search.purpose")}</label>
                  <select
                    id="search-purpose"
                    required
                    className="select"
                    value={purpose}
                    onChange={(e) => setPurpose(e.target.value as typeof purpose)}
                  >
                    <option value="" disabled>{t("search.purpose.choose")}</option>
                    <option value="self">{t("search.purpose.self")}</option>
                    <option value="consenting_person">{t("search.purpose.consenting")}</option>
                  </select>
                </div>
              </li>
              <li className="flex gap-4">
                {done(consent, 2)}
                <div className="min-w-0 flex-1">
                  <ConsentCheck purpose="search" checked={consent} onChange={setConsent} />
                </div>
              </li>
              <li className="flex gap-4">
                <span className="step-num">3</span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-baseline justify-between gap-3 pt-1">
                    <label htmlFor="search-threshold" className="label">Similarity threshold</label>
                    <output htmlFor="search-threshold" className="badge badge-accent font-mono">{threshold.toFixed(2)}</output>
                  </div>
                  <input
                    id="search-threshold"
                    type="range"
                    min={minThreshold}
                    max={0.9}
                    step={0.01}
                    value={threshold}
                    onChange={(e) => setThreshold(parseFloat(e.target.value))}
                    className="h-2 !w-full cursor-pointer"
                  />
                  <p className="hint mt-1">
                    Minimum {minThreshold.toFixed(2)} is set by governance. Higher = fewer candidates.
                  </p>
                </div>
              </li>
              <li className="flex gap-4">
                <span className="step-num">4</span>
                <div className="min-w-0 flex-1">
                  <Dropzone onFile={run} disabled={busy || !consent || !purpose} locked={!consent || !purpose} />
                </div>
              </li>
            </ol>
          )}
          {busy && (
            <div role="status" className="mt-5 flex items-center gap-2 text-sm text-muted">
              <Spinner /> Searching…
            </div>
          )}
          {err && <Alert tone="danger" className="mt-5">{err}</Alert>}
        </section>

        <aside className="space-y-4 text-sm">
          <Link
            href="/accessibility#support"
            className="card flex items-start gap-3 p-5 transition-colors hover:border-accent/50"
          >
            <Icon name="help" className="mt-0.5 h-4 w-4 text-accent" />
            <span className="font-medium text-fg">{t("search.human")}</span>
          </Link>
          <div className="card p-5">
            <details className="group">
              <summary className="cursor-pointer list-none font-medium text-fg marker:hidden">
                <span className="inline-flex items-center gap-1.5">
                  <Icon name="arrowRight" className="h-3.5 w-3.5 text-subtle transition-transform group-open:rotate-90" />
                  {t("search.tech")}
                </span>
              </summary>
              <p className="mt-2 leading-relaxed text-muted">{t("search.techBody")}</p>
            </details>
          </div>
        </aside>
      </div>

      {res && (
        <section className="space-y-4" aria-label="Search case">
          <div className="card space-y-4 p-5 sm:p-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="section-title">Search case</h2>
                <span className="chip font-mono">{res.case_id.slice(0, 8)}</span>
                <StatusBadge status={res.status} />
              </div>
              <div className="flex flex-wrap gap-2">
                <button className="btn-secondary" onClick={refresh}>
                  <Icon name="refresh" /> Refresh
                </button>
                {can("review:decide") && res.status === "pending_review" && (
                  <Link className="btn-secondary" href={`/review?case=${res.case_id}`}>
                    Open in review queue <Icon name="arrowRight" />
                  </Link>
                )}
              </div>
            </div>
            <CaseProgress status={res.status} />
            <p className="text-sm text-muted">{STATUS_TEXT[res.status] ?? res.status}</p>
            <div className="flex flex-wrap gap-2">
              <span className="chip">threshold · {res.threshold_applied.toFixed(2)}</span>
              {res.candidate_count != null && <span className="chip">{res.candidate_count} candidate(s)</span>}
            </div>
            {res.notice && <p className="text-xs text-subtle">{res.notice}</p>}
            <details className="group rounded-xl bg-sunken px-4 py-3 text-xs text-muted">
              <summary className="cursor-pointer list-none font-medium text-fg marker:hidden">
                <span className="inline-flex items-center gap-1.5">
                  <Icon name="arrowRight" className="h-3.5 w-3.5 text-subtle transition-transform group-open:rotate-90" />
                  Limitations of these results
                </span>
              </summary>
              <ul className="mt-2 list-disc space-y-0.5 pl-5">
                {(res.limitations?.length ? res.limitations : LIMITATIONS).map((l) => (
                  <li key={l}>{l}</li>
                ))}
              </ul>
            </details>
          </div>

          {res.matches.length > 0 && (
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
              {res.matches.map((m) => (
                <div key={m.face_id} className="card overflow-hidden">
                  <AuthImage photoId={m.photo_id} alt="confirmed match" className="aspect-square w-full object-cover" />
                  <div className="space-y-2 p-3 text-xs">
                    <span className={`badge ${BAND_LABEL[m.confidence_band]?.tone}`} title={m.band_meaning}>
                      {BAND_LABEL[m.confidence_band]?.label}
                    </span>
                    <div className="flex items-center justify-between gap-2 text-muted">
                      <span>{m.score != null ? `${(m.score * 100).toFixed(1)}% similar` : "added by reviewer"}</span>
                      <span title="verified by" className="inline-flex items-center gap-1">
                        <Icon name="check" className="h-3 w-3 text-success" /> {m.reviewed_by}
                      </span>
                    </div>
                    <button
                      className="inline-flex min-h-[44px] items-center gap-1.5 font-medium text-muted underline-offset-2 hover:text-danger hover:underline"
                      aria-expanded={appealFor === m.face_id}
                      onClick={() => setAppealFor(appealFor === m.face_id ? null : m.face_id)}
                    >
                      <Icon name="flag" className="h-3.5 w-3.5" /> Report incorrect match
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
            <EmptyState icon="search" title="No confirmed matches">
              The reviewer did not confirm any candidate.
            </EmptyState>
          )}
        </section>
      )}
    </div>
  );
}
