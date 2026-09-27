import { Fragment, useEffect, useMemo, useRef, useState } from "react";
import { FormLine, FormCheckbox } from "@/components/oiml/FormPrimitives";
import { CollapsibleFormHeader } from "@/components/oiml/CollapsibleFormHeader";
import { roundForDisplay, roundLoadForDisplay } from "@/lib/displayFormat";
import { useWeighingReadings } from "@/hooks/useWeighingReadings";
import { GuidedEntryPanel } from "@/components/weighing/GuidedEntryPanel";
import { FORM_COLUMNS, buildGuidedWalkPositions } from "@/components/weighing/formColumns";
import { cn } from "@/lib/utils";

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

// The first not-yet-submitted {sequence_no, direction} pair, in the SAME
// guided-walk order the panel itself uses (buildGuidedWalkPositions: the
// full increasing pass first, then the full decreasing pass in reverse —
// never "load N's up, then load N's down" — see formColumns.js). Lets the
// guided panel resume exactly where a technician left off on reload,
// instead of always restarting at load 1 and forcing a click-through of
// already-done work.
function findFirstIncomplete(sequence, cells) {
  const seen = new Set();
  for (const pos of buildGuidedWalkPositions(sequence)) {
    const key = `${pos.sequenceNo}-${pos.apiDirection}`;
    if (seen.has(key)) continue; // each direction appears twice (indication, deltaL) — check once
    seen.add(key);
    if (!cells[pos.sequenceNo]?.[pos.apiDirection]?.result) {
      return { sequenceNo: pos.sequenceNo, apiDirection: pos.apiDirection, field: "indication" };
    }
  }
  return null;
}

// Auto-scale the main data table down to fit beside the guided panel — real
// CSS values (font-size/padding/input height, via a computed `--tscale`
// custom property) rather than a visual `transform: scale()`. A transform
// was rejected: this table relies on `position: sticky` for its Load column
// AND the guided panel targets its `<input>`s directly via DOM refs
// (`inputRefs`, focus()/select()/scrollIntoView-on-focus) — both are exactly
// the kind of thing a scaled ancestor is known to desync (hit-target
// coordinates, sticky offset math, focus-scroll math). Scaling real values
// instead means every input stays its own genuine size/position; only the
// numbers driving font-size/padding/height change, so click targets, sticky
// positioning, and DOM-ref focus all keep working unmodified.
// 720px is the table's own designed width at 1x (10 columns + mpe, matches
// the table's previous static `min-w-[720px]`) — the "would look right"
// reference the scale factor is measured against, never exceeded (no
// upscale on a large monitor). 10/12 is the readability floor: text-xs is
// 12px, and this table's numbers should never render under ~10px. Below
// that floor the table stops shrinking and its own `overflow-x-auto`
// wrapper (unchanged, pre-existing) takes over — the same horizontal-scroll
// fallback the table already had.
const TABLE_NATURAL_WIDTH = 720;
const TABLE_SCALE_FLOOR = 10 / 12;

const SCALE_TEXT = "text-[calc(0.75rem*var(--tscale))]";
const SCALE_PX2 = "px-[calc(0.5rem*var(--tscale))]";
const SCALE_PY1 = "py-[calc(0.25rem*var(--tscale))]";
const SCALE_PX1 = "px-[calc(0.25rem*var(--tscale))]";
const SCALE_H = "h-[calc(1.75rem*var(--tscale))]";

