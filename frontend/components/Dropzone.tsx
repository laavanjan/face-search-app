"use client";

import { useCallback, useRef, useState } from "react";
import { Icon } from "@/components/ui";
import { fmtSize, shrinkForUpload } from "@/lib/image";
import { useT } from "@/lib/i18n";

type Props = {
  onFile: (f: File) => void;
  label?: string;
  hint?: string;
  disabled?: boolean;
  /** Earlier steps (consent, purpose) are incomplete: say so instead of the file hint. */
  locked?: boolean;
};

/** Keyboard-operable (Enter/Space), labelled for screen readers, works with
 * touch (tap opens the picker) and shrinks large photos on the device first. */
export default function Dropzone({ onFile, label, hint, disabled, locked }: Props) {
  const { t } = useT();
  const [active, setActive] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handle = useCallback(
    async (f: File | null) => {
      if (!f) return;
      if (!f.type.startsWith("image/")) return;
      const small = await shrinkForUpload(f);
      setNote(small !== f ? t("drop.shrunk", { from: fmtSize(f.size), to: fmtSize(small.size) }) : null);
      setPreview(URL.createObjectURL(small));
      onFile(small);
    },
    [onFile, t]
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
        handle(e.dataTransfer.files?.[0] ?? null);
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
        className="hidden"
        tabIndex={-1}
        aria-hidden
        onChange={(e) => handle(e.target.files?.[0] ?? null)}
      />
      {preview ? (
        <>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={preview} alt="" className="max-h-64 rounded-xl border border-line shadow-pop" />
          {!disabled && <div className="mt-3 text-xs text-subtle">{t("drop.change")}</div>}
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
