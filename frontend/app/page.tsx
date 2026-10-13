"use client";

import { useState } from "react";
import Link from "next/link";
import ConsentCheck from "@/components/ConsentCheck";
import Dropzone from "@/components/Dropzone";
import StatusBar from "@/components/StatusBar";
import { uploadPhoto, type UploadResponse } from "@/lib/api";
import { useSession } from "@/lib/session";

export default function IndexPage() {
  const { ready, can } = useSession();
  const [busy, setBusy] = useState(false);
  const [consent, setConsent] = useState(false);
  const [result, setResult] = useState<UploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handle(f: File) {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const r = await uploadPhoto(f, consent);
      setResult(r);
    } catch (e: any) {
      setError(e.message ?? "upload failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <section className="glass rounded-2xl p-8">
        <h1 className="text-3xl font-semibold tracking-tight mb-2">
          Index a photo
        </h1>
        <p className="text-slate-400 text-sm mb-4 max-w-2xl">
          Detect faces with InsightFace (and Rekognition, when AWS is
          configured), embed each face as a 512-dim vector, and store it in
          Qdrant. Image metadata (EXIF, GPS) and the filename are discarded.
          A reviewer must approve each photo before it becomes searchable.
        </p>
        <p className="text-slate-500 text-xs mb-6 max-w-2xl">
          For authorised, consented collections only - not for surveillance or identifying
          strangers. See <Link href="/privacy" className="underline">permitted and prohibited use</Link>.
        </p>
        {ready && !can("photos:write") ? (
          <div className="text-sm text-slate-400">
            <Link href="/signin" className="underline">Sign in</Link> with an operator key to index photos.
          </div>
        ) : (
          <>
            <ConsentCheck purpose="index" checked={consent} onChange={setConsent} />
            <Dropzone onFile={handle} disabled={busy || !consent} label="Drop a photo to index" />
          </>
        )}
        {busy && (
          <div className="mt-4 text-sm text-slate-400 animate-pulse">
            Detecting faces · generating embeddings · upserting vectors…
          </div>
        )}
        {error && <div className="mt-4 text-sm text-red-300">{error}</div>}
        {result && (
          <div className="mt-6 space-y-3">
            <div className="text-sm text-slate-300">{result.message}</div>
            <div className="flex flex-wrap gap-2">
              <span className="chip">review · {result.review_status}</span>
              {result.faces.map((f) => (
                <span key={f.face_id} className="chip">
                  face · det {f.det_score.toFixed(2)} · q {f.quality.toFixed(2)}
                </span>
              ))}
            </div>
          </div>
        )}
      </section>
      <StatusBar />
    </div>
  );
}
