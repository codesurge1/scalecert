import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { apiFetch } from "@/lib/api";
import { useSession as useAuthSession } from "@/lib/supabase";
import { FocusedPageHeader } from "@/components/AppShell";
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
      <div className="grid gap-2">
        <FocusedPageHeader title="Tilting" sessionId={id} />
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
        <FocusedPageHeader title="Tilting" sessionId={id} />
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
    // See ZeroTareSessionPage for the `lg:` height-constrained chain and
    // why the form wrapper below scrolls as a whole rather than clipping.
    <div className="grid gap-2 lg:flex lg:h-full lg:min-h-0 lg:flex-col">
      <FocusedPageHeader title="Tilting" sessionId={id} />

      {session.status !== "draft" ? (
        <p className="shrink-0 text-sm font-medium text-warning-foreground">
          This session is "{session.status}", not draft — the form below is read-only.
        </p>
      ) : null}

      {tiltingState === undefined ? (
        <Skeleton className="h-[600px] w-full" />
      ) : (
        <div className="lg:min-h-0 lg:flex-1 lg:overflow-y-auto">
          <TiltingFormTable
            sessionId={id}
            sessionStatus={session.status}
            instrument={instrument}
            initialState={tiltingState}
            verificationType={session.verification_type}
            observerDefault={authSession?.user?.email}
          />
        </div>
      )}
    </div>
  );
}
