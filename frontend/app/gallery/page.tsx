"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import AuthImage from "@/components/AuthImage";
import { deletePhoto, fmtDate, getGallery, type GalleryItem } from "@/lib/api";
import { useDecisionNote } from "@/components/DecisionNote";
import { useSession } from "@/lib/session";

export default function GalleryPage() {
  const { ready, me, can } = useSession();
  const [items, setItems] = useState<GalleryItem[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const note = useDecisionNote();

  function load() {
    getGallery()
      .then((g) => setItems(g.items))
      .catch((e) => setErr(e.message ?? "failed"));
  }

  useEffect(() => {
    if (me) load();
  }, [me]);

  async function remove(photo_id: string) {
    const reason = note.take();
    if (!reason) return;
    try {
      await deletePhoto(photo_id, reason);
      load();
    } catch (e: any) {
      setErr(e.message ?? "delete failed");
    }
  }

  return (
    <div className="space-y-6">
      <section className="glass rounded-2xl p-8">
        <h1 className="text-3xl font-semibold tracking-tight mb-2">Indexed photos</h1>
        <p className="text-slate-400 text-sm">
          Everything that has been uploaded and vectorized, with its review status and the date it
          is automatically deleted.
        </p>
      </section>
      {ready && !me && (
        <div className="glass rounded-2xl p-8 text-center text-slate-400">
          <Link href="/signin" className="underline">Sign in</Link> to view the library.
        </div>
      )}
      {can("photos:delete") && note.field}
      {err && <div className="text-red-300 text-sm">{err}</div>}
      {items && items.length === 0 && (
        <div className="glass rounded-2xl p-8 text-center text-slate-400">
          Nothing indexed yet. Head to <span className="text-slate-200">Index</span>.
        </div>
      )}
      {items && items.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {items.map((it) => (
            <div
              key={it.photo_id}
              className="glass rounded-xl overflow-hidden border border-white/5"
            >
              <AuthImage photoId={it.photo_id} alt="indexed photo" className="aspect-square object-cover w-full" />
              <div className="p-2 text-xs text-slate-400 space-y-1">
                <div className="flex flex-wrap gap-1">
                  <span className="chip">{it.review_status}</span>
                  <span className="chip">{it.face_count} face(s)</span>
                </div>
                <div className="truncate" title={it.photo_id}>{it.photo_id}</div>
                <div>Deletes {fmtDate(it.expires_at)}</div>
                {can("photos:delete") && (
                  <button className="underline text-red-300" onClick={() => remove(it.photo_id)}>
                    Delete now
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
