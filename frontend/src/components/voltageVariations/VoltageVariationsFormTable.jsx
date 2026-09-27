import { useMemo, useState } from "react";
import { toast } from "sonner";
import { apiFetch, ApiError } from "@/lib/api";
import { FormBox, FormCheckbox, FormLine } from "@/components/oiml/FormPrimitives";
import { CollapsibleFormHeader } from "@/components/oiml/CollapsibleFormHeader";
import { roundForDisplay, roundLoadForDisplay } from "@/lib/displayFormat";

const POWER_SUPPLY_OPTIONS = [
  { value: "mains_ac", label: "Mains power supply (AC), A.5.4.1" },
  { value: "external_plugin", label: "External or plug-in power supply device (AC or DC), A.5.4.2" },
  { value: "rechargeable", label: "Rechargeable battery, (re)charge during operation possible, A.5.4.2" },
  { value: "non_rechargeable", label: "Non-rechargeable/rechargeable battery, (re)charge during operation not possible, A.5.4.3" },
  { value: "road_vehicle", label: "12 V or 24 V road vehicle battery power supply, A.5.4.4" },
];

const ZERO_DEVICE_OPTIONS = [
  { value: "non_existent", label: "Non-existent" },
  { value: "not_in_operation", label: "Not in operation" },
  { value: "out_of_range", label: "Out of working range" },
  { value: "in_operation", label: "In operation" },
];

function fmt(value) {
  return value === undefined || value === null || value === "" ? "" : value;
}

function cellsFromInitialReadings(initialReadings) {
  const cells = {};
  for (const record of initialReadings ?? []) {
    cells[record.level_key] = {
      U: record.U ?? "",
      indication: record.I,
      deltaL: record.delta_l,
      result: record,
      submitting: false,
      error: null,
    };
  }
  return cells;
}

/**
 * Voltage variations (R76-2 page 23, A.5.4) — clause 11. Unlike every other
 * test built this task, this one IS computed: it reuses the Weighing
 * change-point formula (app/services/voltage_variations.py delegates
 * straight to engine.weighing.compute_weighing_result) at a single fixed
 * load, 10e, tested with the instrument powered at three voltage levels
 * (reference/lower/upper). Same bordered-document-sheet look as
 * Zero-tare/Eccentricity, the closest structural analogs (a small,
 * server-derived set of check "loads" — here, levels — each independently
 * computed and submitted).
 *
 * Simplified from the source form (documented, not silently dropped): the
 * form prints TWO near-identical 3-level tables ("if an instrument has
 * more than one power supply") and, within each, two blank rows per level
 * (unlabeled — most plausibly a second reading or up/down repeat the form
 * doesn't actually name). This app builds ONE category/table with ONE row
 * per level — a technician testing a second power-supply category records
 * it via a second session or notes it in Remarks, same "blank paper form"
 * convention Eccentricity's mobile-instrument question already used.
 */
