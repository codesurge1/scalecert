// A separate, minimal fetch helper for the PUBLIC, login-free verification
// surface (/verify/:certNumber) ONLY — deliberately does NOT go through
// src/lib/api.js's apiFetch, which reads the Supabase auth session and
// attaches a bearer token. This page must work for a visitor who has never
// logged in and has no Supabase session at all, so it has zero dependency
// on auth state, not just an unused one.
export const API_BASE = import.meta.env.VITE_API_BASE || "/api";

export class ApiError extends Error {
  constructor(status, body) {
    super(typeof body?.detail === "string" ? body.detail : `Request failed with status ${status}`);
    this.status = status;
    this.body = body;
  }
}

export async function publicFetch(path, { method = "GET", body } = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers: { "Content-Type": "application/json" },
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
