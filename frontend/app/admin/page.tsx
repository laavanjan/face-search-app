"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  approveConfig,
  fmtDate,
  getAudit,
  getControls,
  runRetention,
  verifyAudit,
  setControls,
  type Controls,
} from "@/lib/api";
import { useDecisionNote } from "@/components/DecisionNote";
import { Alert, EmptyState, Icon, PageHeader, SectionHeader } from "@/components/ui";
import { useSession } from "@/lib/session";

type AuditRow = Awaited<ReturnType<typeof getAudit>>["items"][number];

export default function AdminPage() {
  const { ready, can } = useSession();
  const [c, setC] = useState<Controls | null>(null);
  const [audit, setAudit] = useState<AuditRow[] | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [changeId, setChangeId] = useState("");
  const note = useDecisionNote();

  const load = useCallback(() => {
    getControls().then(setC).catch((e) => setErr(e.message));
    if (can("audit:read")) getAudit(100).then((r) => setAudit(r.items)).catch(() => {});
  }, [can]);

  useEffect(() => {
    if (ready && can("system:control")) load();
  }, [ready, load, can]);

  async function toggle(kind: "indexing" | "search", paused: boolean) {
    const reason = note.take();
    if (!reason) return;
    try {
      setC(await setControls({ [`${kind}_paused`]: paused, reason }));
    } catch (e: any) {
      setErr(e.message);
    }
  }

  async function approve() {
    const reason = note.take();
    if (!reason || changeId.trim().length < 3) return;
    try {
      await approveConfig(changeId.trim(), reason);
      load();
    } catch (e: any) {
      setErr(e.message);
    }
  }

  if (ready && !can("system:control"))
    return (
      <EmptyState icon="sliders" title="Service Owner console">
        <Link href="/signin" className="link">Sign in</Link> with an admin key.
      </EmptyState>
    );
  if (!c)
    return err ? (
      <Alert tone="danger">{err}</Alert>
    ) : (
      <div className="space-y-4">
        <div className="skeleton h-10 w-48 rounded-lg" />
        <div className="skeleton h-40 rounded-2xl" />
      </div>
    );

  const diff = Object.entries(c.config.pending_diff);
  return (
    <div className="space-y-6">
      <PageHeader
        title="Service controls"
        description="Stop or resume processing, approve configuration changes, run retention and inspect the audit trail."
      />
      {note.field}
      {err && <Alert tone="danger">{err}</Alert>}

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="card p-5 sm:p-6">
          <SectionHeader
            icon="pause"
            title="Stop / resume processing"
            description="Pausing takes effect on the next request: uploads or searches are refused with 503 before any face analysis runs. Use this first in any P0/P1 incident (docs/governance/incident-response.md)."
          />
          <ul className="divide-y divide-line rounded-xl border border-line">
            {(["indexing", "search"] as const).map((k) => {
              const paused = c[`${k}_paused`];
              return (
                <li key={k} className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
                  <div className="flex items-center gap-3">
                    <span
                      aria-hidden
                      className={`h-2.5 w-2.5 rounded-full ${paused ? "bg-warning" : "bg-success"}`}
                    />
                    <div>
                      <div className="text-sm font-medium capitalize text-fg">{k}</div>
                      <div className={`text-xs ${paused ? "text-warning" : "text-success"}`}>{paused ? "Paused" : "Running"}</div>
                    </div>
                  </div>
                  <button className={paused ? "btn" : "btn-danger"} onClick={() => toggle(k, !paused)}>
                    <Icon name={paused ? "play" : "pause"} className="h-3.5 w-3.5" />
                    {paused ? `Resume ${k}` : `Pause ${k}`}
                  </button>
                </li>
              );
            })}
          </ul>
        </section>

        <section className="card p-5 text-sm sm:p-6">
          <SectionHeader icon="shield" title="Configuration approval" />
          <dl className="mb-4 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-xs">
            <dt className="text-subtle">Last approved change</dt>
            <dd className="font-mono text-fg">{c.config.last_approved_change_id ?? "—"}</dd>
            <dt className="text-subtle">Fingerprint</dt>
            <dd className="font-mono text-fg">{c.config.fingerprint.slice(0, 12)}</dd>
          </dl>
          {c.config.approved ? (
            <Alert tone="success" role="status" title="Running configuration is approved." />
          ) : (
            <div className="space-y-3">
              <Alert tone="warning" title="Governance-sensitive settings changed">
                Indexing and search are paused until this change is approved.
              </Alert>
              <ul className="space-y-1 rounded-xl bg-sunken p-3 font-mono text-xs text-muted">
                {diff.map(([k, v]) => (
                  <li key={k}>
                    <span className="text-fg">{k}</span>: {String(v.approved)} → <span className="text-warning">{String(v.running)}</span>
                  </li>
                ))}
              </ul>
              <div className="flex flex-col gap-2 sm:flex-row">
                <label htmlFor="change-id" className="sr-only">Change record id</label>
                <input
                  id="change-id"
                  className="input font-mono"
                  placeholder="Change record id, e.g. CHG-0002"
                  value={changeId}
                  onChange={(e) => setChangeId(e.target.value)}
                />
                <button className="btn" onClick={approve} disabled={changeId.trim().length < 3}>
                  Approve change
                </button>
              </div>
            </div>
          )}
        </section>
      </div>

      <section className="card p-5 text-sm sm:p-6">
        <SectionHeader
          icon="clock"
          title="Retention"
          description="Deletes photos, embeddings, review cases, resolved appeals and audit rows that are past their retention period. It also runs automatically on a schedule."
          actions={
            <button
              className="btn-secondary"
              onClick={() => runRetention().then((r) => setMsg(JSON.stringify(r))).catch((e) => setErr(e.message))}
            >
              <Icon name="trash" /> Run retention sweep now
            </button>
          }
        />
        {msg && (
          <code role="status" className="block overflow-x-auto rounded-xl bg-sunken px-3 py-2 font-mono text-xs text-muted">
            {msg}
          </code>
        )}
      </section>

      {audit && (
        <section className="card p-5 sm:p-6">
          <SectionHeader
            icon="file"
            title="Audit log"
            description="Latest 100 entries. Each row is hash-chained to the one before it."
            actions={
              <button
                className="btn-secondary"
                onClick={() =>
                  verifyAudit()
                    .then((v) => setMsg(v.ok ? `Audit chain intact (${v.rows} rows)` : `INTEGRITY FAILURE at row ${v.first_bad_id} - treat as P0`))
                    .catch((e) => setErr(e.message))
                }
              >
                <Icon name="shield" /> Verify integrity
              </button>
            }
          />
          <div className="max-h-[28rem] overflow-auto rounded-xl border border-line">
            <table className="table text-xs">
              <thead className="sticky top-0 bg-surface">
                <tr>
                  <th scope="col">Time</th>
                  <th scope="col">Actor</th>
                  <th scope="col">Action</th>
                  <th scope="col">Target</th>
                  <th scope="col">Detail</th>
                </tr>
              </thead>
              <tbody>
                {audit.map((a) => (
                  <tr key={a.id} className="hover:bg-sunken/60">
                    <td className="whitespace-nowrap text-subtle">{fmtDate(a.ts)}</td>
                    <td className="font-mono text-fg">{a.actor}</td>
                    <td><span className="chip font-mono">{a.action}</span></td>
                    <td className="font-mono text-subtle">{a.target?.slice(0, 12)}</td>
                    <td className="max-w-md truncate font-mono text-subtle" title={JSON.stringify(a.detail)}>
                      {JSON.stringify(a.detail)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
