import { Fragment, useMemo, useState } from "react";
import { toast } from "sonner";
import { apiFetch, ApiError } from "@/lib/api";
import { FormCheckbox, FormLine } from "@/components/oiml/FormPrimitives";
import { CollapsibleFormHeader } from "@/components/oiml/CollapsibleFormHeader";
import { cn } from "@/lib/utils";

function fmt(value) {
  return value === undefined || value === null || value === "" ? "" : value;
}

function cellsFromInitialReadings(initialReadings) {
  const cells = {};
  for (const record of initialReadings ?? []) {
    cells[record.condition_key] = {
      indication: record.indication ?? "",
      significantFault: record.significant_fault,
      cellRemarks: record.remarks ?? "",
      result: record,
      submitting: false,
      error: null,
    };
  }
  return cells;
}

/**
 * The shared rendering for every RECORD-ONLY clause-12.x disturbance test
 * (12.1 AC mains dips, 12.2 electrical bursts, 12.4 electrostatic
 * discharges — see docs/architecture.md for which are built and why the
 * rest are deferred). One component, not one copy per test, because the
 * shape is identical across all of them: a fixed, predefined list of test
 * conditions (`initialConditions`, from `GET .../{apiPath}/conditions`),
 * each row asking the SAME three things — Indication, whether a
 * significant fault (> e) occurred, and Remarks — never a computed
 * verdict, because none is possible: these require physical EMC test
 * equipment this software has no way to drive or measure
 * (app/contracts/disturbance.py's module docstring has the full
 * reasoning). `headerExtras` is each test's own test-specific static
 * content (test voltage/duration text, category checkboxes) — the one
 * part that genuinely differs per OIML page and can't be shared.
 *
 * A "without disturbance" baseline row (`condition.has_fault_check ===
 * false`) records only a reference Indication — its significant-fault
 * cell is inert (matching the form's own greyed-out No/Yes cells for that
 * row), never user-editable, and the server independently forces it to
 * `false` regardless of what's sent (defense in depth, same discipline as
 * every other server-computed verdict here).
 */
