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

const WEIGHING_ROW = TEST_ROWS.find((row) => row.key === "weighing");

function StatusBadge({ status }) {
  const variant = status === "draft" ? "secondary" : status === "issued" || status === "approved" ? "success" : "outline";
  return <Badge variant={variant} className="capitalize">{status}</Badge>;
}

function computeWeighingProgress(sequence, records) {
  if (!sequence || !records) return { status: "loading" };
  if (records.length === 0) return { status: "not_started" };
  const total = sequence.length * 2; // every load, both directions
  if (records.length < total) return { status: "in_progress", completed: records.length, total };
  const allPassed = records.every((record) => record.passed);
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
 * with live status rather than waiting for a redundant pick; the dialog is
 * the discovery surface for the full 7-item checklist, where only Weighing
 * is actually selectable today. The verification_type was already chosen
 * once, at session creation (StartVerificationDialog), never re-asked here.
 */
export function SessionPage() {
  const { id } = useParams();

  // undefined = loading, null = load failed, object/array = loaded.
  const [session, setSession] = useState(undefined);
  const [instrument, setInstrument] = useState(undefined);
  const [sequence, setSequence] = useState(undefined);
  const [readingRecords, setReadingRecords] = useState(undefined);
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
        ]);
      })
      .then((results) => {
        if (cancelled || !results) return;
        const [instrumentData, sequenceData, readingsData] = results;
        setInstrument(instrumentData);
        setSequence(sequenceData);
        setReadingRecords(readingsData);
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

  const weighingProgress = useMemo(
    () => computeWeighingProgress(sequence, readingRecords),
    [sequence, readingRecords],
  );

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
              {/* Weighing is always already added — its session_test_selection
                  row is created unconditionally at session creation, so it's
                  never in a genuine "not yet added" state. Once a real
                  per-session test selector exists (docs/plan.md Phase 3),
                  this row list will reflect whatever's actually been added,
                  not just Weighing unconditionally. */}
              <TableRow>
                <TableCell>
                  <div className="font-medium">{WEIGHING_ROW.label}</div>
                  <div className="text-xs text-muted-foreground">{WEIGHING_ROW.clause}</div>
                </TableCell>
                <TableCell>
                  <TestStatusBadge status={weighingProgress.status} verdict={weighingProgress.verdict} />
                </TableCell>
                <TableCell className="text-right">
                  <Button asChild size="sm" variant={weighingProgress.status === "not_started" ? "default" : "outline"}>
                    <Link to={`/sessions/${id}/weighing`}>
                      {weighingProgress.status === "not_started" ? "Start" : "Open"}
                    </Link>
                  </Button>
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </Card>
      </div>
    </div>
  );
}
