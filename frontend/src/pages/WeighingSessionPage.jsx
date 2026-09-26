import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiFetch } from "@/lib/api";
import { useSession as useAuthSession } from "@/lib/supabase";
import { PageHeader } from "@/components/AppShell";
import { WeighingFormTable } from "@/components/weighing/WeighingFormTable";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";

/**
 * The Weighing test page proper — reached only from the session overview's
 * "Start"/"Open" button, never straight from an instrument (CLAUDE.md-level
 * navigation rule for this task: verification_type is chosen once, at
 * session creation, not here). Fetches the session, instrument, generated
 * load sequence, and every already-submitted reading in parallel, so a
 * refresh reconstructs the form instead of losing progress.
 */
export function WeighingSessionPage() {
  const { id } = useParams();
  const authSession = useAuthSession();

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

  if (session === undefined) {
    return (
      <div>
        <PageHeader title="Weighing" />
        <div className="space-y-3">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-96 w-full" />
        </div>
      </div>
    );
  }

  if (session === null) {
    return (
      <div>
        <PageHeader title="Weighing" />
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

  const loadingTable = sequence === undefined || readingRecords === undefined;

  return (
    <div className="grid gap-4">
      <Link
        to={`/sessions/${id}`}
        className="text-sm text-muted-foreground hover:text-foreground hover:underline"
      >
        &larr; Session overview
      </Link>
      <PageHeader title="Weighing" />

      {session.status !== "draft" ? (
        <p className="text-sm font-medium text-warning-foreground">
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
        <WeighingFormTable
          sessionId={id}
          sessionStatus={session.status}
          instrument={instrument}
          sequence={sequence}
          observerDefault={authSession?.user?.email}
          initialReadings={readingRecords}
        />
      )}
    </div>
  );
}
