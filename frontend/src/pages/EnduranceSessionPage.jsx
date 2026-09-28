import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { toast } from "sonner";
import { apiFetch } from "@/lib/api";
import { useSession as useAuthSession } from "@/lib/supabase";
import { FocusedPageHeader } from "@/components/AppShell";
import { WeighingFormTable } from "@/components/weighing/WeighingFormTable";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";

/**
 * b) Performance of the test (R76-2 page 47) — the cycling step between
 * Endurance's Initial and Final runs. Purely recorded, never computed
 * (there is no formula — the instrument is simply cycled N times under a
 * load), so this writes straight to the Final run's own `conditions` via
 * `PATCH .../endurance/cycling` (feat/damp-heat-endurance, ADR-0011) — the
 * server derives which run that is, this component never needs a run id.
 * Local-editable-then-saved rather than local-only-and-lost-on-reload
 * (unlike the other OIML header fields still tracked as a known gap) —
 * this one has somewhere real to live.
 */
function CyclingStepCard({ sessionId, initialConditions, disabled, onSaved }) {
  const [numberOfLoadings, setNumberOfLoadings] = useState(initialConditions?.number_of_loadings ?? "");
  const [loadApplied, setLoadApplied] = useState(initialConditions?.load_applied ?? "");
  const [saving, setSaving] = useState(false);

  async function save() {
    if (disabled || saving) return;
    setSaving(true);
    try {
      const body = {
        number_of_loadings: numberOfLoadings === "" ? null : Number(numberOfLoadings),
        load_applied: loadApplied === "" ? null : loadApplied,
      };
      const updated = await apiFetch(`/sessions/${sessionId}/endurance/cycling`, { method: "PATCH", body });
      onSaved?.(updated);
    } catch (err) {
      toast.error(`Couldn't save the cycling step: ${err.message}`);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card className="shrink-0">
      <CardContent className="flex flex-wrap items-end gap-4 py-3 text-sm">
        <span className="shrink-0 font-medium">b) Performance of the test:</span>
        <label className="grid gap-1">
          <span className="text-xs text-muted-foreground">Number of loadings</span>
          <input
            className="h-8 w-36 rounded border border-neutral-400 bg-transparent px-2 focus:outline-none focus:ring-1 focus:ring-inset focus:ring-neutral-900 disabled:opacity-60"
            inputMode="numeric"
            disabled={disabled}
            value={numberOfLoadings}
            onChange={(event) => setNumberOfLoadings(event.target.value)}
            onBlur={save}
          />
        </label>
        <label className="grid gap-1">
          <span className="text-xs text-muted-foreground">Load applied</span>
          <input
            className="h-8 w-36 rounded border border-neutral-400 bg-transparent px-2 focus:outline-none focus:ring-1 focus:ring-inset focus:ring-neutral-900 disabled:opacity-60"
            inputMode="decimal"
            disabled={disabled}
            value={loadApplied}
            onChange={(event) => setLoadApplied(event.target.value)}
            onBlur={save}
          />
        </label>
        {saving ? <span className="text-xs italic text-muted-foreground">Saving…</span> : null}
      </CardContent>
    </Card>
  );
}

/**
 * Endurance (clause 15, A.6, R76-2 pages 46-47) — TWO runs of the exact
 * same Weighing procedure (a) Initial, c) Final) around the non-computed
 * cycling step above, reusing `WeighingFormTable` verbatim per run (same
 * composition-over-duplication approach as `DampHeatSessionPage`). The
 * form's own extra column — durability error due to wear and tear,
 * `|Ec_initial - Ec_final|` — and its all-loads-must-pass verdict come
 * from `GET .../endurance/durability` (feat/test-runs-conditions'
 * compute_run_comparison/compute_durability_check, reused unmodified).
 */
