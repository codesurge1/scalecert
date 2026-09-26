import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiFetch } from "@/lib/api";
import { useSession as useAuthSession } from "@/lib/supabase";
import { PageHeader } from "@/components/AppShell";
import { ZeroTareFormTable } from "@/components/zeroTare/ZeroTareFormTable";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";

/**
 * The Zero/tare device accuracy test page — reached from the session
 * overview's Start/Open button or the Add-test picker, same navigation
 * shape as WeighingSessionPage. Fetches session, instrument, the generated
 * check list, and every already-submitted reading in parallel so a refresh
 * reconstructs the form instead of losing progress.
 */
export function ZeroTareSessionPage() {
  const { id } = useParams();
  const authSession = useAuthSession();

  const [session, setSession] = useState(undefined);
  const [instrument, setInstrument] = useState(undefined);
  const [checks, setChecks] = useState(undefined);
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
          apiFetch(`/sessions/${id}/zero-tare/checks`),
          apiFetch(`/sessions/${id}/zero-tare/readings`),
        ]);
      })
      .then((results) => {
        if (cancelled || !results) return;
        const [instrumentData, checksData, readingsData] = results;
        setInstrument(instrumentData);
        setChecks(checksData);
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
        <PageHeader title="Zero/tare device accuracy" />
        <div className="space-y-3">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      </div>
    );
  }

  if (session === null) {
    return (
      <div>
        <PageHeader title="Zero/tare device accuracy" />
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

  const loadingTable = checks === undefined || readingRecords === undefined;

  return (
    <div className="grid gap-4">
      <Link to={`/sessions/${id}`} className="text-sm text-muted-foreground hover:text-foreground hover:underline">
        &larr; Session overview
      </Link>
      <PageHeader title="Zero/tare device accuracy" />

      {session.status !== "draft" ? (
        <p className="text-sm font-medium text-warning-foreground">
          This session is "{session.status}", not draft — the form below is read-only.
        </p>
      ) : null}

      {loadingTable ? (
        <Skeleton className="h-[400px] w-full" />
      ) : (
        <ZeroTareFormTable
          sessionId={id}
          sessionStatus={session.status}
          instrument={instrument}
          checks={checks}
          observerDefault={authSession?.user?.email}
          initialReadings={readingRecords}
        />
      )}
    </div>
  );
}
