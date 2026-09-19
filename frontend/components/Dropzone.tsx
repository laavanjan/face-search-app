"use client";

import { useCallback, useRef, useState } from "react";

type Props = {
  onFile: (f: File) => void;
  label?: string;
  hint?: string;
  disabled?: boolean;
};

export default function Dropzone({ onFile, label, hint, disabled }: Props) {
  const [active, setActive] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handle = useCallback(
    (f: File | null) => {
      if (!f) return;
      if (!f.type.startsWith("image/")) return;
      setPreview(URL.createObjectURL(f));
      onFile(f);
    },
    [onFile]
  );

  return (
    <div
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
      onClick={() => inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="hidden"
        onChange={(e) => handle(e.target.files?.[0] ?? null)}
      />
      {preview ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={preview}
          alt="preview"
          className="max-h-64 rounded-xl border border-white/10 shadow-lg"
        />
      ) : (
        <>
          <div className="text-3xl mb-2">↑</div>
          <div className="font-medium">{label ?? "Drop a photo here"}</div>
          <div className="text-xs text-slate-400 mt-1">
            {hint ?? "JPG / PNG / WebP · up to 15 MB"}
          </div>
        </>
      )}
    </div>
  );
}
