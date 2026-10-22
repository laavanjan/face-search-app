"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import AuthImage from "@/components/AuthImage";
import { useDecisionNote } from "@/components/DecisionNote";
import { Alert, EmptyState, Icon, PageHeader, SectionHeader, StatusBadge, humanize } from "@/components/ui";
import {
  acknowledgeAppeal,
  closeCase,
  decideCandidate,
  decidePhoto,
  fmtDate,
  getCase,
  listAppeals,
  listCases,
  manualMatch,
  pendingPhotos,
  reopenCase,
  resolveAppeal,
  type Appeal,
  type PendingPhoto,
  type ReviewCase,
} from "@/lib/api";
import { useSession } from "@/lib/session";
import { BAND_LABEL, bandFor } from "@/lib/limitations";

type Take = { take: () => string | null };

function IndexQueue({ take }: Take) {
  const [items, setItems] = useState<PendingPhoto[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const load = useCallback(() => {
    pendingPhotos().then((r) => setItems(r.items)).catch((e) => setErr(e.message));
  }, []);
  useEffect(load, [load]);

  async function act(pid: string, decision: "approve" | "reject") {
    const reason = take();
    if (!reason) return;
    try {
      await decidePhoto(pid, decision, reason);
      load();
    } catch (e: any) {
      setErr(e.message);
    }
  }

  return (
    <section className="card p-5 sm:p-6">
      <SectionHeader
        icon="image"
        title="Indexing approvals"
        count={items?.length}
        description="Faces stay out of search until approved. Check the uploader had authority and consent, and that detections are real faces. Rejecting deletes the photo and its embeddings."
      />
      {err && <Alert tone="danger" className="mb-4" role="alert">{err}</Alert>}
      {items?.length === 0 && (
        <div className="flex items-center gap-2 rounded-xl bg-sunken px-4 py-3 text-sm text-muted">
          <Icon name="check" className="h-4 w-4 text-success" /> Nothing waiting.
        </div>
      )}
      <ul className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-4">
        {items?.map((p) => (
          <li key={p.photo_id} className="overflow-hidden rounded-xl border border-line bg-surface">
            <AuthImage photoId={p.photo_id} alt="pending photo" className="aspect-square w-full object-cover" />
            <div className="space-y-2 p-3 text-xs text-muted">
              <div className="flex items-center justify-between gap-2">
                <span>{p.faces.length} face(s)</span>
                <span className="truncate font-mono text-subtle" title={p.uploaded_by}>by {p.uploaded_by}</span>
              </div>
              <div className="flex flex-wrap gap-1">
                {p.faces.map((f) => (
                  <span key={f.face_id} className="chip font-mono">det {f.det_score.toFixed(2)} · q {f.quality.toFixed(2)}</span>
                ))}
              </div>
              <div className="text-subtle">{fmtDate(p.indexed_at)}</div>
              <div className="grid grid-cols-2 gap-2 pt-1">
                <button className="btn-success btn-sm" onClick={() => act(p.photo_id, "approve")}>
                  <Icon name="check" className="h-3.5 w-3.5" /> Approve
                </button>
                <button className="btn-danger btn-sm" onClick={() => act(p.photo_id, "reject")}>
                  <Icon name="x" className="h-3.5 w-3.5" /> Reject
                </button>
              </div>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

const DECISION_BTN = { approve: "btn-success", reject: "btn-danger", reopen: "btn-secondary" } as const;

function CaseDetail({ id, onChange, take }: Take & { id: string; onChange: () => void }) {
  const [c, setC] = useState<ReviewCase | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [manual, setManual] = useState("");
  // Automation-bias guards (ACC-03): scores stay hidden until the reviewer has
  // looked at the faces, and low-confidence approvals need an explicit check.
  const [showScores, setShowScores] = useState(false);
  const [acked, setAcked] = useState<Record<string, boolean>>({});

  const load = useCallback(() => {
    getCase(id).then(setC).catch((e) => setErr(e.message));
  }, [id]);
  useEffect(load, [load]);

  async function run(fn: () => Promise<ReviewCase>) {
    setErr(null);
    try {
      setC(await fn());
      onChange();
    } catch (e: any) {
      setErr(e.message);
    }
  }

  if (!c) return err ? <Alert tone="danger">{err}</Alert> : <div className="skeleton h-48 rounded-xl" />;
  const open = c.status === "pending_review" || c.status === "escalated";

  return (
    <div className="space-y-5 rounded-2xl border border-line bg-sunken/50 p-4 sm:p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="chip font-mono">case · {c.id.slice(0, 8)}</span>
          <StatusBadge status={c.status} />
          <span className="chip">requested by · {c.requested_by}</span>
          <span className="chip">threshold · {c.threshold.toFixed(2)}</span>
          <span className="chip">{fmtDate(c.created_at)}</span>
        </div>
        <button className="btn-secondary btn-sm" aria-pressed={showScores} onClick={() => setShowScores(!showScores)}>
          <Icon name={showScores ? "eyeOff" : "eye"} className="h-3.5 w-3.5" />
          {showScores ? "Hide model scores" : "Show model scores"}
        </button>
      </div>
      {err && <Alert tone="danger">{err}</Alert>}
      <div className="flex flex-col gap-5 md:flex-row md:items-start">
        <div className="w-40 shrink-0">
          <div className="mb-1.5 text-xs font-medium uppercase tracking-wide text-subtle">Reference photo</div>
          {c.has_query_image ? (
            <AuthImage caseId={c.id} alt="query" className="aspect-square w-40 rounded-xl object-cover ring-2 ring-accent/40" />
          ) : (
            <div className="flex aspect-square w-40 items-center justify-center rounded-xl bg-sunken text-xs text-subtle">
              not retained
            </div>
          )}
        </div>
        <div className="min-w-0 flex-1">
          <div className="mb-1.5 text-xs font-medium uppercase tracking-wide text-subtle">
            Candidates ({c.candidates?.length ?? 0})
          </div>
          <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-4">
            {c.candidates?.map((k) => {
              const band = bandFor(k.score, c.threshold);
              return (
                <li
                  key={k.face_id}
                  className={`overflow-hidden rounded-xl border bg-surface ${
                    k.decision === "approve"
                      ? "border-success/60 ring-1 ring-success/30"
                      : k.decision === "reject"
                        ? "border-danger/40 opacity-60"
                        : "border-line"
                  }`}
                >
                  <AuthImage photoId={k.photo_id} alt="candidate" className="aspect-square w-full object-cover" />
                  <div className="space-y-2 p-2.5 text-xs text-muted">
                    <StatusBadge status={k.decision} />
                    {showScores ? (
                      <div className="space-y-1">
                        <div className="font-mono text-fg">{k.score != null ? `${(k.score * 100).toFixed(1)}% similar` : "manual"}</div>
                        <span className={`badge ${BAND_LABEL[band].tone}`}>{BAND_LABEL[band].label}</span>
                      </div>
                    ) : (
                      <div className="flex items-center gap-1.5 text-subtle">
                        <Icon name="eyeOff" className="h-3.5 w-3.5" /> Compare the faces first - score hidden
                      </div>
                    )}
                    {open && band === "low" && (
                      <label className="flex items-start gap-2 rounded-lg bg-warning/10 p-2 text-warning">
                        <input
                          type="checkbox"
                          className="!h-4 !w-4"
                          checked={!!acked[k.face_id]}
                          onChange={(e) => setAcked({ ...acked, [k.face_id]: e.target.checked })}
                        />
                        <span>Uncertain match: I compared the faces myself</span>
                      </label>
                    )}
                    <div className="font-mono text-[11px] text-subtle">bbox {k.bbox.join(",")}</div>
                    {open && (
                      <div className="grid grid-cols-3 gap-1">
                        {(["approve", "reject", "reopen"] as const).map((d) => (
                          <button
                            key={d}
                            className={`${DECISION_BTN[d]} !px-1 text-xs`}
                            onClick={() => {
                              const r = take();
                              if (r) run(() => decideCandidate(c.id, k.face_id, d, r, !!acked[k.face_id]));
                            }}
                          >
                            {humanize(d)}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      </div>
      {open ? (
        <div className="space-y-4 border-t border-line pt-4">
          <div className="flex flex-col gap-2 sm:flex-row">
            <label htmlFor={`manual-${c.id}`} className="sr-only">Manual takeover: photo id the model missed</label>
            <input
              id={`manual-${c.id}`}
              className="input font-mono"
              placeholder="Manual takeover: photo id the model missed"
              value={manual}
              onChange={(e) => setManual(e.target.value.trim())}
            />
            <button
              className="btn-secondary"
              disabled={!manual}
              onClick={() => {
                const r = take();
                if (r) run(() => manualMatch(c.id, manual, r));
              }}
            >
              <Icon name="plus" /> Add match
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            {(
              [
                ["completed", "Complete & release approved", "btn"],
                ["no_match", "No match", "btn-secondary"],
                ["escalated", "Escalate", "btn-secondary"],
                ["stopped", "Stop - release nothing", "btn-danger"],
              ] as const
            ).map(([o, label, cls]) => (
              <button
                key={o}
                className={cls}
                onClick={() => {
                  const r = take();
                  if (r) run(() => closeCase(c.id, o, r));
                }}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div className="border-t border-line pt-4">
          <button
            className="btn-secondary"
            onClick={() => {
              const r = take();
              if (r) run(() => reopenCase(c.id, r));
            }}
          >
            <Icon name="refresh" /> Reopen case
          </button>
        </div>
      )}
    </div>
  );
}

function CaseQueue({ take }: Take) {
  const params = useSearchParams();
  const [status, setStatus] = useState("pending_review");
  const [items, setItems] = useState<ReviewCase[] | null>(null);
  const [selected, setSelected] = useState<string | null>(params.get("case"));
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(() => {
    listCases(status).then((r) => setItems(r.items)).catch((e) => setErr(e.message));
  }, [status]);
  useEffect(load, [load]);

  return (
    <section className="card p-5 sm:p-6">
      <SectionHeader
        icon="search"
        title="Search result review"
        count={items?.length}
        description="Similarity scores are not identity decisions. Compare each candidate with the reference photo; approve only when you are confident it is the same person. Nothing is released to the requester until you complete the case."
        actions={
          <label className="flex items-center gap-2 text-sm text-muted">
            <span>Status</span>
            <select className="select !w-auto" value={status} onChange={(e) => setStatus(e.target.value)}>
              {["pending_review", "escalated", "completed", "no_match", "stopped", ""].map((s) => (
                <option key={s} value={s}>{s ? humanize(s) : "All"}</option>
              ))}
            </select>
          </label>
        }
      />
      {err && <Alert tone="danger" className="mb-4">{err}</Alert>}
      {items?.length === 0 && (
        <div className="flex items-center gap-2 rounded-xl bg-sunken px-4 py-3 text-sm text-muted">
          <Icon name="check" className="h-4 w-4 text-success" /> No cases.
        </div>
      )}
      {!!items?.length && (
        <ul className="mb-5 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((c) => {
            const on = selected === c.id;
            return (
              <li key={c.id}>
                <button
                  aria-pressed={on}
                  className={`flex w-full min-h-[44px] items-center justify-between gap-3 rounded-xl border px-3 py-2.5 text-left text-sm transition-colors ${
                    on ? "border-accent bg-accent/5 ring-1 ring-accent/30" : "border-line bg-surface hover:border-line-strong"
                  }`}
                  onClick={() => setSelected(c.id)}
                >
                  <span className="min-w-0">
                    <span className="block font-mono text-xs text-fg">{c.id.slice(0, 8)}</span>
                    <span className="block truncate text-xs text-subtle">{c.requested_by}</span>
                  </span>
                  <span className="flex shrink-0 flex-col items-end gap-1">
                    <StatusBadge status={c.status} />
                    <span className="text-[11px] text-subtle">{c.undecided ?? 0} undecided</span>
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
      {selected && <CaseDetail key={selected} id={selected} onChange={load} take={take} />}
    </section>
  );
}

type Outcome = "upheld" | "partially_upheld" | "rejected";
type Action = "none" | "delete_photo" | "restore_photo";

function AppealResolver({ a, onResolve }: { a: Appeal; onResolve: (a: Appeal, o: Outcome, x: Action) => void }) {
  const [outcome, setOutcome] = useState<Outcome>("upheld");
  const [action, setAction] = useState<Action>(a.category === "deletion_request" ? "delete_photo" : "none");
  return (
    <div className="flex flex-wrap items-center gap-2">
      <label className="sr-only" htmlFor={`outcome-${a.id}`}>Outcome</label>
      <select id={`outcome-${a.id}`} className="select !w-auto" value={outcome} onChange={(e) => setOutcome(e.target.value as Outcome)}>
        <option value="upheld">Upheld</option>
        <option value="partially_upheld">Partially upheld</option>
        <option value="rejected">Rejected</option>
      </select>
      <label className="sr-only" htmlFor={`action-${a.id}`}>Data action</label>
      <select id={`action-${a.id}`} className="select !w-auto" value={action} onChange={(e) => setAction(e.target.value as Action)}>
        <option value="none">No data action</option>
        <option value="delete_photo">Delete photo (admin)</option>
        <option value="restore_photo">Restore photo to search</option>
      </select>
      <button className="btn" onClick={() => onResolve(a, outcome, action)}>
        Resolve with note
      </button>
    </div>
  );
}

function AppealQueue({ take }: Take) {
  const [items, setItems] = useState<Appeal[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const load = useCallback(() => {
    listAppeals().then((r) => setItems(r.items)).catch((e) => setErr(e.message));
  }, []);
  useEffect(load, [load]);

  async function resolve(a: Appeal, outcome: Outcome, action: Action) {
    const resolution = take();
    if (!resolution) return;
    try {
      await resolveAppeal(a.id, outcome, resolution, action);
      load();
    } catch (e: any) {
      setErr(e.message);
    }
  }

  return (
    <section className="card p-5 sm:p-6">
      <SectionHeader icon="flag" title="Appeals" count={items?.filter((a) => a.status !== "resolved").length} />
      {err && <Alert tone="danger" className="mb-4">{err}</Alert>}
      {items?.length === 0 && (
        <div className="flex items-center gap-2 rounded-xl bg-sunken px-4 py-3 text-sm text-muted">
          <Icon name="check" className="h-4 w-4 text-success" /> No appeals.
        </div>
      )}
      <ul className="space-y-3">
        {items?.map((a) => (
          <li key={a.id} className="space-y-3 rounded-xl border border-line bg-surface p-4 text-sm">
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="badge badge-accent">{humanize(a.category)}</span>
              <StatusBadge status={a.status} />
              {a.overdue && <StatusBadge status="overdue" />}
              <span className="chip">
                <Icon name="clock" className="h-3 w-3" /> due {fmtDate(a.resolve_by)}
              </span>
              {a.photo_id && <span className="chip font-mono">photo {a.photo_id.slice(0, 8)}</span>}
            </div>
            <p className="leading-relaxed text-fg">{a.reason}</p>
            {a.contact && <div className="text-xs text-subtle">contact: {a.contact}</div>}
            {a.status !== "resolved" ? (
              <div className="flex flex-wrap items-center gap-2 border-t border-line pt-3">
                {a.status === "received" && (
                  <button className="btn-secondary" onClick={() => acknowledgeAppeal(a.id).then(load)}>
                    <Icon name="check" /> Acknowledge
                  </button>
                )}
                <AppealResolver a={a} onResolve={resolve} />
              </div>
            ) : (
              <div className="rounded-lg bg-sunken px-3 py-2 text-xs text-muted">
                <span className="font-medium text-fg">{a.outcome && humanize(a.outcome)}:</span> {a.resolution}
              </div>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}

export default function ReviewPage() {
  const { ready, can } = useSession();
  const note = useDecisionNote();
  if (ready && !can("review:decide") && !can("appeals:manage"))
    return (
      <EmptyState icon="shield" title="Reviewer console">
        This console is for assigned Human Reviewers. <Link href="/signin" className="link">Sign in</Link> with a reviewer key.
      </EmptyState>
    );
  if (!ready) return null;
  return (
    <div className="space-y-6">
      <PageHeader
        title="Review"
        description="Approve photos before they become searchable, verify search candidates before anything is released, and resolve appeals."
      />
      {note.field}
      {can("review:decide") && (
        <>
          <IndexQueue take={note.take} />
          <Suspense>
            <CaseQueue take={note.take} />
          </Suspense>
        </>
      )}
      {can("appeals:manage") && <AppealQueue take={note.take} />}
    </div>
  );
}