export function DisturbanceFormTable({
  sessionId,
  sessionStatus,
  instrument,
  verificationType,
  observerDefault,
  title,
  clauseLabel,
  apiPath,
  initialConditions,
  headerExtras,
  groupLabels,
  initialReadings,
}) {
  const disabled = sessionStatus !== "draft";

  const [observer, setObserver] = useState(observerDefault ?? "");
  const [remarks, setRemarks] = useState("");
  const [cells, setCells] = useState(() => cellsFromInitialReadings(initialReadings));

  function getCell(conditionKey) {
    return cells[conditionKey] ?? { indication: "", significantFault: false, cellRemarks: "", result: null, submitting: false, error: null };
  }

  function updateCell(conditionKey, patch) {
    setCells((prev) => ({ ...prev, [conditionKey]: { ...getCell(conditionKey), ...patch } }));
  }

  async function submitCondition(condition) {
    const cell = getCell(condition.condition_key);
    if (disabled) return;
    updateCell(condition.condition_key, { submitting: true, error: null });
    const payload = {
      condition_key: condition.condition_key,
      indication: cell.indication === "" ? null : cell.indication,
      significant_fault: condition.has_fault_check ? cell.significantFault : false,
      remarks: cell.cellRemarks === "" ? null : cell.cellRemarks,
    };
    try {
      const res = await apiFetch(`/sessions/${sessionId}/${apiPath}/readings`, { method: "POST", body: payload });
      updateCell(condition.condition_key, { result: res, submitting: false, error: null });
    } catch (err) {
      const message = err instanceof ApiError && err.status === 409 ? "Session is no longer in draft — locked." : err.message;
      updateCell(condition.condition_key, { submitting: false, error: message });
      toast.error(`${condition.label}: ${message}`);
    }
  }

  const resolutionDuringTest = instrument?.d_value ?? instrument?.e_value ?? "";

  const overall = useMemo(() => {
    const faultCheckable = (initialConditions ?? []).filter((c) => c.has_fault_check);
    const results = faultCheckable.map((c) => getCell(c.condition_key).result);
    if (results.some((r) => r && !r.passed)) return "FAILED";
    if (results.length > 0 && results.every((r) => r)) return "PASSED";
    return "INCOMPLETE";
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cells, initialConditions]);

  let lastGroup = undefined;

  return (
    <div className="grid gap-3">
      <CollapsibleFormHeader instrument={instrument} verificationType={verificationType} observer={observer}>
        <div className="mx-auto w-full max-w-4xl border-2 border-neutral-900 bg-white p-6 font-serif text-neutral-900 sm:p-8">
          <div className="mb-4 flex items-baseline justify-between border-b border-neutral-900 pb-1 text-xs">
            <span>OIML R 76-2: 2007 (E)</span>
            <span>Report page &hellip;./&hellip;.</span>
          </div>

          <h2 className="text-sm font-bold">{title}</h2>
          {clauseLabel ? <p className="ml-8 text-sm">({clauseLabel})</p> : null}

          <div className="mt-5 grid gap-1.5 text-sm">
            <FormLine label="Application no.:" value={fmt(instrument?.application_no)} />
            <FormLine label="Type designation:" value={fmt(instrument?.type_designation)} />
            <FormLine label="Observer:" value={observer} editable disabled={disabled} onChange={setObserver} />
            <FormLine label="Verification scale interval, e:" value={fmt(instrument?.e_value)} />
            <FormLine label="Resolution during test (smaller than e):" value={fmt(resolutionDuringTest)} />
          </div>

          {headerExtras ? <div className="mt-4">{headerExtras}</div> : null}
        </div>
      </CollapsibleFormHeader>

      <div className="mx-auto w-full max-w-4xl border-2 border-neutral-900 bg-white p-3 font-serif text-neutral-900 sm:p-4">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] border-collapse text-xs">
            <thead>
              <tr>
                <th className="border border-neutral-900 px-2 py-1">Condition</th>
                <th className="border border-neutral-900 px-2 py-1">
                  Indication, <i>I</i>
                </th>
                <th className="border border-neutral-900 px-2 py-1" colSpan={2}>
                  Significant fault (&gt; <i>e</i>) or detection and reaction
                </th>
                <th className="border border-neutral-900 px-2 py-1">Remarks</th>
              </tr>
              <tr>
                <th className="border border-neutral-900 px-2 py-1" colSpan={2} />
                <th className="border border-neutral-900 px-2 py-1 font-normal">No</th>
                <th className="border border-neutral-900 px-2 py-1 font-normal">Yes</th>
                <th className="border border-neutral-900 px-2 py-1" />
              </tr>
            </thead>
            <tbody>
              {(initialConditions ?? []).map((condition) => {
                const cell = getCell(condition.condition_key);
                const showGroupHeader = groupLabels && condition.group && condition.group !== lastGroup;
                lastGroup = condition.group;
                return (
                  <Fragment key={condition.condition_key}>
                    {showGroupHeader ? (
                      <tr key={`group-${condition.group}`} className="bg-neutral-100">
                        <td colSpan={5} className="border border-neutral-900 px-2 py-1 font-bold">
                          {groupLabels[condition.group]}
                        </td>
                      </tr>
                    ) : null}
                    <tr className={cn(!condition.has_fault_check && "bg-neutral-50")}>
                      <td className="border border-neutral-900 px-2 py-1">{condition.label}</td>
                      <td className="border border-neutral-900 p-0" title={cell.error ?? undefined}>
                        <input
                          className={`h-7 w-full border-0 bg-transparent px-1 text-center focus:outline-none focus:ring-1 focus:ring-inset focus:ring-neutral-900 disabled:opacity-60 ${cell.error ? "bg-red-50" : ""}`}
                          inputMode="decimal"
                          disabled={disabled}
                          value={cell.indication}
                          onChange={(event) => updateCell(condition.condition_key, { indication: event.target.value })}
                          onBlur={() => submitCondition(condition)}
                          onKeyDown={(event) => {
                            if (event.key === "Enter") {
                              event.preventDefault();
                              submitCondition(condition);
                            }
                          }}
                        />
                      </td>
                      <td className="border border-neutral-900 px-2 py-1 text-center">
                        {condition.has_fault_check ? (
                          <FormCheckbox
                            checked={!cell.significantFault}
                            disabled={disabled}
                            onClick={() => {
                              updateCell(condition.condition_key, { significantFault: false });
                              submitCondition(condition);
                            }}
                          />
                        ) : null}
                      </td>
                      <td className="border border-neutral-900 px-2 py-1 text-center">
                        {condition.has_fault_check ? (
                          <FormCheckbox
                            checked={cell.significantFault}
                            disabled={disabled}
                            onClick={() => {
                              updateCell(condition.condition_key, { significantFault: true });
                              submitCondition(condition);
                            }}
                          />
                        ) : null}
                      </td>
                      <td className="border border-neutral-900 p-0">
                        <input
                          className="h-7 w-full border-0 bg-transparent px-1 text-xs focus:outline-none focus:ring-1 focus:ring-inset focus:ring-neutral-900 disabled:opacity-60"
                          disabled={disabled || !condition.has_fault_check}
                          value={cell.cellRemarks}
                          onChange={(event) => updateCell(condition.condition_key, { cellRemarks: event.target.value })}
                          onBlur={() => condition.has_fault_check && submitCondition(condition)}
                        />
                      </td>
                    </tr>
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className="mt-3">
          <p className="text-sm">Check if a significant fault occurred</p>
          <div className="mt-1.5 flex flex-wrap items-center gap-x-8 gap-y-2">
            <FormCheckbox label="Passed" checked={overall === "PASSED"} readOnly />
            <FormCheckbox label="Failed" checked={overall === "FAILED"} readOnly />
            {overall === "INCOMPLETE" ? (
              <span className="text-xs italic text-neutral-600">Incomplete — not every condition has been entered yet.</span>
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

      <p className="mx-auto max-w-4xl text-xs text-muted-foreground">
        Reproduced for data-entry fidelity to OIML R 76-2's "{title}" form — not a copy of the copyrighted OIML
        document itself. This is a RECORD-ONLY test: it requires physical EMC test equipment this software has no
        way to drive or measure, so there is no computed verdict — Passed/Failed above simply reflects whether any
        condition was marked as a significant fault. Header fields above (Observer, Remarks) are local to this
        page only, same known gap as every other OIML form here.
      </p>
    </div>
  );
}
