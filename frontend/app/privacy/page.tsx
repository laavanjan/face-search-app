"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Icon, PageHeader, type IconName } from "@/components/ui";
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

  const facts: [IconName, string, string][] = [
    ["shield", "Human review", p ? (p.human_review.indexing_requires_approval ? "Every photo and every match" : "Every match") : "…"],
    ["clock", "Photos kept", p ? `${p.retention_days.photos_and_embeddings} days` : "…"],
    ["file", "Legal basis", p ? BASIS[p.legal_basis] ?? p.legal_basis : "…"],
  ];

  return (
    <div className="space-y-6">
      <PageHeader title="Privacy & AI use">
        <div className="mt-2 text-xs text-subtle">Notice version {p?.privacy_notice_version ?? "…"}</div>
      </PageHeader>

      <dl className="grid gap-4 sm:grid-cols-3">
        {facts.map(([icon, k, v]) => (
          <div key={k} className="card flex items-start gap-3 p-4">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent/10 text-accent">
              <Icon name={icon} />
            </span>
            <div className="min-w-0">
              <dt className="text-xs font-medium uppercase tracking-wide text-subtle">{k}</dt>
              <dd className="mt-0.5 text-sm font-medium text-fg">{v}</dd>
            </div>
          </div>
        ))}
      </dl>

      <article className="card prose-doc max-w-none p-6 sm:p-8">
        <section className="space-y-2">
          <h2>You are using an AI system</h2>
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
          <h2>Known limitations</h2>
          <ul>
            {LIMITATIONS.map((l) => (
              <li key={l}>{l}</li>
            ))}
          </ul>
          <p>Each match shows a confidence band; &quot;low&quot; means the system is uncertain and a mistake is plausible.</p>
        </section>

        <section className="space-y-2">
          <h2>Permitted and prohibited use</h2>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-xl border border-success/25 bg-success/5 p-4">
              <div className="mb-1 flex items-center gap-2 font-semibold text-fg">
                <Icon name="check" className="h-4 w-4 text-success" /> Permitted
              </div>
              <p className="text-sm">
                Finding photos of a person inside a <strong>private photo collection</strong> that the
                operator is entitled to process, where the people shown have consented.
              </p>
            </div>
            <div className="rounded-xl border border-danger/25 bg-danger/5 p-4">
              <div className="mb-1 flex items-center gap-2 font-semibold text-fg">
                <Icon name="x" className="h-4 w-4 text-danger" /> Prohibited
              </div>
              <p className="text-sm">
                Surveillance or tracking; identifying strangers; scraped or public-source images;
                law-enforcement identification; and any decision about employment, housing, credit,
                education, insurance or access to services.
              </p>
            </div>
          </div>
        </section>

        <section className="space-y-2">
          <h2>Legal basis</h2>
          <p>
            {p ? BASIS[p.legal_basis] ?? p.legal_basis : "…"}.{" "}
            {p?.consent_required &&
              "Uploads and searches are refused unless the operator confirms consent, and each confirmation is logged."}
          </p>
        </section>

        <section className="space-y-2">
          <h2>What is kept, and for how long</h2>
          <ul>
            <li>Photos and face embeddings: {p?.retention_days.photos_and_embeddings ?? "…"} days, then deleted automatically.</li>
            <li>Search reference photos: only while a reviewer checks the results; deleted when the case closes (cases themselves: {p?.retention_days.search_review_cases ?? "…"} days).</li>
            <li>Appeals: {p?.retention_days.resolved_appeals ?? "…"} days after resolution. Audit log: {p?.retention_days.audit_log ?? "…"} days.</li>
            <li>Not kept: original filenames, EXIF/GPS/camera metadata, or any inferred age, gender or ethnicity.</li>
          </ul>
        </section>

        <section className="space-y-2">
          <h2>Human oversight and your rights</h2>
          <p>
            Reviewers approve every photo before it becomes searchable and every match before it is
            released. You can challenge a match, object to indexing, or ask for deletion or access at
            any time on the <Link href="/appeal">appeal page</Link>, with or without an account.
          </p>
        </section>

        <p className="border-t border-line pt-4 text-xs text-subtle">
          Full documentation: <code>docs/privacy/privacy-and-ai-use.md</code> in the repository.
        </p>
      </article>
    </div>
  );
}
