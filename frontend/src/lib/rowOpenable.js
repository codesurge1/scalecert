import { TEST_ROWS } from "@/lib/testChecklist";

const TEST_ROWS_BY_KEY = Object.fromEntries(TEST_ROWS.map((row) => [row.key, row]));

/**
 * Whether a `summaryChecklist.js` leaf row can be opened from the session
 * summary — `SessionSummaryTable.jsx`'s `RowLabel`/`SummaryRowGroup` both
 * call this exact function, so there is exactly one place this decision is
 * made. Extracted into its own module (fix/approver-can-open-tests) so it's
 * unit-testable without pulling in React/react-router just to call a pure
 * function.
 *
 * Deliberately takes only `sub` (which row) and `instrument` (its
 * applicability) — NEVER `session`/`status`/`role` — mirroring
 * `testChecklist.js`'s own `isSelectable(row, instrument)` signature and
 * its "no forced sequence" reasoning exactly. An approver reviewing a
 * submitted/returned/approved/issued session must be able to open and
 * inspect every recorded test exactly like a technician on a draft one —
 * status controls a form's EDITABILITY (each form table's own
 * `disabled = sessionStatus !== "draft"`), never a summary row's
 * visibility/reachability. Not accepting a status/role parameter at all is
 * what makes that guarantee impossible to accidentally regress: there is no
 * value here to gate on even by mistake.
 *
 * The two reasons a row is NOT openable: it's `placeholder` (a real OIML
 * clause this app has never built an engine/form for — CLAUDE.md's scope
 * guardrail), or it's N/A for this instrument (`testRow.naReason`) — an N/A
 * test has nothing recorded, so it stays inert with its reason shown rather
 * than opening a page with nothing on it (this app's deliberate choice, see
 * `SessionSummaryTable.jsx`'s module doc).
 */
export function isRowOpenable(sub, instrument) {
  if (sub.placeholder) return false;
  const testRow = TEST_ROWS_BY_KEY[sub.testKey];
  if (!testRow) return false;
  const naReason = instrument && testRow.naReason ? testRow.naReason(instrument) : null;
  return !naReason;
}
