import { useMemo, useState } from "react";
import { toast } from "sonner";
import { apiFetch, ApiError } from "@/lib/api";
import { FormBox, FormCheckbox, FormLine } from "@/components/oiml/FormPrimitives";
import { roundForDisplay, roundLoadForDisplay } from "@/lib/displayFormat";

const ZERO_DEVICE_OPTIONS = [
  { value: "non_existent", label: "Non-existent" },
  { value: "in_operation", label: "In operation" },
];

const ROWS_PER_SERIES = 10;

function fmt(value) {
  return value === undefined || value === null || value === "" ? "" : value;
}

// Seeds local per-cell edit state from the two already-fetched series
// (GET .../repeatability/readings always returns both, L/mpe populated even
// with zero readings) — same "reconstruct on refresh" pattern as the other
// two forms.
function cellsFromSeries(seriesList) {
  const cells = {};
  for (const series of seriesList ?? []) {
    for (const reading of series.readings) {
      cells[`${series.series_no}-${reading.sequence_no}`] = {
        indication: reading.I,
        deltaL: reading.delta_l,
        E: reading.E,
        submitting: false,
        error: null,
      };
    }
  }
  return cells;
}

/**
 * Repeatability (R76-2 page 16, A.4.10) — structurally different from
 * Weighing/Zero-tare, not a variant of them: two independent 10-reading
 * series at fixed loads (~50% and ~100% of Max), NO E0/Ec (E is checked
 * directly against mpe), and a series' pass/fail depends on the WHOLE
 * series (every reading within mpe, AND the spread Emax-Emin within mpe),
 * not any single reading — see engine/repeatability.py. Two side-by-side
 * 10-row tables reproduce the form's own "weighing 1-10" / "weighing 11-20"
 * layout.
 */
