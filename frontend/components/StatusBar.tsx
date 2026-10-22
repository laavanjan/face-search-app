"use client";

import { useEffect, useState } from "react";
import { Alert } from "@/components/ui";
import { getHealth, type Health } from "@/lib/api";

export default function StatusBar() {
  const [h, setH] = useState<Health | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    const tick = async () => {
      try {
        const data = await getHealth();
        if (alive) {
          setH(data);
          setErr(null);
        }
      } catch (e: any) {
        if (alive) setErr(e.message ?? "offline");
      }
    };
    tick();
    const id = setInterval(tick, 5000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  if (err) {
    return (
      <Alert tone="danger" title="Backend unreachable">
        Start it with <code className="rounded bg-sunken px-1 font-mono text-xs text-fg">uvicorn app.main:app --reload</code>
      </Alert>
    );
  }

  const warnings = h
    ? [
        h.indexing_paused && "Indexing paused",
        h.search_paused && "Search paused",
        !h.config_approved && "Config change awaiting approval",
      ].filter(Boolean)
    : [];
  const rows: [string, string | number][] = h
    ? [
        ["Detector", h.detector],
        ["Model", h.model],
        ["Storage", h.storage],
        ["Vectors", h.vector_store],
        ...(h.indexed_faces !== null ? ([["Indexed faces", h.indexed_faces]] as [string, number][]) : []),
      ]
    : [];

  return (
    <section aria-label="System status" className="card p-5">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-fg">System status</h2>
        {h ? (
          <span className={`badge ${warnings.length ? "badge-warning" : "badge-success"}`}>
            <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-current" />
            {warnings.length ? "Attention" : h.status === "ok" ? "Operational" : h.status}
          </span>
        ) : (
          <span className="skeleton h-5 w-20 rounded-full" />
        )}
      </div>
      {h ? (
        <>
          <dl className="space-y-2 text-sm">
            {rows.map(([k, v]) => (
              <div key={k} className="flex items-center justify-between gap-3">
                <dt className="text-muted">{k}</dt>
                <dd className="truncate font-mono text-xs text-fg">{v}</dd>
              </div>
            ))}
          </dl>
          {warnings.length > 0 && (
            <ul className="mt-3 space-y-1 border-t border-line pt-3 text-xs font-medium text-warning">
              {warnings.map((w) => (
                <li key={w as string}>{w}</li>
              ))}
            </ul>
          )}
        </>
      ) : (
        <div className="space-y-2">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="skeleton h-4 rounded" />
          ))}
        </div>
      )}
    </section>
  );
}
