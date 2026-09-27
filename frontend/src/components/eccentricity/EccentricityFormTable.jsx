import { useMemo, useState } from "react";
import { toast } from "sonner";
import { apiFetch, ApiError } from "@/lib/api";
import { FormCheckbox, FormLine } from "@/components/oiml/FormPrimitives";
import { CollapsibleFormHeader } from "@/components/oiml/CollapsibleFormHeader";
import { roundForDisplay, roundLoadForDisplay } from "@/lib/displayFormat";

const ZERO_DEVICE_OPTIONS = [
  { value: "non_existent", label: "Non-existent" },
  { value: "not_in_operation", label: "Not in operation" },
  { value: "out_of_working_range", label: "Out of working range" },
];

// 1=top-left, 2=top-right, 3=bottom-right, 4=bottom-left, clockwise —
// R76-2 page 12's own position sketch (engine/eccentricity.py).
const POSITIONS = [1, 2, 3, 4];

function fmt(value) {
  return value === undefined || value === null || value === "" ? "" : value;
}

function cellsFromInitialReadings(initialReadings) {
  const cells = {};
  for (const record of initialReadings ?? []) {
    cells[record.position_no] = {
      indication: record.I,
      deltaL: record.delta_l,
      e0: record.E0,
      result: { E: record.E, Ec: record.Ec, mpe: record.mpe, passed: record.passed },
      submitting: false,
      error: null,
    };
  }
  return cells;
}

/**
 * Eccentricity, 3.1 weights (R76-2 page 12, A.4.7) — the Weighing
 * change-point formula (engine/eccentricity.py) applied independently at
 * each of 4 receptor positions, each with its OWN E0 (re-measured before
 * each position — a per-row input here, per the task's own simplification
 * of the source form's two-row-per-position "zero check then measurement"
 * layout into one row with an E0 field). The "mobile instrument?"
 * pre-question is out of scope to fully model (per this task) and is kept
 * as a local-only remark, not submitted/stored.
 */
