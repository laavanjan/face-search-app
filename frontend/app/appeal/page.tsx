"use client";

import { useEffect, useState } from "react";
import AppealForm from "@/components/AppealForm";
import { Alert, Icon, PageHeader, StatusBadge, humanize } from "@/components/ui";
import { fmtDate, getAppeal, getPolicy, type Appeal, type Policy } from "@/lib/api";

export default function AppealPage() {
  const [policy, setPolicy] = useState<Policy | null>(null);
  const [lookup, setLookup] = useState("");
  const [token, setToken] = useState("");
  const [found, setFound] = useState<Appeal | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    getPolicy().then(setPolicy).catch(() => {});
  }, []);

  const ack = policy?.appeal_sla_days.acknowledge ?? 2;
  const resolve = policy?.appeal_sla_days.resolve ?? 30;

  const steps = [
    <>If you give a photo reference, that photo is <strong>immediately excluded from search</strong> until the appeal is decided.</>,
    <>A Human Reviewer acknowledges your appeal within <strong>{ack} days</strong>.</>,
    <>A decision is made within <strong>{resolve} days</strong>: upheld, partially upheld, or rejected - with the reason.</>,
    <>Upheld deletion requests remove the photo and every face embedding derived from it.</>,
    <>If you disagree with the decision, reply quoting your reference; it is escalated to the Service Owner (see the escalation path in GOVERNANCE.md).</>,
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Challenge a result"
        description={
          <>
            You can appeal whether or not you have an account - including if you appear in someone else&apos;s photo.
          </>
        }
      />
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
        <div className="space-y-6">
          <section className="card p-5 sm:p-6">
            <h2 className="section-title mb-3">You can challenge</h2>
            <ul className="space-y-2 text-sm text-muted">
              {[
                <><strong className="text-fg">An incorrect match</strong> - the system linked a photo to the wrong person</>,
                <>Your face being <strong className="text-fg">indexed</strong> at all</>,
                <>A <strong className="text-fg">deletion</strong> of a photo of you, or <strong className="text-fg">access</strong> to the data held about you</>,
              ].map((item, i) => (
                <li key={i} className="flex gap-2.5">
                  <Icon name="check" className="mt-1 h-3.5 w-3.5 text-accent" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </section>
          <section className="card p-5 sm:p-6">
            <h2 className="section-title mb-4">What happens next</h2>
            <ol className="relative space-y-4 text-sm text-muted">
              {steps.map((s, i) => (
                <li key={i} className="relative flex gap-3">
                  {i < steps.length - 1 && <span aria-hidden className="absolute left-3.5 top-8 h-[calc(100%-1rem)] w-px bg-line" />}
                  <span className="step-num">{i + 1}</span>
                  <span className="pt-1 leading-relaxed [&_strong]:font-semibold [&_strong]:text-fg">{s}</span>
                </li>
              ))}
            </ol>
            <p className="mt-5 border-t border-line pt-4 text-xs text-subtle">
              We store the appeal text and, if you choose to give it, a contact for our reply. Resolved appeals are
              deleted after {policy?.retention_days.resolved_appeals ?? 365} days.
            </p>
          </section>
        </div>

        <div className="space-y-6">
          <section className="card p-5 sm:p-6">
            <h2 className="section-title mb-4">File an appeal</h2>
            <AppealForm />
          </section>

          <section className="card p-5 text-sm sm:p-6">
            <h2 className="section-title mb-4">Check status</h2>
            <form
              className="space-y-3"
              onSubmit={(e) => {
                e.preventDefault();
                setErr(null);
                getAppeal(lookup, token).then(setFound).catch(() => setErr("No appeal found for that reference and token."));
              }}
            >
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label htmlFor="appeal-ref" className="label">Appeal reference</label>
                  <input
                    id="appeal-ref"
                    className="input font-mono"
                    value={lookup}
                    onChange={(e) => setLookup(e.target.value.trim())}
                  />
                </div>
                <div>
                  <label htmlFor="appeal-token" className="label">Access token</label>
                  <input
                    id="appeal-token"
                    className="input font-mono"
                    type="password"
                    value={token}
                    onChange={(e) => setToken(e.target.value.trim())}
                  />
                </div>
              </div>
              <button className="btn-secondary" disabled={!lookup || !token}>
                <Icon name="search" /> Look up
              </button>
            </form>
            {err && <Alert tone="danger" className="mt-4">{err}</Alert>}
            {found && (
              <div role="status" className="mt-4 space-y-2 rounded-xl bg-sunken p-4">
                <div className="flex items-center gap-2">
                  <span className="text-muted">Status</span>
                  <StatusBadge status={found.status} />
                </div>
                <div className="text-muted">Decision due {fmtDate(found.resolve_by)}</div>
                {found.outcome && (
                  <div className="text-fg">
                    <span className="font-medium">{humanize(found.outcome)}</span> - {found.resolution}
                  </div>
                )}
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
