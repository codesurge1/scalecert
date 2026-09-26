import { Fragment, useMemo, useState } from "react";
import { toast } from "sonner";
import { apiFetch, ApiError } from "@/lib/api";

// Direction mapping — explicit and intentional, do not "simplify" this away.
// The OIML R 76-2 form prints two sub-columns per quantity, headed with the
// glyphs "↓" and "↑" (increasing load, then decreasing load). This app's API
// names directions semantically instead ("up" = increasing, "down" =
// decreasing). So: the form's "↓" sub-column is the increasing-load pass,
// i.e. API direction "up"; the form's "↑" sub-column is the decreasing-load
// pass, i.e. API direction "down". The glyph-to-API mapping is deliberately
// crossed like this and must stay exactly as specified.
const FORM_COLUMNS = [
  { glyph: "↓", apiDirection: "up" },
  { glyph: "↑", apiDirection: "down" },
];

const ZERO_DEVICE_OPTIONS = [
  { value: "non_existent", label: "Non-existent" },
  { value: "not_in_operation", label: "Not in operation" },
  { value: "out_of_range", label: "Out of working range" },
  { value: "in_operation", label: "In operation" },
];

const ENV_ROWS = [
  { key: "temp", label: "Temp.:", unit: "°C" },
  { key: "relH", label: "Rel. h.:", unit: "%" },
  { key: "time", label: "Time:", unit: "" },
  { key: "barPres", label: "Bar. pres.:", unit: "hPa", note: "(only class I)" },
];

const ENV_COLS = [
  { key: "start", label: "At start" },
  { key: "max", label: "At max" },
  { key: "end", label: "At end" },
];

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

function fmt(value) {
  return value === undefined || value === null || value === "" ? "" : value;
}

/** A label + dotted fill-in line, matching the form's "Label: …………" rows. */
function FormLine({ label, value, editable, disabled, onChange }) {
  return (
    <div className="flex items-baseline gap-2">
      <span className="shrink-0">{label}</span>
      {editable ? (
        <input
          className="min-w-0 flex-1 border-0 border-b border-dotted border-neutral-500 bg-transparent px-1 text-sm focus:outline-none focus:border-solid focus:border-neutral-900 disabled:opacity-60"
          disabled={disabled}
          value={value}
          onChange={(event) => onChange(event.target.value)}
        />
      ) : (
        <span className="min-w-0 flex-1 truncate border-b border-dotted border-neutral-500 px-1 text-sm">
          {value || " "}
        </span>
      )}
    </div>
  );
}

/** A square ☐-style checkbox, matching the form's tick-box controls. Used
 * both interactively (zero-device / initial-zero radios) and read-only (the
 * Passed/Failed boxes, which reflect the computed verdict rather than a
 * manual click). */
function FormCheckbox({ checked, onClick, label, readOnly }) {
  return (
    <span
      role={readOnly ? undefined : "checkbox"}
      aria-checked={checked}
      onClick={readOnly ? undefined : onClick}
      className={`flex items-center gap-2 text-sm ${readOnly ? "" : "cursor-pointer"}`}
    >
      <span className="flex h-4 w-4 shrink-0 items-center justify-center border border-neutral-900">
        {checked ? <span className="h-2.5 w-2.5 bg-neutral-900" /> : null}
      </span>
      {label}
    </span>
  );
}

