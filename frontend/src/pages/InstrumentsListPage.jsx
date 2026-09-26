import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/AppShell";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export function InstrumentsListPage() {
  // undefined = loading, [] = loaded-and-empty, [...] = loaded — three
  // distinct states, not collapsed into one "falsy" check, so loading never
  // gets mistaken for empty.
  const [instruments, setInstruments] = useState(undefined);
  const [error, setError] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    apiFetch("/instruments")
      .then((rows) => {
        if (!cancelled) setInstruments(rows);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message);
          setInstruments([]);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  return (
    <div>
      <PageHeader
        title="Instruments"
        description="Registered non-automatic weighing instruments."
        actions={
          <Button asChild>
            <Link to="/instruments/new">Register instrument</Link>
          </Button>
        }
      />

      {error ? (
        <Card className="mb-4 border-destructive/50 bg-destructive/5">
          <CardContent className="flex items-center justify-between py-4 text-sm text-destructive">
            <span>Couldn't load instruments: {error}</span>
            <Button variant="outline" size="sm" onClick={() => setReloadKey((key) => key + 1)}>
              Retry
            </Button>
          </CardContent>
        </Card>
      ) : null}

      {instruments === undefined ? (
        <div className="space-y-2">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      ) : instruments.length === 0 && !error ? (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            No instruments registered yet.{" "}
            <Link to="/instruments/new" className="font-medium text-primary underline-offset-4 hover:underline">
              Register the first one.
            </Link>
          </CardContent>
        </Card>
      ) : instruments.length > 0 ? (
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Type designation</TableHead>
                <TableHead>Manufacturer / model</TableHead>
                <TableHead>Serial no.</TableHead>
                <TableHead>Class</TableHead>
                <TableHead>e</TableHead>
                <TableHead>Max</TableHead>
                <TableHead>Min</TableHead>
                <TableHead>Indication</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {instruments.map((instrument) => (
                <TableRow key={instrument.id}>
                  <TableCell className="font-medium">{instrument.type_designation || "—"}</TableCell>
                  <TableCell>
                    {[instrument.manufacturer, instrument.model].filter(Boolean).join(" / ") || "—"}
                  </TableCell>
                  <TableCell>{instrument.serial_number || "—"}</TableCell>
                  <TableCell>
                    <Badge variant="secondary">Class {instrument.accuracy_class}</Badge>
                  </TableCell>
                  <TableCell>{instrument.e_value} g</TableCell>
                  <TableCell>{instrument.max_capacity} g</TableCell>
                  <TableCell>{instrument.min_capacity ?? "—"}</TableCell>
                  <TableCell className="capitalize">{instrument.indication_type.replaceAll("_", " ")}</TableCell>
                  <TableCell className="text-right">
                    <Button asChild size="sm" variant="outline">
                      <Link to={`/instruments/${instrument.id}`}>View</Link>
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      ) : null}
    </div>
  );
}
