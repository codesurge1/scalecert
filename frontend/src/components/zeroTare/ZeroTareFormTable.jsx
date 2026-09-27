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

function fmt(value) {
  return value === undefined || value === null || value === "" ? "" : value;
}

function cellsFromInitialReadings(initialReadings) {
  const cells = {};
  for (const record of initialReadings ?? []) {
    cells[record.sequence_no] = {
      indication: record.I,
      deltaL: record.delta_l,
      result: { E: record.E, Ec: record.Ec, mpe: record.mpe, passed: record.passed },
      submitting: false,
      error: null,
    };
  }
  return cells;
}

/**
 * Zero/tare device accuracy — the Weighing change-point formula applied to
 * a handful of small, server-derived check loads instead of a full load
 * sequence (engine/zero_tare.py; docs/architecture.md). Simpler than
 * WeighingFormTable by design: no ↓/↑ bidirectional columns, no
 * environmental-conditions grid — just Location/Load/I/ΔL/E/Ec/mpe per
 * check, matching the "a few readings on the zero/tare device" scope.
 * Same OIML bordered-document-sheet look as the other two forms in this
 * task, reusing the shared FormPrimitives.
 */
export function ZeroTareFormTable({
  sessionId,
  sessionStatus,
  instrument,
  checks,
  verificationType,
  observerDefault,
  initialReadings,
}) {
  const disabled = sessionStatus !== "draft";

  const [observer, setObserver] = useState(observerDefault ?? "");
  const [zeroDeviceStatus, setZeroDeviceStatus] = useState("");
  const [e0, setE0] = useState(initialReadings?.[0]?.E0 ?? "0");
  const [remarks, setRemarks] = useState("");
  const [cells, setCells] = useState(() => cellsFromInitialReadings(initialReadings));

  function getCell(sequenceNo) {
    return cells[sequenceNo] ?? { indication: "", deltaL: "0", result: null, submitting: false, error: null };
  }

  function updateCell(sequenceNo, patch) {
    setCells((prev) => ({ ...prev, [sequenceNo]: { ...getCell(sequenceNo), ...patch } }));
  }

  async function submitCheck(check) {
    const cell = getCell(check.sequence_no);
    if (cell.indication === "" || disabled) return;
    updateCell(check.sequence_no, { submitting: true, error: null });
    // Decimal-as-string discipline (CLAUDE.md): indication/deltaL/e0 go to
    // the API exactly as typed — never through Number()/parseFloat().
    const payload = {
      sequence_no: check.sequence_no,
      I: cell.indication,
      delta_l: cell.deltaL === "" ? "0" : cell.deltaL,
      E0: e0,
    };
    try {
      const res = await apiFetch(`/sessions/${sessionId}/zero-tare/readings`, { method: "POST", body: payload });
      updateCell(check.sequence_no, { result: res, submitting: false, error: null });
    } catch (err) {
      const message = err instanceof ApiError && err.status === 409 ? "Session is no longer in draft — locked." : err.message;
      updateCell(check.sequence_no, { submitting: false, error: message });
      toast.error(`Check #${check.sequence_no}: ${message}`);
    }
  }

  function handleEnter(check) {
    return (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        submitCheck(check);
      }
    };
  }

  const resolutionDuringTest = instrument?.d_value ?? instrument?.e_value ?? "";

  const overall = useMemo(() => {
    const results = checks.map((check) => getCell(check.sequence_no).result);
    if (results.some((r) => r && !r.passed)) return "FAILED";
    if (results.length > 0 && results.every((r) => r)) return "PASSED";
    return "INCOMPLETE";
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cells, checks]);

  return (
    <div className="grid gap-3">
      <CollapsibleFormHeader instrument={instrument} verificationType={verificationType} observer={observer}>
        <div className="mx-auto w-full max-w-3xl border-2 border-neutral-900 bg-white p-6 font-serif text-neutral-900 sm:p-8">
          <div className="mb-4 flex items-baseline justify-between border-b border-neutral-900 pb-1 text-xs">
            <span>OIML R 76-2: 2007 (E)</span>
            <span>Report page &hellip;./&hellip;.</span>
          </div>

          <h2 className="text-sm font-bold">1&nbsp;&nbsp;&nbsp;WEIGHING PERFORMANCE (A.4.4)</h2>
          <p className="ml-8 text-sm">(Zero/tare device accuracy)</p>

          <div className="mt-5 grid gap-1.5 text-sm">
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

          <div className="mt-5 text-sm">
            <p>
              <i>E</i> = <i>I</i> + ½ <i>e</i> − Δ<i>L</i> − <i>L</i>, &nbsp; <i>E</i>
              <sub>c</sub> = <i>E</i> − <i>E</i>
              <sub>0</sub>
            </p>
            <div className="mt-1 flex items-baseline gap-2 text-xs text-neutral-700">
              <span>
                <i>E</i>
                <sub>0</sub> =
              </span>
              <input
                className="w-24 border-0 border-b border-dotted border-neutral-500 bg-transparent px-1 text-center focus:outline-none focus:border-solid focus:border-neutral-900 disabled:opacity-60"
                inputMode="decimal"
                disabled={disabled}
                value={e0}
                onChange={(event) => setE0(event.target.value)}
              />
              <span>g</span>
            </div>
          </div>
        </div>
      </CollapsibleFormHeader>

      <div className="mx-auto w-full max-w-3xl border-2 border-neutral-900 bg-white p-3 font-serif text-neutral-900 sm:p-4">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[520px] border-collapse text-xs">
            <thead>
              <tr>
                <th className="border border-neutral-900 px-2 py-1">Check</th>
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
              {checks.map((check) => {
                const cell = getCell(check.sequence_no);
                const colorClass = cell.result ? (cell.result.passed ? "text-emerald-700" : "text-red-700 font-semibold") : "text-neutral-500";
                return (
                  <tr key={check.sequence_no}>
                    <td className="border border-neutral-900 px-2 py-1 text-center">{check.sequence_no + 1}</td>
                    <td className="border border-neutral-900 px-2 py-1 text-right">{roundLoadForDisplay(check.L)}</td>
                    <td className="border border-neutral-900 p-0" title={cell.error ?? undefined}>
                      <input
                        className={`h-7 w-full border-0 bg-transparent px-1 text-center focus:outline-none focus:ring-1 focus:ring-inset focus:ring-neutral-900 disabled:opacity-60 ${cell.error ? "bg-red-50" : ""}`}
                        inputMode="decimal"
                        disabled={disabled}
                        value={cell.indication}
                        onChange={(event) => updateCell(check.sequence_no, { indication: event.target.value })}
                        onKeyDown={handleEnter(check)}
                      />
                    </td>
                    <td className="border border-neutral-900 p-0">
                      <input
                        className="h-7 w-full border-0 bg-transparent px-1 text-center focus:outline-none focus:ring-1 focus:ring-inset focus:ring-neutral-900 disabled:opacity-60"
                        inputMode="decimal"
                        disabled={disabled}
                        value={cell.deltaL}
                        onChange={(event) => updateCell(check.sequence_no, { deltaL: event.target.value })}
                        onBlur={() => submitCheck(check)}
                        onKeyDown={handleEnter(check)}
                      />
                    </td>
                    <td className={`border border-neutral-900 px-2 py-1 text-center ${colorClass}`}>
                      {cell.submitting ? "…" : roundForDisplay(cell.result?.E)}
                    </td>
                    <td className={`border border-neutral-900 px-2 py-1 text-center ${colorClass}`}>
                      {cell.submitting ? "…" : roundForDisplay(cell.result?.Ec)}
                    </td>
                    <td className="border border-neutral-900 px-2 py-1 text-right">{roundForDisplay(cell.result?.mpe ?? check.mpe)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className="mt-3">
          <p className="text-sm">
            Check if |<i>E</i>
            <sub>c</sub>| ≤ |mpe|
          </p>
          <div className="mt-1.5 flex flex-wrap items-center gap-x-8 gap-y-2">
            <FormCheckbox label="Passed" checked={overall === "PASSED"} readOnly />
            <FormCheckbox label="Failed" checked={overall === "FAILED"} readOnly />
            {overall === "INCOMPLETE" ? (
              <span className="text-xs italic text-neutral-600">Incomplete — not every check has been entered yet.</span>
            ) : null}
          </div>
        </div>

        <div className="mt-3">
          <p className="text-sm">Remarks:</p>
          <textarea
            className="mt-1 min-h-10 w-full border border-neutral-900 bg-transparent px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-inset focus:ring-neutral-900 disabled:opacity-60"
            disabled={disabled}
            value={remarks}
            onChange={(event) => setRemarks(event.target.value)}
          />
        </div>
      </div>

      <p className="mx-auto max-w-3xl text-xs text-muted-foreground">
        Reproduced for data-entry fidelity to OIML R 76-2's Weighing-performance form, applied here to the
        zero/tare device accuracy variant (A.4.4) — not a copy of the copyrighted OIML document itself. Header
        fields above (Observer, zero-device status, Remarks) are local to this page only, same known gap as
        the Weighing form (docs/architecture.md).
      </p>
    </div>
  );
}
