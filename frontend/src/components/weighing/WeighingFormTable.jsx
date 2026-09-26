import { Fragment, useMemo, useState } from "react";
import { toast } from "sonner";
import { apiFetch, ApiError } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

// Direction mapping — explicit and intentional, do not "simplify" this away.
// The OIML R 76-2 form prints two columns per quantity, headed with the
// glyphs "↓" and "↑" (increasing load, then decreasing load). This app's API
// names directions semantically instead ("up" = increasing, "down" =
// decreasing). So: the form's "↓" column is the increasing-load pass, i.e.
// API direction "up"; the form's "↑" column is the decreasing-load pass,
// i.e. API direction "down". The glyph-to-API mapping is deliberately
// crossed like this and must stay exactly as specified.
const FORM_COLUMNS = [
  { glyph: "↓", apiDirection: "up", label: "Increasing (↓)" },
  { glyph: "↑", apiDirection: "down", label: "Decreasing (↑)" },
];

const ZERO_DEVICE_OPTIONS = [
  { value: "non_existent", label: "Non-existent" },
  { value: "not_in_operation", label: "Not in operation" },
  { value: "out_of_range", label: "Out of working range" },
  { value: "in_operation", label: "In operation" },
];

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

function fmt(value) {
  return value === undefined || value === null || value === "" ? "—" : value;
}

/**
 * One environmental-conditions row (Temp / Rel.h / Time / Bar.pres for one
 * of "At start" / "At max" / "At end"). Local-only state — see the header-
 * block note below on why this can't be persisted yet.
 */
function EnvRow({ rowLabel, values, onChange, disabled }) {
  return (
    <TableRow>
      <TableCell className="text-xs font-medium text-muted-foreground">{rowLabel}</TableCell>
      {["temp", "relH", "time", "barPres"].map((field) => (
        <TableCell key={field} className="p-1.5">
          <Input
            className="h-8 text-sm"
            value={values[field]}
            disabled={disabled}
            onChange={(event) => onChange(field, event.target.value)}
          />
        </TableCell>
      ))}
    </TableRow>
  );
}

/**
 * One direction's editable I/ΔL cell-pair plus its computed E/Ec, for one
 * load row. Submission happens on blur of the ΔL field (the natural second
 * stop in the I -> ΔL tab order) or Enter in either field — a per-cell
 * "compute" click was the other option the task left open, but blur/Enter
 * needs no extra chrome in an already-dense table.
 */
function DirectionCells({ sessionId, sessionStatus, entry, column, cellState, e0, onCellChange, onResult }) {
  const disabled = sessionStatus !== "draft";
  const { indication, deltaL, result, submitting, error } = cellState;

  async function submit() {
    if (indication === "" || disabled) return;
    onCellChange({ submitting: true, error: null });
    // Decimal-as-string discipline (CLAUDE.md, backend StrictDecimal
    // contract): indication/deltaL are the raw string values typed into
    // these <input>s, sent to the API exactly as typed — never passed
    // through Number()/parseFloat() first, since a JS `number` is a float
    // and e.g. "300.6" must never round-trip through one before reaching
    // the Decimal-based engine.
    const payload = {
      sequence_no: entry.sequence_no,
      direction: column.apiDirection,
      I: indication,
      delta_l: deltaL === "" ? "0" : deltaL,
      E0: e0,
    };
    try {
      const res = await apiFetch(`/sessions/${sessionId}/weighing/readings`, {
        method: "POST",
        body: payload,
      });
      onResult(res);
      onCellChange({ submitting: false, error: null });
    } catch (err) {
      const message =
        err instanceof ApiError && err.status === 409
          ? "Session is no longer in draft — locked."
          : err.message;
      onCellChange({ submitting: false, error: message });
      toast.error(`Load #${entry.sequence_no} (${column.label}): ${message}`);
    }
  }

  function handleKeyDown(event) {
    if (event.key === "Enter") {
      event.preventDefault();
      submit();
    }
  }

  return (
    <>
      <TableCell className="border-l p-1.5" title={error ?? undefined}>
        <Input
          className={`h-8 w-24 text-sm ${error ? "border-destructive" : ""}`}
          inputMode="decimal"
          disabled={disabled}
          value={indication}
          placeholder="I"
          onChange={(event) => onCellChange({ indication: event.target.value })}
          onKeyDown={handleKeyDown}
        />
      </TableCell>
      <TableCell className="p-1.5">
        <Input
          className="h-8 w-20 text-sm"
          inputMode="decimal"
          disabled={disabled}
          value={deltaL}
          placeholder="ΔL"
          onChange={(event) => onCellChange({ deltaL: event.target.value })}
          onBlur={submit}
          onKeyDown={handleKeyDown}
        />
      </TableCell>
      <TableCell
        className={`p-1.5 text-right font-mono text-sm ${
          result ? (result.passed ? "text-success" : "text-destructive") : "text-muted-foreground"
        }`}
      >
        {submitting ? "…" : fmt(result?.E)}
      </TableCell>
      <TableCell
        className={`p-1.5 text-right font-mono text-sm ${
          result ? (result.passed ? "text-success" : "text-destructive") : "text-muted-foreground"
        }`}
      >
        {fmt(result?.Ec)}
      </TableCell>
    </>
  );
}

