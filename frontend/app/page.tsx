"use client";

import { useState } from "react";
import Link from "next/link";
import ConsentCheck from "@/components/ConsentCheck";
import Dropzone from "@/components/Dropzone";
import StatusBar from "@/components/StatusBar";
import { Alert, Icon, PageHeader, Spinner, StatusBadge } from "@/components/ui";
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

  const minorsDone = minors === "no" || (minors === "yes" && guardian);
  const ready2 = consent && minorsDone;

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
    <div>
      <PageHeader title={t("index.title")} description={t("index.lead")} />
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_300px]">
        <section className="card p-5 sm:p-6">
          {ready && !can("photos:write") ? (
            <div className="flex flex-col items-center py-10 text-center">
              <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-sunken text-subtle">
                <Icon name="lock" className="h-5 w-5" />
              </div>
              <p className="text-muted">{t("index.signin")}</p>
              <Link href="/signin" className="btn mt-4">{t("nav.signin")}</Link>
            </div>
          ) : (
            <ol className="space-y-6">
              <li className="flex gap-4">
                <span className={`step-num ${consent ? "done" : ""}`}>{consent ? <Icon name="check" className="h-3.5 w-3.5" /> : 1}</span>
                <div className="min-w-0 flex-1">
                  <ConsentCheck purpose="index" checked={consent} onChange={setConsent} />
                </div>
              </li>
              <li className="flex gap-4">
                <span className={`step-num ${minorsDone ? "done" : ""}`}>{minorsDone ? <Icon name="check" className="h-3.5 w-3.5" /> : 2}</span>
                <fieldset className="min-w-0 flex-1 text-sm text-fg">
                  <legend className="mb-2 pt-1 font-medium">{t("minors.question")}</legend>
                  <div className="grid grid-cols-2 gap-3 sm:max-w-xs">
                    {(["no", "yes"] as const).map((v) => (
                      <label key={v} className="choice items-center">
                        <input type="radio" name="minors" checked={minors === v} onChange={() => setMinors(v)} />
                        {t(`minors.${v}`)}
                      </label>
                    ))}
                  </div>
                  {minors === "yes" && (
                    <label className="choice mt-3">
                      <input type="checkbox" className="mt-0.5" checked={guardian} onChange={(e) => setGuardian(e.target.checked)} />
                      <span className="leading-relaxed">{t("minors.guardian")}</span>
                    </label>
                  )}
                </fieldset>
              </li>
              <li className="flex gap-4">
                <span className="step-num">3</span>
                <div className="min-w-0 flex-1">
                  <Dropzone onFile={handle} disabled={busy || !ready2} locked={!ready2} />
                </div>
              </li>
            </ol>
          )}
          {busy && (
            <div role="status" className="mt-5 flex items-center gap-2 text-sm text-muted">
              <Spinner /> {t("index.busy")}
            </div>
          )}
          {error && <Alert tone="danger" className="mt-5">{error}</Alert>}
          {result && (
            <div role="status" className="mt-5">
              <Alert tone="success" title={result.message}>
                <div className="mt-1 flex flex-wrap items-center gap-2">
                  <StatusBadge status={result.review_status} label={`Review · ${result.review_status}`} />
                  {result.faces.map((f) => (
                    <span key={f.face_id} className="chip font-mono">
                      det {f.det_score.toFixed(2)} · q {f.quality.toFixed(2)}
                    </span>
                  ))}
                </div>
              </Alert>
            </div>
          )}
        </section>

        <aside className="space-y-4">
          <div className="card p-5 text-sm">
            <div className="flex gap-3">
              <Icon name="shield" className="mt-0.5 h-4 w-4 text-accent" />
              <p className="leading-relaxed text-muted">
                {t("index.scope")}{" "}
                <Link href="/privacy" className="link">{t("consent.link")}</Link>.
              </p>
            </div>
            <details className="group mt-3 border-t border-line pt-3">
              <summary className="cursor-pointer list-none font-medium text-fg marker:hidden">
                <span className="inline-flex items-center gap-1.5">
                  <Icon name="arrowRight" className="h-3.5 w-3.5 text-subtle transition-transform group-open:rotate-90" />
                  {t("index.tech")}
                </span>
              </summary>
              <p className="mt-2 leading-relaxed text-muted">{t("index.techBody")}</p>
            </details>
          </div>
          <StatusBar />
        </aside>
      </div>
    </div>
  );
}
