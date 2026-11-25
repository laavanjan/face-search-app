"use client";

import { useState } from "react";
import Link from "next/link";
import ConsentCheck from "@/components/ConsentCheck";
import Dropzone, { MAX_BATCH } from "@/components/Dropzone";
import StatusBar from "@/components/StatusBar";
import { Alert, Icon, PageHeader, Spinner, StatusBadge } from "@/components/ui";
import { uploadPhoto, type UploadResponse } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { useSession } from "@/lib/session";

type BatchItem = {
  name: string;
  state: "waiting" | "uploading" | "done" | "error";
  result?: UploadResponse;
  error?: string;
};

export default function IndexPage() {
  const { ready, can } = useSession();
  const { t } = useT();
  const [busy, setBusy] = useState(false);
  const [consent, setConsent] = useState(false);
  // Neither answer is pre-selected: the uploader must choose (ACC-07).
  const [minors, setMinors] = useState<"" | "no" | "yes">("");
  const [guardian, setGuardian] = useState(false);
  const [items, setItems] = useState<BatchItem[]>([]);

  const minorsDone = minors === "no" || (minors === "yes" && guardian);
  const ready2 = consent && minorsDone;
  const doneCount = items.filter((i) => i.state === "done" || i.state === "error").length;

  // Photos go up one at a time, with the same consent and under-18 answers for the whole batch.
  async function handleMany(files: File[]) {
    setBusy(true);
    setItems(files.map((f) => ({ name: f.name, state: "waiting" as const })));
    const patch = (i: number, p: Partial<BatchItem>) =>
      setItems((cur) => cur.map((it, j) => (j === i ? { ...it, ...p } : it)));
    for (let i = 0; i < files.length; i++) {
      patch(i, { state: "uploading" });
      try {
        const r = await uploadPhoto(files[i], consent, { present: minors === "yes", guardianConsent: guardian });
        patch(i, { state: "done", result: r });
      } catch (e: any) {
        patch(i, { state: "error", error: e.message ?? "upload failed" });
      }
    }
    setBusy(false);
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
                  <Dropzone
                    onFiles={handleMany}
                    disabled={busy || !ready2}
                    locked={!ready2}
                    hint={`JPG, PNG or WebP, up to 15 MB each. Choose up to ${MAX_BATCH} photos at once.`}
                  />
                  <p className="mt-2 text-xs text-subtle">Your answers in steps 1 and 2 apply to every photo in the batch.</p>
                </div>
              </li>
            </ol>
          )}
          {busy && (
            <div role="status" className="mt-5 flex items-center gap-2 text-sm text-muted">
              <Spinner /> {t("index.busy")} ({doneCount} of {items.length} done)
            </div>
          )}
          {items.length > 0 && (
            <ul className="mt-5 space-y-3" aria-label="Upload results">
              {items.map((it, i) => (
                <li key={`${it.name}-${i}`} className="rounded-xl border border-line p-3 text-sm">
                  <div className="flex items-center justify-between gap-3">
                    <span className="min-w-0 truncate font-medium text-fg">{it.name}</span>
                    <span className="shrink-0 text-xs text-subtle">
                      {it.state === "waiting" && "Waiting"}
                      {it.state === "uploading" && "Uploading…"}
                    </span>
                  </div>
                  {it.state === "error" && <Alert tone="danger" className="mt-2">{it.error}</Alert>}
                  {it.state === "done" && it.result && (
                    <div role="status" className="mt-2">
                      <Alert tone="success" title={it.result.message}>
                        <div className="mt-1 flex flex-wrap items-center gap-2">
                          <StatusBadge status={it.result.review_status} label={`Review · ${it.result.review_status}`} />
                          {it.result.faces.map((f) => (
                            <span key={f.face_id} className="chip font-mono">
                              det {f.det_score.toFixed(2)} · q {f.quality.toFixed(2)}
                            </span>
                          ))}
                        </div>
                      </Alert>
                    </div>
                  )}
                </li>
              ))}
            </ul>
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
