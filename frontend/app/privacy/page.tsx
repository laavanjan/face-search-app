"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getPolicy, type Policy } from "@/lib/api";
import { LIMITATIONS } from "@/lib/limitations";

const BASIS: Record<string, string> = {
  consent: "Consent of the people shown in the photos",
  contract: "Performance of a contract",
  legitimate_interest: "Legitimate interest",
  legal_obligation: "Legal obligation",
  vital_interests: "Vital interests",
  public_task: "Public task",
};

export default function PrivacyPage() {
  const [p, setP] = useState<Policy | null>(null);
  useEffect(() => {
    getPolicy().then(setP).catch(() => {});
  }, []);

  return (
    <article className="glass rounded-2xl p-8 space-y-6 text-sm text-slate-300 max-w-3xl">
      <header>
        <h1 className="text-3xl font-semibold tracking-tight">Privacy &amp; AI use</h1>
        <div className="text-xs text-slate-500 mt-1">Notice version {p?.privacy_notice_version ?? "…"}</div>
      </header>

      <section className="space-y-2">
        <h2 className="text-lg font-medium text-slate-100">You are using an AI system</h2>
        <p>
          Face Search is an automated <strong>facial-recognition</strong> system. When a photo is
          uploaded, a machine-learning model ({p?.model ?? "InsightFace buffalo_l"}) detects faces
          and turns each one into a 512-number <strong>face embedding</strong> - biometric data.
          Searching compares a reference face against stored embeddings using cosine similarity.
          {p?.uses_aws && " This deployment also sends photos to Amazon Rekognition (face quality scoring) and stores them in Amazon S3."}
        </p>
        <p>
          A similarity score is an estimate, not an identification. It can be wrong, and accuracy
          can differ across ages, skin tones, lighting and image quality. That is why a human
          reviewer must confirm every match before it is shown.
        </p>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-medium text-slate-100">Known limitations</h2>
        <ul className="list-disc pl-6 space-y-1">
          {LIMITATIONS.map((l) => (
            <li key={l}>{l}</li>
          ))}
        </ul>
        <p>Each match shows a confidence band; "low" means the system is uncertain and a mistake is plausible.</p>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-medium text-slate-100">Permitted and prohibited use</h2>
        <p>
          Permitted: finding photos of a person inside a <strong>private photo collection</strong>
          that the operator is entitled to process, where the people shown have consented.
        </p>
        <p>
          Prohibited: surveillance or tracking; identifying strangers; scraped or public-source
          images; law-enforcement identification; and any decision about employment, housing,
          credit, education, insurance or access to services.
        </p>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-medium text-slate-100">Legal basis</h2>
        <p>
          {p ? BASIS[p.legal_basis] ?? p.legal_basis : "…"}.{" "}
          {p?.consent_required &&
            "Uploads and searches are refused unless the operator confirms consent, and each confirmation is logged."}
        </p>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-medium text-slate-100">What is kept, and for how long</h2>
        <ul className="list-disc pl-6 space-y-1">
          <li>Photos and face embeddings: {p?.retention_days.photos_and_embeddings ?? "…"} days, then deleted automatically.</li>
          <li>Search reference photos: only while a reviewer checks the results; deleted when the case closes (cases themselves: {p?.retention_days.search_review_cases ?? "…"} days).</li>
          <li>Appeals: {p?.retention_days.resolved_appeals ?? "…"} days after resolution. Audit log: {p?.retention_days.audit_log ?? "…"} days.</li>
          <li>Not kept: original filenames, EXIF/GPS/camera metadata, or any inferred age, gender or ethnicity.</li>
        </ul>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-medium text-slate-100">Human oversight and your rights</h2>
        <p>
          Reviewers approve every photo before it becomes searchable and every match before it is
          released. You can challenge a match, object to indexing, or ask for deletion or access at
          any time on the <Link href="/appeal" className="underline">appeal page</Link>, with or
          without an account.
        </p>
      </section>

      <p className="text-xs text-slate-500">
        Full documentation: <code>docs/privacy/privacy-and-ai-use.md</code> in the repository.
      </p>
    </article>
  );
}
