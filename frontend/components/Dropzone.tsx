"use client";

import { useCallback, useRef, useState } from "react";
import { Icon } from "@/components/ui";
import { fmtSize, shrinkForUpload } from "@/lib/image";
import { useT } from "@/lib/i18n";

/** Most photos taken in one batch: keeps a small server from running out of memory. */
export const MAX_BATCH = 20;

type Props = {
  /** One photo at a time (search page). */
  onFile?: (f: File) => void;
  /** Several photos at once (upload page). When set, the picker allows multiple files. */
  onFiles?: (f: File[]) => void;
  label?: string;
  hint?: string;
  disabled?: boolean;
  /** Earlier steps (consent, purpose) are incomplete: say so instead of the file hint. */
  locked?: boolean;
};

/** Keyboard-operable (Enter/Space), labelled for screen readers, works with
 * touch (tap opens the picker) and shrinks large photos on the device first. */
export default function Dropzone({ onFile, onFiles, label, hint, disabled, locked }: Props) {
  const { t } = useT();
  const multiple = !!onFiles;
  const [active, setActive] = useState(false);
  const [previews, setPreviews] = useState<string[]>([]);
  const [count, setCount] = useState(0);
  const [note, setNote] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handle = useCallback(
    async (f: File | null) => {
      if (!f) return;
      if (!f.type.startsWith("image/")) return;
      const small = await shrinkForUpload(f);
      setNote(small !== f ? t("drop.shrunk", { from: fmtSize(f.size), to: fmtSize(small.size) }) : null);
      setPreviews([URL.createObjectURL(small)]);
      setCount(1);
      onFile?.(small);
    },
    [onFile, t]
  );

  const handleMany = useCallback(
    async (list: FileList | null) => {
      const all = Array.from(list ?? []).filter((f) => f.type.startsWith("image/"));
      if (!all.length) return;
      const chosen = all.slice(0, MAX_BATCH);
      const small: File[] = [];
      for (const f of chosen) small.push(await shrinkForUpload(f)); // one at a time: low memory
      setNote(all.length > MAX_BATCH ? `Only the first ${MAX_BATCH} photos were used.` : null);
      setPreviews(small.slice(0, 8).map((f) => URL.createObjectURL(f)));
      setCount(small.length);
      onFiles?.(small);
    },
    [onFiles]
  );

  const open = () => !disabled && inputRef.current?.click();

  return (
    <div
      role="button"
      tabIndex={disabled ? -1 : 0}
      aria-disabled={disabled}
      aria-label={t("drop.aria")}
      className={`dropzone ${active ? "active" : ""} ${disabled ? "pointer-events-none opacity-60" : ""}`}
      onDragOver={(e) => {
        e.preventDefault();
        setActive(true);
      }}
      onDragLeave={() => setActive(false)}
      onDrop={(e) => {
        e.preventDefault();
        setActive(false);
        if (multiple) handleMany(e.dataTransfer.files);
        else handle(e.dataTransfer.files?.[0] ?? null);
      }}
      onClick={open}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          open();
        }
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        multiple={multiple}
        className="hidden"
        tabIndex={-1}
        aria-hidden
        onChange={(e) => {
          if (multiple) handleMany(e.target.files);
          else handle(e.target.files?.[0] ?? null);
          e.target.value = ""; // allow choosing the same file again
        }}
      />
      {previews.length > 0 ? (
        <>
          {multiple && count > 1 ? (
            <div className="flex flex-wrap justify-center gap-2">
              {previews.map((src) => (
                // eslint-disable-next-line @next/next/no-img-element
                <img key={src} src={src} alt="" className="h-20 w-20 rounded-lg border border-line object-cover shadow-pop" />
              ))}
            </div>
          ) : (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={previews[0]} alt="" className="max-h-64 rounded-xl border border-line shadow-pop" />
          )}
          {multiple && count > 1 && <div className="mt-2 text-sm font-medium text-fg">{count} photos selected</div>}
          {!disabled && <div className="mt-3 text-xs text-subtle">{multiple ? "Click or drop more photos to start another batch." : t("drop.change")}</div>}
        </>
      ) : (
        <>
          <div aria-hidden className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-surface text-accent shadow-card ring-1 ring-line">
            <Icon name={locked ? "lock" : "upload"} className="h-5 w-5" />
          </div>
          <div className="font-medium text-fg">{label ?? t("drop.label")}</div>
          <div className="mt-1 max-w-md text-sm text-muted">{locked ? t("drop.locked") : hint ?? t("drop.hint")}</div>
        </>
      )}
      {note && <div role="status" className="mt-2 text-xs text-muted">{note}</div>}
    </div>
  );
}
