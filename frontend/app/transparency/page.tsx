"use client";

import { useEffect, useState } from "react";
import { Alert, PageHeader } from "@/components/ui";
import { getTransparency } from "@/lib/api";
import { useT } from "@/lib/i18n";

/** Public disclosure (SOC-07): aggregate figures from GET /transparency-report.
 * Counts from 1 to 4 are shown as "<5" so nobody can be singled out. */
export default function TransparencyPage() {
  const { t } = useT();
  const [r, setR] = useState<Record<string, any> | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    getTransparency().then(setR).catch((e) => setErr(e.message));
  }, []);

  const rows: [string, string][] = [
    ["searches_requested", "Searches requested"],
    ["matches_approved_by_humans", "Matches confirmed by a person"],
    ["matches_rejected_by_humans", "Suggestions rejected by a person"],
    ["search_cases_stopped_by_reviewer", "Searches stopped by a reviewer"],
    ["photos_rejected_at_index_review", "Photos refused at review"],
    ["photos_deleted", "Photos deleted"],
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("footer.transparency")}
        description="What this system did in the last 90 days, published for anyone to check. Small numbers are hidden to protect people."
      />
      {err && <Alert tone="danger">{err}</Alert>}
      {!r && !err && (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
          {rows.map(([k]) => (
            <div key={k} className="skeleton h-24 rounded-2xl" />
          ))}
        </div>
      )}
      {r && (
        <>
          <section aria-labelledby="activity-title">
            <h2 id="activity-title" className="sr-only">Activity in the last {r.period_days} days</h2>
            <dl className="grid grid-cols-2 gap-4 md:grid-cols-3">
              {rows.map(([k, label]) => (
                <div key={k} className="card p-4 sm:p-5">
                  <dt className="text-sm text-muted">{label}</dt>
                  <dd className="mt-1 text-2xl font-semibold tabular-nums tracking-tight text-fg sm:text-3xl">{String(r[k])}</dd>
                </div>
              ))}
            </dl>
          </section>
          <section className="card p-5 sm:p-6">
            <h2 className="section-title mb-4">Appeals, misuse reports and help requests</h2>
            <div className="overflow-x-auto">
              <table className="table">
                <thead>
                  <tr>
                    <th scope="col">Type</th>
                    <th scope="col" className="text-right">Received</th>
                    <th scope="col" className="text-right">Resolved</th>
                    <th scope="col" className="text-right">Upheld</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(r.appeals_and_reports ?? {}).map(([k, v]: [string, any]) => (
                    <tr key={k}>
                      <th scope="row" className="!text-sm !font-normal !normal-case !tracking-normal text-fg">
                        {k.charAt(0).toUpperCase() + k.slice(1).replace(/_/g, " ")}
                      </th>
                      <td className="text-right tabular-nums">{String(v.received)}</td>
                      <td className="text-right tabular-nums">{String(v.resolved)}</td>
                      <td className="text-right tabular-nums">{String(v.upheld)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-4 border-t border-line pt-4 text-sm text-muted">
              Median days to resolve: <span className="font-medium text-fg">{r.median_days_to_resolve ?? "not enough cases yet"}</span>. {r.how_to_report_harm}.
            </p>
          </section>
        </>
      )}
    </div>
  );
}
