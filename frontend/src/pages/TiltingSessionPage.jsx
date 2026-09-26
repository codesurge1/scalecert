import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiFetch } from "@/lib/api";
import { useSession as useAuthSession } from "@/lib/supabase";
import { PageHeader } from "@/components/AppShell";
import { TiltingFormTable } from "@/components/tilting/TiltingFormTable";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";

/**
 * The Tilting test page — same navigation shape as the other test pages.
 * `GET .../tilting/readings` always returns the full current state (L,
 * mpe for both loaded rows, submitted readings, pass criteria) even with
 * zero readings, so there's no separate "setup" fetch (same reasoning as
 * Repeatability).
 */
export function TiltingSessionPage() {
  const { id } = useParams();
  const authSession = useAuthSession();

  const [session, setSession] = useState(undefined);
  const [instrument, setInstrument] = useState(undefined);
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
          apiFetch(`/sessions/${id}/tilting/readings`),
        ]);
      })
      .then((results) => {
        if (cancelled || !results) return;
        const [instrumentData, stateData] = results;
        setInstrument(instrumentData);
        setTiltingState(stateData);
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
        <PageHeader title="Tilting" />
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
        <PageHeader title="Tilting" />
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
    <div className="grid gap-4">
      <Link to={`/sessions/${id}`} className="text-sm text-muted-foreground hover:text-foreground hover:underline">
        &larr; Session overview
      </Link>
      <PageHeader title="Tilting" />

      {session.status !== "draft" ? (
        <p className="text-sm font-medium text-warning-foreground">
          This session is "{session.status}", not draft — the form below is read-only.
        </p>
      ) : null}

      {tiltingState === undefined ? (
        <Skeleton className="h-[600px] w-full" />
      ) : (
        <TiltingFormTable
          sessionId={id}
          sessionStatus={session.status}
          instrument={instrument}
          initialState={tiltingState}
          observerDefault={authSession?.user?.email}
        />
      )}
    </div>
  );
}
