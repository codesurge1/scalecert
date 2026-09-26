import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { apiFetch } from "@/lib/api";
import { useSession as useAuthSession } from "@/lib/supabase";
import { PageHeader } from "@/components/AppShell";
import { WeighingFormTable } from "@/components/weighing/WeighingFormTable";
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
  const authSession = useAuthSession();

  // undefined = loading, null = load failed, object = loaded.
  const [session, setSession] = useState(undefined);
  const [instrument, setInstrument] = useState(undefined);
  const [sequence, setSequence] = useState(undefined);
  const [error, setError] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setError(null);

    Promise.all([apiFetch(`/sessions/${id}`), apiFetch(`/sessions/${id}/weighing/sequence`)])
      .then(([sessionData, sequenceData]) => {
        if (cancelled) return;
        setSession(sessionData);
        setSequence(sequenceData);
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
        <WeighingFormTable
          sessionId={id}
          sessionStatus={session.status}
          instrument={instrument}
          sequence={sequence}
          observerDefault={authSession?.user?.email}
        />
      )}

      {session.status !== "draft" ? (
        <p className="text-sm font-medium text-warning-foreground">
          This session is "{session.status}", not draft — the form above is read-only. Entered
          readings from earlier in this draft may not reappear here: there is no endpoint yet to
          list a session's previously submitted readings (tracked gap; see docs/architecture.md).
        </p>
      ) : null}
    </div>
  );
}
