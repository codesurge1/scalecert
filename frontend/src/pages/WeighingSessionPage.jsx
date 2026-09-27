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
 * The Weighing test page proper — reached only from the session overview's
 * "Start"/"Open" button, never straight from an instrument (CLAUDE.md-level
 * navigation rule for this task: verification_type is chosen once, at
 * session creation, not here). Fetches the session, instrument, generated
 * load sequence, and the session's Weighing runs (feat/test-runs-conditions)
 * in parallel; readings and cross-run comparison are fetched separately,
 * keyed by the currently selected run, so a refresh reconstructs the form
 * instead of losing progress.
 */
export function WeighingSessionPage() {
  const { id } = useParams();
  const authSession = useAuthSession();

  // undefined = loading, null = load failed, object/array = loaded.
  const [session, setSession] = useState(undefined);
  const [instrument, setInstrument] = useState(undefined);
  const [sequence, setSequence] = useState(undefined);
  const [runs, setRuns] = useState(undefined);
  const [error, setError] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);

  // Runs/conditions (feat/test-runs-conditions). `null` is the implicit
  // default/only run — the exact behavior every session had before runs
  // existed — never a real `test_runs` row itself.
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
        return Promise.all([
          apiFetch(`/instruments/${sessionData.instrument_id}`),
          apiFetch(`/sessions/${id}/weighing/sequence`),
          apiFetch(`/sessions/${id}/weighing/runs`),
        ]);
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

  // Each run has its own independent set of readings — refetched whenever
  // the selected run changes. `selectedRunId === null` (the default case,
  // and the only case for every session that never grows a second run)
  // omits `run_id` entirely, the exact pre-existing query.
  useEffect(() => {
    if (session == null) return undefined;
    let cancelled = false;
    setReadingRecords(undefined);
    const query = selectedRunId ? `?run_id=${encodeURIComponent(selectedRunId)}` : "";
    apiFetch(`/sessions/${id}/weighing/readings${query}`)
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

  // Cross-run comparison (feat/test-runs-conditions): the currently
  // selected run against the default/Initial run. Nothing to compare when
  // viewing the default run itself (selectedRunId === null) — that's the
  // baseline, not a second run.
  useEffect(() => {
    if (session == null || selectedRunId === null) {
      setComparison(null);
      return undefined;
    }
    let cancelled = false;
    apiFetch(`/sessions/${id}/weighing/runs/compare?run_id_b=${encodeURIComponent(selectedRunId)}`)
      .then((data) => {
        if (!cancelled) setComparison(data);
      })
      .catch((err) => {
        if (!cancelled) toast.error(`Couldn't load the run comparison: ${err.message}`);
      });
    return () => {
      cancelled = true;
    };
  }, [id, session, selectedRunId, reloadKey]);

  async function handleCreateRun(runLabel, conditions) {
    const newRun = await apiFetch(`/sessions/${id}/weighing/runs`, {
      method: "POST",
      body: { run_label: runLabel, conditions },
    });
    setRuns((prev) => [...(prev ?? []), newRun]);
    setSelectedRunId(newRun.id);
    return newRun;
  }

  if (session === undefined) {
    return (
      <div className="grid gap-2">
        <FocusedPageHeader title="Weighing" sessionId={id} />
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
        <FocusedPageHeader title="Weighing" sessionId={id} />
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

  const loadingTable = sequence === undefined || runs === undefined || readingRecords === undefined;

  return (
    // `lg:flex lg:h-full lg:min-h-0 lg:flex-col` — matches FocusedShell's
    // `lg:` height-constrained frame (docs/architecture.md): at `lg`+ this
    // column gets a real, definite height from `<main>`, and hands its own
    // remaining height down to the `lg:min-h-0 lg:flex-1` wrapper around
    // `WeighingFormTable` below — the chain that lets the table's own row
    // area be the one thing that scrolls, instead of the page. Below `lg`,
    // plain `grid` stacking with normal page scroll, unchanged.
    <div className="grid gap-2 lg:flex lg:h-full lg:min-h-0 lg:flex-col">
      <FocusedPageHeader title="Weighing" sessionId={id} />

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
      ) : (
        <div className="lg:min-h-0 lg:flex-1 lg:overflow-hidden">
          {/* Keyed by the selected run: switching runs remounts the table
              (and useWeighingReadings' cell state) from that run's own
              freshly-fetched readingRecords, rather than trying to
              in-place resync a hook whose whole design assumes it seeds
              its state once, from whatever readings it was handed. */}
          <WeighingFormTable
            key={selectedRunId ?? "default"}
            sessionId={id}
            sessionStatus={session.status}
            instrument={instrument}
            sequence={sequence}
            verificationType={session.verification_type}
            observerDefault={authSession?.user?.email}
            initialReadings={readingRecords}
            actorId={authSession?.user?.id}
            runId={selectedRunId}
            runs={runs}
            selectedRunId={selectedRunId}
            onSelectRun={setSelectedRunId}
            onCreateRun={handleCreateRun}
            comparison={comparison}
          />
        </div>
      )}
    </div>
  );
}
