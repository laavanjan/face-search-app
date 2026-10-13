"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { setAccessKey, whoami } from "@/lib/api";

export default function SignInPage() {
  const [key, setKey] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const router = useRouter();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    setAccessKey(key.trim());
    try {
      const me = await whoami();
      router.push(me.permissions.includes("photos:write") ? "/" : me.permissions.includes("review:decide") ? "/review" : "/gallery");
    } catch {
      setAccessKey(null);
      setErr("That access key was not accepted.");
    }
  }

  return (
    <section className="glass rounded-2xl p-8 max-w-lg">
      <h1 className="text-2xl font-semibold tracking-tight mb-2">Sign in</h1>
      <p className="text-slate-400 text-sm mb-6">
        Use the personal access key issued by the Service Owner. Your role (operator, reviewer,
        admin, viewer) decides what you can do. The key is kept only for this browser tab.
      </p>
      <form onSubmit={submit} className="space-y-3">
        <input
          type="password"
          autoComplete="off"
          className="w-full rounded-xl bg-black/30 border border-white/10 p-2 text-sm"
          placeholder="Access key"
          value={key}
          onChange={(e) => setKey(e.target.value)}
        />
        {err && <div className="text-sm text-red-300">{err}</div>}
        <button className="btn" disabled={!key.trim()}>Sign in</button>
      </form>
    </section>
  );
}
