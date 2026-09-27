// Direction mapping — explicit and intentional, do not "simplify" this away.
// The OIML R 76-2 form prints two sub-columns per quantity, headed with the
// glyphs "↓" and "↑" (increasing load, then decreasing load). This app's API
// names directions semantically instead ("up" = increasing, "down" =
// decreasing). So: the form's "↓" sub-column is the increasing-load pass,
// i.e. API direction "up"; the form's "↑" sub-column is the decreasing-load
// pass, i.e. API direction "down". The glyph-to-API mapping is deliberately
// crossed like this and must stay exactly as specified.
//
// Its own module (not exported from WeighingFormTable.jsx) specifically so
// GuidedEntryPanel.jsx can import it too without the two components
// importing each other.
export const FORM_COLUMNS = [
  { glyph: "↓", apiDirection: "up" },
  { glyph: "↑", apiDirection: "down" },
];

/**
 * The real lab procedure (OIML R76-1 A.4.4.1): "apply test loads from zero
 * up to and including Max, and likewise remove the test loads down to
 * zero" — the technician loads progressively up, THEN unloads progressively
 * down. They never add and remove weights load-by-load. So the guided
 * walk is NOT "load1 up, load1 down, load2 up, load2 down, ..." — it's the
 * full increasing pass (every load ascending, `sequence`'s own order —
 * `L`'s ascending order is exactly the order `engine.load_sequence`
 * returns), THEN the full decreasing pass in REVERSE (every load
 * descending, Max first).
 *
 * The one, shared definition of "what comes next" for both the guided
 * panel's auto-advance/Previous/Next AND the table's own initial-resume
 * position (`WeighingFormTable.jsx`'s `findFirstIncomplete`) — kept here,
 * next to `FORM_COLUMNS`, so there is exactly one place this order is
 * defined, not two that could drift apart.
 */
export function buildGuidedWalkPositions(sequence) {
  const positions = [];
  for (const entry of sequence) {
    positions.push({ sequenceNo: entry.sequence_no, apiDirection: "up", field: "indication" });
    positions.push({ sequenceNo: entry.sequence_no, apiDirection: "up", field: "deltaL" });
  }
  for (let i = sequence.length - 1; i >= 0; i--) {
    const entry = sequence[i];
    positions.push({ sequenceNo: entry.sequence_no, apiDirection: "down", field: "indication" });
    positions.push({ sequenceNo: entry.sequence_no, apiDirection: "down", field: "deltaL" });
  }
  return positions;
}