/**
 * The OIML R 76-2 "1 Weighing performance" entry screen — a visual
 * reproduction of the standard's page-10 form (header block, environmental
 * grid, zero-device/initial-zero lines, the E/Ec formula, the ↓/↑ data
 * table, and the Passed/Failed + Remarks footer), reproduced for data-entry
 * fidelity only, not a copy of the copyrighted OIML document itself — no
 * OIML explanatory text is included beyond the form's own field labels and
 * structural chrome.
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

  // Submission happens on blur of the ΔL input (the natural second stop in
  // the I -> ΔL tab order) or Enter in either field — a per-cell "compute"
  // click was the other option the task left open, but blur/Enter needs no
  // extra chrome on an already-dense, form-styled table.
  async function submitDirection(entry, apiDirection) {
    const cell = getCell(entry.sequence_no, apiDirection);
    if (cell.indication === "" || disabled) return;
    updateCell(entry.sequence_no, apiDirection, { submitting: true, error: null });
    // Decimal-as-string discipline (CLAUDE.md, backend StrictDecimal
    // contract): indication/deltaL/e0 are the raw string values typed into
    // these <input>s, sent to the API exactly as typed — never passed
    // through Number()/parseFloat() first, since a JS `number` is a float
    // and e.g. "300.6" must never round-trip through one before reaching
    // the Decimal-based engine.
    const payload = {
      sequence_no: entry.sequence_no,
      direction: apiDirection,
      I: cell.indication,
      delta_l: cell.deltaL === "" ? "0" : cell.deltaL,
      E0: e0,
    };
    try {
      const res = await apiFetch(`/sessions/${sessionId}/weighing/readings`, {
        method: "POST",
        body: payload,
      });
      setCells((prev) => ({
        ...prev,
        [entry.sequence_no]: {
          ...prev[entry.sequence_no],
          [apiDirection]: { ...getCell(entry.sequence_no, apiDirection), result: res, submitting: false, error: null },
        },
      }));
    } catch (err) {
      const message =
        err instanceof ApiError && err.status === 409
          ? "Session is no longer in draft — locked."
          : err.message;
      updateCell(entry.sequence_no, apiDirection, { submitting: false, error: message });
      toast.error(`Load #${entry.sequence_no} (${apiDirection}): ${message}`);
    }
  }

  function handleEnter(entry, apiDirection) {
    return (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        submitDirection(entry, apiDirection);
      }
    };
  }

  const resolutionDuringTest = instrument?.d_value ?? instrument?.e_value ?? "";

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

  function inputCell(entry, apiDirection, field) {
    const cell = getCell(entry.sequence_no, apiDirection);
    return (
      <td className="border border-neutral-900 p-0" title={cell.error ?? undefined}>
        <input
          className={`h-7 w-full border-0 bg-transparent px-1 text-center text-xs focus:outline-none focus:ring-1 focus:ring-inset focus:ring-neutral-900 disabled:opacity-60 ${
            cell.error ? "bg-red-50" : ""
          }`}
          inputMode="decimal"
          disabled={disabled}
          value={field === "indication" ? cell.indication : cell.deltaL}
          onChange={(event) =>
            updateCell(entry.sequence_no, apiDirection, { [field]: event.target.value })
          }
          onBlur={field === "deltaL" ? () => submitDirection(entry, apiDirection) : undefined}
          onKeyDown={handleEnter(entry, apiDirection)}
        />
      </td>
    );
  }

  function computedCell(entry, apiDirection, field) {
    const cell = getCell(entry.sequence_no, apiDirection);
    const value = cell.result?.[field];
    const colorClass = cell.result
      ? cell.result.passed
        ? "text-emerald-700"
        : "text-red-700 font-semibold"
      : "text-neutral-500";
    return (
      <td className={`border border-neutral-900 px-1 py-1 text-center text-xs ${colorClass}`}>
        {cell.submitting ? "…" : fmt(value)}
      </td>
    );
  }

  return (
    <div className="grid gap-3">
      <div className="mx-auto w-full max-w-4xl border-2 border-neutral-900 bg-white p-6 font-serif text-neutral-900 sm:p-8">
        <div className="mb-4 flex items-baseline justify-between border-b border-neutral-900 pb-1 text-xs">
          <span>OIML R 76-2: 2007 (E)</span>
          <span>Report page &hellip;./&hellip;.</span>
        </div>

        <h2 className="text-sm font-bold">1&nbsp;&nbsp;&nbsp;WEIGHING PERFORMANCE (A.4.4) (A.5.3.1)</h2>
        <p className="ml-8 text-sm">(Calculation of the error)</p>

        <div className="mt-5 grid gap-x-8 gap-y-1.5 sm:grid-cols-2">
          <div className="grid gap-1.5">
            <FormLine label="Application no.:" value={fmt(instrument?.application_no)} />
            <FormLine label="Type designation:" value={fmt(instrument?.type_designation)} />
            <FormLine label="Date:" value={testDate} editable disabled={disabled} onChange={setTestDate} />
            <FormLine label="Observer:" value={observer} editable disabled={disabled} onChange={setObserver} />
            <FormLine label="Verification scale interval, e:" value={fmt(instrument?.e_value)} />
            <FormLine label="Resolution during test (smaller than e):" value={fmt(resolutionDuringTest)} />
          </div>

          <div>
            <table className="w-full border-collapse text-xs">
              <thead>
                <tr>
                  <th className="border border-neutral-900 px-2 py-1" />
                  {ENV_COLS.map((col) => (
                    <th key={col.key} className="border border-neutral-900 px-2 py-1 font-normal">
                      {col.label}
                    </th>
                  ))}
                  <th className="border border-neutral-900 px-1 py-1" />
                </tr>
              </thead>
              <tbody>
                {ENV_ROWS.map((row) => (
                  <tr key={row.key}>
                    <td className="border border-neutral-900 px-2 py-1 align-top">
                      {row.label}
                      {row.note ? <div className="text-[10px] italic text-neutral-600">{row.note}</div> : null}
                    </td>
                    {ENV_COLS.map((col) => (
                      <td key={col.key} className="border border-neutral-900 p-0">
                        <input
                          className="h-6 w-full border-0 bg-transparent px-1 text-center text-xs focus:outline-none focus:ring-1 focus:ring-inset focus:ring-neutral-900 disabled:opacity-60"
                          disabled={disabled}
                          value={env[col.key][row.key]}
                          onChange={(event) =>
                            setEnv((prev) => ({
                              ...prev,
                              [col.key]: { ...prev[col.key], [row.key]: event.target.value },
                            }))
                          }
                        />
                      </td>
                    ))}
                    <td className="border border-neutral-900 px-1 py-1">{row.unit}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="mt-5">
          <p className="text-sm">Automatic zero-setting and zero-tracking device is:</p>
          <div className="mt-1.5 flex flex-wrap gap-x-8 gap-y-2">
            {ZERO_DEVICE_OPTIONS.map((opt) => (
              <FormCheckbox
                key={opt.value}
                label={opt.label}
                checked={zeroDeviceStatus === opt.value}
                onClick={() => !disabled && setZeroDeviceStatus(opt.value)}
              />
            ))}
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-x-8 gap-y-2">
          <p className="text-sm">Initial zero-setting &gt; 20 % of Max:</p>
          <FormCheckbox
            label="Yes"
            checked={initialZeroOver20 === "yes"}
            onClick={() => !disabled && setInitialZeroOver20("yes")}
          />
          <FormCheckbox
            label="No  (see R 76-1, A.4.4.2)"
            checked={initialZeroOver20 === "no"}
            onClick={() => !disabled && setInitialZeroOver20("no")}
          />
        </div>

        <div className="mt-5 text-sm">
          <p>
            <i>E</i> = <i>I</i> + ½ <i>e</i> − Δ<i>L</i> − <i>L</i>
          </p>
          <p>
            <i>E</i>
            <sub>c</sub> = <i>E</i> − <i>E</i>
            <sub>0</sub> with <i>E</i>
            <sub>0</sub> = error calculated at or near zero*
          </p>
          <div className="mt-1 flex items-baseline gap-2 text-xs text-neutral-700">
            <span>
              * <i>E</i>
              <sub>0</sub> =
            </span>
            <input
              className="w-24 border-0 border-b border-dotted border-neutral-500 bg-transparent px-1 text-center focus:outline-none focus:border-solid focus:border-neutral-900 disabled:opacity-60"
              inputMode="decimal"
              disabled={disabled}
              value={e0}
              onChange={(event) => setE0(event.target.value)}
            />
            <span>g — entered here; no dedicated zero-capture step yet (tracked gap).</span>
          </div>
        </div>

        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[720px] border-collapse text-xs">
            <thead>
              <tr>
                <th rowSpan={2} className="border border-neutral-900 px-2 py-1 align-middle">
                  Load, <i>L</i>
                </th>
                <th colSpan={2} className="border border-neutral-900 px-2 py-1 font-normal">
                  Indication, <i>I</i>
                </th>
                <th colSpan={2} className="border border-neutral-900 px-2 py-1 font-normal">
                  Add. load,
                  <br />Δ<i>L</i>
                </th>
                <th colSpan={2} className="border border-neutral-900 px-2 py-1 font-normal">
                  Error, <i>E</i>
                </th>
                <th colSpan={2} className="border border-neutral-900 px-2 py-1 font-normal">
                  Corrected error, <i>E</i>
                  <sub>c</sub>
                </th>
                <th rowSpan={2} className="border border-neutral-900 px-2 py-1 align-middle">
                  mpe
                </th>
              </tr>
              <tr>
                {["I", "dL", "E", "Ec"].flatMap((group) =>
                  FORM_COLUMNS.map((col) => (
                    <th key={`${group}-${col.apiDirection}`} className="border border-neutral-900 px-1 py-1 font-normal">
                      {col.glyph}
                    </th>
                  )),
                )}
              </tr>
            </thead>
            <tbody>
              {sequence.map((entry) => (
                <tr key={entry.sequence_no}>
                  <td className="border border-neutral-900 px-2 py-1 text-right">{entry.L}</td>
                  {FORM_COLUMNS.map((col) => (
                    <Fragment key={`I-${col.apiDirection}`}>{inputCell(entry, col.apiDirection, "indication")}</Fragment>
                  ))}
                  {FORM_COLUMNS.map((col) => (
                    <Fragment key={`dL-${col.apiDirection}`}>{inputCell(entry, col.apiDirection, "deltaL")}</Fragment>
                  ))}
                  {FORM_COLUMNS.map((col) => (
                    <Fragment key={`E-${col.apiDirection}`}>{computedCell(entry, col.apiDirection, "E")}</Fragment>
                  ))}
                  {FORM_COLUMNS.map((col) => (
                    <Fragment key={`Ec-${col.apiDirection}`}>{computedCell(entry, col.apiDirection, "Ec")}</Fragment>
                  ))}
                  <td className="border border-neutral-900 px-2 py-1 text-right">{entry.mpe}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-5">
          <p className="text-sm">
            Check if |<i>E</i>
            <sub>c</sub>| ≤ |mpe|
          </p>
          <div className="mt-1.5 flex flex-wrap items-center gap-x-8 gap-y-2">
            <FormCheckbox label="Passed" checked={overall === "PASSED"} readOnly />
            <FormCheckbox label="Failed" checked={overall === "FAILED"} readOnly />
            {overall === "INCOMPLETE" ? (
              <span className="text-xs italic text-neutral-600">
                Incomplete — not every load's both directions have been entered yet.
              </span>
            ) : null}
          </div>
        </div>

        <div className="mt-5">
          <p className="text-sm">Remarks:</p>
          <textarea
            className="mt-1 min-h-16 w-full border border-neutral-900 bg-transparent px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-inset focus:ring-neutral-900 disabled:opacity-60"
            disabled={disabled}
            value={remarks}
            onChange={(event) => setRemarks(event.target.value)}
          />
        </div>
      </div>

      <p className="mx-auto max-w-4xl text-xs text-muted-foreground">
        Reproduced for data-entry fidelity to OIML R 76-2's page-10 "Weighing performance" form —
        not a copy of the copyrighted OIML document itself. Header fields above (Date, Observer,
        environmental conditions, zero-device status, initial-zero-setting flag, Remarks) are local
        to this page only — there is no session-update endpoint yet (tracked gap; see
        docs/architecture.md) — and reset on reload.
      </p>
    </div>
  );
}
