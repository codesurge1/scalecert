import { supabase } from "@/lib/supabase";

// Same-origin in production (frontend and backend share one Vercel domain via
// Vercel Services, routed by /vercel.json), so the default is a relative
// path — never a hardcoded host. VITE_API_BASE overrides this for local dev,
// where the Vite dev server and uvicorn are on different ports.
export const API_BASE = import.meta.env.VITE_API_BASE || "/api";

export class ApiError extends Error {
  constructor(status, body) {
    super(typeof body?.detail === "string" ? body.detail : `Request failed with status ${status}`);
    this.status = status;
    this.body = body;
  }
}

/**
 * Every /api call goes through here so the caller's session token is always
 * attached the same way, and never has to be threaded through by hand.
 *
 * Decimal-as-string discipline (CLAUDE.md / backend StrictDecimal contract):
 * the backend rejects any numeric field sent as a bare JSON number, because
 * a JS `number` is a float and a value like 300.6 must never round-trip
 * through one before reaching the Decimal-based engine. Callers must build
 * `body` with every numeric field already as a string (e.g. "300.6", not
 * 300.6) — this helper does not coerce anything; it just serializes and
 * sends whatever shape it's given, so the discipline has to hold at the call
 * site, all the way from the input element's value to this call.
 */
export async function apiFetch(path, { method = "GET", body, headers } = {}) {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;

  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  let responseBody = null;
  const text = await response.text();
  if (text) {
    try {
      responseBody = JSON.parse(text);
    } catch {
      responseBody = text;
    }
  }

  if (!response.ok) {
    throw new ApiError(response.status, responseBody);
  }

  return responseBody;
}