export function EnduranceSessionPage() {
  const { id } = useParams();
  const authSession = useAuthSession();

  const [session, setSession] = useState(undefined);
  const [instrument, setInstrument] = useState(undefined);
  const [sequence, setSequence] = useState(undefined);
  const [runs, setRuns] = useState(undefined);
  const [error, setError] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);

  const [selectedRunId, setSelectedRunId] = useState(null);
  const [readingRecords, setReadingRecords] = useState(undefined);
  const [durability, setDurability] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setError(null);

    apiFetch(`/sessions/${id}`)
      .then((sessionData) => {
        if (cancelled) return undefined;
        setSession(sessionData);
        // POST .../endurance/setup auto-provisions the two fixed runs and
        // is draft-only (409s otherwise, db/schema.sql's runs_write
        // policy) — it may only fire while this session is draft. Viewing
        // a non-draft session (e.g. an approver) uses the read-only
        // GET .../endurance/runs listing instead, which never creates
        // anything — see docs/errors/ERROR_LOG.md.
        const runsFetch =
          sessionData.status === "draft"
            ? apiFetch(`/sessions/${id}/endurance/setup`, { method: "POST" })
            : apiFetch(`/sessions/${id}/endurance/runs`);
        return Promise.all([apiFetch(`/instruments/${sessionData.instrument_id}`), apiFetch(`/sessions/${id}/endurance/sequence`), runsFetch]);
      })
      .then((results) => {
        if (cancelled || !results) return;
        const [instrumentData, sequenceData, runsData] = results;
        setInstrument(instrumentData);
        setSequence(sequenceData);
        setRuns(runsData);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message);
          setSession(null);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [id, reloadKey]);

  // No implicit default run for Endurance — default to the first (a)
  // Initial) run once the fixed two are known.
  useEffect(() => {
    if (runs && runs.length > 0 && selectedRunId === null) {
      setSelectedRunId(runs[0].id);
    }
  }, [runs, selectedRunId]);

  useEffect(() => {
    if (session == null || selectedRunId === null) return undefined;
    let cancelled = false;
    setReadingRecords(undefined);
    apiFetch(`/sessions/${id}/endurance/readings?run_id=${encodeURIComponent(selectedRunId)}`)
      .then((data) => {
        if (!cancelled) setReadingRecords(data);
      })
      .catch((err) => {
        if (!cancelled) {
          toast.error(`Couldn't load this run's readings: ${err.message}`);
          setReadingRecords([]);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [id, session, selectedRunId, reloadKey]);

  // The durability check (all loads' |Ec_initial - Ec_final| <= mpe) —
  // shown regardless of which of the two runs is currently selected,
  // same reasoning as Damp heat's own comparison. 409 (runs not set up
  // yet) is expected before any reading exists on either run; not an error.
  useEffect(() => {
    if (session == null || !runs || runs.length < 2) {
      setDurability(null);
      return undefined;
    }
    let cancelled = false;
    apiFetch(`/sessions/${id}/endurance/durability`)
      .then((data) => {
        if (!cancelled) setDurability(data);
      })
      .catch(() => {
        if (!cancelled) setDurability(null);
      });
    return () => {
      cancelled = true;
    };
  }, [id, session, runs, reloadKey]);

  function handleCyclingSaved(updatedFinalRun) {
    setRuns((prev) => (prev ? prev.map((run) => (run.id === updatedFinalRun.id ? updatedFinalRun : run)) : prev));
  }

  if (session === undefined) {
    return (
      <div className="grid gap-2">
        <FocusedPageHeader title="Endurance" sessionId={id} />
        <div className="space-y-3">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-96 w-full" />
        </div>
      </div>
    );
  }

  if (session === null) {
    return (
      <div className="grid gap-2">
        <FocusedPageHeader title="Endurance" sessionId={id} />
        <Card className="border-destructive/50 bg-destructive/5">
          <CardContent className="flex items-center justify-between py-4 text-sm text-destructive">
            <span>Couldn't load this session: {error}</span>
            <Button variant="outline" size="sm" onClick={() => setReloadKey((key) => key + 1)}>
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // `runs` can legitimately settle at [] — a non-draft session viewed
  // read-only (e.g. by an approver) whose Endurance runs were never
  // provisioned (the technician never opened this page while it was still
  // draft) — that's "nothing recorded", not "still loading", so it gets
  // its own branch below rather than spinning forever waiting for a
  // `selectedRunId` that will never be set.
  const loadingTable = sequence === undefined || runs === undefined;
  const noRunsRecorded = runs?.length === 0;
  const finalRun = runs?.find((run) => run.ordinal === 1);
  const disabled = session.status !== "draft";

  return (
    <div className="grid gap-2 lg:flex lg:h-full lg:min-h-0 lg:flex-col">
      <FocusedPageHeader title="Endurance" sessionId={id} />

      {session.status !== "draft" ? (
        <p className="shrink-0 text-sm font-medium text-warning-foreground">
          This session is "{session.status}", not draft — the form below is read-only.
        </p>
      ) : null}

      {finalRun ? (
        <CyclingStepCard
          sessionId={id}
          initialConditions={finalRun.conditions}
          disabled={disabled}
          onSaved={handleCyclingSaved}
        />
      ) : null}

      {loadingTable ? (
        <Skeleton className="h-[600px] w-full" />
      ) : sequence.length === 0 ? (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            No load sequence could be generated for this instrument.
          </CardContent>
        </Card>
      ) : noRunsRecorded ? (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            No Endurance runs have been recorded for this session.
          </CardContent>
        </Card>
      ) : selectedRunId === null || readingRecords === undefined ? (
        <Skeleton className="h-[600px] w-full" />
      ) : (
        <div className="lg:min-h-0 lg:flex-1 lg:overflow-hidden">
          <WeighingFormTable
            key={selectedRunId}
            sessionId={id}
            apiPath="endurance"
            sessionStatus={session.status}
            instrument={instrument}
            sequence={sequence}
            verificationType={session.verification_type}
            observerDefault={authSession?.user?.email}
            initialReadings={readingRecords}
            actorId={authSession?.user?.id}
            runId={selectedRunId}
            runs={runs ?? []}
            selectedRunId={selectedRunId}
            onSelectRun={setSelectedRunId}
            showDefaultRunTab={false}
            comparison={durability?.comparisons}
            comparisonLabel="Initial compared to Final (durability error due to wear and tear)"
            durabilityVerdict={durability ? { allPassed: durability.all_passed } : undefined}
          />
        </div>
      )}
    </div>
  );
}