export function RepeatabilityFormTable({ sessionId, sessionStatus, instrument, series, observerDefault }) {
  const disabled = sessionStatus !== "draft";

  const [observer, setObserver] = useState(observerDefault ?? "");
  const [zeroDeviceStatus, setZeroDeviceStatus] = useState("");
  const [remarks, setRemarks] = useState("");
  const [cells, setCells] = useState(() => cellsFromSeries(series));
  // The up-to-date series objects (L/mpe/spread/passed/...) — replaced
  // wholesale per series whenever a submission for that series returns,
  // since the aggregate is inherently a property of the whole series, not
  // any one reading (app/services/repeatability.py mirrors this exactly).
  const [seriesState, setSeriesState] = useState(() =>
    Object.fromEntries((series ?? []).map((s) => [s.series_no, s])),
  );

  function getCell(seriesNo, sequenceNo) {
    return cells[`${seriesNo}-${sequenceNo}`] ?? { indication: "", deltaL: "0", E: null, submitting: false, error: null };
  }

  function updateCell(seriesNo, sequenceNo, patch) {
    setCells((prev) => ({
      ...prev,
      [`${seriesNo}-${sequenceNo}`]: { ...getCell(seriesNo, sequenceNo), ...patch },
    }));
  }

  async function submitReading(seriesNo, sequenceNo) {
    const cell = getCell(seriesNo, sequenceNo);
    if (cell.indication === "" || disabled) return;
    updateCell(seriesNo, sequenceNo, { submitting: true, error: null });
    // Decimal-as-string discipline (CLAUDE.md): never Number()/parseFloat().
    const payload = {
      series_no: seriesNo,
      sequence_no: sequenceNo,
      I: cell.indication,
      delta_l: cell.deltaL === "" ? "0" : cell.deltaL,
    };
    try {
      const seriesOut = await apiFetch(`/sessions/${sessionId}/repeatability/readings`, { method: "POST", body: payload });
      setSeriesState((prev) => ({ ...prev, [seriesNo]: seriesOut }));
      setCells((prev) => {
        const next = { ...prev };
        for (const reading of seriesOut.readings) {
          next[`${seriesNo}-${reading.sequence_no}`] = {
            indication: reading.I,
            deltaL: reading.delta_l,
            E: reading.E,
            submitting: false,
            error: null,
          };
        }
        return next;
      });
    } catch (err) {
      const message = err instanceof ApiError && err.status === 409 ? "Session is no longer in draft — locked." : err.message;
      updateCell(seriesNo, sequenceNo, { submitting: false, error: message });
      toast.error(`Series ${seriesNo}, reading ${sequenceNo + 1}: ${message}`);
    }
  }

  function handleEnter(seriesNo, sequenceNo) {
    return (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        submitReading(seriesNo, sequenceNo);
      }
    };
  }

  const overall = useMemo(() => {
    const both = [seriesState[1], seriesState[2]];
    if (both.some((s) => s && s.passed === false)) return "FAILED";
    if (both.every((s) => s && s.passed === true)) return "PASSED";
    return "INCOMPLETE";
  }, [seriesState]);

  function seriesTable(seriesNo, rowOffset) {
    const s = seriesState[seriesNo];
    return (
      <div>
        <FormBox label={`Load (weighing ${rowOffset + 1}-${rowOffset + ROWS_PER_SERIES})`} value={roundLoadForDisplay(s?.L)} width="w-28" />
        <table className="mt-2 w-full border-collapse text-xs">
          <thead>
            <tr>
              <th className="border border-neutral-900 px-2 py-1" />
              <th className="border border-neutral-900 px-2 py-1">
                Indication, <i>I</i>
              </th>
              <th className="border border-neutral-900 px-2 py-1">
                Add. load, Δ<i>L</i>
              </th>
              <th className="border border-neutral-900 px-2 py-1">
                <i>E</i>
              </th>
            </tr>
          </thead>
          <tbody>
            {Array.from({ length: ROWS_PER_SERIES }, (_, i) => i).map((sequenceNo) => {
              const cell = getCell(seriesNo, sequenceNo);
              const readingOut = s?.readings.find((r) => r.sequence_no === sequenceNo);
              const colorClass = readingOut ? (readingOut.within_mpe ? "text-emerald-700" : "text-red-700 font-semibold") : "text-neutral-500";
              return (
                <tr key={sequenceNo}>
                  <td className="border border-neutral-900 px-2 py-1 text-center">{rowOffset + sequenceNo + 1}</td>
                  <td className="border border-neutral-900 p-0" title={cell.error ?? undefined}>
                    <input
                      className={`h-7 w-full border-0 bg-transparent px-1 text-center focus:outline-none focus:ring-1 focus:ring-inset focus:ring-neutral-900 disabled:opacity-60 ${cell.error ? "bg-red-50" : ""}`}
                      inputMode="decimal"
                      disabled={disabled}
                      value={cell.indication}
                      onChange={(event) => updateCell(seriesNo, sequenceNo, { indication: event.target.value })}
                      onKeyDown={handleEnter(seriesNo, sequenceNo)}
                    />
                  </td>
                  <td className="border border-neutral-900 p-0">
                    <input
                      className="h-7 w-full border-0 bg-transparent px-1 text-center focus:outline-none focus:ring-1 focus:ring-inset focus:ring-neutral-900 disabled:opacity-60"
                      inputMode="decimal"
                      disabled={disabled}
                      value={cell.deltaL}
                      onChange={(event) => updateCell(seriesNo, sequenceNo, { deltaL: event.target.value })}
                      onBlur={() => submitReading(seriesNo, sequenceNo)}
                      onKeyDown={handleEnter(seriesNo, sequenceNo)}
                    />
                  </td>
                  <td className={`border border-neutral-900 px-2 py-1 text-center ${colorClass}`}>
                    {cell.submitting ? "…" : roundForDisplay(readingOut?.E)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        <div className="mt-2 flex flex-col gap-1 text-xs">
          <FormBox label={`Emax − Emin (weighing ${rowOffset + 1}-${rowOffset + ROWS_PER_SERIES})`} value={roundForDisplay(s?.spread)} width="w-24" />
          <FormBox label="mpe" value={roundForDisplay(s?.mpe)} width="w-24" />
        </div>
      </div>
    );
  }

  const resolutionDuringTest = instrument?.d_value ?? instrument?.e_value ?? "";

  return (
    <div className="grid gap-3">
      <div className="mx-auto w-full max-w-5xl border-2 border-neutral-900 bg-white p-6 font-serif text-neutral-900 sm:p-8">
        <div className="mb-4 flex items-baseline justify-between border-b border-neutral-900 pb-1 text-xs">
          <span>OIML R 76-2: 2007 (E)</span>
          <span>Report page &hellip;./&hellip;.</span>
        </div>

        <h2 className="text-sm font-bold">5&nbsp;&nbsp;&nbsp;REPEATABILITY (A.4.10)</h2>

        <div className="mt-5 grid gap-1.5 text-sm sm:grid-cols-2 sm:gap-x-10">
          <FormLine label="Application no.:" value={fmt(instrument?.application_no)} />
          <FormLine label="Type designation:" value={fmt(instrument?.type_designation)} />
          <FormLine label="Observer:" value={observer} editable disabled={disabled} onChange={setObserver} />
          <FormLine label="Verification scale interval, e:" value={fmt(instrument?.e_value)} />
          <FormLine label="Resolution during test (smaller than e):" value={fmt(resolutionDuringTest)} />
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

        <p className="mt-5 text-sm">
          <i>E</i> = <i>I</i> + ½ <i>e</i> − Δ<i>L</i> − <i>L</i>
        </p>

        <div className="mt-4 grid gap-6 overflow-x-auto sm:grid-cols-2">
          {seriesTable(1, 0)}
          {seriesTable(2, ROWS_PER_SERIES)}
        </div>

        <div className="mt-6">
          <p className="text-sm">
            Check if a) <i>E</i> ≤ mpe (3.6 of R 76-1); b) <i>E</i>
            <sub>max</sub> − <i>E</i>
            <sub>min</sub> ≤ absolute value of mpe (3.6.1 of R 76-1)
          </p>
          <div className="mt-1.5 flex flex-wrap items-center gap-x-8 gap-y-2">
            <FormCheckbox label="Passed" checked={overall === "PASSED"} readOnly />
            <FormCheckbox label="Failed" checked={overall === "FAILED"} readOnly />
            {overall === "INCOMPLETE" ? (
              <span className="text-xs italic text-neutral-600">Incomplete — not every reading in both series has been entered yet.</span>
            ) : null}
          </div>
        </div>

        <div className="mt-5">
          <p className="text-sm">Remarks:</p>
          <textarea
            className="mt-1 min-h-14 w-full border border-neutral-900 bg-transparent px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-inset focus:ring-neutral-900 disabled:opacity-60"
            disabled={disabled}
            value={remarks}
            onChange={(event) => setRemarks(event.target.value)}
          />
        </div>
      </div>

      <p className="mx-auto max-w-5xl text-xs text-muted-foreground">
        Reproduced for data-entry fidelity to OIML R 76-2's page-16 "Repeatability" form — not a copy of the
        copyrighted OIML document itself. Header fields above (Observer, zero-device status, Remarks) are
        local to this page only, same known gap as the Weighing form (docs/architecture.md).
      </p>
    </div>
  );
}
