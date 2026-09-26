import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/AppShell";
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

// The OIML clause 8.3.3 seven-item checklist (CLAUDE.md). Only Weighing has
// a working form so far; `zero_tare` has no own `test_type` in the schema
// yet — it's tracked as a Weighing variant (docs/plan.md Phase 3) — so it's
// shown here for completeness but is never itself "startable". The other
// five map onto real `test_type` values that will get their own forms in
// later tasks; applicability for the conditional three is computed from the
// instrument here rather than from `session_test_selections`, since no
// selection rows are created for them yet (only `weighing` is, at session
// creation) — the per-session test selector is a later task (docs/plan.md
// Phase 3), not built here.
const TEST_ROWS = [
  { key: "weighing", label: "Weighing", clause: "A.4.4 / A.5.3.1" },
  {
    key: "zero_tare",
    label: "Zero / tare device accuracy",
    clause: "A.4.4 variant",
    note: "Tracked as part of Weighing in this build — not yet its own form.",
  },
  { key: "repeatability", label: "Repeatability", clause: "A.4.5" },
  { key: "eccentricity", label: "Eccentricity (3.1 weights)", clause: "A.4.6" },
  {
    key: "discrimination",
    label: "Discrimination",
    clause: "A.4.8",
    naReason: (instrument) => (instrument.indication_type === "digital" ? "N/A — digital instrument" : null),
  },
  {
    key: "tilting",
    label: "Tilting",
    clause: "A.5.1.3",
    naReason: (instrument) => (!instrument.is_mobile ? "N/A — mobile instruments only" : null),
  },
  {
    key: "sensitivity",
    label: "Sensitivity",
    clause: "A.4.9",
    naReason: (instrument) =>
      instrument.indication_type !== "non_self_indicating" ? "N/A — non-self-indicating instruments only" : null,
  },
];

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
    case "na":
      return (
        <Badge variant="outline" className="text-muted-foreground">
          N/A
        </Badge>
      );
    case "not_available":
      return (
        <Badge variant="outline" className="text-muted-foreground">
          Not yet available
        </Badge>
      );
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
 * test page. Shows the 7-item checklist with status/applicability and a
 * Start/Open button — only Weighing's does anything yet. Replaces the old
 * behavior where opening a session jumped straight into the Weighing table;
 * the verification_type was already chosen once, at session creation
 * (StartVerificationDialog), never re-asked here.
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
          <Skeleton className="h-64 w-full" />
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
          OIML clause 8.3.3 verification checklist
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
              {TEST_ROWS.map((row) => {
                const naReason = instrument && row.naReason ? row.naReason(instrument) : null;
                const isWeighing = row.key === "weighing";
                const status = naReason
                  ? "na"
                  : isWeighing
                    ? weighingProgress.status
                    : "not_available";
                const startLabel = weighingProgress.status === "not_started" ? "Start" : "Open";

                return (
                  <TableRow key={row.key}>
                    <TableCell>
                      <div className="font-medium">{row.label}</div>
                      <div className="text-xs text-muted-foreground">
                        {naReason || row.note || row.clause}
                      </div>
                    </TableCell>
                    <TableCell>
                      <TestStatusBadge status={status} verdict={weighingProgress.verdict} />
                    </TableCell>
                    <TableCell className="text-right">
                      {isWeighing ? (
                        <Button asChild size="sm" variant={weighingProgress.status === "not_started" ? "default" : "outline"}>
                          <Link to={`/sessions/${id}/weighing`}>{startLabel}</Link>
                        </Button>
                      ) : (
                        <Button size="sm" variant="outline" disabled>
                          {naReason ? "N/A" : "Coming soon"}
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
