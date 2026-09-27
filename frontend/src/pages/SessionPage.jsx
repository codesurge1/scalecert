import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiFetch } from "@/lib/api";
import { useSession as useAuthSession } from "@/lib/supabase";
import { useProfile } from "@/hooks/useProfile";
import { PageHeader } from "@/components/AppShell";
import { AddTestDialog } from "@/components/session/AddTestDialog";
import { SessionLifecyclePanel } from "@/components/session/SessionLifecyclePanel";
import { TEST_ROWS } from "@/lib/testChecklist";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const VERIFICATION_TYPE_LABELS = {
  initial: "Initial verification",
  subsequent: "Subsequent verification",
  in_service: "In-service verification",
};

function StatusBadge({ status }) {
  const variant = status === "draft" ? "secondary" : status === "issued" || status === "approved" ? "success" : "outline";
  return <Badge variant={variant} className="capitalize">{status}</Badge>;
}

// A single shared progress shape for every implemented test: given how many
// of `total` expected readings/positions/series-slots are in and whether
// everything submitted so far passed, derive Not started / In progress /
// Complete Pass-Fail. `total === undefined` means still loading.
function computeProgress(total, completedCount, allPassed) {
  if (total === undefined) return { status: "loading" };
  if (completedCount === 0) return { status: "not_started" };
  if (completedCount < total) return { status: "in_progress", completed: completedCount, total };
  return { status: "complete", verdict: allPassed ? "PASS" : "FAIL" };
}

function TestStatusBadge({ status, verdict }) {
  switch (status) {
    case "loading":
      return <Skeleton className="h-5 w-24" />;
    case "na":
      return <Badge variant="outline">N/A</Badge>;
    case "not_started":
      return <Badge variant="outline">Not started</Badge>;
    case "in_progress":
      return <Badge variant="warning">In progress</Badge>;
    case "complete":
      return (
        <Badge variant={verdict === "PASS" ? "success" : "destructive"}>
          Complete — {verdict === "PASS" ? "Pass" : "Fail"}
        </Badge>
      );
    default:
      return null;
  }
}

/**
 * The session overview: instrument -> instrument detail -> THIS PAGE -> a
 * test page, via "Add test" (AddTestDialog) -> pick from the 7 -> that
 * test's table opens. Weighing is always already "added" the moment a
 * session exists (its session_test_selection row is created unconditionally
 * at session creation, docs/architecture.md), so it's listed here directly
 * with live status rather than waiting for a redundant pick; the same is
 * now true for every other test, purely because each has real data to
 * derive status from, not because any of them (Weighing aside) has a
 * session_test_selection row. All seven checklist rows are shown here now
 * (not just the "implemented" subset) — a row whose naReason(instrument)
 * is truthy shows "N/A" instead of a Start/Open button; every other row
 * shows live status. The dialog remains the discovery surface with the
 * same N/A/"Coming soon" distinctions. The verification_type was already
 * chosen once, at session creation (StartVerificationDialog), never
 * re-asked here.
 *
 * No forced sequence (docs/architecture.md, RRSL-confirmed): every
 * Start/Open button below is always enabled and each test's own status
 * (Not started/In progress/Complete) is shown purely for information —
 * nothing here ever reads another test's status to decide a button's
 * enabled state.
 */
