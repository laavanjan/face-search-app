"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  approveConfig,
  fmtDate,
  getAudit,
  getControls,
  runRetention,
  setControls,
  type Controls,
} from "@/lib/api";
import { useDecisionNote } from "@/components/DecisionNote";
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
      <div className="glass rounded-2xl p-8 text-sm text-slate-400">
        Service Owner console. <Link href="/signin" className="underline">Sign in</Link> with an admin key.
      </div>
    );
  if (!c) return <div className="text-sm text-slate-500">{err ?? "Loading…"}</div>;

  const diff = Object.entries(c.config.pending_diff);
  return (
    <div className="space-y-6">
      {note.field}
      {err && <div className="text-sm text-red-300">{err}</div>}
      <section className="glass rounded-2xl p-6 space-y-3">
        <h2 className="text-lg font-medium">Stop / resume processing</h2>
        <p className="text-xs text-slate-400">
          Pausing takes effect on the next request: uploads or searches are refused with 503 before
          any face analysis runs. Use this first in any P0/P1 incident (docs/governance/incident-response.md).
        </p>
        <div className="flex flex-wrap gap-3">
          {(["indexing", "search"] as const).map((k) => {
            const paused = c[`${k}_paused`];
            return (
              <button key={k} className={paused ? "btn" : "btn-ghost text-red-300"} onClick={() => toggle(k, !paused)}>
                {paused ? `Resume ${k}` : `Pause ${k}`}
              </button>
            );
          })}
        </div>
      </section>

      <section className="glass rounded-2xl p-6 space-y-3 text-sm">
        <h2 className="text-lg font-medium">Configuration approval</h2>
        <div className="text-xs text-slate-400">
          Last approved change: {c.config.last_approved_change_id ?? "—"} · fingerprint {c.config.fingerprint.slice(0, 12)}
        </div>
        {c.config.approved ? (
          <div className="text-emerald-300">Running configuration is approved.</div>
        ) : (
          <>
            <div className="text-amber-300">
              Governance-sensitive settings changed. Indexing and search are paused until this change is approved.
            </div>
            <ul className="text-xs text-slate-300 list-disc pl-6">
              {diff.map(([k, v]) => (
                <li key={k}>
                  {k}: {String(v.approved)} → {String(v.running)}
                </li>
              ))}
            </ul>
            <div className="flex gap-2">
              <input
                className="rounded-lg bg-black/30 border border-white/10 p-2"
                placeholder="Change record id, e.g. CHG-0002"
                value={changeId}
                onChange={(e) => setChangeId(e.target.value)}
              />
              <button className="btn" onClick={approve} disabled={changeId.trim().length < 3}>
                Approve change
              </button>
            </div>
          </>
        )}
      </section>

      <section className="glass rounded-2xl p-6 space-y-3 text-sm">
        <h2 className="text-lg font-medium">Retention</h2>
        <button
          className="btn-ghost"
          onClick={() => runRetention().then((r) => setMsg(JSON.stringify(r))).catch((e) => setErr(e.message))}
        >
          Run retention sweep now
        </button>
        {msg && <code className="block text-xs text-slate-400">{msg}</code>}
      </section>

      {audit && (
        <section className="glass rounded-2xl p-6 space-y-2 text-xs">
          <h2 className="text-lg font-medium">Audit log (latest 100)</h2>
          <div className="max-h-96 overflow-auto">
            <table className="w-full">
              <tbody>
                {audit.map((a) => (
                  <tr key={a.id} className="border-b border-white/5">
                    <td className="py-1 pr-2 text-slate-500 whitespace-nowrap">{fmtDate(a.ts)}</td>
                    <td className="pr-2">{a.actor}</td>
                    <td className="pr-2 text-slate-300">{a.action}</td>
                    <td className="pr-2 text-slate-500">{a.target?.slice(0, 12)}</td>
                    <td className="text-slate-500">{JSON.stringify(a.detail)}</td>
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
