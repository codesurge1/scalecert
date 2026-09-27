import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { apiFetch } from "@/lib/api";
import { useSession as useAuthSession } from "@/lib/supabase";
import { FocusedBackLink, PageHeader } from "@/components/AppShell";
import { EccentricityFormTable } from "@/components/eccentricity/EccentricityFormTable";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";

/**
 * The Eccentricity test page — same navigation shape as the other test
 * pages. Fetches session, instrument, the fixed test-load setup
 * (GET .../eccentricity/setup), and every already-submitted position in
 * parallel so a refresh reconstructs the form instead of losing progress.
 */
export function EccentricitySessionPage() {
  const { id } = useParams();
  const authSession = useAuthSession();

  const [session, setSession] = useState(undefined);
  const [instrument, setInstrument] = useState(undefined);
  const [setup, setSetup] = useState(undefined);
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
          apiFetch(`/sessions/${id}/eccentricity/setup`),
          apiFetch(`/sessions/${id}/eccentricity/readings`),
        ]);
      })
      .then((results) => {
        if (cancelled || !results) return;
        const [instrumentData, setupData, readingsData] = results;
        setInstrument(instrumentData);
        setSetup(setupData);
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
        <PageHeader title="Eccentricity" />
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
        <PageHeader title="Eccentricity" />
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

  const loadingTable = setup === undefined || readingRecords === undefined;

  return (
    <div className="grid gap-4">
      <FocusedBackLink sessionId={id} />
      <PageHeader title="Eccentricity" />

      {session.status !== "draft" ? (
        <p className="text-sm font-medium text-warning-foreground">
          This session is "{session.status}", not draft — the form below is read-only.
        </p>
      ) : null}

      {loadingTable ? (
        <Skeleton className="h-[500px] w-full" />
      ) : (
        <EccentricityFormTable
          sessionId={id}
          sessionStatus={session.status}
          instrument={instrument}
          setup={setup}
          verificationType={session.verification_type}
          observerDefault={authSession?.user?.email}
          initialReadings={readingRecords}
        />
      )}
    </div>
  );
}
