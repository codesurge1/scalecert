import { createClient } from "@supabase/supabase-js";

// The frontend only ever uses the anon key — same rule as the backend
// (CLAUDE.md): the service-role key never appears here.
export const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL,
  import.meta.env.VITE_SUPABASE_ANON_KEY,
);

// In production the backend shares this domain (Vercel Services, routed by
// /vercel.json), so the default is a same-origin relative path — never a
// hardcoded host. VITE_API_BASE overrides this for local dev, where the Vite
// dev server and uvicorn are on different ports.
export const API_BASE = import.meta.env.VITE_API_BASE || "/api";
