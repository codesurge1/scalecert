import { useState } from "react";
import { toast } from "sonner";
import { apiFetch, ApiError } from "@/lib/api";
import { FormBox, FormCheckbox, FormLine } from "@/components/oiml/FormPrimitives";
import { roundForDisplay, roundLoadForDisplay } from "@/lib/displayFormat";

const ZERO_DEVICE_OPTIONS = [
  { value: "non_existent", label: "Non-existent" },
  { value: "not_in_operation", label: "Not in operation" },
  { value: "out_of_working_range", label: "Out of working range" },
];

// 1 = reference position, 2-5 = tilted (engine/tilting.py TILT_POSITIONS).
const POSITIONS = [1, 2, 3, 4, 5];
const PHASES = [
  { key: "unloaded", label: "unloaded" },
  { key: "loaded_l", label: "L =" },
  { key: "loaded_max", label: "(Max)" },
];

function fmt(value) {
  return value === undefined || value === null || value === "" ? "" : value;
}

function keyFor(phase, positionNo) {
  return `${phase}-${positionNo}`;
}

function cellsFromState(state) {
  const cells = {};
  for (const r of state.readings) {
    cells[keyFor(r.phase, r.position_no)] = { I: r.I, deltaL: r.delta_l, submitting: false, error: null };
  }
  return cells;
}

/**
 * Tilting (R76-2 page 20, A.5.1/A.5.1.1-A.5.1.3) — mobile instruments only.
 * Implements the minimal 8.3.3/4.18 slice (reference + 4 tilted positions,
 * unloaded then two loaded rows), not the full Annex A.5.1 battery — see
 * engine/tilting.py. Unlike every other form in this app, the pass
 * criteria are properties of the WHOLE dataset (like Repeatability), so
 * every submission replaces the entire local state with the fresh,
 * server-recomputed TiltingStateOut the POST returns.
 */
