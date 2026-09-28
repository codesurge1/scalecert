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
 * Damp heat, steady state (clause 13, B.2, R76-2 pages 37-39) — THREE runs
 * of the exact same Weighing procedure under different conditions (a)
 * Initial at reference temperature, b) high temperature + 85% RH, c)
 * Final at reference temperature), reusing `WeighingFormTable` verbatim
 * per run (feat/test-runs-conditions' runs/conditions infrastructure,
 * feat/damp-heat-endurance's own use of it) rather than a new form
 * component — same computation, same table, just three labelled runs
 * instead of Weighing's own optional ones.
 *
 * `POST .../damp-heat/setup` is called once on load (idempotent — a
 * no-op once all three runs already exist) so the three fixed runs are
 * always there before the technician needs to pick one; there is no
 * "Initial" implicit default run here (unlike Weighing) — every reading
 * belongs to one of the three, so the first fetched run is selected by
 * default rather than `null`.
 */
export function DampHeatSessionPage() {
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
  const [comparison, setComparison] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setError(null);

    apiFetch(`/sessions/${id}`)
      .then((sessionData) => {
        if (cancelled) return undefined;
        setSession(sessionData);
        // POST .../damp-heat/setup auto-provisions the three fixed runs
        // and is draft-only (409s otherwise, db/schema.sql's runs_write
        // policy) — it may only fire while this session is draft. Viewing
        // a non-draft session (e.g. an approver) uses the read-only
        // GET .../damp-heat/runs listing instead, which never creates
        // anything — see docs/errors/ERROR_LOG.md.
        const runsFetch =
          sessionData.status === "draft"
            ? apiFetch(`/sessions/${id}/damp-heat/setup`, { method: "POST" })
            : apiFetch(`/sessions/${id}/damp-heat/runs`);
        return Promise.all([apiFetch(`/instruments/${sessionData.instrument_id}`), apiFetch(`/sessions/${id}/damp-heat/sequence`), runsFetch]);
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

  // No implicit default run for Damp heat — default to the first (a)
  // Initial) run once the fixed three are known.
  useEffect(() => {
    if (runs && runs.length > 0 && selectedRunId === null) {
      setSelectedRunId(runs[0].id);
    }
  }, [runs, selectedRunId]);

  useEffect(() => {
    if (session == null || selectedRunId === null) return undefined;
    let cancelled = false;
    setReadingRecords(undefined);
    apiFetch(`/sessions/${id}/damp-heat/readings?run_id=${encodeURIComponent(selectedRunId)}`)
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

  // Informational cross-run comparison (Initial vs Final) — shown
  // regardless of which of the three runs is currently selected, since
  // it's the a)-vs-c) drift the form's own reasoning cares about, not a
  // property of "the currently viewed run" the way Weighing's own
  // optional-run comparison is.
  useEffect(() => {
    if (session == null || !runs || runs.length < 3) {
      setComparison(null);
      return undefined;
    }
    let cancelled = false;
    const runIdA = runs[0].id;
    const runIdC = runs[2].id;
    apiFetch(`/sessions/${id}/damp-heat/runs/compare?run_id_a=${encodeURIComponent(runIdA)}&run_id_b=${encodeURIComponent(runIdC)}`)
      .then((data) => {
        if (!cancelled) setComparison(data);
      })
      .catch((err) => {
        if (!cancelled) toast.error(`Couldn't load the run comparison: ${err.message}`);
      });
    return () => {
      cancelled = true;
    };
  }, [id, session, runs, reloadKey]);

  if (session === undefined) {
    return (
      <div className="grid gap-2">
        <FocusedPageHeader title="Damp heat, steady state" sessionId={id} />
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
        <FocusedPageHeader title="Damp heat, steady state" sessionId={id} />
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
  // read-only (e.g. by an approver) whose Damp heat runs were never
  // provisioned (the technician never opened this page while it was
  // still draft) — that's "nothing recorded", not "still loading", so it
  // gets its own branch below rather than spinning forever waiting for a
  // `selectedRunId` that will never be set.
  const loadingTable = sequence === undefined || runs === undefined;
  const noRunsRecorded = runs?.length === 0;

  return (
    <div className="grid gap-2 lg:flex lg:h-full lg:min-h-0 lg:flex-col">
      <FocusedPageHeader title="Damp heat, steady state" sessionId={id} />

      {session.status !== "draft" ? (
        <p className="shrink-0 text-sm font-medium text-warning-foreground">
          This session is "{session.status}", not draft — the form below is read-only.
        </p>
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
            No Damp heat runs have been recorded for this session.
          </CardContent>
        </Card>
      ) : selectedRunId === null || readingRecords === undefined ? (
        <Skeleton className="h-[600px] w-full" />
      ) : (
        <div className="lg:min-h-0 lg:flex-1 lg:overflow-hidden">
          <WeighingFormTable
            key={selectedRunId}
            sessionId={id}
            apiPath="damp-heat"
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
            comparison={comparison}
            comparisonLabel="Initial compared to Final"
          />
        </div>
      )}
    </div>
  );
}
