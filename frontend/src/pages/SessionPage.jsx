import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/AppShell";
import { AddTestDialog } from "@/components/session/AddTestDialog";
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

// The four tests with working forms today — each listed directly on the
// overview with live status, same treatment Weighing alone used to get.
// Status for every one of them is derived purely from what's actually been
// submitted (readings-GET), never from a session_test_selection row (only
// Weighing has one, created unconditionally at session creation) — so none
// of this needs the per-session test selector (docs/plan.md Phase 3) to
// work.
const IMPLEMENTED_ROWS = TEST_ROWS.filter((row) => row.route);

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
 * now true for Zero/tare, Repeatability, and Eccentricity, purely because
 * they have real data to derive status from, not because they have
 * selection rows. The dialog is the discovery surface for the full 7-item
 * checklist, where these four are selectable and the remaining three show
 * their N/A reason or "Coming soon". The verification_type was already
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

  // undefined = loading, null = load failed, object/array = loaded.
  const [session, setSession] = useState(undefined);
  const [instrument, setInstrument] = useState(undefined);
  const [weighingSequence, setWeighingSequence] = useState(undefined);
  const [weighingReadings, setWeighingReadings] = useState(undefined);
  const [zeroTareChecks, setZeroTareChecks] = useState(undefined);
  const [zeroTareReadings, setZeroTareReadings] = useState(undefined);
  const [repeatabilitySeries, setRepeatabilitySeries] = useState(undefined);
  const [eccentricityReadings, setEccentricityReadings] = useState(undefined);
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
        ]);
      })
      .then((results) => {
        if (cancelled || !results) return;
        const [instrumentData, sequenceData, weighingReadingsData, checksData, zeroTareReadingsData, seriesData, eccentricityReadingsData] = results;
        setInstrument(instrumentData);
        setWeighingSequence(sequenceData);
        setWeighingReadings(weighingReadingsData);
        setZeroTareChecks(checksData);
        setZeroTareReadings(zeroTareReadingsData);
        setRepeatabilitySeries(seriesData);
        setEccentricityReadings(eccentricityReadingsData);
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

  const PROGRESS_BY_KEY = {
    weighing: weighingProgress,
    zero_tare: zeroTareProgress,
    repeatability: repeatabilityProgress,
    eccentricity: eccentricityProgress,
  };

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
              {/* Once a real per-session test selector exists (docs/plan.md
                  Phase 3), this row list will reflect whatever's actually
                  been added via session_test_selection rows for the
                  remaining three test_types too, not just these four. */}
              {IMPLEMENTED_ROWS.map((row) => {
                const progress = PROGRESS_BY_KEY[row.key];
                return (
                  <TableRow key={row.key}>
                    <TableCell>
                      <div className="font-medium">{row.label}</div>
                      <div className="text-xs text-muted-foreground">{row.clause}</div>
                    </TableCell>
                    <TableCell>
                      <TestStatusBadge status={progress.status} verdict={progress.verdict} />
                    </TableCell>
                    <TableCell className="text-right">
                      <Button asChild size="sm" variant={progress.status === "not_started" ? "default" : "outline"}>
                        <Link to={row.route(id)}>{progress.status === "not_started" ? "Start" : "Open"}</Link>
                      </Button>
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
