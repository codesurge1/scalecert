import { createClient } from "@supabase/supabase-js";

// The frontend only ever uses the anon key — same rule as the backend
// (CLAUDE.md): the service-role key never appears here.
export const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL,
  import.meta.env.VITE_SUPABASE_ANON_KEY,
);

export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";
