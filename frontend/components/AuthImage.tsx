"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { Icon } from "@/components/ui";
import { caseQueryImageUrl, photoObjectUrl } from "@/lib/api";

type Props = {
  photoId?: string;
  caseId?: string;
  alt: string;
  className?: string;
  /** Click (or Enter) opens the photo full size in a viewer. */
  enlarge?: boolean;
};

/** Photos are behind auth, so plain <img src> cannot load them: fetch with the
 * bearer token and render a short-lived object URL instead. */
export default function AuthImage({ photoId, caseId, alt, className, enlarge }: Props) {
  const [src, setSrc] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    let url: string | null = null;
    let alive = true;
    const p = caseId ? caseQueryImageUrl(caseId) : photoObjectUrl(photoId!);
    p.then((u) => {
      url = u;
      if (alive) setSrc(u);
      else URL.revokeObjectURL(u);
    }).catch(() => alive && setFailed(true));
    return () => {
      alive = false;
      if (url) URL.revokeObjectURL(url);
    };
  }, [photoId, caseId]);

  // Esc closes the viewer.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  if (failed)
    return (
      <div className={`${className ?? ""} flex flex-col items-center justify-center gap-1 bg-sunken text-xs text-subtle`}>
        <Icon name="image" className="h-5 w-5" />
        unavailable
      </div>
    );
  if (!src) return <div className={`${className ?? ""} skeleton`} />;
  if (!enlarge) {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={src} alt={alt} className={`${className ?? ""} bg-sunken`} />;
  }
  return (
    <>
      <button
        type="button"
        className="block w-full cursor-zoom-in focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
        aria-label={`View ${alt} full size`}
        onClick={() => setOpen(true)}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={src} alt={alt} className={`${className ?? ""} bg-sunken`} />
      </button>
      {open &&
        createPortal(
        <div
          role="dialog"
          aria-modal="true"
          aria-label={alt}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4"
          onClick={() => setOpen(false)}
        >
          <button
            type="button"
            autoFocus
            aria-label="Close"
            className="absolute right-4 top-4 flex h-11 w-11 items-center justify-center rounded-full bg-white/90 text-fg shadow-lg"
            onClick={() => setOpen(false)}
          >
            <Icon name="x" className="h-5 w-5" />
          </button>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={src}
            alt={alt}
            className="max-h-full max-w-full rounded-lg object-contain shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          />
        </div>,
        document.body
      )}
    </>
  );
}
