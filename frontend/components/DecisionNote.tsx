"use client";

import { useCallback, useState } from "react";

/** A required free-text reason for oversight actions. Every decision sends it
 * to the backend, which rejects reasons under 3 characters and writes it to
 * the audit log. */
export function useDecisionNote() {
  const [note, setNote] = useState("");
  const [missing, setMissing] = useState(false);

  const take = useCallback((): string | null => {
    const n = note.trim();
    if (n.length < 3) {
      setMissing(true);
      return null;
    }
    setMissing(false);
    return n;
  }, [note]);

  const field = (
    <div className="sticky top-2 z-10 glass rounded-xl p-3 text-sm">
      <label className="block text-xs text-slate-400 mb-1">
        Decision note - required for every action and recorded in the audit log
      </label>
      <input
        className={`w-full rounded-lg bg-black/30 border p-2 ${missing ? "border-red-400" : "border-white/10"}`}
        placeholder="e.g. consent form on file; same person - matching scar and glasses"
        value={note}
        onChange={(e) => {
          setNote(e.target.value);
          setMissing(false);
        }}
      />
      {missing && <div className="text-xs text-red-300 mt-1">Write a note (3+ characters) first.</div>}
    </div>
  );

  return { take, field, note };
}
