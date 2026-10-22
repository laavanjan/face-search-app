"use client";

import { useCallback, useId, useState } from "react";
import { Icon } from "@/components/ui";

/** A required free-text reason for oversight actions. Every decision sends it
 * to the backend, which rejects reasons under 3 characters and writes it to
 * the audit log. */
export function useDecisionNote() {
  const id = useId();
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
    <div className="sticky top-[108px] z-20 rounded-2xl border border-line bg-surface/95 p-4 shadow-pop backdrop-blur">
      <label htmlFor={id} className="mb-1.5 flex items-center gap-2 text-sm font-medium text-fg">
        <Icon name="file" className="h-4 w-4 text-subtle" />
        Decision note
        <span className="font-normal text-subtle">- required for every action and recorded in the audit log</span>
      </label>
      <input
        id={id}
        className={`input ${missing ? "input-error" : ""}`}
        placeholder="e.g. consent form on file; same person - matching scar and glasses"
        aria-invalid={missing}
        aria-describedby={missing ? `${id}-err` : undefined}
        value={note}
        onChange={(e) => {
          setNote(e.target.value);
          setMissing(false);
        }}
      />
      {missing && (
        <div id={`${id}-err`} role="alert" className="mt-1.5 text-xs font-medium text-danger">
          Write a note (3+ characters) first.
        </div>
      )}
    </div>
  );

  return { take, field, note };
}