export function EccentricityFormTable({
  sessionId,
  sessionStatus,
  instrument,
  setup,
  verificationType,
  observerDefault,
  initialReadings,
}) {
  const disabled = sessionStatus !== "draft";

  const [observer, setObserver] = useState(observerDefault ?? "");
  const [zeroDeviceStatus, setZeroDeviceStatus] = useState("");
  const [mobileInstrument, setMobileInstrument] = useState(null);
  const [remarks, setRemarks] = useState("");
  const [cells, setCells] = useState(() => cellsFromInitialReadings(initialReadings));

  function getCell(positionNo) {
    return cells[positionNo] ?? { indication: "", deltaL: "0", e0: "0", result: null, submitting: false, error: null };
  }

  function updateCell(positionNo, patch) {
    setCells((prev) => ({ ...prev, [positionNo]: { ...getCell(positionNo), ...patch } }));
  }

  async function submitPosition(positionNo) {
    const cell = getCell(positionNo);
    if (cell.indication === "" || disabled) return;
    updateCell(positionNo, { submitting: true, error: null });
    // Decimal-as-string discipline (CLAUDE.md): never Number()/parseFloat().
    const payload = {
      position_no: positionNo,
      I: cell.indication,
      delta_l: cell.deltaL === "" ? "0" : cell.deltaL,
      E0: cell.e0 === "" ? "0" : cell.e0,
    };
    try {
      const res = await apiFetch(`/sessions/${sessionId}/eccentricity/readings`, { method: "POST", body: payload });
      updateCell(positionNo, { result: res, submitting: false, error: null });
    } catch (err) {
      const message = err instanceof ApiError && err.status === 409 ? "Session is no longer in draft — locked." : err.message;
      updateCell(positionNo, { submitting: false, error: message });
      toast.error(`Position ${positionNo}: ${message}`);
    }
  }

  function handleEnter(positionNo) {
    return (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        submitPosition(positionNo);
      }
    };
  }

  const resolutionDuringTest = instrument?.d_value ?? instrument?.e_value ?? "";

  const overall = useMemo(() => {
    const results = POSITIONS.map((p) => getCell(p).result);
    if (results.some((r) => r && !r.passed)) return "FAILED";
    if (results.every((r) => r)) return "PASSED";
    return "INCOMPLETE";
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cells]);

  return (
    <div className="grid gap-3">
      <CollapsibleFormHeader instrument={instrument} verificationType={verificationType} observer={observer}>
        <div className="mx-auto w-full max-w-3xl border-2 border-neutral-900 bg-white p-6 font-serif text-neutral-900 sm:p-8">
          <div className="mb-4 flex items-baseline justify-between border-b border-neutral-900 pb-1 text-xs">
            <span>OIML R 76-2: 2007 (E)</span>
            <span>Report page &hellip;./&hellip;.</span>
          </div>

          <h2 className="text-sm font-bold">3&nbsp;&nbsp;&nbsp;ECCENTRICITY (A.4.7)</h2>
          <p className="ml-8 text-sm">3.1 Eccentricity using weights (A.4.7.1, 2 and 3)</p>

          <div className="mt-5 grid gap-1.5 text-sm">
            <FormLine label="Application no.:" value={fmt(instrument?.application_no)} />
            <FormLine label="Type designation:" value={fmt(instrument?.type_designation)} />
            <FormLine label="Observer:" value={observer} editable disabled={disabled} onChange={setObserver} />
            <FormLine label="Verification scale interval, e:" value={fmt(instrument?.e_value)} />
            <FormLine label="Resolution during test (smaller than e):" value={fmt(resolutionDuringTest)} />
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-x-8 gap-y-2 text-sm">
            <span>Test(s) performed on a mobile instrument:</span>
            <FormCheckbox label="Yes" checked={mobileInstrument === "yes"} onClick={() => !disabled && setMobileInstrument("yes")} />
            <FormCheckbox label="No" checked={mobileInstrument === "no"} onClick={() => !disabled && setMobileInstrument("no")} />
            <span className="text-xs italic text-neutral-600">(remark only — not modeled beyond this flag)</span>
          </div>

          <div className="mt-5 flex items-start gap-6">
            <div>
              <p className="mb-1 text-sm">Location of test loads:</p>
              <div className="grid w-28 grid-cols-2 grid-rows-2 border border-neutral-900 text-center text-sm">
                <div className="border-b border-r border-dashed border-neutral-500 py-2">1</div>
                <div className="border-b border-dashed border-neutral-500 py-2">2</div>
                <div className="border-r border-dashed border-neutral-500 py-2">4</div>
                <div className="py-2">3</div>
              </div>
            </div>
            <div className="mt-5">
              <p className="text-sm">Automatic zero-setting and zero-tracking device is:</p>
              <div className="mt-1.5 flex flex-wrap gap-x-6 gap-y-2">
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
          </div>

          <p className="mt-5 text-sm">
            <i>E</i> = <i>I</i> + ½ <i>e</i> − Δ<i>L</i> − <i>L</i>, &nbsp; <i>E</i>
            <sub>c</sub> = <i>E</i> − <i>E</i>
            <sub>0</sub> with <i>E</i>
            <sub>0</sub> determined prior to each measurement
          </p>
        </div>
      </CollapsibleFormHeader>

      <div className="mx-auto w-full max-w-3xl border-2 border-neutral-900 bg-white p-6 font-serif text-neutral-900 sm:p-8">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] border-collapse text-xs">
            <thead>
              <tr>
                <th className="border border-neutral-900 px-2 py-1">Location</th>
                <th className="border border-neutral-900 px-2 py-1">
                  <i>E</i>
                  <sub>0</sub>
                </th>
                <th className="border border-neutral-900 px-2 py-1">
                  Load, <i>L</i>
                </th>
                <th className="border border-neutral-900 px-2 py-1">
                  Indication, <i>I</i>
                </th>
                <th className="border border-neutral-900 px-2 py-1">
                  Add. load, Δ<i>L</i>
                </th>
                <th className="border border-neutral-900 px-2 py-1">
                  Error, <i>E</i>
                </th>
                <th className="border border-neutral-900 px-2 py-1">
                  Corrected error, <i>E</i>
                  <sub>c</sub>
                </th>
                <th className="border border-neutral-900 px-2 py-1">mpe</th>
              </tr>
            </thead>
            <tbody>
              {POSITIONS.map((positionNo) => {
                const cell = getCell(positionNo);
                const colorClass = cell.result ? (cell.result.passed ? "text-emerald-700" : "text-red-700 font-semibold") : "text-neutral-500";
                return (
                  <tr key={positionNo}>
                    <td className="border border-neutral-900 px-2 py-1 text-center">{positionNo}</td>
                    <td className="border border-neutral-900 p-0">
                      <input
                        className="h-7 w-full border-0 bg-transparent px-1 text-center focus:outline-none focus:ring-1 focus:ring-inset focus:ring-neutral-900 disabled:opacity-60"
                        inputMode="decimal"
                        disabled={disabled}
                        value={cell.e0}
                        onChange={(event) => updateCell(positionNo, { e0: event.target.value })}
                      />
                    </td>
                    <td className="border border-neutral-900 px-2 py-1 text-right">{roundLoadForDisplay(setup?.L)}</td>
                    <td className="border border-neutral-900 p-0" title={cell.error ?? undefined}>
                      <input
                        className={`h-7 w-full border-0 bg-transparent px-1 text-center focus:outline-none focus:ring-1 focus:ring-inset focus:ring-neutral-900 disabled:opacity-60 ${cell.error ? "bg-red-50" : ""}`}
                        inputMode="decimal"
                        disabled={disabled}
                        value={cell.indication}
                        onChange={(event) => updateCell(positionNo, { indication: event.target.value })}
                        onKeyDown={handleEnter(positionNo)}
                      />
                    </td>
                    <td className="border border-neutral-900 p-0">
                      <input
                        className="h-7 w-full border-0 bg-transparent px-1 text-center focus:outline-none focus:ring-1 focus:ring-inset focus:ring-neutral-900 disabled:opacity-60"
                        inputMode="decimal"
                        disabled={disabled}
                        value={cell.deltaL}
                        onChange={(event) => updateCell(positionNo, { deltaL: event.target.value })}
                        onBlur={() => submitPosition(positionNo)}
                        onKeyDown={handleEnter(positionNo)}
                      />
                    </td>
                    <td className={`border border-neutral-900 px-2 py-1 text-center ${colorClass}`}>
                      {cell.submitting ? "…" : roundForDisplay(cell.result?.E)}
                    </td>
                    <td className={`border border-neutral-900 px-2 py-1 text-center ${colorClass}`}>
                      {cell.submitting ? "…" : roundForDisplay(cell.result?.Ec)}
                    </td>
                    <td className="border border-neutral-900 px-2 py-1 text-right">{roundForDisplay(cell.result?.mpe ?? setup?.mpe)}</td>
                  </tr>
                );
              })}
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
              <span className="text-xs italic text-neutral-600">Incomplete — not every position has been entered yet.</span>
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

      <p className="mx-auto max-w-3xl text-xs text-muted-foreground">
        Reproduced for data-entry fidelity to OIML R 76-2's page-12 "Eccentricity using weights" form — not a
        copy of the copyrighted OIML document itself. Header fields above (Observer, zero-device status,
        mobile-instrument flag, Remarks) are local to this page only, same known gap as the Weighing form
        (docs/architecture.md).
      </p>
    </div>
  );
}
