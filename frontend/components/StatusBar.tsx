"use client";

import { useEffect, useState } from "react";
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
      <div className="glass rounded-2xl p-4 text-sm text-red-300">
        Backend unreachable. Start it with{" "}
        <code className="bg-black/30 px-1 rounded">uvicorn app.main:app --reload</code>
      </div>
    );
  }
  if (!h) return <div className="glass rounded-2xl p-4 text-sm text-slate-400">Loading…</div>;

  return (
    <div className="glass rounded-2xl p-4 flex flex-wrap items-center gap-2 text-sm">
      <span className="chip">status · {h.status}</span>
      <span className="chip">detector · {h.detector}</span>
      <span className="chip">model · {h.model}</span>
      <span className="chip">storage · {h.storage}</span>
      <span className="chip">vectors · {h.vector_store}</span>
      {h.indexed_faces !== null && <span className="chip">indexed · {h.indexed_faces} face(s)</span>}
      {h.indexing_paused && <span className="chip text-amber-300">indexing paused</span>}
      {h.search_paused && <span className="chip text-amber-300">search paused</span>}
      {!h.config_approved && <span className="chip text-amber-300">config change awaiting approval</span>}
    </div>
  );
}
