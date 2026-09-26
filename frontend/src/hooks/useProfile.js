import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

/**
 * The caller's own `profiles` row (id, role, full_name), via the existing
 * /api/whoami route — reused rather than adding a new endpoint. `profile` is
 * `undefined` while loading, `null` if RLS returns no visible row (CLAUDE.md:
 * that's a valid outcome, not an error), or the row once fetched.
 */
export function useProfile(session) {
  const [profile, setProfile] = useState(undefined);

  useEffect(() => {
    if (!session) {
      setProfile(session === null ? null : undefined);
      return;
    }
    let cancelled = false;
    apiFetch("/whoami")
      .then((res) => {
        if (!cancelled) setProfile(res.profile ?? null);
      })
      .catch(() => {
        if (!cancelled) setProfile(null);
      });
    return () => {
      cancelled = true;
    };
  }, [session]);

  return profile;
}
