"use client";

import { useState } from "react";
import Link from "next/link";
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

  const field = "w-full rounded-xl bg-black/30 border border-white/20 p-2";

  return (
    <div className="space-y-6 max-w-3xl">
      <section className="glass rounded-2xl p-6 sm:p-8 space-y-4 text-slate-200">
        <h1 className="text-3xl font-semibold tracking-tight">{t("a11y.title")}</h1>
        <p>{t("a11y.lead")}</p>

        <h2 className="text-lg font-medium text-slate-100">Using the site</h2>
        <ul className="list-disc pl-6 space-y-1">
          <li>Target: WCAG 2.2 level AA. Works with keyboard only (visible focus, skip link) and screen readers (labels, live status messages).</li>
          <li>Text can be zoomed to 200% and the layout works on phones, tablets and desktops. Motion is reduced if your device asks for it.</li>
          <li>Languages: English and Spanish (choose at the top of the page). Other languages: ask below and a person will help.</li>
          <li>Plain language first; technical details are behind &quot;Technical details&quot;.</li>
        </ul>

        <h2 className="text-lg font-medium text-slate-100">A person instead of the AI</h2>
        <p>
          You never have to rely on the AI. Every match is checked by a person before anyone sees it, and you can ask a
          person to do the search or help with any form instead. Choose &quot;A person to do this for me&quot; below.
        </p>

        <h2 className="text-lg font-medium text-slate-100">Cost and connection</h2>
        <ul className="list-disc pl-6 space-y-1">
          <li>The service is free. Appeals, misuse reports and help requests need no account.</li>
          <li>Large photos are made smaller on your device before upload, to save data on slow or metered connections.</li>
          <li>No device or internet? Ask someone you trust to send a help request for you and choose &quot;Phone call&quot;. We reply by phone.</li>
        </ul>

        <h2 className="text-lg font-medium text-slate-100">Known issues</h2>
        <ul className="list-disc pl-6 space-y-1">
          <li>Photo comparison in the reviewer console relies on sight; reviewers who need another method should ask the Service Owner.</li>
          <li>Only two interface languages so far.</li>
        </ul>
        <p className="text-sm text-slate-300">
          Other ways to get help: <Link href="/appeal" className="underline">challenge a result</Link> or report misuse.
        </p>
      </section>

      <section id="support" className="glass rounded-2xl p-6 sm:p-8 space-y-3" aria-labelledby="support-title">
        <h2 id="support-title" className="text-xl font-medium">{t("support.title")}</h2>
        <p className="text-slate-200">{t("support.lead")}</p>
        {done ? (
          <p role="status" className="text-slate-100">{t("support.sent", { id: done.id, token: done.access_token ?? "" })}</p>
        ) : (
          <form onSubmit={send} className="space-y-3 text-sm">
            <label className="block" htmlFor="sup-topic">
              <span className="block mb-1">{t("support.topic")}</span>
              <select id="sup-topic" className={field} value={topic} onChange={(e) => setTopic(e.target.value as typeof topic)}>
                {TOPICS.map((v) => (
                  <option key={v} value={v}>{t(`support.topic.${v}`)}</option>
                ))}
              </select>
            </label>
            <label className="block" htmlFor="sup-message">
              <span className="block mb-1">{t("support.message")}</span>
              <textarea id="sup-message" required minLength={5} maxLength={2000} rows={4} className={field} value={message} onChange={(e) => setMessage(e.target.value)} />
            </label>
            <label className="block" htmlFor="sup-format">
              <span className="block mb-1">{t("support.format")}</span>
              <select id="sup-format" className={field} value={format} onChange={(e) => setFormat(e.target.value as typeof format)}>
                {FORMATS.map((v) => (
                  <option key={v} value={v}>{t(`support.format.${v}`)}</option>
                ))}
              </select>
            </label>
            <label className="block" htmlFor="sup-contact">
              <span className="block mb-1">{t("support.contact")}</span>
              <input id="sup-contact" className={field} maxLength={200} autoComplete="email" value={contact} onChange={(e) => setContact(e.target.value)} />
            </label>
            {err && <div role="alert" className="text-red-300">{err}</div>}
            <button className="btn" disabled={busy || message.trim().length < 5}>{t("support.send")}</button>
          </form>
        )}
      </section>
    </div>
  );
}
