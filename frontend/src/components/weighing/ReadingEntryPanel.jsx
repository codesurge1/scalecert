import { useEffect, useState } from "react";
import { toast } from "sonner";
import { apiFetch, ApiError } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const DEFAULT_E0 = "0";

function DerivationRow({ label, value, unit }) {
  return (
    <div className="flex items-baseline justify-between border-b py-1.5 last:border-b-0">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="font-mono text-sm">
        {value}
        {unit ? <span className="ml-1 text-muted-foreground">{unit}</span> : null}
      </span>
    </div>
  );
}

/**
 * The centerpiece: the technician enters only Indication (I) and additional
 * load (ΔL) — L is shown from the sequence, never editable. On submit, shows
 * the full computed derivation, not just a verdict, so the working is always
 * visible (CLAUDE.md / this project's whole traceability point).
 */
export function ReadingEntryPanel({ sessionId, sessionStatus, entry, onSubmitted }) {
  const [direction, setDirection] = useState("up");
  const [indication, setIndication] = useState("");
  const [deltaL, setDeltaL] = useState("0");
  const [zeroError, setZeroError] = useState(DEFAULT_E0);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [lastResult, setLastResult] = useState(null);

  // Switching loads/direction starts a fresh entry rather than carrying over
  // the previous load's Indication reading by accident.
  useEffect(() => {
    setIndication("");
    setDeltaL("0");
    setError(null);
  }, [entry?.sequence_no, direction]);

  if (!entry) {
    return (
      <Card>
        <CardContent className="py-10 text-center text-sm text-muted-foreground">
          Select a load from the sequence to enter a reading.
        </CardContent>
      </Card>
    );
  }

  const notDraft = sessionStatus !== "draft";

  async function handleSubmit(event) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);

    // Decimal-as-string discipline (CLAUDE.md, backend StrictDecimal
    // contract): indication/deltaL/zeroError are the raw string values from
    // their <input>s, sent to the API exactly as typed. They are NEVER
    // passed through Number()/parseFloat() before the request body is
    // built — a JS `number` is a float, and a value like "300.6" must never
    // round-trip through one before reaching the Decimal-based engine.
    const payload = {
      sequence_no: entry.sequence_no,
      direction,
      I: indication,
      delta_l: deltaL,
      E0: zeroError,
    };

    try {
      const result = await apiFetch(`/sessions/${sessionId}/weighing/readings`, {
        method: "POST",
        body: payload,
      });
      setLastResult({ ...result, direction, sequence_no: entry.sequence_no });
      toast.success(`Reading recorded — ${result.passed ? "PASS" : "FAIL"}.`);
      onSubmitted(entry.sequence_no, direction, result);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setError("This session is no longer in draft — readings can no longer be added.");
      } else {
        setError(err.message);
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="grid gap-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Load #{entry.sequence_no}</CardTitle>
          <CardDescription>
            Applied load <span className="font-medium text-foreground">L = {entry.L} g</span> —
            system-supplied from the generated sequence, not entered by hand.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="grid gap-5">
            <div className="flex gap-2">
              <Button
                type="button"
                size="sm"
                variant={direction === "up" ? "default" : "outline"}
                onClick={() => setDirection("up")}
              >
                ↑ Up
              </Button>
              <Button
                type="button"
                size="sm"
                variant={direction === "down" ? "default" : "outline"}
                onClick={() => setDirection("down")}
              >
                ↓ Down
              </Button>
            </div>

            <div className="grid grid-cols-2 gap-4 rounded-md border bg-secondary/40 p-4">
              <div className="grid gap-1.5">
                <Label htmlFor="indication" className="font-semibold">
                  Indication (I), g
                </Label>
                <Input
                  id="indication"
                  inputMode="decimal"
                  required
                  autoFocus
                  placeholder="reading shown on the display"
                  value={indication}
                  onChange={(event) => setIndication(event.target.value)}
                />
              </div>
              <div className="grid gap-1.5">
                <Label htmlFor="delta-l" className="font-semibold">
                  Additional load (ΔL), g
                </Label>
                <Input
                  id="delta-l"
                  inputMode="decimal"
                  required
                  value={deltaL}
                  onChange={(event) => setDeltaL(event.target.value)}
                />
              </div>
              <p className="col-span-2 text-xs text-muted-foreground">
                These are the only two values the technician enters for this reading.
              </p>
            </div>

            <div className="grid gap-1.5">
              <Label htmlFor="zero-error">Zero-point error (E0), g</Label>
              <Input
                id="zero-error"
                inputMode="decimal"
                required
                className="max-w-40"
                value={zeroError}
                onChange={(event) => setZeroError(event.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                Defaults to 0 — there is no dedicated zero-capture step yet (a later task); enter the
                measured zero-point error here in the meantime.
              </p>
            </div>

            {error ? <p className="text-sm font-medium text-destructive">{error}</p> : null}
            {notDraft ? (
              <p className="text-sm font-medium text-warning-foreground">
                Session status is "{sessionStatus}" — readings are only accepted while a session is
                draft.
              </p>
            ) : null}

            <Button type="submit" disabled={submitting || notDraft} className="justify-self-start">
              {submitting ? "Submitting…" : "Submit reading"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {lastResult ? (
        <Card className={lastResult.passed ? "border-success/40" : "border-destructive/40"}>
          <CardHeader className="flex-row items-center justify-between space-y-0">
            <div>
              <CardTitle className="text-base">
                Derivation — load #{lastResult.sequence_no} ({lastResult.direction})
              </CardTitle>
              <CardDescription>The full working, not just the verdict.</CardDescription>
            </div>
            <Badge variant={lastResult.passed ? "success" : "destructive"} className="text-sm">
              {lastResult.passed ? "PASS" : "FAIL"}
            </Badge>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-x-8">
              <div>
                <DerivationRow label="L (applied load)" value={lastResult.L} unit="g" />
                <DerivationRow label="I (indication)" value={lastResult.I} unit="g" />
                <DerivationRow label="ΔL (additional load)" value={lastResult.delta_l} unit="g" />
                <DerivationRow label="E0 (zero-point error)" value={lastResult.E0} unit="g" />
              </div>
              <div>
                <DerivationRow label="E (error)" value={lastResult.E} unit="g" />
                <DerivationRow label="Ec (corrected error)" value={lastResult.Ec} unit="g" />
                <DerivationRow label="MPE" value={`±${lastResult.mpe}`} unit="g" />
                <DerivationRow label="Margin" value={lastResult.margin} unit="g" />
              </div>
            </div>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
