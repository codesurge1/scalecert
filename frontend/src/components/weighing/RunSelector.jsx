import { useState } from "react";
import { cn } from "@/lib/utils";

/**
 * The run/condition selector for Weighing (feat/test-runs-conditions) — the
 * concept behind clause 1's page-9 "Initial" + multiple °C rows: the SAME
 * weighing procedure re-run under different labelled conditions.
 *
 * Deliberately near-invisible in the common case: with no runs created yet
 * (`runs` empty), this renders only a small "+ Add another run" affordance
 * — no tab bar, no extra chrome, nothing that changes how the page looks
 * or behaves for the single-run technician. "Initial" always represents
 * the implicit default/only run (`null` run_id) — it is never itself a
 * `test_runs` row, so it's always present without needing to be created.
 *
 * Reused as-is (feat/damp-heat-endurance) by Damp heat/Endurance, whose
 * runs are a FIXED, auto-provisioned set (a/b/c, a/c — see
 * `POST .../damp-heat/setup` / `.../endurance/setup`) rather than
 * technician-labelled ones: `showDefaultTab={false}` (there is no
 * implicit default/only run for either test — every reading belongs to
 * one of the fixed runs) and `onCreateRun` simply omitted, which hides
 * the "+ Add run" affordance entirely — nothing here lets a technician
 * add an extra, unplanned run to either of those two tests.
 */
export function RunSelector({
  runs,
  selectedRunId,
  onSelectRun,
  onCreateRun,
  disabled,
  showDefaultTab = true,
  defaultTabLabel = "Initial",
}) {
  const [adding, setAdding] = useState(false);
  const [label, setLabel] = useState("");
  const [temperature, setTemperature] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const hasRuns = (runs?.length ?? 0) > 0;

  async function handleCreate() {
    if (!label.trim() || submitting) return;
    setSubmitting(true);
    try {
      const conditions = temperature.trim() ? { temperature_c: temperature.trim() } : null;
      await onCreateRun(label.trim(), conditions);
      setLabel("");
      setTemperature("");
      setAdding(false);
    } catch {
      // onCreateRun's own apiFetch already surfaces a toast on failure
      // (WeighingSessionPage) — nothing further to show here, just don't
      // close the inline form so the technician can retry without
      // retyping.
    } finally {
      setSubmitting(false);
    }
  }

  if (!hasRuns && !adding && (disabled || !onCreateRun)) {
    return null; // nothing to show and nothing creatable — render nothing at all
  }

  return (
    <div className="flex shrink-0 flex-wrap items-center gap-2 text-xs">
      {hasRuns ? (
        <>
          {showDefaultTab ? (
            <button
              type="button"
              className={cn(
                "rounded border px-2 py-1",
                selectedRunId === null
                  ? "border-neutral-900 bg-neutral-900 text-white"
                  : "border-neutral-400 text-neutral-700 hover:bg-neutral-50",
              )}
              onClick={() => onSelectRun(null)}
            >
              {defaultTabLabel}
            </button>
          ) : null}
          {runs.map((run) => (
            <button
              key={run.id}
              type="button"
              className={cn(
                "rounded border px-2 py-1",
                selectedRunId === run.id
                  ? "border-neutral-900 bg-neutral-900 text-white"
                  : "border-neutral-400 text-neutral-700 hover:bg-neutral-50",
              )}
              onClick={() => onSelectRun(run.id)}
            >
              {run.run_label}
            </button>
          ))}
        </>
      ) : null}

      {!onCreateRun || disabled ? null : adding ? (
        <div className="flex items-center gap-1.5">
          <input
            className="h-7 w-36 rounded border border-neutral-400 px-1.5 focus:outline-none focus:ring-1 focus:ring-inset focus:ring-neutral-900"
            placeholder="Run label (e.g. at 40 °C)"
            value={label}
            onChange={(event) => setLabel(event.target.value)}
            autoFocus
          />
          <input
            className="h-7 w-20 rounded border border-neutral-400 px-1.5 focus:outline-none focus:ring-1 focus:ring-inset focus:ring-neutral-900"
            placeholder="Temp °C"
            inputMode="decimal"
            value={temperature}
            onChange={(event) => setTemperature(event.target.value)}
          />
          <button
            type="button"
            className="rounded bg-neutral-900 px-2 py-1 text-white disabled:opacity-60"
            disabled={!label.trim() || submitting}
            onClick={handleCreate}
          >
            {submitting ? "…" : "Create"}
          </button>
          <button
            type="button"
            className="px-1 text-neutral-500 hover:text-neutral-800"
            onClick={() => {
              setAdding(false);
              setLabel("");
              setTemperature("");
            }}
          >
            Cancel
          </button>
        </div>
      ) : (
        <button
          type="button"
          className="rounded border border-dashed border-neutral-400 px-2 py-1 text-neutral-600 hover:bg-neutral-50"
          onClick={() => setAdding(true)}
        >
          + Add {hasRuns ? "another " : ""}run{hasRuns ? "" : " (e.g. a different temperature)"}
        </button>
      )}
    </div>
  );
}
