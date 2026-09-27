import { useEffect, useRef } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { roundForDisplay, roundLoadForDisplay } from "@/lib/displayFormat";
import { addDecimalStrings, multiplyDecimalStringBySmallInt } from "@/lib/decimalMath";
import { FORM_COLUMNS } from "@/components/weighing/formColumns";

const DIRECTION_WORDS = { up: "increasing", down: "decreasing" };
const FINE_STEPS = [-10, -5, -1, 1, 5, 10];
const SCALE_MULTIPLIERS = [-5, -2, -1, 1, 2, 5];

function directionGlyph(apiDirection) {
  return FORM_COLUMNS.find((col) => col.apiDirection === apiDirection)?.glyph ?? apiDirection;
}

// The full guided walk, flattened to one ordered list of every
// {sequenceNo, apiDirection, field} stop — one shared list drives BOTH
// "Enter" auto-advance (I -> ΔL -> submit -> next direction's I) and the
// manual Previous/Next buttons, so there's exactly one definition of "what
// comes next" rather than two that could disagree.
function buildFlatPositions(sequence) {
  const positions = [];
  for (const entry of sequence) {
    for (const col of FORM_COLUMNS) {
      positions.push({ sequenceNo: entry.sequence_no, apiDirection: col.apiDirection, field: "indication" });
      positions.push({ sequenceNo: entry.sequence_no, apiDirection: col.apiDirection, field: "deltaL" });
    }
  }
  return positions;
}

function findPositionIndex(positions, cursor) {
  if (!cursor) return -1;
  return positions.findIndex(
    (p) => p.sequenceNo === cursor.sequenceNo && p.apiDirection === cursor.apiDirection && p.field === cursor.field,
  );
}

// One entry per (load, direction) — used only to find "the most recently
// submitted direction before the current one," for the "last recorded"
// readout. A coarser list than buildFlatPositions on purpose: a reading's
// result lives per-direction, not per-field.
function buildDirectionPositions(sequence) {
  const positions = [];
  for (const entry of sequence) {
    for (const col of FORM_COLUMNS) positions.push({ sequenceNo: entry.sequence_no, apiDirection: col.apiDirection });
  }
  return positions;
}

/**
 * The keyboard-first accelerator next to the Weighing OIML form table — see
 * docs/architecture.md, Frontend, for the full design rationale. Reads and
 * writes the exact same per-cell state as `WeighingFormTable` (via the
 * `getCell`/`updateCell`/`submitDirection` props, all sourced from the
 * shared `useWeighingReadings` hook), so nothing here is a second copy of
 * the table's data — only the "where am I" cursor and the quick-adjust
 * arithmetic are specific to this component.
 */
