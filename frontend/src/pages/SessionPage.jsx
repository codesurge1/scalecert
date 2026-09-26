import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/AppShell";
import { LoadSequenceTable } from "@/components/weighing/LoadSequenceTable";
import { ReadingEntryPanel } from "@/components/weighing/ReadingEntryPanel";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";

const VERIFICATION_TYPE_LABELS = {
  initial: "Initial verification",
  subsequent: "Subsequent verification",
  in_service: "In-service verification",
};

function StatusBadge({ status }) {
  const variant = status === "draft" ? "secondary" : status === "issued" || status === "approved" ? "success" : "outline";
  return <Badge variant={variant} className="capitalize">{status}</Badge>;
}

export function SessionPage() {
  const { id } = useParams();

  // undefined = loading, null = load failed, object = loaded.
  const [session, setSession] = useState(undefined);
  const [instrument, setInstrument] = useState(undefined);
  const [sequence, setSequence] = useState(undefined);
  const [error, setError] = useState(null);

  // Readings recorded THIS page load, keyed "<sequence_no>-<direction>".
  // There is no GET .../weighing/readings list route yet (a later task) —
  // the API only supports submitting one, not listing what's already been
  // submitted — so a page refresh currently loses this table. Noted in
  // docs/architecture.md rather than worked around here.
  const [readingsByKey, setReadingsByKey] = useState({});
  const [selectedSeq, setSelectedSeq] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setError(null);

    Promise.all([apiFetch(`/sessions/${id}`), apiFetch(`/sessions/${id}/weighing/sequence`)])
      .then(([sessionData, sequenceData]) => {
        if (cancelled) return;
        setSession(sessionData);
        setSequence(sequenceData);
        setSelectedSeq((current) => current ?? sequenceData[0]?.sequence_no ?? null);
        return apiFetch(`/instruments/${sessionData.instrument_id}`);
      })
      .then((instrumentData) => {
        if (!cancelled && instrumentData) setInstrument(instrumentData);
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

  const selectedEntry = useMemo(
    () => sequence?.find((entry) => entry.sequence_no === selectedSeq) ?? null,
    [sequence, selectedSeq],
  );

  function handleSubmitted(sequenceNo, direction, result) {
    setReadingsByKey((prev) => ({ ...prev, [`${sequenceNo}-${direction}`]: result }));
  }

  if (session === undefined) {
    return (
      <div>
        <PageHeader title="Verification session" />
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
        <PageHeader title="Verification session" />
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

  const weighingSelection = session.test_selections?.find((selection) => selection.test_type === "weighing");

  return (
    <div className="grid gap-6">
      <PageHeader
        title="Verification session"
        description={VERIFICATION_TYPE_LABELS[session.verification_type] ?? session.verification_type}
      />

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
            <div className="text-xs text-muted-foreground">Selected tests</div>
            <div className="mt-0.5">
              {weighingSelection ? (
                <Badge variant="secondary">Weighing</Badge>
              ) : (
                <span className="text-sm text-muted-foreground">None</span>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {sequence === undefined ? (
        <Skeleton className="h-64 w-full" />
      ) : sequence.length === 0 ? (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            No load sequence could be generated for this instrument.
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-6 lg:grid-cols-2">
          <LoadSequenceTable
            sequence={sequence}
            readingsByKey={readingsByKey}
            selected={selectedEntry}
            onSelect={setSelectedSeq}
          />
          <ReadingEntryPanel
            sessionId={id}
            sessionStatus={session.status}
            entry={selectedEntry}
            onSubmitted={handleSubmitted}
          />
        </div>
      )}
    </div>
  );
}