export function VoltageVariationsFormTable({
  sessionId,
  sessionStatus,
  instrument,
  verificationType,
  observerDefault,
  initialLevels,
  initialReadings,
}) {
  const disabled = sessionStatus !== "draft";

  const [observer, setObserver] = useState(observerDefault ?? "");
  const [powerSupplyType, setPowerSupplyType] = useState(null);
  const [zeroDeviceStatus, setZeroDeviceStatus] = useState("");
  const [category, setCategory] = useState("");
  const [uNom, setUNom] = useState(instrument?.u_nom != null ? String(instrument.u_nom) : "");
  const [uMin, setUMin] = useState(instrument?.u_min != null ? String(instrument.u_min) : "");
  const [uMax, setUMax] = useState(instrument?.u_max != null ? String(instrument.u_max) : "");
  const [remarks, setRemarks] = useState("");
  const [cells, setCells] = useState(() => cellsFromInitialReadings(initialReadings));

  function getCell(levelKey) {
    return cells[levelKey] ?? { U: "", indication: "", deltaL: "0", result: null, submitting: false, error: null };
  }

  function updateCell(levelKey, patch) {
    setCells((prev) => ({ ...prev, [levelKey]: { ...getCell(levelKey), ...patch } }));
  }

  async function submitLevel(levelKey) {
    const cell = getCell(levelKey);
    if (cell.indication === "" || disabled) return;
    updateCell(levelKey, { submitting: true, error: null });
    // Decimal-as-string discipline (CLAUDE.md): never Number()/parseFloat().
    const payload = {
      level_key: levelKey,
      U: cell.U === "" ? null : cell.U,
      I: cell.indication,
      delta_l: cell.deltaL === "" ? "0" : cell.deltaL,
      E0: "0",
    };
    try {
      const res = await apiFetch(`/sessions/${sessionId}/voltage-variations/readings`, { method: "POST", body: payload });
      updateCell(levelKey, { result: res, submitting: false, error: null });
    } catch (err) {
      const message = err instanceof ApiError && err.status === 409 ? "Session is no longer in draft — locked." : err.message;
      updateCell(levelKey, { submitting: false, error: message });
      toast.error(`${levelKey}: ${message}`);
    }
  }

  function handleEnter(levelKey) {
    return (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        submitLevel(levelKey);
      }
    };
  }

  const resolutionDuringTest = instrument?.d_value ?? instrument?.e_value ?? "";

  const overall = useMemo(() => {
    const results = (initialLevels ?? []).map((level) => getCell(level.level_key).result);
    if (results.some((r) => r && !r.passed)) return "FAILED";
    if (results.length > 0 && results.every((r) => r)) return "PASSED";
    return "INCOMPLETE";
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cells, initialLevels]);

  return (
    <div className="grid gap-3">
      <CollapsibleFormHeader instrument={instrument} verificationType={verificationType} observer={observer}>
        <div className="mx-auto w-full max-w-4xl border-2 border-neutral-900 bg-white p-6 font-serif text-neutral-900 sm:p-8">
          <div className="mb-4 flex items-baseline justify-between border-b border-neutral-900 pb-1 text-xs">
            <span>OIML R 76-2: 2007 (E)</span>
            <span>Report page &hellip;./&hellip;.</span>
          </div>

          <h2 className="text-sm font-bold">11&nbsp;&nbsp;&nbsp;VOLTAGE VARIATIONS (A.5.4)</h2>

          <div className="mt-5 grid gap-1.5 text-sm">
            <FormLine label="Application no.:" value={fmt(instrument?.application_no)} />
            <FormLine label="Type designation:" value={fmt(instrument?.type_designation)} />
            <FormLine label="Observer:" value={observer} editable disabled={disabled} onChange={setObserver} />
            <FormLine label="Verification scale interval, e:" value={fmt(instrument?.e_value)} />
            <FormLine label="Resolution during test (smaller than e):" value={fmt(resolutionDuringTest)} />
          </div>

          <div className="mt-5 grid gap-1.5">
            {POWER_SUPPLY_OPTIONS.map((opt) => (
              <FormCheckbox
                key={opt.value}
                label={opt.label}
                checked={powerSupplyType === opt.value}
                onClick={() => !disabled && setPowerSupplyType(opt.value)}
                disabled={disabled}
              />
            ))}
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-4">
            <FormBox label="Unom" value={uNom} unit="V" editable disabled={disabled} onChange={setUNom} width="w-24" />
            <FormBox label="Umin" value={uMin} unit="V" editable disabled={disabled} onChange={setUMin} width="w-24" />
            <FormBox label="Umax" value={uMax} unit="V" editable disabled={disabled} onChange={setUMax} width="w-24" />
          </div>
          <p className="mt-1 text-xs text-neutral-600">
            Calculate lower and upper limits of applied voltages according to A.5.4. If a voltage-range
            (Umin/Umax) is marked, use the average value as reference value.
          </p>

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

          <div className="mt-4">
            <FormLine
              label="Category of power supply (if more than one):"
              value={category}
              editable
              disabled={disabled}
              onChange={setCategory}
            />
          </div>

          <p className="mt-4 text-sm">
            <i>E</i> = <i>I</i> + ½ <i>e</i> − Δ<i>L</i> − <i>L</i>, &nbsp; <i>E</i>
            <sub>c</sub> = <i>E</i> − <i>E</i>
            <sub>0</sub> with <i>E</i>
            <sub>0</sub> = error calculated at or near zero
          </p>
        </div>
      </CollapsibleFormHeader>

      <div className="mx-auto w-full max-w-3xl border-2 border-neutral-900 bg-white p-3 font-serif text-neutral-900 sm:p-4">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] border-collapse text-xs">
            <thead>
              <tr>
                <th className="border border-neutral-900 px-2 py-1">Voltage</th>
                <th className="border border-neutral-900 px-2 py-1">
                  <i>U</i>, (V)
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
              {(initialLevels ?? []).map((level) => {
                const cell = getCell(level.level_key);
                const colorClass = cell.result ? (cell.result.passed ? "text-emerald-700" : "text-red-700 font-semibold") : "text-neutral-500";
                return (
                  <tr key={level.level_key}>
                    <td className="border border-neutral-900 px-2 py-1">{level.label}</td>
                    <td className="border border-neutral-900 p-0">
                      <input
                        className="h-7 w-full border-0 bg-transparent px-1 text-center focus:outline-none focus:ring-1 focus:ring-inset focus:ring-neutral-900 disabled:opacity-60"
                        inputMode="decimal"
                        disabled={disabled}
                        value={cell.U}
                        onChange={(event) => updateCell(level.level_key, { U: event.target.value })}
                      />
                    </td>
                    <td className="border border-neutral-900 px-2 py-1 text-right">{roundLoadForDisplay(level.L)}</td>
                    <td className="border border-neutral-900 p-0" title={cell.error ?? undefined}>
                      <input
                        className={`h-7 w-full border-0 bg-transparent px-1 text-center focus:outline-none focus:ring-1 focus:ring-inset focus:ring-neutral-900 disabled:opacity-60 ${cell.error ? "bg-red-50" : ""}`}
                        inputMode="decimal"
                        disabled={disabled}
                        value={cell.indication}
                        onChange={(event) => updateCell(level.level_key, { indication: event.target.value })}
                        onKeyDown={handleEnter(level.level_key)}
                      />
                    </td>
                    <td className="border border-neutral-900 p-0">
                      <input
                        className="h-7 w-full border-0 bg-transparent px-1 text-center focus:outline-none focus:ring-1 focus:ring-inset focus:ring-neutral-900 disabled:opacity-60"
                        inputMode="decimal"
                        disabled={disabled}
                        value={cell.deltaL}
                        onChange={(event) => updateCell(level.level_key, { deltaL: event.target.value })}
                        onBlur={() => submitLevel(level.level_key)}
                        onKeyDown={handleEnter(level.level_key)}
                      />
                    </td>
                    <td className={`border border-neutral-900 px-2 py-1 text-center ${colorClass}`}>
                      {cell.submitting ? "…" : roundForDisplay(cell.result?.E)}
                    </td>
                    <td className={`border border-neutral-900 px-2 py-1 text-center ${colorClass}`}>
                      {cell.submitting ? "…" : roundForDisplay(cell.result?.Ec)}
                    </td>
                    <td className="border border-neutral-900 px-2 py-1 text-right">{roundForDisplay(cell.result?.mpe ?? level.mpe)}</td>
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
              <span className="text-xs italic text-neutral-600">Incomplete — not every voltage level has been entered yet.</span>
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
        Reproduced for data-entry fidelity to OIML R 76-2's page-23 "Voltage variations" form — not a copy of the
        copyrighted OIML document itself. Simplified to one power-supply category and one row per voltage level
        (the source form's second category table and second blank row per level are not modeled — see
        docs/architecture.md). Header fields above (Observer, power-supply type, zero-device status, category,
        Remarks) are local to this page only, same known gap as every other OIML form here.
      </p>
    </div>
  );
}
