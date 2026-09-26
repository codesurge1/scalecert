import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/AppShell";
import { StartVerificationDialog } from "@/components/StartVerificationDialog";
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

function StatusBadge({ status }) {
  const variant = status === "draft" ? "secondary" : status === "issued" || status === "approved" ? "success" : "outline";
  return <Badge variant={variant} className="capitalize">{status}</Badge>;
}

/**
 * Instruments -> Instrument detail (this page) -> Session overview -> test
 * page. The verification-type choice happens exactly once, here, via
 * StartVerificationDialog — never when opening a test.
 */
export function InstrumentDetailPage() {
  const { id } = useParams();

  // undefined = loading, null = load failed, object/array = loaded.
  const [instrument, setInstrument] = useState(undefined);
  const [sessions, setSessions] = useState(undefined);
  const [error, setError] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setError(null);

    Promise.all([apiFetch(`/instruments/${id}`), apiFetch(`/instruments/${id}/sessions`)])
      .then(([instrumentData, sessionsData]) => {
        if (cancelled) return;
        setInstrument(instrumentData);
        setSessions(sessionsData);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message);
          setInstrument(null);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [id, reloadKey]);

  if (instrument === undefined) {
    return (
      <div>
        <PageHeader title="Instrument" />
        <div className="space-y-3">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-48 w-full" />
        </div>
      </div>
    );
  }

  if (instrument === null) {
    return (
      <div>
        <PageHeader title="Instrument" />
        <Card className="border-destructive/50 bg-destructive/5">
          <CardContent className="flex items-center justify-between py-4 text-sm text-destructive">
            <span>Couldn't load this instrument: {error}</span>
            <Button variant="outline" size="sm" onClick={() => setReloadKey((key) => key + 1)}>
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const label = instrument.type_designation || `Class ${instrument.accuracy_class} instrument`;

  return (
    <div className="grid gap-6">
      <div>
        <Link to="/instruments" className="text-sm text-muted-foreground hover:text-foreground hover:underline">
          &larr; Instruments
        </Link>
        <PageHeader
          title={label}
          actions={<StartVerificationDialog instrumentId={id} instrumentLabel={label} />}
        />
      </div>

      <Card>
        <CardContent className="grid grid-cols-2 gap-4 py-4 sm:grid-cols-4">
          <div>
            <div className="text-xs text-muted-foreground">Manufacturer / model</div>
            <div className="text-sm font-medium">
              {[instrument.manufacturer, instrument.model].filter(Boolean).join(" / ") || "—"}
            </div>
          </div>
          <div>
            <div className="text-xs text-muted-foreground">Serial no.</div>
            <div className="text-sm font-medium">{instrument.serial_number || "—"}</div>
          </div>
          <div>
            <div className="text-xs text-muted-foreground">Class / e / Max / Min</div>
            <div className="text-sm font-medium">
              Class {instrument.accuracy_class} · e={instrument.e_value}g · Max={instrument.max_capacity}g · Min=
              {instrument.min_capacity ?? "—"}g
            </div>
          </div>
          <div>
            <div className="text-xs text-muted-foreground">Indication</div>
            <div className="text-sm font-medium capitalize">{instrument.indication_type.replaceAll("_", " ")}</div>
          </div>
        </CardContent>
      </Card>

      <div>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Verification sessions
        </h2>
        {sessions === undefined ? (
          <Skeleton className="h-32 w-full" />
        ) : sessions.length === 0 ? (
          <Card>
            <CardContent className="py-10 text-center text-sm text-muted-foreground">
              No verification sessions yet for this instrument. Use "New verification session" above to open one.
            </CardContent>
          </Card>
        ) : (
          <Card>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Verification type</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Started</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sessions.map((session) => (
                  <TableRow key={session.id}>
                    <TableCell className="font-medium">
                      {VERIFICATION_TYPE_LABELS[session.verification_type] ?? session.verification_type}
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={session.status} />
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {new Date(session.created_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button asChild size="sm" variant="outline">
                        <Link to={`/sessions/${session.id}`}>Open</Link>
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>
        )}
      </div>
    </div>
  );
}