export function GuidedEntryPanel({
  sequence,
  instrument,
  disabled,
  getCell,
  updateCell,
  submitDirection,
  cursor,
  setCursor,
  inputRefs,
}) {
  const indicationRef = useRef(null);
  const deltaLRef = useRef(null);

  const entry = cursor ? sequence.find((e) => e.sequence_no === cursor.sequenceNo) : null;
  const cell = entry ? getCell(entry.sequence_no, cursor.apiDirection) : null;

  // Pre-fill I with the expected value (L) the first time this direction is
  // visited — never overwrites a value already typed/submitted, so
  // navigating back to amend an already-recorded direction shows what's on
  // record, not the theoretical target again.
  useEffect(() => {
    if (!entry || !cursor || cursor.field !== "indication" || !cell) return;
    if (cell.indication === "") {
      updateCell(entry.sequence_no, cursor.apiDirection, { indication: entry.L });
    }
    // `cell` changes identity on every keystroke (any cells-state update),
    // so this re-checks more often than strictly necessary, but the guard
    // above makes every extra check a harmless no-op — `updateCell` is
    // memoized (useWeighingReadings.js) specifically so this dependency
    // array can be complete without over-firing the way a plain
    // per-render function would cause.
  }, [entry, cursor, cell, updateCell]);

  // Deliberate focus management: whenever the cursor moves because of THIS
  // panel's own navigation (submit-and-advance, or the Previous/Next
  // buttons), move real DOM focus to the matching panel input — this is
  // what makes "complete a run without touching the mouse" actually true,
  // rather than just updating state and leaving focus wherever it was.
  // Skipped when `cursor.source === "table"` (WeighingFormTable's onFocus
  // sets this when a table cell is clicked directly) — the panel updates
  // its displayed context either way, but must NOT steal focus back out of
  // the table cell the technician just clicked to amend.
  useEffect(() => {
    if (!cursor || cursor.source === "table") return;
    const target = cursor.field === "indication" ? indicationRef.current : deltaLRef.current;
    target?.focus();
    target?.select?.();
  }, [cursor]);

  if (!entry || !cell) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Guided entry</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          Every load's both directions are already recorded. Use the table to review or amend any reading.
        </CardContent>
      </Card>
    );
  }

  const loadIndex = sequence.findIndex((e) => e.sequence_no === entry.sequence_no);
  const field = cursor.field;
  const value = field === "indication" ? cell.indication : cell.deltaL;
  const eValue = instrument?.e_value;

  function moveTo(delta) {
    const positions = buildFlatPositions(sequence);
    const idx = findPositionIndex(positions, cursor);
    const target = idx === -1 ? null : positions[idx + delta] ?? null;
    if (target) setCursor(target);
  }

  function adjust(amount) {
    if (disabled) return;
    const adjusted = addDecimalStrings(value === "" ? "0" : value, amount);
    if (adjusted === null) return;
    updateCell(entry.sequence_no, cursor.apiDirection, { [field]: adjusted });
  }

  function adjustByScale(multiplier) {
    if (!eValue) return;
    const amount = multiplyDecimalStringBySmallInt(eValue, multiplier);
    if (amount !== null) adjust(amount);
  }

  async function commitAndAdvance() {
    if (disabled) return;
    if (field === "deltaL") {
      const result = await submitDirection(entry, cursor.apiDirection);
      if (!result) return; // failed — error already toasted, stay put so the technician can retry
    }
    moveTo(1);
  }

  function handleKeyDown(event) {
    if (event.key === "Enter") {
      event.preventDefault();
      commitAndAdvance();
      return;
    }
    if (event.key === "Escape") {
      event.preventDefault();
      const key = `${entry.sequence_no}-${cursor.apiDirection}-${field}`;
      inputRefs?.current?.get(key)?.focus();
      return;
    }
    // Nice-to-have: Up/Down step by the finest adjust amount. Deliberately
    // NOT Left/Right, which must keep moving the text caret inside the
    // input as normal.
    if (event.key === "ArrowUp") {
      event.preventDefault();
      adjust("1");
    } else if (event.key === "ArrowDown") {
      event.preventDefault();
      adjust("-1");
    }
  }

  // "Last recorded" — the nearest earlier direction (in guided-walk order)
  // that already has a submitted result, regardless of which field the
  // cursor is currently on.
  const directionPositions = buildDirectionPositions(sequence);
  const currentDirIdx = directionPositions.findIndex(
    (p) => p.sequenceNo === cursor.sequenceNo && p.apiDirection === cursor.apiDirection,
  );
  let lastResult = null;
  let lastLabel = null;
  for (let i = currentDirIdx - 1; i >= 0; i--) {
    const pos = directionPositions[i];
    const result = getCell(pos.sequenceNo, pos.apiDirection).result;
    if (result) {
      lastResult = result;
      lastLabel = { ...pos, loadNumber: sequence.findIndex((e) => e.sequence_no === pos.sequenceNo) + 1 };
      break;
    }
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Guided entry</CardTitle>
        <p className="text-xs text-muted-foreground">
          Load {loadIndex + 1} of {sequence.length} · {directionGlyph(cursor.apiDirection)}{" "}
          {DIRECTION_WORDS[cursor.apiDirection]}
        </p>
      </CardHeader>
      <CardContent className="grid gap-4">
        <div className="grid gap-1 rounded-md border bg-muted/40 px-3 py-2 text-xs">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Applied load L</span>
            <span className="font-medium">{roundLoadForDisplay(entry.L)} g</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">mpe</span>
            <span className="font-medium">±{roundForDisplay(entry.mpe)} g</span>
          </div>
        </div>

        <div>
          <label className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {field === "indication" ? "Indication, I — what the machine shows" : "Additional load, ΔL"}
          </label>
          {field === "indication" ? (
            <p className="mt-0.5 text-xs text-muted-foreground">
              Expected (a perfect instrument would read):{" "}
              <span className="font-medium">{roundLoadForDisplay(entry.L)} g</span> — adjust to what the machine
              actually shows.
            </p>
          ) : null}
          <input
            ref={field === "indication" ? indicationRef : deltaLRef}
            className="mt-1 h-10 w-full rounded-md border border-input bg-background px-3 text-center text-lg font-medium focus:outline-none focus:ring-1 focus:ring-ring disabled:opacity-60"
            inputMode="decimal"
            disabled={disabled}
            value={value}
            onChange={(event) => updateCell(entry.sequence_no, cursor.apiDirection, { [field]: event.target.value })}
            onKeyDown={handleKeyDown}
          />
        </div>

        <div className="grid gap-1.5">
          <span className="text-xs text-muted-foreground">Fine (grams)</span>
          <div className="grid grid-cols-6 gap-1">
            {FINE_STEPS.map((step) => (
              <Button
                key={step}
                type="button"
                variant="outline"
                size="sm"
                className="px-1 text-xs"
                disabled={disabled}
                onClick={() => adjust(String(step))}
              >
                {step > 0 ? `+${step}` : step}
              </Button>
            ))}
          </div>
        </div>

        {eValue ? (
          <div className="grid gap-1.5">
            <span className="text-xs text-muted-foreground">Scale divisions</span>
            <div className="grid grid-cols-3 gap-1 sm:grid-cols-6">
              {SCALE_MULTIPLIERS.map((multiplier) => {
                const amount = multiplyDecimalStringBySmallInt(eValue, multiplier);
                return (
                  <Button
                    key={multiplier}
                    type="button"
                    variant="outline"
                    size="sm"
                    className="flex h-auto flex-col px-1 py-1 text-xs leading-tight"
                    disabled={disabled || amount === null}
                    onClick={() => adjustByScale(multiplier)}
                  >
                    <span>{multiplier > 0 ? `+${multiplier}e` : `${multiplier}e`}</span>
                    <span className="text-[10px] opacity-70">
                      ({multiplier > 0 ? "+" : ""}
                      {amount} g)
                    </span>
                  </Button>
                );
              })}
            </div>
          </div>
        ) : null}

        <div className="flex gap-2">
          <Button type="button" variant="outline" size="sm" onClick={() => moveTo(-1)} disabled={disabled}>
            &larr; Previous
          </Button>
          <Button type="button" className="flex-1" onClick={commitAndAdvance} disabled={disabled}>
            {field === "indication" ? "Next: ΔL" : "Submit & continue"}
          </Button>
        </div>

        {cell.error ? <p className="text-xs font-medium text-destructive">{cell.error}</p> : null}

        {lastResult ? (
          <div className="grid gap-1 rounded-md border px-3 py-2 text-xs">
            <span className="font-medium text-muted-foreground">
              Last recorded — load {lastLabel.loadNumber} ({directionGlyph(lastLabel.apiDirection)}):
            </span>
            <div className="flex justify-between">
              <span>E / Ec</span>
              <span>
                {roundForDisplay(lastResult.E)} / {roundForDisplay(lastResult.Ec)}
              </span>
            </div>
            <Badge variant={lastResult.passed ? "success" : "destructive"} className="w-fit">
              {lastResult.passed ? "PASS" : "FAIL"}
            </Badge>
          </div>
        ) : null}

        <p className="text-[11px] text-muted-foreground">
          Enter commits and moves on. Up/Down arrow = ±1 g. Escape returns focus to the table. Click any table cell
          to jump the guide there and amend it — resubmitting a changed value logs an amendment (see
          docs/architecture.md).
        </p>
      </CardContent>
    </Card>
  );
}
