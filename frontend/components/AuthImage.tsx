"use client";

import { useEffect, useState } from "react";
import { Icon } from "@/components/ui";
import { caseQueryImageUrl, photoObjectUrl } from "@/lib/api";

type Props = {
  photoId?: string;
  caseId?: string;
  alt: string;
  className?: string;
};

/** Photos are behind auth, so plain <img src> cannot load them: fetch with the
 * bearer token and render a short-lived object URL instead. */
export default function AuthImage({ photoId, caseId, alt, className }: Props) {
  const [src, setSrc] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

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

  if (failed)
    return (
      <div className={`${className ?? ""} flex flex-col items-center justify-center gap-1 bg-sunken text-xs text-subtle`}>
        <Icon name="image" className="h-5 w-5" />
        unavailable
      </div>
    );
  if (!src) return <div className={`${className ?? ""} skeleton`} />;
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={src} alt={alt} className={`${className ?? ""} bg-sunken`} />;
}
