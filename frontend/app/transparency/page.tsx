"use client";

import { useEffect, useState } from "react";
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
    <section className="glass rounded-2xl p-6 sm:p-8 space-y-4 max-w-3xl text-slate-200">
      <h1 className="text-3xl font-semibold tracking-tight">{t("footer.transparency")}</h1>
      <p>What this system did in the last 90 days, published for anyone to check. Small numbers are hidden to protect people.</p>
      {err && <div role="alert" className="text-red-300">{err}</div>}
      {r && (
        <>
          <table className="w-full text-sm">
            <caption className="sr-only">Activity in the last {r.period_days} days</caption>
            <tbody>
              {rows.map(([k, label]) => (
                <tr key={k} className="border-b border-white/10">
                  <th scope="row" className="text-left font-normal py-2">{label}</th>
                  <td className="text-right">{String(r[k])}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <h2 className="text-lg font-medium text-slate-100">Appeals, misuse reports and help requests</h2>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-300">
                <th scope="col" className="py-2">Type</th>
                <th scope="col">Received</th>
                <th scope="col">Resolved</th>
                <th scope="col">Upheld</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(r.appeals_and_reports ?? {}).map(([k, v]: [string, any]) => (
                <tr key={k} className="border-b border-white/10">
                  <th scope="row" className="text-left font-normal py-2">{k.replace(/_/g, " ")}</th>
                  <td>{String(v.received)}</td>
                  <td>{String(v.resolved)}</td>
                  <td>{String(v.upheld)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="text-sm text-slate-300">
            Median days to resolve: {r.median_days_to_resolve ?? "not enough cases yet"}. {r.how_to_report_harm}.
          </p>
        </>
      )}
    </section>
  );
}
