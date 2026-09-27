import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

/**
 * Composes "every session visible to me" client-side from two existing
 * endpoints — GET /api/instruments (RLS: every authenticated user sees
 * every instrument, db/schema.sql `instruments_select_auth`) plus
 * GET /api/instruments/{id}/sessions per instrument (RLS: a technician
 * sees only their own sessions, an approver/admin sees all — `sessions_select`).
 *
 * KNOWN GAP, not fixed here (frontend-only task, no new backend routes):
 * there is no role-scoped `GET /api/sessions` endpoint. That would be the
 * clean fix — one request instead of 1 + N, and it would let the backend
 * express "sessions I can see" directly instead of the frontend re-deriving
 * it by joining instruments -> sessions. This composition is correct today
 * because RLS already scopes each per-instrument sessions call correctly
 * (a technician's calls simply return fewer rows), but it's O(instruments)
 * requests and will not scale past a small instrument count.
 *
 * Returns each session enriched with its own `instrument` (for display —
 * type designation, etc.) under `.instrument`.
 */
export function useAllSessions() {
  const [status, setStatus] = useState("loading"); // "loading" | "loaded" | "error"
  const [sessions, setSessions] = useState([]);
  const [instruments, setInstruments] = useState([]);
  const [error, setError] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setStatus("loading");
    setError(null);

    apiFetch("/instruments")
      .then((instrumentRows) =>
        Promise.all(
          instrumentRows.map((instrument) =>
            apiFetch(`/instruments/${instrument.id}/sessions`).then((sessionRows) =>
              sessionRows.map((session) => ({ ...session, instrument })),
            ),
          ),
        ).then((sessionsByInstrument) => ({ instrumentRows, sessions: sessionsByInstrument.flat() })),
      )
      .then(({ instrumentRows, sessions: allSessions }) => {
        if (cancelled) return;
        setInstruments(instrumentRows);
        setSessions(allSessions);
        setStatus("loaded");
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err.message);
        setStatus("error");
      });

    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  return { status, sessions, instruments, error, reload: () => setReloadKey((k) => k + 1) };
}