// Measures the actual rendered width available to the table (the
// `overflow-x-auto` wrapper's own clientWidth — stable, since that
// wrapper's width comes from the surrounding grid/flex layout, not from
// the table's own intrinsic content, so there's no feedback loop with the
// ResizeObserver below) and turns it into a scale factor, clamped to
// [floor, 1].
function useAutoScale(naturalWidth, floor) {
  const ref = useRef(null);
  const [scale, setScale] = useState(1);

  useEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    const observer = new ResizeObserver((entries) => {
      const width = entries[0]?.contentRect.width;
      if (!width) return;
      setScale(Math.min(1, Math.max(floor, width / naturalWidth)));
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, [naturalWidth, floor]);

  return { ref, scale };
}

/**
 * The OIML R 76-2 "1 Weighing performance" entry screen — a visual
 * reproduction of the standard's page-10 form (header block, environmental
 * grid, zero-device/initial-zero lines, the E/Ec formula, the ↓/↑ data
 * table, and the Passed/Failed + Remarks footer), reproduced for data-entry
 * fidelity only, not a copy of the copyrighted OIML document itself — no
 * OIML explanatory text is included beyond the form's own field labels and
 * structural chrome. Rendered alongside `GuidedEntryPanel`, a keyboard-first
 * accelerator that reads/writes the exact same cell state (via
 * `useWeighingReadings`) — clicking a cell here still works exactly as
 * before; the panel is an additional way to drive the same data, not a
 * replacement for this table.
 */
export function WeighingFormTable({
  sessionId,
  sessionStatus,
  instrument,
  sequence,
  verificationType,
  observerDefault,
  initialReadings,
  actorId,
}) {
  const [testDate, setTestDate] = useState(todayIso());
  const [observer, setObserver] = useState(observerDefault ?? "");
  const [env, setEnv] = useState({
    start: { temp: "", relH: "", time: "", barPres: "" },
    max: { temp: "", relH: "", time: "", barPres: "" },
    end: { temp: "", relH: "", time: "", barPres: "" },
  });
  const [zeroDeviceStatus, setZeroDeviceStatus] = useState("");
  const [initialZeroOver20, setInitialZeroOver20] = useState(null);
  // Prefilled from the first already-submitted reading's E0 if any exist —
  // E0 is one session-level value in this simplified model (no dedicated
  // zero-capture step yet), so reopening a session should show the value
  // actually used, not reset to the "0" default.
  const [e0, setE0] = useState(initialReadings?.[0]?.E0 ?? "0");
  const [remarks, setRemarks] = useState("");

  const { disabled, cells, getCell, updateCell, submitDirection } = useWeighingReadings({
    sessionId,
    sessionStatus,
    initialReadings,
    e0,
    actorId,
  });

  // The guided panel's "where am I" pointer — shared state, not owned by
  // either surface exclusively: focusing a table input moves it here too
  // (see inputCell's onFocus below), and the panel's own navigation moves
  // it the other way. This is what "the panel reflects table state and
  // vice versa" actually means for focus/position (the cell VALUES were
  // already shared via useWeighingReadings above).
  const [cursor, setCursor] = useState(() => findFirstIncomplete(sequence, cells));

  // Keyed `${sequence_no}-${apiDirection}-${field}` -> the real <input> DOM
  // node, so the panel's Escape key can return focus to the actual table
  // cell it's currently pointing at, deliberately, instead of just calling
  // blur() and leaving focus nowhere.
  const inputRefs = useRef(new Map());

  const { ref: tableWrapRef, scale: tableScale } = useAutoScale(TABLE_NATURAL_WIDTH, TABLE_SCALE_FLOOR);

  function inputCell(entry, apiDirection, field) {
    const cell = getCell(entry.sequence_no, apiDirection);
    const key = `${entry.sequence_no}-${apiDirection}-${field}`;
    // The precise field the guided panel is on right now — not just "this
    // row" (that's the subtler `isActiveRow` tint below) but this exact
    // cell, tracking the I -> ΔL sub-step too, so the panel and the table
    // are unmistakably pointing at the same thing.
    const isActiveCell =
      cursor?.sequenceNo === entry.sequence_no && cursor?.apiDirection === apiDirection && cursor?.field === field;
    return (
      <td
        className={cn("border border-neutral-900 p-0", isActiveCell && "bg-amber-200 ring-2 ring-inset ring-amber-500")}
        title={cell.error ?? undefined}
      >
        <input
          ref={(el) => {
            if (el) inputRefs.current.set(key, el);
            else inputRefs.current.delete(key);
          }}
          className={cn(
            SCALE_H,
            SCALE_PX1,
            SCALE_TEXT,
            "w-full border-0 bg-transparent text-center focus:outline-none focus:ring-1 focus:ring-inset focus:ring-neutral-900 disabled:opacity-60",
            cell.error && "bg-red-50",
          )}
          inputMode="decimal"
          disabled={disabled}
          value={field === "indication" ? cell.indication : cell.deltaL}
          onChange={(event) => updateCell(entry.sequence_no, apiDirection, { [field]: event.target.value })}
          // `source: "table"` tells the panel's own focus-management effect
          // NOT to steal focus back — the panel still updates its displayed
          // context (progress, expected value, mpe) to match this cell, it
          // just doesn't yank the cursor away from a cell just clicked.
          onFocus={() => setCursor({ sequenceNo: entry.sequence_no, apiDirection, field, source: "table" })}
          // Submission happens on blur of the ΔL input (the natural second
          // stop in the I -> ΔL tab order) or Enter in either field — this
          // table-cell behavior is UNCHANGED by the guided panel; the panel
          // has its own, separate Enter semantics (commit I -> ΔL -> submit
          // -> advance), described in GuidedEntryPanel.jsx.
          onBlur={field === "deltaL" ? () => submitDirection(entry, apiDirection) : undefined}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              submitDirection(entry, apiDirection);
            }
          }}
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
      <td className={cn("border border-neutral-900 text-center", SCALE_PX1, SCALE_PY1, SCALE_TEXT, colorClass)}>
        {cell.submitting ? "…" : roundForDisplay(value)}
      </td>
    );
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

  return (
    // `min-w-0` on BOTH grid items, not just `lg:` — without it, a grid
    // item defaults to using its content's intrinsic width (here, the
    // table's own `min-w-[720px]`) as its minimum, which forces the grid
    // track — and the whole page — wider than the viewport instead of
    // letting the table's own `overflow-x-auto` contain the scroll like
    // it's supposed to. `order-*` puts the panel FIRST when stacked below
    // `lg` (the primary keyboard-first entry point shouldn't sit below a
    // potentially long table the technician has to scroll past first),
    // reverting to natural left-table/right-panel order at `lg` and up.
    //
    // `lg:flex lg:h-full lg:min-h-0` (new, `fix/vertical-fit-no-page-scroll`)
    // — switches this container from `grid` to `flex` ONLY at `lg` (a grid
    // track's own height stays content-sized even inside an `h-full`
    // grid container, a well-known CSS Grid gotcha; a flex row's
    // `align-items: stretch` default makes both columns genuinely fill
    // the real height `WeighingSessionPage` hands down, no extra utility
    // needed). Column widths that used to come from `grid-cols-[...]` now
    // come from the columns' own `lg:flex-1`/`lg:w-[320px]` below. Below
    // `lg`, `display:grid` (the base class) still applies, unchanged.
    <div className="grid gap-4 lg:flex lg:h-full lg:min-h-0">
      <div className="order-2 grid min-w-0 gap-2 lg:order-none lg:flex lg:h-full lg:min-h-0 lg:flex-1 lg:flex-col">
        {/* `lg:shrink-0` — guarantees this header strip keeps its natural
            height under the flex column's default shrink behavior, so any
            space pressure at `lg`+ is absorbed by the table sheet below
            (the one flex item actually designed to grow/shrink,
            `lg:flex-1`), never by squeezing this header. */}
        <div className="lg:shrink-0">
          <CollapsibleFormHeader instrument={instrument} verificationType={verificationType} date={testDate} observer={observer}>
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
          </div>
          </CollapsibleFormHeader>
        </div>

        {/* The workstation part: full remaining column width (no max-w
            cap, unlike the header sheet above) — reclaimed specifically so
            all 10 data columns + mpe are comfortably visible next to the
            320px guided panel, per docs/architecture.md's focused
            test-entry mode. The Load column is sticky within the
            scrollable table container so it stays in view when the table
            scrolls horizontally on a narrower screen. Padding cut
            (`p-4 sm:p-6` -> `p-2 sm:p-3`, `fix/vertical-fit-no-page-scroll`)
            — this is a workstation control surface now, not a page
            reproduction, and every reclaimed pixel here is a pixel back
            for the table's own row-scroll region below. `lg:flex
            lg:min-h-0 lg:flex-1 lg:flex-col` makes this sheet fill the
            left column's remaining height at `lg`, so its own children
            (the table-scroll div, Passed/Failed, Remarks) can divide that
            real height instead of just stacking to their natural size. */}
        <div className="w-full border-2 border-neutral-900 bg-white p-2 font-serif text-neutral-900 sm:p-3 lg:flex lg:min-h-0 lg:flex-1 lg:flex-col">
          {/* `ref={tableWrapRef}` is what useAutoScale measures — this
              wrapper's own clientWidth is "the space the table actually
              has," which drives `--tscale` below. `max-h-[65vh]
              overflow-auto` (unchanged) is the sub-`lg` behavior — the
              same cap the previous task set, since below `lg` the page
              scrolls normally and a hard vh cap is still the right
              fallback. At `lg`+, `lg:max-h-none lg:min-h-0 lg:flex-1`
              replaces that guess with the table's REAL remaining height
              (whatever the sheet above didn't spend on Passed/Failed +
              Remarks) — on a long load sequence, only these rows scroll,
              while the header row, Passed/Failed, Remarks, and the guided
              panel all stay in view without hunting; on a short one, no
              scrollbar appears at all. `<thead>` gets its own `sticky
              top-0` so both header rows stay pinned to the top of THIS
              scrolling container as the body scrolls underneath —
              independent of, and composes cleanly with, the Load column's
              separate `sticky left-0` (horizontal) below; a focused input
              still auto-scrolls into view here via the browser's own
              default focus-scroll behavior, so the guided panel's
              Escape/Enter navigation needs no changes. */}
          <div ref={tableWrapRef} className="max-h-[65vh] overflow-auto lg:max-h-none lg:min-h-0 lg:flex-1">
            <table
              className={cn("w-full border-collapse", SCALE_TEXT)}
              style={{ "--tscale": tableScale, minWidth: `${TABLE_NATURAL_WIDTH * TABLE_SCALE_FLOOR}px` }}
            >
              <thead className="sticky top-0 z-20 bg-white">
                <tr>
                  <th
                    rowSpan={2}
                    className={cn(
                      "sticky left-0 z-10 border border-neutral-900 bg-neutral-50 align-middle shadow-[2px_0_4px_-2px_rgba(0,0,0,0.3)]",
                      SCALE_PX2,
                      SCALE_PY1,
                    )}
                  >
                    Load, <i>L</i>
                  </th>
                  <th colSpan={2} className={cn("border border-neutral-900 bg-white font-normal", SCALE_PX2, SCALE_PY1)}>
                    Indication, <i>I</i>
                  </th>
                  <th colSpan={2} className={cn("border border-neutral-900 bg-white font-normal", SCALE_PX2, SCALE_PY1)}>
                    Add. load,
                    <br />Δ<i>L</i>
                  </th>
                  <th colSpan={2} className={cn("border border-neutral-900 bg-white font-normal", SCALE_PX2, SCALE_PY1)}>
                    Error, <i>E</i>
                  </th>
                  <th colSpan={2} className={cn("border border-neutral-900 bg-white font-normal", SCALE_PX2, SCALE_PY1)}>
                    Corrected error, <i>E</i>
                    <sub>c</sub>
                  </th>
                  <th rowSpan={2} className={cn("border border-neutral-900 bg-white align-middle", SCALE_PX2, SCALE_PY1)}>
                    mpe
                  </th>
                </tr>
                <tr>
                  {["I", "dL", "E", "Ec"].flatMap((group) =>
                    FORM_COLUMNS.map((col) => (
                      <th
                        key={`${group}-${col.apiDirection}`}
                        className={cn("border border-neutral-900 bg-white font-normal", SCALE_PX1, SCALE_PY1)}
                      >
                        {col.glyph}
                      </th>
                    )),
                  )}
                </tr>
              </thead>
              <tbody>
                {sequence.map((entry) => {
                  // Subtler row-level tint for orientation ("this is the
                  // panel's current load") — the PRECISE field is the
                  // stronger per-cell highlight in inputCell(), below.
                  const isActiveRow = cursor?.sequenceNo === entry.sequence_no;
                  return (
                    <tr key={entry.sequence_no} className={cn(isActiveRow && "bg-amber-50/70")}>
                      <td
                        className={cn(
                          "sticky left-0 z-10 border border-neutral-900 text-right shadow-[2px_0_4px_-2px_rgba(0,0,0,0.3)]",
                          SCALE_PX2,
                          SCALE_PY1,
                          isActiveRow ? "bg-amber-50 font-medium" : "bg-white",
                        )}
                      >
                        {roundLoadForDisplay(entry.L)}
                      </td>
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
                      <td className={cn("border border-neutral-900 text-right", SCALE_PX2, SCALE_PY1)}>
                        {roundForDisplay(entry.mpe)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="mt-3 shrink-0">
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

          <div className="mt-3 shrink-0">
            <p className="text-sm">Remarks:</p>
            <textarea
              className="mt-1 min-h-10 w-full border border-neutral-900 bg-transparent px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-inset focus:ring-neutral-900 disabled:opacity-60"
              disabled={disabled}
              value={remarks}
              onChange={(event) => setRemarks(event.target.value)}
            />
          </div>
        </div>

        <p className="shrink-0 text-xs text-muted-foreground">
          Reproduced for data-entry fidelity to OIML R 76-2's page-10 "Weighing performance" form —
          not a copy of the copyrighted OIML document itself. Header fields above (Date, Observer,
          environmental conditions, zero-device status, initial-zero-setting flag, Remarks) are local
          to this page only — there is no session-update endpoint yet (tracked gap; see
          docs/architecture.md) — and reset on reload.
        </p>
      </div>

      {/* `order-1`/`lg:order-none` puts the panel above the table when
          stacked (see the comment on the outer container). `max-w-xl`/
          `lg:max-w-none` keeps it from stretching edge-to-edge on a
          tablet-width screen still below `lg` — full-bleed is still fine
          on a genuinely narrow phone, where max-w-xl (36rem) never
          actually constrains anything.
          `lg:sticky lg:top-4` (the previous task's page-scroll-era
          treatment) is GONE at `lg`+, replaced by `lg:h-full lg:w-[320px]
          lg:shrink-0 lg:overflow-y-auto` (`fix/vertical-fit-no-page-scroll`)
          — the page no longer scrolls at `lg`+ (FocusedShell), so `sticky`
          has nothing to stick against; instead the panel fills the exact
          height its sibling column fills (flex `align-items: stretch`,
          the parent's default) and scrolls INTERNALLY if its own content
          (title, applied-load box, input, adjust buttons, Previous/Next,
          "Last recorded," footer text — in that DOM order) doesn't fit.
          Because the input + adjust buttons + Next button sit earlier in
          that order than "Last recorded"/the footer text, a plain
          top-anchored `overflow-y-auto` already keeps the primary controls
          visible first and lets only the lower-priority content require a
          scroll — no reordering needed to satisfy that priority. */}
      <div className="order-1 mx-auto w-full min-w-0 max-w-xl lg:order-none lg:mx-0 lg:h-full lg:w-[320px] lg:min-h-0 lg:max-w-none lg:shrink-0 lg:overflow-y-auto">
        <GuidedEntryPanel
          sequence={sequence}
          instrument={instrument}
          disabled={disabled}
          getCell={getCell}
          updateCell={updateCell}
          submitDirection={submitDirection}
          cursor={cursor}
          setCursor={setCursor}
          inputRefs={inputRefs}
        />
      </div>
    </div>
  );
}
