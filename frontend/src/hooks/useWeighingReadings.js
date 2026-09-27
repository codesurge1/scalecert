import { useCallback, useState } from "react";
import { toast } from "sonner";
import { apiFetch, ApiError } from "@/lib/api";
import { supabase } from "@/lib/supabase";
import { equalDecimalStrings } from "@/lib/decimalMath";

// Builds the cells map from GET .../weighing/readings records, so a page
// load/refresh reconstructs exactly what was already submitted instead of
// starting blank (unchanged from the pre-panel WeighingFormTable — moved
// here so both the table and the guided panel read/write the exact same
// state instead of each keeping their own copy).
function cellsFromInitialReadings(initialReadings) {
  const cells = {};
  for (const record of initialReadings ?? []) {
    cells[record.sequence_no] = {
      ...cells[record.sequence_no],
      [record.direction]: {
        indication: record.I,
        deltaL: record.delta_l,
        result: { E: record.E, Ec: record.Ec, mpe: record.mpe, passed: record.passed, I: record.I, delta_l: record.delta_l },
        submitting: false,
        error: null,
      },
    };
  }
  return cells;
}

const EMPTY_CELL = { indication: "", deltaL: "0", result: null, submitting: false, error: null };

/**
 * The single source of truth for every Weighing cell's state — shared by
 * `WeighingFormTable` (the click-any-cell OIML form) and `GuidedEntryPanel`
 * (the keyboard-first accelerator next to it), so a submit from either
 * surface is immediately visible on the other with no extra sync code:
 * both just read/write the same `cells` map via `getCell`/`updateCell`.
 *
 * `cells[sequence_no][apiDirection] = { indication, deltaL, result, submitting, error }`
 *
 * `runId` (feat/test-runs-conditions) scopes every submission to a run —
 * `null`/omitted means the implicit default/only run, the exact behavior
 * from before runs existed. The caller (`WeighingFormTable`, mounted with
 * `key={runId}` by `WeighingSessionPage`) is responsible for handing this
 * hook a fresh instance per run; this hook itself has no run-switching
 * logic, by design — it only ever seeds `cells` once, from whichever
 * run's `initialReadings` it was constructed with.
 */
export function useWeighingReadings({ sessionId, sessionStatus, initialReadings, e0, actorId, runId = null }) {
  const disabled = sessionStatus !== "draft";

  // Lazily seeded from initialReadings once, on mount — this page is keyed
  // per session, so it doesn't need to re-sync if the prop identity changes.
  const [cells, setCells] = useState(() => cellsFromInitialReadings(initialReadings));

  // Memoized (not just plain functions) specifically so GuidedEntryPanel's
  // effects can list them as dependencies without over-firing on every
  // unrelated render — `getCell` only changes identity when `cells` itself
  // does; `updateCell` never does at all, since it only ever reads through
  // `setCells`'s own updater-callback argument, never the outer `cells`.
  const getCell = useCallback(
    (sequenceNo, apiDirection) => cells[sequenceNo]?.[apiDirection] ?? EMPTY_CELL,
    [cells],
  );

  const updateCell = useCallback((sequenceNo, apiDirection, patch) => {
    setCells((prev) => ({
      ...prev,
      [sequenceNo]: {
        ...prev[sequenceNo],
        [apiDirection]: { ...(prev[sequenceNo]?.[apiDirection] ?? EMPTY_CELL), ...patch },
      },
    }));
  }, []);

  // Amendment audit trail (docs/architecture.md). There is no update
  // endpoint for a reading — POST always inserts a new row, and the GET
  // list already dedupes to the latest by created_at, so a resubmission
  // correctly "supersedes" at the DATA layer with no change needed here.
  // What that alone doesn't do is leave a record that a correction
  // happened. `audit_log` has a plain INSERT policy, `actor_id = auth.uid()`
  // (db/schema.sql) — open to any authenticated user, not just the backend
  // — so this writes the amendment directly via the Supabase client: the
  // same per-request, JWT-scoped client the rest of the frontend already
  // uses everywhere (CLAUDE.md: never the service-role key), no new
  // backend route needed. Non-fatal, same convention as every backend
  // audit write (app/routers/sessions.py) — the reading itself already
  // succeeded; losing the audit note shouldn't roll back real lab data.
  function logAmendment({ sequenceNo, apiDirection, before, after }) {
    if (!actorId) return; // no signed-in actor to attribute the write to
    supabase
      .from("audit_log")
      .insert({
        session_id: sessionId,
        actor_id: actorId,
        action: "weighing_reading_amended",
        data: { sequence_no: sequenceNo, direction: apiDirection, before, after },
      })
      .then(({ error }) => {
        if (error) console.warn("audit_log insert failed for weighing amendment:", error.message);
      });
  }

  // Shared by both surfaces — the table's onBlur/Enter handlers and the
  // guided panel's "commit and advance" both call this exact function, so
  // there is exactly one place a reading is ever POSTed from.
  async function submitDirection(entry, apiDirection) {
    const cell = getCell(entry.sequence_no, apiDirection);
    if (cell.indication === "" || disabled) return;

    const wasAlreadySubmitted = Boolean(cell.result);
    const before = wasAlreadySubmitted ? { I: cell.result.I, delta_l: cell.result.delta_l } : null;

    updateCell(entry.sequence_no, apiDirection, { submitting: true, error: null });
    // Decimal-as-string discipline (CLAUDE.md, backend StrictDecimal
    // contract): indication/deltaL/e0 are sent exactly as their raw string
    // values — never through Number()/parseFloat() first.
    const payload = {
      sequence_no: entry.sequence_no,
      direction: apiDirection,
      I: cell.indication,
      delta_l: cell.deltaL === "" ? "0" : cell.deltaL,
      E0: e0,
      run_id: runId,
    };
    try {
      const res = await apiFetch(`/sessions/${sessionId}/weighing/readings`, { method: "POST", body: payload });
      updateCell(entry.sequence_no, apiDirection, { result: res, submitting: false, error: null });

      const after = { I: payload.I, delta_l: payload.delta_l };
      if (
        wasAlreadySubmitted &&
        (!equalDecimalStrings(before.I, after.I) || !equalDecimalStrings(before.delta_l, after.delta_l))
      ) {
        logAmendment({ sequenceNo: entry.sequence_no, apiDirection, before, after });
      }
      return res;
    } catch (err) {
      const message =
        err instanceof ApiError && err.status === 409 ? "Session is no longer in draft — locked." : err.message;
      updateCell(entry.sequence_no, apiDirection, { submitting: false, error: message });
      toast.error(`Load #${entry.sequence_no} (${apiDirection}): ${message}`);
      return null;
    }
  }

  return { disabled, cells, getCell, updateCell, submitDirection };
}
