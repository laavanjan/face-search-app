"use client";

import { useId, useState } from "react";
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
      <div className="text-sm text-slate-300 space-y-1">
        <div>
          Appeal received. Reference <code className="chip">{done.id}</code> and access token{" "}
          <code className="chip">{done.access_token}</code> - keep both; the token is shown only once and is
          needed to check the status.
        </div>
        <div className="text-slate-400">
          Acknowledged by {fmtDate(done.ack_by)} · decision by {fmtDate(done.resolve_by)}
          {done.photo_restricted && " · the photo is excluded from search until this is resolved"}
        </div>
      </div>
    );

  return (
    <form onSubmit={submit} className="space-y-3 text-sm">
      <label htmlFor={`${uid}-cat`} className="block">
        <span className="block mb-1 text-slate-200">What is this about?</span>
        <select
          id={`${uid}-cat`}
          className="w-full rounded-xl bg-black/30 border border-white/20 p-2"
          value={category}
          onChange={(e) => setCategory(e.target.value as AppealCategory)}
        >
          {CATEGORIES.map((c) => (
            <option key={c.value} value={c.value}>{c.label}</option>
          ))}
        </select>
      </label>
      {!compact && (
        <label htmlFor={`${uid}-pid`} className="block">
          <span className="block mb-1 text-slate-200">Photo reference (optional)</span>
          <input
            id={`${uid}-pid`}
            className="w-full rounded-xl bg-black/30 border border-white/20 p-2"
            placeholder="e.g. 3f2a…e1.jpg"
            value={pid}
            onChange={(e) => setPid(e.target.value.trim())}
          />
        </label>
      )}
      <label htmlFor={`${uid}-reason`} className="block">
        <span className="block mb-1 text-slate-200">What is wrong and what outcome do you want?</span>
        <textarea
          id={`${uid}-reason`}
          required
          minLength={10}
          maxLength={2000}
          rows={compact ? 2 : 4}
          className="w-full rounded-xl bg-black/30 border border-white/20 p-2"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
        />
      </label>
      <label htmlFor={`${uid}-contact`} className="block">
        <span className="block mb-1 text-slate-200">Email or phone for our reply (optional, stored encrypted)</span>
        <input
          id={`${uid}-contact`}
          className="w-full rounded-xl bg-black/30 border border-white/20 p-2"
          maxLength={200}
          autoComplete="email"
          value={contact}
          onChange={(e) => setContact(e.target.value)}
        />
      </label>
      {err && <div role="alert" className="text-red-300">{err}</div>}
      <button className="btn" disabled={busy || reason.length < 10}>
        {busy ? "Submitting…" : "Submit appeal"}
      </button>
    </form>
  );
}
