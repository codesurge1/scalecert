import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { apiFetch } from "@/lib/api";
import { useSession as useAuthSession } from "@/lib/supabase";
import { FocusedBackLink, PageHeader } from "@/components/AppShell";
import { RepeatabilityFormTable } from "@/components/repeatability/RepeatabilityFormTable";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";

/**
 * The Repeatability test page — same navigation shape as
 * WeighingSessionPage/ZeroTareSessionPage. `GET .../repeatability/readings`
 * always returns both series (L/mpe populated even with zero readings
 * submitted so far — app/services/repeatability.py), so there's no separate
 * "setup" fetch needed here.
 */
export function RepeatabilitySessionPage() {
  const { id } = useParams();
  const authSession = useAuthSession();

  const [session, setSession] = useState(undefined);
  const [instrument, setInstrument] = useState(undefined);
  const [series, setSeries] = useState(undefined);
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
          apiFetch(`/sessions/${id}/repeatability/readings`),
        ]);
      })
      .then((results) => {
        if (cancelled || !results) return;
        const [instrumentData, seriesData] = results;
        setInstrument(instrumentData);
        setSeries(seriesData);
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
        <PageHeader title="Repeatability" />
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
        <PageHeader title="Repeatability" />
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
      <FocusedBackLink sessionId={id} />
      <PageHeader title="Repeatability" />

      {session.status !== "draft" ? (
        <p className="text-sm font-medium text-warning-foreground">
          This session is "{session.status}", not draft — the form below is read-only.
        </p>
      ) : null}

      {series === undefined ? (
        <Skeleton className="h-[500px] w-full" />
      ) : (
        <RepeatabilityFormTable
          sessionId={id}
          sessionStatus={session.status}
          instrument={instrument}
          series={series}
          verificationType={session.verification_type}
          observerDefault={authSession?.user?.email}
        />
      )}
    </div>
  );
}
