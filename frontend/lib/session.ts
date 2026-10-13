"use client";

import { useCallback, useEffect, useState } from "react";
import { AUTH_EVENT, getAccessKey, whoami, type Me } from "@/lib/api";

/** Current principal (null when signed out). `ready` is false until checked. */
export function useSession() {
  const [me, setMe] = useState<Me | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let alive = true;
    const load = () => {
      if (!getAccessKey()) {
        setMe(null);
        setReady(true);
        return;
      }
      whoami()
        .then((m) => alive && setMe(m))
        .catch(() => alive && setMe(null))
        .finally(() => alive && setReady(true));
    };
    load();
    window.addEventListener(AUTH_EVENT, load);
    return () => {
      alive = false;
      window.removeEventListener(AUTH_EVENT, load);
    };
  }, []);

  const can = useCallback((perm: string) => !!me?.permissions.includes(perm), [me]);
  return { me, ready, can };
}
