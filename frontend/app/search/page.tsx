"use client";

import { useState } from "react";
import Dropzone from "@/components/Dropzone";
import { searchPhoto, type SearchResponse } from "@/lib/api";

export default function SearchPage() {
  const [busy, setBusy] = useState(false);
  const [res, setRes] = useState<SearchResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [threshold, setThreshold] = useState(0.35);

  async function run(f: File) {
    setBusy(true);
    setErr(null);
    setRes(null);
    try {
      const r = await searchPhoto(f, { limit: 40, threshold });
      setRes(r);
    } catch (e: any) {
      setErr(e.message ?? "search failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <section className="glass rounded-2xl p-8">
        <h1 className="text-3xl font-semibold tracking-tight mb-2">
          Find every photo of this person
        </h1>
        <p className="text-slate-400 text-sm mb-6 max-w-2xl">
          Drop a reference photo. We embed the largest face and run cosine
          similarity against every indexed vector in Qdrant.
        </p>
        <Dropzone onFile={run} disabled={busy} label="Drop a reference photo" />
        <div className="flex items-center gap-3 mt-4 text-sm text-slate-300">
          <label>Threshold</label>
          <input
            type="range"
            min={0}
            max={0.9}
            step={0.01}
            value={threshold}
            onChange={(e) => setThreshold(parseFloat(e.target.value))}
            className="accent-accent"
          />
          <span className="chip">{threshold.toFixed(2)}</span>
          <span className="text-slate-500 text-xs">
            Higher = stricter (fewer, more confident matches)
          </span>
        </div>
        {busy && (
          <div className="mt-4 text-sm text-slate-400 animate-pulse">Searching…</div>
        )}
        {err && <div className="mt-4 text-sm text-red-300">{err}</div>}
      </section>

      {res && (
        <section>
          <div className="flex items-baseline justify-between mb-4">
            <h2 className="text-lg font-medium">
              {res.matches.length} match{res.matches.length === 1 ? "" : "es"}
            </h2>
            <div className="text-xs text-slate-500">
              {res.query_faces} face(s) detected in reference
            </div>
          </div>
          {res.matches.length === 0 ? (
            <div className="glass rounded-2xl p-8 text-center text-slate-400">
              No matches above threshold. Try lowering it, or index more photos first.
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
              {res.matches.map((m) => (
                <a
                  key={m.face_id}
                  href={`/photos/${m.photo_id}`}
                  target="_blank"
                  className="group glass rounded-xl overflow-hidden border border-white/5 hover:border-accent/50 transition"
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={`/photos/${m.photo_id}`}
                    alt={m.photo_id}
                    className="aspect-square object-cover w-full group-hover:scale-[1.02] transition"
                  />
                  <div className="p-2 flex items-center justify-between text-xs">
                    <span className="text-slate-400">
                      {(m.score * 100).toFixed(1)}%
                    </span>
                    <span
                      className="h-1.5 w-16 rounded-full bg-white/10 overflow-hidden"
                      title="similarity"
                    >
                      <span
                        className="block h-full bg-gradient-to-r from-accent to-accent2"
                        style={{ width: `${Math.min(100, m.score * 100)}%` }}
                      />
                    </span>
                  </div>
                </a>
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  );
}
