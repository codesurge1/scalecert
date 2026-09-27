import { useMemo, useState } from "react";
import { toast } from "sonner";
import { apiFetch, ApiError } from "@/lib/api";
import { FormCheckbox, FormLine } from "@/components/oiml/FormPrimitives";
import { CollapsibleFormHeader } from "@/components/oiml/CollapsibleFormHeader";
import { roundForDisplay, roundLoadForDisplay } from "@/lib/displayFormat";

function fmt(value) {
  return value === undefined || value === null || value === "" ? "" : value;
}

function cellsFromInitialReadings(initialReadings) {
  const cells = {};
  for (const record of initialReadings ?? []) {
    cells[record.sequence_no] = {
      displacement: record.permanent_displacement_mm,
      result: record,
      submitting: false,
      error: null,
    };
  }
  return cells;
}

/**
 * Sensitivity (R76-2 page 15, A.4.9) — non-self-indicating instruments
 * only. The pass threshold is tiered by accuracy class AND Max
 * (engine.sensitivity.sensitivity_threshold_mm) — shown explicitly below
 * the table, with the actual threshold for THIS instrument called out, not
 * just the generic three-tier text the paper form prints.
 */
export function SensitivityFormTable({
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
  const [remarks, setRemarks] = useState("");
  const [cells, setCells] = useState(() => cellsFromInitialReadings(initialReadings));

  function getCell(sequenceNo) {
    return cells[sequenceNo] ?? { displacement: "", result: null, submitting: false, error: null };
  }

  function updateCell(sequenceNo, patch) {
    setCells((prev) => ({ ...prev, [sequenceNo]: { ...getCell(sequenceNo), ...patch } }));
  }

  async function submitCheck(check) {
    const cell = getCell(check.sequence_no);
    if (cell.displacement === "" || disabled) return;
    updateCell(check.sequence_no, { submitting: true, error: null });
    try {
      const res = await apiFetch(`/sessions/${sessionId}/sensitivity/readings`, {
        method: "POST",
        body: { sequence_no: check.sequence_no, permanent_displacement_mm: cell.displacement },
      });
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

  const overall = useMemo(() => {
    const results = checks.map((check) => getCell(check.sequence_no).result);
    if (results.some((r) => r && !r.passed)) return "FAILED";
    if (results.length > 0 && results.every((r) => r)) return "PASSED";
    return "INCOMPLETE";
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cells, checks]);

  const thresholdMm = checks[0]?.threshold_mm;
  const resolutionDuringTest = instrument?.d_value ?? instrument?.e_value ?? "";

  return (
    <div className="grid gap-3">
      <CollapsibleFormHeader instrument={instrument} verificationType={verificationType} observer={observer}>
        <div className="mx-auto w-full max-w-3xl border-2 border-neutral-900 bg-white p-6 font-serif text-neutral-900 sm:p-8">
          <div className="mb-4 flex items-baseline justify-between border-b border-neutral-900 pb-1 text-xs">
            <span>OIML R 76-2: 2007 (E)</span>
            <span>Report page &hellip;./&hellip;.</span>
          </div>

          <h2 className="text-sm font-bold">4.2&nbsp;&nbsp;&nbsp;SENSITIVITY (non-self-indicating instrument) (A.4.9)</h2>

          <div className="mt-5 grid gap-1.5 text-sm">
            <FormLine label="Application no.:" value={fmt(instrument?.application_no)} />
            <FormLine label="Type designation:" value={fmt(instrument?.type_designation)} />
            <FormLine label="Observer:" value={observer} editable disabled={disabled} onChange={setObserver} />
            <FormLine label="Verification scale interval, e:" value={fmt(instrument?.e_value)} />
            <FormLine label="Resolution during test (smaller than e):" value={fmt(resolutionDuringTest)} />
          </div>
        </div>
      </CollapsibleFormHeader>

      <div className="mx-auto w-full max-w-3xl border-2 border-neutral-900 bg-white p-6 font-serif text-neutral-900 sm:p-8">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[480px] border-collapse text-xs">
            <thead>
              <tr>
                <th className="border border-neutral-900 px-2 py-1">Load L</th>
                <th className="border border-neutral-900 px-2 py-1">Extra load, = |mpe|</th>
                <th className="border border-neutral-900 px-2 py-1">Permanent displacement of indicating element</th>
              </tr>
            </thead>
            <tbody>
              {checks.map((check) => {
                const cell = getCell(check.sequence_no);
                const colorClass = cell.result ? (cell.result.passed ? "text-emerald-700" : "text-red-700 font-semibold") : "text-neutral-500";
                return (
                  <tr key={check.sequence_no}>
                    <td className="border border-neutral-900 px-2 py-1 text-right">{roundLoadForDisplay(check.L)}</td>
                    <td className="border border-neutral-900 px-2 py-1 text-right">{roundForDisplay(check.extra_load)}</td>
                    <td className="border border-neutral-900 p-0" title={cell.error ?? undefined}>
                      <div className="flex items-center">
                        <input
                          className={`h-7 w-full border-0 bg-transparent px-1 text-center focus:outline-none focus:ring-1 focus:ring-inset focus:ring-neutral-900 disabled:opacity-60 ${
                            cell.error ? "bg-red-50" : colorClass
                          }`}
                          inputMode="decimal"
                          disabled={disabled}
                          value={cell.displacement}
                          onChange={(event) => updateCell(check.sequence_no, { displacement: event.target.value })}
                          onBlur={() => submitCheck(check)}
                          onKeyDown={handleEnter(check)}
                        />
                        <span className="pr-2 text-neutral-600">mm</span>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className="mt-5 text-sm">
          <p>Check if the permanent displacement is equal to or greater than:</p>
          <ul className="ml-6 mt-1 list-disc">
            <li className={thresholdMm === "1" ? "font-semibold" : ""}>1 mm for an instrument of accuracy class I or II</li>
            <li className={thresholdMm === "2" ? "font-semibold" : ""}>2 mm for an instrument of accuracy class III or IIII with Max ≤ 30 kg</li>
            <li className={thresholdMm === "5" ? "font-semibold" : ""}>5 mm for an instrument of accuracy class III or IIII with Max &gt; 30 kg</li>
          </ul>
          <p className="mt-1 text-xs text-neutral-600">
            This instrument (Class {instrument?.accuracy_class}, Max={instrument?.max_capacity}g): threshold = {roundForDisplay(thresholdMm, 0)} mm.
          </p>
        </div>

        <div className="mt-3">
          <div className="flex flex-wrap items-center gap-x-8 gap-y-2">
            <FormCheckbox label="Passed" checked={overall === "PASSED"} readOnly />
            <FormCheckbox label="Failed" checked={overall === "FAILED"} readOnly />
            {overall === "INCOMPLETE" ? (
              <span className="text-xs italic text-neutral-600">Incomplete — not every check has been entered yet.</span>
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
        Reproduced for data-entry fidelity to OIML R 76-2's page-15 "Sensitivity" form — not a copy of the
        copyrighted OIML document itself. Header fields above (Observer, Remarks) are local to this page only,
        same known gap as the Weighing form (docs/architecture.md).
      </p>
    </div>
  );
}
