"use client";

import { useId, useState } from "react";
import { Alert, Spinner } from "@/components/ui";
import { fmtDate, submitAppeal, type Appeal, type AppealCategory } from "@/lib/api";

const CATEGORIES: { value: AppealCategory; label: string }[] = [
  { value: "incorrect_match", label: "Incorrect match - this is not the same person" },
  { value: "indexing_objection", label: "I object to my face being indexed" },
  { value: "deletion_request", label: "Delete a photo of me" },
  { value: "access_request", label: "Tell me what data you hold about me" },
  { value: "abuse_report", label: "Report misuse (e.g. someone searched for me without consent)" },
  { value: "other", label: "Something else" },
];

type Props = {
  photoId?: string;
  faceId?: string;
  caseId?: string;
  defaultCategory?: AppealCategory;
  compact?: boolean;
};

export default function AppealForm({ photoId, faceId, caseId, defaultCategory, compact }: Props) {
  const uid = useId();
  const [category, setCategory] = useState<AppealCategory>(defaultCategory ?? "incorrect_match");
  const [reason, setReason] = useState("");
  const [contact, setContact] = useState("");
  const [pid, setPid] = useState(photoId ?? "");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [done, setDone] = useState<Appeal | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      setDone(
        await submitAppeal({
          category,
          reason,
          photo_id: pid || undefined,
          face_id: faceId,
          case_id: caseId,
          contact: contact || undefined,
        })
      );
    } catch (e: any) {
      setErr(e.message ?? "failed");
    } finally {
      setBusy(false);
    }
  }

  if (done)
    return (
      <Alert tone="success" role="status" title="Appeal received">
        <div className="space-y-2">
          <div>
            Keep both values below - the access token is shown only once and is needed to check the status.
          </div>
          <dl className="grid gap-1 text-xs sm:grid-cols-[auto_1fr] sm:gap-x-3">
            <dt className="text-subtle">Reference</dt>
            <dd><code className="break-all font-mono text-fg">{done.id}</code></dd>
            <dt className="text-subtle">Access token</dt>
            <dd><code className="break-all font-mono text-fg">{done.access_token}</code></dd>
          </dl>
          <div className="text-xs">
            Acknowledged by {fmtDate(done.ack_by)} · decision by {fmtDate(done.resolve_by)}
            {done.photo_restricted && " · the photo is excluded from search until this is resolved"}
          </div>
        </div>
      </Alert>
    );

  return (
    <form onSubmit={submit} className={compact ? "space-y-3 text-sm" : "space-y-4 text-sm"}>
      <div>
        <label htmlFor={`${uid}-cat`} className="label">What is this about?</label>
        <select
          id={`${uid}-cat`}
          className="select"
          value={category}
          onChange={(e) => setCategory(e.target.value as AppealCategory)}
        >
          {CATEGORIES.map((c) => (
            <option key={c.value} value={c.value}>{c.label}</option>
          ))}
        </select>
      </div>
      {!compact && (
        <div>
          <label htmlFor={`${uid}-pid`} className="label">
            Photo reference <span className="font-normal text-subtle">(optional)</span>
          </label>
          <input
            id={`${uid}-pid`}
            className="input font-mono"
            placeholder="e.g. 3f2a…e1.jpg"
            value={pid}
            onChange={(e) => setPid(e.target.value.trim())}
          />
        </div>
      )}
      <div>
        <label htmlFor={`${uid}-reason`} className="label">What is wrong and what outcome do you want?</label>
        <textarea
          id={`${uid}-reason`}
          required
          minLength={10}
          maxLength={2000}
          rows={compact ? 2 : 4}
          className="textarea"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
        />
        <div className="hint mt-1">At least 10 characters.</div>
      </div>
      <div>
        <label htmlFor={`${uid}-contact`} className="label">
          Email or phone for our reply <span className="font-normal text-subtle">(optional, stored encrypted)</span>
        </label>
        <input
          id={`${uid}-contact`}
          className="input"
          maxLength={200}
          autoComplete="email"
          value={contact}
          onChange={(e) => setContact(e.target.value)}
        />
      </div>
      {err && <Alert tone="danger">{err}</Alert>}
      <button className="btn" disabled={busy || reason.length < 10}>
        {busy && <Spinner />}
        {busy ? "Submitting…" : "Submit appeal"}
      </button>
    </form>
  );
}
