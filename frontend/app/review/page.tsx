"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import AuthImage from "@/components/AuthImage";
import { useDecisionNote } from "@/components/DecisionNote";
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
    <section className="glass rounded-2xl p-6 space-y-4">
      <h2 className="text-lg font-medium">Indexing approvals</h2>
      <p className="text-xs text-slate-400">
        Faces stay out of search until approved. Check the uploader had authority and consent, and
        that detections are real faces. Rejecting deletes the photo and its embeddings.
      </p>
      {err && <div className="text-sm text-red-300">{err}</div>}
      {items?.length === 0 && <div className="text-sm text-slate-500">Nothing waiting.</div>}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {items?.map((p) => (
          <div key={p.photo_id} className="rounded-xl border border-white/10 overflow-hidden">
            <AuthImage photoId={p.photo_id} alt="pending photo" className="aspect-square object-cover w-full" />
            <div className="p-2 text-xs space-y-1 text-slate-400">
              <div>{p.faces.length} face(s) · by {p.uploaded_by}</div>
              <div>
                {p.faces.map((f) => (
                  <span key={f.face_id} className="chip mr-1">det {f.det_score.toFixed(2)} · q {f.quality.toFixed(2)}</span>
                ))}
              </div>
              <div>{fmtDate(p.indexed_at)}</div>
              <div className="flex gap-2 pt-1">
                <button className="btn-ghost" onClick={() => act(p.photo_id, "approve")}>Approve</button>
                <button className="btn-ghost text-red-300" onClick={() => act(p.photo_id, "reject")}>Reject</button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

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

  if (!c) return <div className="text-sm text-slate-500">{err ?? "Loading…"}</div>;
  const open = c.status === "pending_review" || c.status === "escalated";

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="chip">case · {c.id.slice(0, 8)}</span>
        <span className="chip">status · {c.status}</span>
        <span className="chip">requested by · {c.requested_by}</span>
        <span className="chip">threshold · {c.threshold.toFixed(2)}</span>
        <button className="btn-ghost !py-1 text-xs" aria-pressed={showScores} onClick={() => setShowScores(!showScores)}>
          {showScores ? "Hide model scores" : "Show model scores"}
        </button>
        <span className="chip">{fmtDate(c.created_at)}</span>
      </div>
      {err && <div className="text-sm text-red-300">{err}</div>}
      <div className="flex flex-wrap gap-4 items-start">
        <div className="w-40">
          <div className="text-xs text-slate-400 mb-1">Reference photo</div>
          {c.has_query_image ? (
            <AuthImage caseId={c.id} alt="query" className="w-40 aspect-square object-cover rounded-lg" />
          ) : (
            <div className="w-40 aspect-square rounded-lg bg-white/5 text-xs text-slate-500 flex items-center justify-center">
              not retained
            </div>
          )}
        </div>
        <div className="flex-1 grid grid-cols-2 md:grid-cols-4 gap-3">
          {c.candidates?.map((k) => (
            <div
              key={k.face_id}
              className={`rounded-lg border overflow-hidden ${
                k.decision === "approve" ? "border-emerald-400/50" : k.decision === "reject" ? "border-red-400/40 opacity-60" : "border-white/10"
              }`}
            >
              <AuthImage photoId={k.photo_id} alt="candidate" className="aspect-square object-cover w-full" />
              <div className="p-2 text-xs space-y-1 text-slate-400">
                <div>{k.decision}</div>
                {showScores ? (
                  <>
                    <div>{k.score != null ? `${(k.score * 100).toFixed(1)}% similar` : "manual"}</div>
                    <div className={BAND_LABEL[bandFor(k.score, c.threshold)].tone}>
                      {BAND_LABEL[bandFor(k.score, c.threshold)].label}
                    </div>
                  </>
                ) : (
                  <div className="text-slate-300">Compare the faces first - score hidden</div>
                )}
                {open && bandFor(k.score, c.threshold) === "low" && (
                  <label className="flex items-start gap-1 text-amber-200">
                    <input
                      type="checkbox"
                      checked={!!acked[k.face_id]}
                      onChange={(e) => setAcked({ ...acked, [k.face_id]: e.target.checked })}
                    />
                    <span>Uncertain match: I compared the faces myself</span>
                  </label>
                )}
                <div>bbox {k.bbox.join(",")}</div>
                {open && (
                  <div className="flex flex-wrap gap-1">
                    {(["approve", "reject", "reopen"] as const).map((d) => (
                      <button
                        key={d}
                        className="btn-ghost !px-2 !py-1"
                        onClick={() => {
                          const r = take();
                          if (r) run(() => decideCandidate(c.id, k.face_id, d, r, !!acked[k.face_id]));
                        }}
                      >
                        {d}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
      {open ? (
        <div className="space-y-3">
          <div className="flex gap-2 text-sm">
            <input
              className="flex-1 rounded-xl bg-black/30 border border-white/10 p-2"
              placeholder="Manual takeover: photo id the model missed"
              value={manual}
              onChange={(e) => setManual(e.target.value.trim())}
            />
            <button
              className="btn-ghost"
              disabled={!manual}
              onClick={() => {
                const r = take();
                if (r) run(() => manualMatch(c.id, manual, r));
              }}
            >
              Add match
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            {(
              [
                ["completed", "Complete & release approved"],
                ["no_match", "No match"],
                ["escalated", "Escalate"],
                ["stopped", "Stop - release nothing"],
              ] as const
            ).map(([o, label]) => (
              <button
                key={o}
                className={o === "completed" ? "btn" : "btn-ghost"}
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
        <button
          className="btn-ghost"
          onClick={() => {
            const r = take();
            if (r) run(() => reopenCase(c.id, r));
          }}
        >
          Reopen case
        </button>
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
    <section className="glass rounded-2xl p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-medium">Search result review</h2>
        <select
          className="rounded-xl bg-black/30 border border-white/10 p-1 text-sm"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
        >
          {["pending_review", "escalated", "completed", "no_match", "stopped", ""].map((s) => (
            <option key={s} value={s}>{s || "all"}</option>
          ))}
        </select>
      </div>
      <p className="text-xs text-slate-400">
        Similarity scores are not identity decisions. Compare each candidate with the reference
        photo; approve only when you are confident it is the same person. Nothing is released to
        the requester until you complete the case.
      </p>
      {err && <div className="text-sm text-red-300">{err}</div>}
      <div className="flex flex-wrap gap-2">
        {items?.map((c) => (
          <button
            key={c.id}
            className={`btn-ghost text-xs ${selected === c.id ? "border-accent" : ""}`}
            onClick={() => setSelected(c.id)}
          >
            {c.id.slice(0, 8)} · {c.requested_by} · {c.undecided ?? 0} undecided
          </button>
        ))}
        {items?.length === 0 && <div className="text-sm text-slate-500">No cases.</div>}
      </div>
      {selected && <CaseDetail key={selected} id={selected} onChange={load} take={take} />}
    </section>
  );
}

type Outcome = "upheld" | "partially_upheld" | "rejected";
type Action = "none" | "delete_photo" | "restore_photo";

function AppealResolver({ a, onResolve }: { a: Appeal; onResolve: (a: Appeal, o: Outcome, x: Action) => void }) {
  const [outcome, setOutcome] = useState<Outcome>("upheld");
  const [action, setAction] = useState<Action>(a.category === "deletion_request" ? "delete_photo" : "none");
  const sel = "rounded-lg bg-black/30 border border-white/10 p-1 text-xs";
  return (
    <div className="flex flex-wrap items-center gap-2">
      <select className={sel} value={outcome} onChange={(e) => setOutcome(e.target.value as Outcome)}>
        <option value="upheld">upheld</option>
        <option value="partially_upheld">partially upheld</option>
        <option value="rejected">rejected</option>
      </select>
      <select className={sel} value={action} onChange={(e) => setAction(e.target.value as Action)}>
        <option value="none">no data action</option>
        <option value="delete_photo">delete photo (admin)</option>
        <option value="restore_photo">restore photo to search</option>
      </select>
      <button className="btn-ghost" onClick={() => onResolve(a, outcome, action)}>
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
    <section className="glass rounded-2xl p-6 space-y-3">
      <h2 className="text-lg font-medium">Appeals</h2>
      {err && <div className="text-sm text-red-300">{err}</div>}
      {items?.length === 0 && <div className="text-sm text-slate-500">No appeals.</div>}
      <div className="space-y-2">
        {items?.map((a) => (
          <div key={a.id} className="rounded-lg border border-white/10 p-3 text-sm space-y-1">
            <div className="flex flex-wrap gap-2 text-xs">
              <span className="chip">{a.category}</span>
              <span className="chip">{a.status}</span>
              {a.overdue && <span className="chip text-red-300">overdue</span>}
              <span className="chip">due {fmtDate(a.resolve_by)}</span>
              {a.photo_id && <span className="chip">photo {a.photo_id.slice(0, 8)}</span>}
            </div>
            <div className="text-slate-300">{a.reason}</div>
            {a.contact && <div className="text-xs text-slate-500">contact: {a.contact}</div>}
            {a.status !== "resolved" ? (
              <div className="flex gap-2">
                {a.status === "received" && (
                  <button className="btn-ghost" onClick={() => acknowledgeAppeal(a.id).then(load)}>Acknowledge</button>
                )}
                <AppealResolver a={a} onResolve={resolve} />
              </div>
            ) : (
              <div className="text-xs text-slate-400">{a.outcome}: {a.resolution}</div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

export default function ReviewPage() {
  const { ready, can } = useSession();
  const note = useDecisionNote();
  if (ready && !can("review:decide") && !can("appeals:manage"))
    return (
      <div className="glass rounded-2xl p-8 text-sm text-slate-400">
        This console is for assigned Human Reviewers. <Link href="/signin" className="underline">Sign in</Link> with a reviewer key.
      </div>
    );
  if (!ready) return null;
  return (
    <div className="space-y-6">
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