export function SessionPage() {
  const { id } = useParams();
  const authSession = useAuthSession();
  const profile = useProfile(authSession);

  // undefined = loading, null = load failed, object/array = loaded.
  const [session, setSession] = useState(undefined);
  const [instrument, setInstrument] = useState(undefined);
  const [weighingSequence, setWeighingSequence] = useState(undefined);
  const [weighingReadings, setWeighingReadings] = useState(undefined);
  const [zeroTareChecks, setZeroTareChecks] = useState(undefined);
  const [zeroTareReadings, setZeroTareReadings] = useState(undefined);
  const [repeatabilitySeries, setRepeatabilitySeries] = useState(undefined);
  const [eccentricityReadings, setEccentricityReadings] = useState(undefined);
  const [discriminationChecks, setDiscriminationChecks] = useState(undefined);
  const [discriminationReadings, setDiscriminationReadings] = useState(undefined);
  const [sensitivityChecks, setSensitivityChecks] = useState(undefined);
  const [sensitivityReadings, setSensitivityReadings] = useState(undefined);
  const [tiltingState, setTiltingState] = useState(undefined);
  const [error, setError] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);

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
          apiFetch(`/sessions/${id}/weighing/readings`),
          apiFetch(`/sessions/${id}/zero-tare/checks`),
          apiFetch(`/sessions/${id}/zero-tare/readings`),
          apiFetch(`/sessions/${id}/repeatability/readings`),
          apiFetch(`/sessions/${id}/eccentricity/readings`),
          apiFetch(`/sessions/${id}/discrimination/checks`),
          apiFetch(`/sessions/${id}/discrimination/readings`),
          apiFetch(`/sessions/${id}/sensitivity/checks`),
          apiFetch(`/sessions/${id}/sensitivity/readings`),
          apiFetch(`/sessions/${id}/tilting/readings`),
        ]);
      })
      .then((results) => {
        if (cancelled || !results) return;
        const [
          instrumentData,
          sequenceData,
          weighingReadingsData,
          checksData,
          zeroTareReadingsData,
          seriesData,
          eccentricityReadingsData,
          discriminationChecksData,
          discriminationReadingsData,
          sensitivityChecksData,
          sensitivityReadingsData,
          tiltingStateData,
        ] = results;
        setInstrument(instrumentData);
        setWeighingSequence(sequenceData);
        setWeighingReadings(weighingReadingsData);
        setZeroTareChecks(checksData);
        setZeroTareReadings(zeroTareReadingsData);
        setRepeatabilitySeries(seriesData);
        setEccentricityReadings(eccentricityReadingsData);
        setDiscriminationChecks(discriminationChecksData);
        setDiscriminationReadings(discriminationReadingsData);
        setSensitivityChecks(sensitivityChecksData);
        setSensitivityReadings(sensitivityReadingsData);
        setTiltingState(tiltingStateData);
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

  const weighingProgress = useMemo(() => {
    const total = weighingSequence ? weighingSequence.length * 2 : undefined; // every load, both directions
    return computeProgress(total, weighingReadings?.length ?? 0, weighingReadings?.every((r) => r.passed));
  }, [weighingSequence, weighingReadings]);

  const zeroTareProgress = useMemo(() => {
    const total = zeroTareChecks ? zeroTareChecks.length : undefined;
    return computeProgress(total, zeroTareReadings?.length ?? 0, zeroTareReadings?.every((r) => r.passed));
  }, [zeroTareChecks, zeroTareReadings]);

  const repeatabilityProgress = useMemo(() => {
    if (!repeatabilitySeries) return { status: "loading" };
    const total = 20; // 10 readings x 2 series
    const completedCount = repeatabilitySeries.reduce((sum, s) => sum + s.readings.length, 0);
    return computeProgress(total, completedCount, repeatabilitySeries.every((s) => s.passed === true));
  }, [repeatabilitySeries]);

  const eccentricityProgress = useMemo(() => {
    const total = eccentricityReadings ? 4 : undefined;
    return computeProgress(total, eccentricityReadings?.length ?? 0, eccentricityReadings?.every((r) => r.passed));
  }, [eccentricityReadings]);

  const discriminationProgress = useMemo(() => {
    const total = discriminationChecks ? discriminationChecks.length : undefined;
    return computeProgress(total, discriminationReadings?.length ?? 0, discriminationReadings?.every((r) => r.passed));
  }, [discriminationChecks, discriminationReadings]);

  const sensitivityProgress = useMemo(() => {
    const total = sensitivityChecks ? sensitivityChecks.length : undefined;
    return computeProgress(total, sensitivityReadings?.length ?? 0, sensitivityReadings?.every((r) => r.passed));
  }, [sensitivityChecks, sensitivityReadings]);

  const tiltingProgress = useMemo(() => {
    if (!tiltingState) return { status: "loading" };
    const total = 15; // 3 phases x 5 positions
    return computeProgress(total, tiltingState.readings.length, tiltingState.passed === true);
  }, [tiltingState]);

  const PROGRESS_BY_KEY = {
    weighing: weighingProgress,
    zero_tare: zeroTareProgress,
    repeatability: repeatabilityProgress,
    eccentricity: eccentricityProgress,
    discrimination: discriminationProgress,
    sensitivity: sensitivityProgress,
    tilting: tiltingProgress,
  };

  // Submit-for-review is only meaningfully offered once at least one test
  // has SOME recorded progress — the server is the actual source of truth
  // (409 "no test has recorded" otherwise, app/services/sessions.py), this
  // is just a friendlier disabled state instead of a round-trip error.
  const hasAnyProgress = Object.values(PROGRESS_BY_KEY).some(
    (p) => p.status === "in_progress" || p.status === "complete",
  );
  const canSubmit = hasAnyProgress;
  const submitBlockedReason = "Complete at least one test before submitting for review.";

  if (session === undefined) {
    return (
      <div>
        <PageHeader title="Session overview" />
        <div className="space-y-3">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      </div>
    );
  }

  if (session === null) {
    return (
      <div>
        <PageHeader title="Session overview" />
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

  return (
    <div className="grid gap-6">
      <div>
        <Link
          to={`/instruments/${session.instrument_id}`}
          className="text-sm text-muted-foreground hover:text-foreground hover:underline"
        >
          &larr; {instrument === undefined ? "Instrument" : instrument?.type_designation || "Instrument"}
        </Link>
        <PageHeader
          title="Session overview"
          description={VERIFICATION_TYPE_LABELS[session.verification_type] ?? session.verification_type}
          actions={instrument === undefined ? null : <AddTestDialog sessionId={id} instrument={instrument} />}
        />
      </div>

      <Card>
        <CardContent className="grid grid-cols-2 gap-4 py-4 sm:grid-cols-4">
          <div>
            <div className="text-xs text-muted-foreground">Instrument</div>
            <div className="text-sm font-medium">
              {instrument === undefined ? (
                <Skeleton className="h-4 w-24" />
              ) : (
                instrument?.type_designation || instrument?.model || "—"
              )}
            </div>
          </div>
          <div>
            <div className="text-xs text-muted-foreground">Class / e / Max</div>
            <div className="text-sm font-medium">
              {instrument === undefined ? (
                <Skeleton className="h-4 w-24" />
              ) : (
                `Class ${instrument.accuracy_class} · e=${instrument.e_value}g · Max=${instrument.max_capacity}g`
              )}
            </div>
          </div>
          <div>
            <div className="text-xs text-muted-foreground">Status</div>
            <div className="mt-0.5">
              <StatusBadge status={session.status} />
            </div>
          </div>
          <div>
            <div className="text-xs text-muted-foreground">Verification type</div>
            <div className="text-sm font-medium">
              {VERIFICATION_TYPE_LABELS[session.verification_type] ?? session.verification_type}
            </div>
          </div>
        </CardContent>
      </Card>

      {profile ? (
        <SessionLifecyclePanel
          session={session}
          profile={profile}
          canSubmit={canSubmit}
          submitBlockedReason={submitBlockedReason}
          onChanged={(updated) => setSession(updated)}
        />
      ) : null}

      <div>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Tests added to this session
        </h2>
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Test</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {/* All seven checklist rows, always. A row's naReason
                  (instrument-driven, never session/progress state — the
                  no-forced-sequence guardrail) decides N/A vs. live status;
                  once a real per-session test selector exists
                  (docs/plan.md Phase 3), this can additionally reflect
                  session_test_selection rows, but doesn't need to for any
                  of this to work today. */}
              {TEST_ROWS.map((row) => {
                const naReason = instrument && row.naReason ? row.naReason(instrument) : null;
                const progress = naReason ? { status: "na" } : PROGRESS_BY_KEY[row.key];
                return (
                  <TableRow key={row.key}>
                    <TableCell>
                      <div className="font-medium">{row.label}</div>
                      <div className="text-xs text-muted-foreground">{naReason || row.clause}</div>
                    </TableCell>
                    <TableCell>
                      <TestStatusBadge status={progress.status} verdict={progress.verdict} />
                    </TableCell>
                    <TableCell className="text-right">
                      {naReason ? null : (
                        <Button asChild size="sm" variant={progress.status === "not_started" ? "default" : "outline"}>
                          <Link to={row.route(id)}>{progress.status === "not_started" ? "Start" : "Open"}</Link>
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </Card>
      </div>
    </div>
  );
}
