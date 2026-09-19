"use client";

import { useEffect, useState } from "react";
import { getGallery } from "@/lib/api";

type Item = { photo_id: string; url: string; filename?: string; quality?: number };

export default function GalleryPage() {
  const [items, setItems] = useState<Item[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    getGallery()
      .then((g) => setItems(g.items))
      .catch((e) => setErr(e.message ?? "failed"));
  }, []);

  return (
    <div className="space-y-6">
      <section className="glass rounded-2xl p-8">
        <h1 className="text-3xl font-semibold tracking-tight mb-2">Indexed photos</h1>
        <p className="text-slate-400 text-sm">
          Everything that has been uploaded and vectorized.
        </p>
      </section>
      {err && <div className="text-red-300 text-sm">{err}</div>}
      {items && items.length === 0 && (
        <div className="glass rounded-2xl p-8 text-center text-slate-400">
          Nothing indexed yet. Head to <span className="text-slate-200">Index</span>.
        </div>
      )}
      {items && items.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {items.map((it) => (
            <a
              key={it.photo_id}
              href={`/photos/${it.photo_id}`}
              target="_blank"
              className="glass rounded-xl overflow-hidden border border-white/5 hover:border-accent/50 transition"
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={`/photos/${it.photo_id}`}
                alt={it.photo_id}
                className="aspect-square object-cover w-full"
              />
              <div className="p-2 text-xs text-slate-400 truncate">
                {it.filename ?? it.photo_id}
              </div>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