export function TiltingFormTable({ sessionId, sessionStatus, instrument, initialState, observerDefault }) {
  const disabled = sessionStatus !== "draft";

  const [state, setState] = useState(initialState);
  const [cells, setCells] = useState(() => cellsFromState(initialState));
  const [observer, setObserver] = useState(observerDefault ?? "");
  const [zeroDeviceStatus, setZeroDeviceStatus] = useState("");
  const [limitingTiltValue, setLimitingTiltValue] = useState("");
  const [remarks, setRemarks] = useState("");

  function getCell(phase, positionNo) {
    return cells[keyFor(phase, positionNo)] ?? { I: "", deltaL: "0", submitting: false, error: null };
  }

  function updateCell(phase, positionNo, patch) {
    setCells((prev) => ({ ...prev, [keyFor(phase, positionNo)]: { ...getCell(phase, positionNo), ...patch } }));
  }

  function resultFor(phase, positionNo) {
    return state.readings.find((r) => r.phase === phase && r.position_no === positionNo) ?? null;
  }

  async function submitCell(phase, positionNo) {
    const cell = getCell(phase, positionNo);
    if (cell.I === "" || disabled) return;
    updateCell(phase, positionNo, { submitting: true, error: null });
    // Decimal-as-string discipline (CLAUDE.md): never Number()/parseFloat().
    const payload = { phase, position_no: positionNo, I: cell.I, delta_l: cell.deltaL === "" ? "0" : cell.deltaL };
    try {
      const res = await apiFetch(`/sessions/${sessionId}/tilting/readings`, { method: "POST", body: payload });
      setState(res);
      setCells(cellsFromState(res));
    } catch (err) {
      const message = err instanceof ApiError && err.status === 409 ? "Session is no longer in draft — locked." : err.message;
      updateCell(phase, positionNo, { submitting: false, error: message });
      toast.error(`${phase}, position ${positionNo}: ${message}`);
    }
  }

  function handleEnter(phase, positionNo) {
    return (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        submitCell(phase, positionNo);
      }
    };
  }

  function phaseLoadLabel(phaseKey) {
    if (phaseKey === "unloaded") return "0";
    if (phaseKey === "loaded_l") return roundLoadForDisplay(state.L);
    return roundLoadForDisplay(state.max_capacity);
  }

  function phaseTable(phase) {
    const isLoaded = phase.key !== "unloaded";
    return (
      <div key={phase.key} className="mt-4">
        <div className="mb-1 flex flex-wrap items-baseline gap-x-6 gap-y-1 text-sm">
          <span className="font-medium">
            {phase.label} (Load = {phaseLoadLabel(phase.key)})
          </span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] border-collapse text-xs">
            <thead>
              <tr>
                <th className="border border-neutral-900 px-2 py-1" />
                {POSITIONS.map((p) => (
                  <th key={p} className="border border-neutral-900 px-2 py-1 font-normal">
                    {p === 1 ? "Reference (1)" : `Tilted (${p})`}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="border border-neutral-900 px-2 py-1">
                  <i>I</i>
                  <sub>v</sub> =
                </td>
                {POSITIONS.map((p) => {
                  const cell = getCell(phase.key, p);
                  return (
                    <td key={p} className="border border-neutral-900 p-0" title={cell.error ?? undefined}>
                      <input
                        className={`h-7 w-full border-0 bg-transparent px-1 text-center focus:outline-none focus:ring-1 focus:ring-inset focus:ring-neutral-900 disabled:opacity-60 ${cell.error ? "bg-red-50" : ""}`}
                        inputMode="decimal"
                        disabled={disabled}
                        value={cell.I}
                        onChange={(event) => updateCell(phase.key, p, { I: event.target.value })}
                        onKeyDown={handleEnter(phase.key, p)}
                      />
                    </td>
                  );
                })}
              </tr>
              <tr>
                <td className="border border-neutral-900 px-2 py-1">
                  Δ<i>L</i>
                  <sub>v</sub> =
                </td>
                {POSITIONS.map((p) => {
                  const cell = getCell(phase.key, p);
                  return (
                    <td key={p} className="border border-neutral-900 p-0">
                      <input
                        className="h-7 w-full border-0 bg-transparent px-1 text-center focus:outline-none focus:ring-1 focus:ring-inset focus:ring-neutral-900 disabled:opacity-60"
                        inputMode="decimal"
                        disabled={disabled}
                        value={cell.deltaL}
                        onChange={(event) => updateCell(phase.key, p, { deltaL: event.target.value })}
                        onBlur={() => submitCell(phase.key, p)}
                        onKeyDown={handleEnter(phase.key, p)}
                      />
                    </td>
                  );
                })}
              </tr>
              <tr>
                <td className="border border-neutral-900 px-2 py-1">
                  <i>E</i>
                  {isLoaded ? (
                    <sub>v</sub>
                  ) : (
                    <>
                      <sub>v</sub>0
                    </>
                  )}{" "}
                  =
                </td>
                {POSITIONS.map((p) => {
                  const cell = getCell(phase.key, p);
                  const result = resultFor(phase.key, p);
                  return (
                    <td key={p} className="border border-neutral-900 px-2 py-1 text-center text-neutral-700">
                      {cell.submitting ? "…" : roundForDisplay(result?.E)}
                    </td>
                  );
                })}
              </tr>
              {isLoaded ? (
                <tr>
                  <td className="border border-neutral-900 px-2 py-1">
                    <i>E</i>
                    <sub>c v</sub> =
                  </td>
                  {POSITIONS.map((p) => {
                    const result = resultFor(phase.key, p);
                    return (
                      <td key={p} className="border border-neutral-900 px-2 py-1 text-center font-medium text-neutral-900">
                        {roundForDisplay(result?.Ec)}
                      </td>
                    );
                  })}
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
        <div className="mt-1.5 flex flex-wrap gap-x-6 gap-y-1 text-xs">
          {phase.key === "unloaded" ? (
            <>
              <FormBox label="2e" value={roundForDisplay(state.unloaded_limit)} width="w-20" />
              <FormBox label="|E1,0 − Ev,0|max" value={roundForDisplay(state.unloaded_max_abs_deviation)} width="w-20" />
            </>
          ) : (
            <>
              <FormBox label="mpe" value={roundForDisplay(phase.key === "loaded_l" ? state.mpe_l : state.mpe_max)} width="w-20" />
              <FormBox
                label="|Ec1 − Ecv|max"
                value={roundForDisplay(phase.key === "loaded_l" ? state.loaded_l_max_abs_deviation : state.loaded_max_max_abs_deviation)}
                width="w-20"
              />
            </>
          )}
        </div>
      </div>
    );
  }

  const overall = state.passed === true ? "PASSED" : state.passed === false ? "FAILED" : "INCOMPLETE";
  const resolutionDuringTest = instrument?.d_value ?? instrument?.e_value ?? "";

  return (
    <div className="grid gap-3">
      <div className="mx-auto w-full max-w-5xl border-2 border-neutral-900 bg-white p-6 font-serif text-neutral-900 sm:p-8">
        <div className="mb-4 flex items-baseline justify-between border-b border-neutral-900 pb-1 text-xs">
          <span>OIML R 76-2: 2007 (E)</span>
          <span>Report page &hellip;./&hellip;.</span>
        </div>

        <h2 className="text-sm font-bold">8&nbsp;&nbsp;&nbsp;TILTING (A.5.1, A.5.1.1-A.5.1.3)</h2>
        <p className="ml-8 text-xs italic text-neutral-600">
          Minimal 8.3.3/4.18 slice — reference + 4 tilted positions, unloaded and at two loads (a mid load and
          Max), not the full Annex A.5.1 5-position × N-cycle battery.
        </p>

        <div className="mt-5 grid gap-1.5 text-sm">
          <FormLine label="Application no.:" value={fmt(instrument?.application_no)} />
          <FormLine label="Type designation:" value={fmt(instrument?.type_designation)} />
          <FormLine label="Observer:" value={observer} editable disabled={disabled} onChange={setObserver} />
          <FormLine label="Verification scale interval, e:" value={fmt(instrument?.e_value)} />
          <FormLine label="Resolution during test (smaller than e):" value={fmt(resolutionDuringTest)} />
        </div>

        <div className="mt-4">
          <FormBox label="Limiting value of tilting" value={limitingTiltValue} editable disabled={disabled} onChange={setLimitingTiltValue} width="w-28" />
        </div>

        <div className="mt-4">
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

        <p className="mt-4 text-sm">
          <i>E</i>
          <sub>v</sub> = <i>I</i>
          <sub>v</sub> + ½ <i>e</i> − Δ<i>L</i>
          <sub>v</sub> − <i>L</i> (v = 1, 2, 3, 4, 5); <i>E</i>
          <sub>cv</sub> = <i>E</i>
          <sub>v</sub> − <i>E</i>
          <sub>v0</sub>
        </p>

        {PHASES.map(phaseTable)}

        <div className="mt-5">
          <p className="text-sm">
            Check if the differences are: a) ≤ 2e for the unloaded instrument (not valid for class II
            instruments, if not used for direct sales to the public — not modeled here, see caption); b) ≤
            absolute value of mpe for the loaded instrument (checked independently at both loads).
          </p>
          <div className="mt-1.5 flex flex-wrap items-center gap-x-8 gap-y-2">
            <FormCheckbox label="Passed" checked={overall === "PASSED"} readOnly />
            <FormCheckbox label="Failed" checked={overall === "FAILED"} readOnly />
            {overall === "INCOMPLETE" ? (
              <span className="text-xs italic text-neutral-600">Incomplete — not every position/load has been entered yet.</span>
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
        Reproduced for data-entry fidelity to OIML R 76-2's page-20 "Tilting" form — not a copy of the
        copyrighted OIML document itself. This is the minimal 8.3.3/4.18 slice, not the full Annex A.5.1
        battery. The class-II-direct-sale carve-out on criterion (a) and the "(not valid for...)" note are not
        modeled — no such flag exists on a registered instrument. Header fields above (Observer, zero-device
        status, Limiting value of tilting, Remarks) are local to this page only, same known gap as the
        Weighing form (docs/architecture.md).
      </p>
    </div>
  );
}
