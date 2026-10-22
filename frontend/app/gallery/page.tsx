"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import AuthImage from "@/components/AuthImage";
import { deletePhoto, fmtDate, fmtDay, getGallery, type GalleryItem } from "@/lib/api";
import { useDecisionNote } from "@/components/DecisionNote";
import { Alert, EmptyState, Icon, PageHeader, StatusBadge } from "@/components/ui";
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

  const pending = items?.filter((i) => i.review_status === "pending").length ?? 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Indexed photos"
        description="Everything that has been uploaded and vectorized, with its review status and the date it is automatically deleted."
        actions={
          items && (
            <>
              <span className="badge badge-neutral">{items.length} photo(s)</span>
              {pending > 0 && <StatusBadge status="pending" label={`${pending} pending review`} />}
            </>
          )
        }
      />
      {ready && !me && (
        <EmptyState icon="lock" title="Sign in to view the library">
          <Link href="/signin" className="link">Sign in</Link> with an access key that can read photos.
        </EmptyState>
      )}
      {can("photos:delete") && note.field}
      {err && <Alert tone="danger">{err}</Alert>}
      {me && !items && !err && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
          {Array.from({ length: 10 }, (_, i) => (
            <div key={i} className="card overflow-hidden">
              <div className="skeleton aspect-square" />
              <div className="space-y-2 p-3">
                <div className="skeleton h-3 w-2/3 rounded" />
                <div className="skeleton h-3 w-1/2 rounded" />
              </div>
            </div>
          ))}
        </div>
      )}
      {items && items.length === 0 && (
        <EmptyState icon="image" title="Nothing indexed yet">
          Photos appear here after they are added on the <Link href="/" className="link">Add photos</Link> page.
        </EmptyState>
      )}
      {items && items.length > 0 && (
        <ul className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
          {items.map((it) => (
            <li key={it.photo_id} className="card group overflow-hidden">
              <div className="relative">
                <AuthImage photoId={it.photo_id} alt="indexed photo" className="aspect-square w-full object-cover" />
                <div className="absolute left-2 top-2 rounded-full bg-surface/90 shadow-sm backdrop-blur">
                  <StatusBadge status={it.review_status} />
                </div>
              </div>
              <div className="space-y-1.5 p-3 text-xs text-muted">
                <div className="flex items-center justify-between gap-2">
                  <span className="inline-flex items-center gap-1">
                    <Icon name="scan" className="h-3.5 w-3.5 text-subtle" />
                    {it.face_count} face(s)
                  </span>
                  <span className="inline-flex items-center gap-1" title={`Deleted automatically ${fmtDate(it.expires_at)}`}>
                    <Icon name="clock" className="h-3.5 w-3.5 text-subtle" />
                    {fmtDay(it.expires_at)}
                  </span>
                </div>
                <div className="truncate font-mono text-[11px] text-subtle" title={it.photo_id}>
                  {it.photo_id}
                </div>
                {can("photos:delete") && (
                  <button className="btn-danger btn-sm mt-1 w-full" onClick={() => remove(it.photo_id)}>
                    <Icon name="trash" className="h-3.5 w-3.5" /> Delete now
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
