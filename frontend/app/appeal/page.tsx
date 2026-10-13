"use client";

import { useEffect, useState } from "react";
import AppealForm from "@/components/AppealForm";
import { fmtDate, getAppeal, getPolicy, type Appeal, type Policy } from "@/lib/api";

export default function AppealPage() {
  const [policy, setPolicy] = useState<Policy | null>(null);
  const [lookup, setLookup] = useState("");
  const [found, setFound] = useState<Appeal | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    getPolicy().then(setPolicy).catch(() => {});
  }, []);

  const ack = policy?.appeal_sla_days.acknowledge ?? 2;
  const resolve = policy?.appeal_sla_days.resolve ?? 30;

  return (
    <div className="space-y-6">
      <section className="glass rounded-2xl p-8 space-y-4 text-sm text-slate-300">
        <h1 className="text-3xl font-semibold tracking-tight">Challenge a result</h1>
        <p>
          You can appeal whether or not you have an account - including if you appear in someone
          else&apos;s photo. You can challenge:
        </p>
        <ul className="list-disc pl-6 space-y-1 text-slate-400">
          <li>an <strong>incorrect match</strong> - the system linked a photo to the wrong person;</li>
          <li>your face being <strong>indexed</strong> at all;</li>
          <li>a <strong>deletion</strong> of a photo of you, or <strong>access</strong> to the data held about you.</li>
        </ul>
        <h2 className="text-lg font-medium text-slate-200 pt-2">What happens next</h2>
        <ol className="list-decimal pl-6 space-y-1 text-slate-400">
          <li>If you give a photo reference, that photo is <strong>immediately excluded from search</strong> until the appeal is decided.</li>
          <li>A Human Reviewer acknowledges your appeal within <strong>{ack} days</strong>.</li>
          <li>A decision is made within <strong>{resolve} days</strong>: upheld, partially upheld, or rejected - with the reason.</li>
          <li>Upheld deletion requests remove the photo and every face embedding derived from it.</li>
          <li>If you disagree with the decision, reply quoting your reference; it is escalated to the Service Owner (see the escalation path in GOVERNANCE.md).</li>
        </ol>
        <p className="text-slate-500 text-xs">
          We store the appeal text and, if you choose to give it, a contact for our reply. Resolved
          appeals are deleted after {policy?.retention_days.resolved_appeals ?? 365} days.
        </p>
      </section>

      <section className="glass rounded-2xl p-8">
        <h2 className="text-lg font-medium mb-4">File an appeal</h2>
        <AppealForm />
      </section>

      <section className="glass rounded-2xl p-8 space-y-3 text-sm">
        <h2 className="text-lg font-medium">Check status</h2>
        <div className="flex gap-2">
          <input
            className="flex-1 rounded-xl bg-black/30 border border-white/10 p-2"
            placeholder="Appeal reference"
            value={lookup}
            onChange={(e) => setLookup(e.target.value.trim())}
          />
          <button
            className="btn-ghost"
            disabled={!lookup}
            onClick={() => {
              setErr(null);
              getAppeal(lookup).then(setFound).catch((e) => setErr(e.message));
            }}
          >
            Look up
          </button>
        </div>
        {err && <div className="text-red-300">{err}</div>}
        {found && (
          <div className="text-slate-300 space-y-1">
            <div>Status: <span className="chip">{found.status}</span></div>
            <div className="text-slate-400">Decision due {fmtDate(found.resolve_by)}</div>
            {found.outcome && <div>Outcome: {found.outcome} - {found.resolution}</div>}
          </div>
        )}
      </section>
    </div>
  );
}