/**
 * The OIML R 76-2 "1 Weighing performance" entry screen — a single table the
 * technician types directly into, reproducing that form's field layout
 * (header block, environmental conditions, the ↓/↑ paired-column data table,
 * the E = I + ½e − ΔL − L / Ec = E − E0 formula line, and the overall
 * |Ec| ≤ mpe verdict box) faithfully. This is a faithful reproduction of the
 * FORMAT of that OIML form for data-entry purposes, not a copy of the
 * copyrighted OIML document itself — no OIML text, numbering, or branding
 * beyond the field layout is reproduced.
 */
export function WeighingFormTable({ sessionId, sessionStatus, instrument, sequence, observerDefault }) {
  const disabled = sessionStatus !== "draft";

  const [testDate, setTestDate] = useState(todayIso());
  const [observer, setObserver] = useState(observerDefault ?? "");
  const [env, setEnv] = useState({
    start: { temp: "", relH: "", time: "", barPres: "" },
    max: { temp: "", relH: "", time: "", barPres: "" },
    end: { temp: "", relH: "", time: "", barPres: "" },
  });
  const [zeroDeviceStatus, setZeroDeviceStatus] = useState("");
  const [initialZeroOver20, setInitialZeroOver20] = useState(null);
  const [e0, setE0] = useState("0");
  const [remarks, setRemarks] = useState("");

  // cells[sequence_no][apiDirection] = { indication, deltaL, result, submitting, error }
  const [cells, setCells] = useState({});

  function getCell(sequenceNo, apiDirection) {
    return (
      cells[sequenceNo]?.[apiDirection] ?? {
        indication: "",
        deltaL: "0",
        result: null,
        submitting: false,
        error: null,
      }
    );
  }

  function updateCell(sequenceNo, apiDirection, patch) {
    setCells((prev) => ({
      ...prev,
      [sequenceNo]: {
        ...prev[sequenceNo],
        [apiDirection]: { ...getCell(sequenceNo, apiDirection), ...patch },
      },
    }));
  }

  function setResult(sequenceNo, apiDirection, result) {
    setCells((prev) => ({
      ...prev,
      [sequenceNo]: {
        ...prev[sequenceNo],
        [apiDirection]: { ...getCell(sequenceNo, apiDirection), result },
      },
    }));
  }

  const resolutionDuringTest = instrument?.d_value ?? instrument?.e_value ?? "—";

  const rowVerdicts = useMemo(() => {
    return sequence.map((entry) => {
      const up = cells[entry.sequence_no]?.up?.result;
      const down = cells[entry.sequence_no]?.down?.result;
      const complete = Boolean(up && down);
      const failed = (up && !up.passed) || (down && !down.passed);
      return { sequence_no: entry.sequence_no, complete, failed };
    });
  }, [cells, sequence]);

  const overall = useMemo(() => {
    if (rowVerdicts.some((r) => r.failed)) return "FAILED";
    if (rowVerdicts.length > 0 && rowVerdicts.every((r) => r.complete)) return "PASSED";
    return "INCOMPLETE";
  }, [rowVerdicts]);

  return (
    <div className="grid gap-6">
      <Card className="border-2">
        <div className="border-b bg-muted/40 px-6 py-3">
          <h2 className="text-sm font-semibold uppercase tracking-wide">
            1 Weighing performance
          </h2>
          <p className="text-xs text-muted-foreground">
            OIML R 76-2 weighing-performance format — reproduced for data entry only, not a copy of
            the OIML document itself.
          </p>
        </div>

        <div className="grid gap-4 p-6">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <Field label="Application no.">{fmt(instrument?.application_no)}</Field>
            <Field label="Type designation">{fmt(instrument?.type_designation)}</Field>
            <Field label="Date" editable disabled={disabled} value={testDate} onChange={setTestDate} />
            <Field label="Observer" editable disabled={disabled} value={observer} onChange={setObserver} />
            <Field label="Verification scale interval e">{fmt(instrument?.e_value)}</Field>
            <Field label="Resolution during test (< e)">{fmt(resolutionDuringTest)}</Field>
          </div>

          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead />
                  <TableHead>Temp.</TableHead>
                  <TableHead>Rel. h.</TableHead>
                  <TableHead>Time</TableHead>
                  <TableHead>Bar. pres. (class I only)</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <EnvRow
                  rowLabel="At start"
                  values={env.start}
                  disabled={disabled}
                  onChange={(field, value) => setEnv((prev) => ({ ...prev, start: { ...prev.start, [field]: value } }))}
                />
                <EnvRow
                  rowLabel="At max"
                  values={env.max}
                  disabled={disabled}
                  onChange={(field, value) => setEnv((prev) => ({ ...prev, max: { ...prev.max, [field]: value } }))}
                />
                <EnvRow
                  rowLabel="At end"
                  values={env.end}
                  disabled={disabled}
                  onChange={(field, value) => setEnv((prev) => ({ ...prev, end: { ...prev.end, [field]: value } }))}
                />
              </TableBody>
            </Table>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <Label className="text-xs">Automatic zero-setting and zero-tracking device is:</Label>
              <div className="mt-1.5 flex flex-wrap gap-3">
                {ZERO_DEVICE_OPTIONS.map((opt) => (
                  <label key={opt.value} className="flex items-center gap-1.5 text-sm">
                    <input
                      type="radio"
                      name="zero-device-status"
                      disabled={disabled}
                      checked={zeroDeviceStatus === opt.value}
                      onChange={() => setZeroDeviceStatus(opt.value)}
                    />
                    {opt.label}
                  </label>
                ))}
              </div>
            </div>
            <div>
              <Label className="text-xs">Initial zero-setting &gt; 20% of Max:</Label>
              <div className="mt-1.5 flex gap-3">
                {["yes", "no"].map((opt) => (
                  <label key={opt} className="flex items-center gap-1.5 text-sm capitalize">
                    <input
                      type="radio"
                      name="initial-zero-over-20"
                      disabled={disabled}
                      checked={initialZeroOver20 === opt}
                      onChange={() => setInitialZeroOver20(opt)}
                    />
                    {opt}
                  </label>
                ))}
              </div>
            </div>
          </div>

          <p className="rounded-md bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
            The header fields above (Date, Observer, environmental conditions, zero-device status,
            initial-zero-setting flag) are entered here but not yet persisted to the session record —
            there is no session-update endpoint yet (tracked gap; see docs/architecture.md). They
            reset on page reload.
          </p>
        </div>
      </Card>

      <Card className="border-2">
        <div className="border-b bg-muted/40 px-6 py-3">
          <p className="font-mono text-xs">E = I + ½e − ΔL − L</p>
          <p className="font-mono text-xs">Ec = E − E0 (E0 = error calculated at or near zero)</p>
        </div>

        <div className="flex flex-wrap items-center gap-3 border-b px-6 py-3">
          <Label htmlFor="e0" className="text-sm font-semibold">
            E0 (zero-point error), g
          </Label>
          <Input
            id="e0"
            className="h-8 w-32"
            inputMode="decimal"
            disabled={disabled}
            value={e0}
            onChange={(event) => setE0(event.target.value)}
          />
          <p className="text-xs text-muted-foreground">
            Captured once per session (simplification pending a dedicated zero-capture step).
          </p>
        </div>

        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead rowSpan={2} className="border-r align-bottom">Load L</TableHead>
                {FORM_COLUMNS.map((col) => (
                  <TableHead key={col.glyph} colSpan={4} className="border-l text-center">
                    {col.glyph}
                  </TableHead>
                ))}
                <TableHead rowSpan={2} className="border-l align-bottom text-center">Result</TableHead>
              </TableRow>
              <TableRow>
                {FORM_COLUMNS.map((col) => (
                  <Fragment key={col.glyph}>
                    <TableHead className="border-l text-center">Indication I</TableHead>
                    <TableHead className="text-center">Add. load ΔL</TableHead>
                    <TableHead className="text-center">Error E</TableHead>
                    <TableHead className="text-center">Corr. err Ec</TableHead>
                  </Fragment>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {sequence.map((entry) => {
                const verdict = rowVerdicts.find((r) => r.sequence_no === entry.sequence_no);
                return (
                  <TableRow key={entry.sequence_no}>
                    <TableCell className="border-r font-medium">
                      {entry.L}
                      <div className="text-xs text-muted-foreground">mpe ±{entry.mpe}</div>
                    </TableCell>
                    {FORM_COLUMNS.map((col) => (
                      <DirectionCells
                        key={col.apiDirection}
                        sessionId={sessionId}
                        sessionStatus={sessionStatus}
                        entry={entry}
                        column={col}
                        cellState={getCell(entry.sequence_no, col.apiDirection)}
                        e0={e0}
                        onCellChange={(patch) => updateCell(entry.sequence_no, col.apiDirection, patch)}
                        onResult={(result) => setResult(entry.sequence_no, col.apiDirection, result)}
                      />
                    ))}
                    <TableCell className="border-l text-right">
                      {verdict.complete ? (
                        <Badge variant={verdict.failed ? "destructive" : "success"}>
                          {verdict.failed ? "FAIL" : "PASS"}
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="text-muted-foreground">Pending</Badge>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 border-t px-6 py-4">
          <p className="text-sm font-medium">Check if |Ec| ≤ |mpe|</p>
          <Badge
            variant={overall === "PASSED" ? "success" : overall === "FAILED" ? "destructive" : "warning"}
            className="text-sm"
          >
            {overall}
          </Badge>
        </div>
      </Card>

      <Card>
        <div className="p-6">
          <Label htmlFor="remarks" className="text-sm font-semibold">Remarks</Label>
          <textarea
            id="remarks"
            className="mt-1.5 flex min-h-20 w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
            disabled={disabled}
            value={remarks}
            onChange={(event) => setRemarks(event.target.value)}
          />
        </div>
      </Card>
    </div>
  );
}

function Field({ label, children, editable, disabled, value, onChange }) {
  return (
    <div className="grid gap-1">
      <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</span>
      {editable ? (
        <Input className="h-8" disabled={disabled} value={value} onChange={(event) => onChange(event.target.value)} />
      ) : (
        <span className="text-sm font-medium">{children}</span>
      )}
    </div>
  );
}
