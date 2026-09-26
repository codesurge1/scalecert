import { useEffect, useState } from "react";
import { createClient } from "@supabase/supabase-js";

// The frontend only ever uses the anon key — same rule as the backend
// (CLAUDE.md): the service-role key never appears here.
export const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL,
  import.meta.env.VITE_SUPABASE_ANON_KEY,
);

/**
 * Reactive Supabase auth session. `session` is `undefined` while the initial
 * check is in flight (render a loading state, not a login redirect), `null`
 * once checked and there is no session, or the session object once signed
 * in. Kept up to date via `onAuthStateChange` (login, logout, token refresh).
 */
export function useSession() {
  const [session, setSession] = useState(undefined);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => setSession(data.session ?? null));

    const { data: subscription } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession);
    });

    return () => subscription.subscription.unsubscribe();
  }, []);

  return session;
}
