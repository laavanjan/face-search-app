"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Alert, Icon, Spinner } from "@/components/ui";
import { setAccessKey, whoami } from "@/lib/api";

export default function SignInPage() {
  const [key, setKey] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const router = useRouter();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    setBusy(true);
    setAccessKey(key.trim());
    try {
      const me = await whoami();
      router.push(me.permissions.includes("photos:write") ? "/" : me.permissions.includes("review:decide") ? "/review" : "/gallery");
    } catch {
      setAccessKey(null);
      setErr("That access key was not accepted.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex justify-center py-6 sm:py-10">
      <section className="card w-full max-w-md p-6 sm:p-8">
        <div className="mb-5 flex h-11 w-11 items-center justify-center rounded-xl bg-accent/10 text-accent">
          <Icon name="lock" className="h-5 w-5" />
        </div>
        <h1 className="text-2xl font-semibold tracking-tight text-fg">Sign in</h1>
        <p className="mb-6 mt-2 text-sm leading-relaxed text-muted">
          Use the personal access key issued by the Service Owner. Your role (operator, reviewer,
          admin, viewer) decides what you can do. The key is kept only for this browser tab.
        </p>
        <form onSubmit={submit} className="space-y-4">
          <div>
            <label htmlFor="access-key" className="label">Access key</label>
            <input
              id="access-key"
              type="password"
              autoComplete="off"
              className={`input font-mono ${err ? "input-error" : ""}`}
              aria-invalid={!!err}
              value={key}
              onChange={(e) => setKey(e.target.value)}
            />
          </div>
          {err && <Alert tone="danger">{err}</Alert>}
          <button className="btn w-full" disabled={!key.trim() || busy}>
            {busy && <Spinner />}
            Sign in
          </button>
        </form>
        <p className="mt-6 border-t border-line pt-4 text-xs text-subtle">
          No account? You can still <Link href="/appeal" className="link">challenge a result</Link> or{" "}
          <Link href="/accessibility#support" className="link">ask for help</Link>.
        </p>
      </section>
    </div>
  );
}
