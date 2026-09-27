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
      I1: record.I1 ?? "",
      I2: record.I2 ?? "",
      visibleDisplacement: record.visible_displacement ?? null,
      result: record,
      submitting: false,
      error: null,
    };
  }
  return cells;
}

/**
 * Discrimination (R76-2 page 14, A.4.8) — THREE distinct sub-procedures,
 * one per instrument indication_type (never a client choice — the same
 * "server derives it" discipline as accuracy_class). This component renders
 * only the ONE sub-table matching `instrument.indication_type`, faithful to
 * that sub-table's own columns — they genuinely differ (analog has I1/I2
 * and a 0.7*mpe threshold; non-self-indicating is qualitative Yes/No;
 * digital compares against d, not mpe, and has no mpe column at all).
 * Digital is implemented for spec completeness (R76-1 A.4.8.2 exists) but
 * is NOT required for verification of digital instruments per clause
 * 8.3.3 — this page is unreachable through normal navigation for a digital
 * instrument (testChecklist.js keeps it N/A), reachable here only if
 * directly navigated to.
 */
export function DiscriminationFormTable({
  sessionId,
  sessionStatus,
  instrument,
  checks,
  verificationType,
  observerDefault,
  initialReadings,
}) {
  const disabled = sessionStatus !== "draft";
  const variant = checks[0]?.variant;

  const [observer, setObserver] = useState(observerDefault ?? "");
  const [remarks, setRemarks] = useState("");
  const [cells, setCells] = useState(() => cellsFromInitialReadings(initialReadings));

  function getCell(sequenceNo) {
    return cells[sequenceNo] ?? { I1: "", I2: "", visibleDisplacement: null, result: null, submitting: false, error: null };
  }

  function updateCell(sequenceNo, patch) {
    setCells((prev) => ({ ...prev, [sequenceNo]: { ...getCell(sequenceNo), ...patch } }));
  }

  async function submit(sequenceNo, body) {
    if (disabled) return;
    updateCell(sequenceNo, { submitting: true, error: null });
    try {
      const res = await apiFetch(`/sessions/${sessionId}/discrimination/readings`, {
        method: "POST",
        body: { sequence_no: sequenceNo, ...body },
      });
      updateCell(sequenceNo, { result: res, submitting: false, error: null });
    } catch (err) {
      const message = err instanceof ApiError && err.status === 409 ? "Session is no longer in draft — locked." : err.message;
      updateCell(sequenceNo, { submitting: false, error: message });
      toast.error(`Check #${sequenceNo}: ${message}`);
    }
  }

  function submitI1I2(check) {
    const cell = getCell(check.sequence_no);
    if (cell.I1 === "" || cell.I2 === "") return;
    submit(check.sequence_no, { I1: cell.I1, I2: cell.I2 });
  }

  function handleEnter(fn) {
    return (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        fn();
      }
    };
  }

  const overall = useMemo(() => {
    const results = checks.map((check) => getCell(check.sequence_no).result);
    if (results.some((r) => r && !r.passed)) return "FAILED";
    if (results.every((r) => r)) return "PASSED";
    return "INCOMPLETE";
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cells, checks]);

  const resolutionDuringTest = instrument?.d_value ?? instrument?.e_value ?? "";

  function analogTable() {
    return (
      <table className="w-full min-w-[560px] border-collapse text-xs">
        <thead>
          <tr>
            <th className="border border-neutral-900 px-2 py-1">Load, L</th>
            <th className="border border-neutral-900 px-2 py-1">Indication, I1</th>
            <th className="border border-neutral-900 px-2 py-1">Extra load, = |mpe|</th>
            <th className="border border-neutral-900 px-2 py-1">Indication, I2</th>
            <th className="border border-neutral-900 px-2 py-1">I2 − I1</th>
          </tr>
        </thead>
        <tbody>
          {checks.map((check) => {
            const cell = getCell(check.sequence_no);
            const colorClass = cell.result ? (cell.result.passed ? "text-emerald-700" : "text-red-700 font-semibold") : "text-neutral-500";
            return (
              <tr key={check.sequence_no}>
                <td className="border border-neutral-900 px-2 py-1 text-right">{roundLoadForDisplay(check.L)}</td>
                <td className="border border-neutral-900 p-0">
                  <input
                    className="h-7 w-full border-0 bg-transparent px-1 text-center focus:outline-none focus:ring-1 focus:ring-inset focus:ring-neutral-900 disabled:opacity-60"
                    inputMode="decimal"
                    disabled={disabled}
                    value={cell.I1}
                    onChange={(event) => updateCell(check.sequence_no, { I1: event.target.value })}
                  />
                </td>
                <td className="border border-neutral-900 px-2 py-1 text-right">{roundForDisplay(cell.result?.mpe ?? check.mpe)}</td>
                <td className="border border-neutral-900 p-0" title={cell.error ?? undefined}>
                  <input
                    className={`h-7 w-full border-0 bg-transparent px-1 text-center focus:outline-none focus:ring-1 focus:ring-inset focus:ring-neutral-900 disabled:opacity-60 ${cell.error ? "bg-red-50" : ""}`}
                    inputMode="decimal"
                    disabled={disabled}
                    value={cell.I2}
                    onChange={(event) => updateCell(check.sequence_no, { I2: event.target.value })}
                    onBlur={() => submitI1I2(check)}
                    onKeyDown={handleEnter(() => submitI1I2(check))}
                  />
                </td>
                <td className={`border border-neutral-900 px-2 py-1 text-center ${colorClass}`}>
                  {cell.submitting ? "…" : roundForDisplay(cell.result?.difference)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    );
  }

  function nonSelfIndicatingTable() {
    return (
      <table className="w-full min-w-[520px] border-collapse text-xs">
        <thead>
          <tr>
            <th className="border border-neutral-900 px-2 py-1">Load, L</th>
            <th className="border border-neutral-900 px-2 py-1">Extra load, = 0.4 |mpe|</th>
            <th className="border border-neutral-900 px-2 py-1">Visible displacement</th>
          </tr>
        </thead>
        <tbody>
          {checks.map((check) => {
            const cell = getCell(check.sequence_no);
            return (
              <tr key={check.sequence_no}>
                <td className="border border-neutral-900 px-2 py-1 text-right">{roundLoadForDisplay(check.L)}</td>
                <td className="border border-neutral-900 px-2 py-1 text-right">{roundForDisplay(cell.result?.extra_load ?? check.mpe)}</td>
                <td className="border border-neutral-900 px-2 py-1">
                  <div className="flex justify-center gap-6">
                    <FormCheckbox
                      label="Yes"
                      checked={cell.visibleDisplacement === true}
                      onClick={() => {
                        updateCell(check.sequence_no, { visibleDisplacement: true });
                        submit(check.sequence_no, { visible_displacement: true });
                      }}
                      disabled={disabled}
                    />
                    <FormCheckbox
                      label="No"
                      checked={cell.visibleDisplacement === false}
                      onClick={() => {
                        updateCell(check.sequence_no, { visibleDisplacement: false });
                        submit(check.sequence_no, { visible_displacement: false });
                      }}
                      disabled={disabled}
                    />
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    );
  }

  function digitalTable() {
    return (
      <table className="w-full min-w-[720px] border-collapse text-xs">
        <thead>
          <tr>
            <th className="border border-neutral-900 px-2 py-1">Load, L</th>
            <th className="border border-neutral-900 px-2 py-1">Indication, I1</th>
            <th className="border border-neutral-900 px-2 py-1">
              Removed load
              <br />Δ<i>L</i>
            </th>
            <th className="border border-neutral-900 px-2 py-1">Add 1/10 d</th>
            <th className="border border-neutral-900 px-2 py-1">Extra load, = 1.4 d</th>
            <th className="border border-neutral-900 px-2 py-1">Indication, I2</th>
            <th className="border border-neutral-900 px-2 py-1">I2 − I1</th>
          </tr>
        </thead>
        <tbody>
          {checks.map((check) => {
            const cell = getCell(check.sequence_no);
            const colorClass = cell.result ? (cell.result.passed ? "text-emerald-700" : "text-red-700 font-semibold") : "text-neutral-500";
            return (
              <tr key={check.sequence_no}>
                <td className="border border-neutral-900 px-2 py-1 text-right">{roundLoadForDisplay(check.L)}</td>
                <td className="border border-neutral-900 p-0">
                  <input
                    className="h-7 w-full border-0 bg-transparent px-1 text-center focus:outline-none focus:ring-1 focus:ring-inset focus:ring-neutral-900 disabled:opacity-60"
                    inputMode="decimal"
                    disabled={disabled}
                    value={cell.I1}
                    onChange={(event) => updateCell(check.sequence_no, { I1: event.target.value })}
                  />
                </td>
                {/* Removed load / Add 1/10 d — procedural steps, not stored
                    data (engine.discrimination.compute_discrimination_digital
                    only needs I1/I2/d/L) — blank for layout fidelity, per
                    the established "blank paper form" convention. */}
                <td className="border border-neutral-900 px-2 py-1" />
                <td className="border border-neutral-900 px-2 py-1" />
                <td className="border border-neutral-900 px-2 py-1 text-right">{roundForDisplay(cell.result?.d)}</td>
                <td className="border border-neutral-900 p-0" title={cell.error ?? undefined}>
                  <input
                    className={`h-7 w-full border-0 bg-transparent px-1 text-center focus:outline-none focus:ring-1 focus:ring-inset focus:ring-neutral-900 disabled:opacity-60 ${cell.error ? "bg-red-50" : ""}`}
                    inputMode="decimal"
                    disabled={disabled}
                    value={cell.I2}
                    onChange={(event) => updateCell(check.sequence_no, { I2: event.target.value })}
                    onBlur={() => submitI1I2(check)}
                    onKeyDown={handleEnter(() => submitI1I2(check))}
                  />
                </td>
                <td className={`border border-neutral-900 px-2 py-1 text-center ${colorClass}`}>
                  {cell.submitting ? "…" : roundForDisplay(cell.result?.difference)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    );
  }

  const checkText =
    variant === "analog"
      ? "Check if I2 − I1 ≥ 0.7 mpe"
      : variant === "digital"
        ? "Check if I2 − I1 ≥ d"
        : "Check if there is a visible displacement";

  return (
    <div className="grid gap-3">
      <CollapsibleFormHeader instrument={instrument} verificationType={verificationType} observer={observer}>
        <div className="mx-auto w-full max-w-4xl border-2 border-neutral-900 bg-white p-6 font-serif text-neutral-900 sm:p-8">
          <div className="mb-4 flex items-baseline justify-between border-b border-neutral-900 pb-1 text-xs">
            <span>OIML R 76-2: 2007 (E)</span>
            <span>Report page &hellip;./&hellip;.</span>
          </div>

          <h2 className="text-sm font-bold">4&nbsp;&nbsp;&nbsp;DISCRIMINATION AND SENSITIVITY</h2>
          <p className="ml-8 text-sm">
            4.1 Discrimination —{" "}
            {variant === "digital" ? "Digital indication (A.4.8.2)" : variant === "analog" ? "Analog indication (A.4.8.1)" : "Non-self-indicating instrument (A.4.8.1)"}
          </p>

          <div className="mt-5 grid gap-1.5 text-sm">
            <FormLine label="Application no.:" value={fmt(instrument?.application_no)} />
            <FormLine label="Type designation:" value={fmt(instrument?.type_designation)} />
            <FormLine label="Observer:" value={observer} editable disabled={disabled} onChange={setObserver} />
            <FormLine label="Verification scale interval, e:" value={fmt(instrument?.e_value)} />
            <FormLine label="Scale interval, d:" value={fmt(resolutionDuringTest)} />
          </div>
        </div>
      </CollapsibleFormHeader>

      <div className="mx-auto w-full max-w-4xl border-2 border-neutral-900 bg-white p-3 font-serif text-neutral-900 sm:p-4">
        <div className="overflow-x-auto">
          {variant === "analog" ? analogTable() : variant === "digital" ? digitalTable() : nonSelfIndicatingTable()}
        </div>

        <div className="mt-3">
          <p className="text-sm">{checkText}</p>
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

      <p className="mx-auto max-w-4xl text-xs text-muted-foreground">
        Reproduced for data-entry fidelity to OIML R 76-2's page-14 "Discrimination" form — not a copy of the
        copyrighted OIML document itself. The sub-table shown is derived from the instrument's own indication
        type, never chosen on this page. Header fields above (Observer, Remarks) are local to this page only,
        same known gap as the Weighing form (docs/architecture.md).
      </p>
    </div>
  );
}
