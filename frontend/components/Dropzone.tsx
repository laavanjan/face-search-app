"use client";

import { useCallback, useRef, useState } from "react";
import { fmtSize, shrinkForUpload } from "@/lib/image";
import { useT } from "@/lib/i18n";

type Props = {
  onFile: (f: File) => void;
  label?: string;
  hint?: string;
  disabled?: boolean;
};

/** Keyboard-operable (Enter/Space), labelled for screen readers, works with
 * touch (tap opens the picker) and shrinks large photos on the device first. */
export default function Dropzone({ onFile, label, hint, disabled }: Props) {
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
      className={`dropzone ${active ? "active" : ""} ${disabled ? "opacity-50 pointer-events-none" : ""}`}
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
        // eslint-disable-next-line @next/next/no-img-element
        <img src={preview} alt="" className="max-h-64 rounded-xl border border-white/10 shadow-lg" />
      ) : (
        <>
          <div aria-hidden className="text-3xl mb-2">↑</div>
          <div className="font-medium">{label ?? t("drop.label")}</div>
          <div className="text-sm text-slate-300 mt-1">{hint ?? t("drop.hint")}</div>
        </>
      )}
      {note && <div role="status" className="text-xs text-slate-300 mt-2">{note}</div>}
    </div>
  );
}
