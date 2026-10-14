"use client";

import { useState } from "react";
import Link from "next/link";
import ConsentCheck from "@/components/ConsentCheck";
import Dropzone from "@/components/Dropzone";
import StatusBar from "@/components/StatusBar";
import { uploadPhoto, type UploadResponse } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { useSession } from "@/lib/session";

export default function IndexPage() {
  const { ready, can } = useSession();
  const { t } = useT();
  const [busy, setBusy] = useState(false);
  const [consent, setConsent] = useState(false);
  // Neither answer is pre-selected: the uploader must choose (ACC-07).
  const [minors, setMinors] = useState<"" | "no" | "yes">("");
  const [guardian, setGuardian] = useState(false);
  const [result, setResult] = useState<UploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const ready2 = consent && (minors === "no" || (minors === "yes" && guardian));

  async function handle(f: File) {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const r = await uploadPhoto(f, consent, { present: minors === "yes", guardianConsent: guardian });
      setResult(r);
    } catch (e: any) {
      setError(e.message ?? "upload failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <section className="glass rounded-2xl p-6 sm:p-8">
        <h1 className="text-3xl font-semibold tracking-tight mb-2">{t("index.title")}</h1>
        <p className="text-slate-200 mb-3 max-w-2xl">{t("index.lead")}</p>
        <details className="text-sm text-slate-300 mb-3 max-w-2xl">
          <summary className="cursor-pointer underline">{t("index.tech")}</summary>
          <p className="mt-1">{t("index.techBody")}</p>
        </details>
        <p className="text-slate-300 text-sm mb-6 max-w-2xl">
          {t("index.scope")} <Link href="/privacy" className="underline">{t("consent.link")}</Link>.
        </p>
        {ready && !can("photos:write") ? (
          <div className="text-slate-300">
            <Link href="/signin" className="underline">{t("nav.signin")}</Link> · {t("index.signin")}
          </div>
        ) : (
          <>
            <ConsentCheck purpose="index" checked={consent} onChange={setConsent} />
            <fieldset className="mb-4 max-w-2xl text-sm text-slate-200">
              <legend className="mb-2">{t("minors.question")}</legend>
              <div className="flex gap-6">
                {(["no", "yes"] as const).map((v) => (
                  <label key={v} className="flex items-center gap-2">
                    <input type="radio" name="minors" className="h-5 w-5" checked={minors === v} onChange={() => setMinors(v)} />
                    {t(`minors.${v}`)}
                  </label>
                ))}
              </div>
              {minors === "yes" && (
                <label className="flex items-start gap-3 mt-3">
                  <input type="checkbox" className="mt-1 h-5 w-5" checked={guardian} onChange={(e) => setGuardian(e.target.checked)} />
                  <span>{t("minors.guardian")}</span>
                </label>
              )}
            </fieldset>
            <Dropzone onFile={handle} disabled={busy || !ready2} />
          </>
        )}
        {busy && (
          <div role="status" className="mt-4 text-sm text-slate-300 animate-pulse">{t("index.busy")}</div>
        )}
        {error && <div role="alert" className="mt-4 text-sm text-red-300">{error}</div>}
        {result && (
          <div role="status" className="mt-6 space-y-3">
            <div className="text-sm text-slate-200">{result.message}</div>
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
