"use client";

import { useState } from "react";
import Link from "next/link";
import { Alert, PageHeader, Spinner } from "@/components/ui";
import { submitSupport, type Appeal, type SupportRequest } from "@/lib/api";
import { useT } from "@/lib/i18n";

const TOPICS: SupportRequest["topic"][] = ["human_assistance", "accessibility", "language", "cost", "technical", "other"];
const FORMATS: SupportRequest["preferred_format"][] = ["email", "phone", "large_print", "easy_read", "sign_language_interpreter", "other"];

export default function AccessibilityPage() {
  const { t, locale } = useT();
  const [topic, setTopic] = useState<SupportRequest["topic"]>("human_assistance");
  const [format, setFormat] = useState<SupportRequest["preferred_format"]>("email");
  const [message, setMessage] = useState("");
  const [contact, setContact] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [done, setDone] = useState<Appeal | null>(null);

  async function send(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      setDone(await submitSupport({ topic, message, preferred_format: format, language: locale, contact: contact || undefined }));
    } catch (e: any) {
      setErr(e.message ?? "failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader title={t("a11y.title")} description={t("a11y.lead")} />
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)] lg:items-start">
        <article className="card prose-doc max-w-none p-6 sm:p-8">
          <h2 className="!pt-0">Using the site</h2>
          <ul>
            <li>Target: WCAG 2.2 level AA. Works with keyboard only (visible focus, skip link) and screen readers (labels, live status messages).</li>
            <li>Text can be zoomed to 200% and the layout works on phones, tablets and desktops. Motion is reduced if your device asks for it. Light and dark themes follow your device setting.</li>
            <li>Languages: English and Spanish (choose at the top of the page). Other languages: ask below and a person will help.</li>
            <li>Plain language first; technical details are behind &quot;Technical details&quot;.</li>
          </ul>

          <h2>A person instead of the AI</h2>
          <p>
            You never have to rely on the AI. Every match is checked by a person before anyone sees it, and you can ask a
            person to do the search or help with any form instead. Choose &quot;A person to do this for me&quot; below.
          </p>

          <h2>Cost and connection</h2>
          <ul>
            <li>The service is free. Appeals, misuse reports and help requests need no account.</li>
            <li>Large photos are made smaller on your device before upload, to save data on slow or metered connections.</li>
            <li>No device or internet? Ask someone you trust to send a help request for you and choose &quot;Phone call&quot;. We reply by phone.</li>
          </ul>

          <h2>Known issues</h2>
          <ul>
            <li>Photo comparison in the reviewer console relies on sight; reviewers who need another method should ask the Service Owner.</li>
            <li>Only two interface languages so far.</li>
          </ul>
          <p className="text-sm">
            Other ways to get help: <Link href="/appeal">challenge a result</Link> or report misuse.
          </p>
        </article>

        <section id="support" className="card scroll-mt-32 p-6 sm:p-8 lg:sticky lg:top-32" aria-labelledby="support-title">
          <h2 id="support-title" className="text-xl font-semibold tracking-tight text-fg">{t("support.title")}</h2>
          <p className="mb-5 mt-1 text-sm text-muted">{t("support.lead")}</p>
          {done ? (
            <Alert tone="success" role="status">
              <span className="text-fg">{t("support.sent", { id: done.id, token: done.access_token ?? "" })}</span>
            </Alert>
          ) : (
            <form onSubmit={send} className="space-y-4 text-sm">
              <div>
                <label className="label" htmlFor="sup-topic">{t("support.topic")}</label>
                <select id="sup-topic" className="select" value={topic} onChange={(e) => setTopic(e.target.value as typeof topic)}>
                  {TOPICS.map((v) => (
                    <option key={v} value={v}>{t(`support.topic.${v}`)}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="label" htmlFor="sup-message">{t("support.message")}</label>
                <textarea id="sup-message" required minLength={5} maxLength={2000} rows={4} className="textarea" value={message} onChange={(e) => setMessage(e.target.value)} />
              </div>
              <div>
                <label className="label" htmlFor="sup-format">{t("support.format")}</label>
                <select id="sup-format" className="select" value={format} onChange={(e) => setFormat(e.target.value as typeof format)}>
                  {FORMATS.map((v) => (
                    <option key={v} value={v}>{t(`support.format.${v}`)}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="label" htmlFor="sup-contact">{t("support.contact")}</label>
                <input id="sup-contact" className="input" maxLength={200} autoComplete="email" value={contact} onChange={(e) => setContact(e.target.value)} />
              </div>
              {err && <Alert tone="danger">{err}</Alert>}
              <button className="btn w-full sm:w-auto" disabled={busy || message.trim().length < 5}>
                {busy && <Spinner />}
                {t("support.send")}
              </button>
            </form>
          )}
        </section>
      </div>
    </div>
  );
}
