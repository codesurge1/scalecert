// The OIML clause 8.3.3 seven-item checklist (CLAUDE.md), shared between the
// session overview (which lists added/started tests) and the "Add test"
// picker (which lets a technician pick one to open). Weighing, Zero/tare
// device accuracy, Repeatability, and Eccentricity now have working forms
// (`route` below); `zero_tare` has no own `test_type` in the schema — it's
// stored as a Weighing variant (db/schema.sql's test_type enum comment;
// distinguished by `direction` being null — see
// backend/app/contracts/zero_tare.py) — but IS its own selectable row and
// form here, same as any other test. The remaining three (Discrimination,
// Tilting, Sensitivity) don't have forms yet; applicability for those is
// computed from the instrument here rather than from
// `session_test_selections`, since no selection rows are created for them
// yet (only `weighing` is, at session creation) — the per-session test
// selector is a later task (docs/plan.md Phase 3), not built here.
export const TEST_ROWS = [
  { key: "weighing", label: "Weighing", clause: "A.4.4 / A.5.3.1", route: (sessionId) => `/sessions/${sessionId}/weighing` },
  {
    key: "zero_tare",
    label: "Zero / tare device accuracy",
    clause: "A.4.4 variant",
    route: (sessionId) => `/sessions/${sessionId}/zero-tare`,
  },
  {
    key: "repeatability",
    label: "Repeatability",
    clause: "A.4.10",
    route: (sessionId) => `/sessions/${sessionId}/repeatability`,
  },
  {
    key: "eccentricity",
    label: "Eccentricity (3.1 weights)",
    clause: "A.4.7",
    route: (sessionId) => `/sessions/${sessionId}/eccentricity`,
  },
  {
    key: "discrimination",
    label: "Discrimination",
    clause: "A.4.8",
    naReason: (instrument) => (instrument.indication_type === "digital" ? "N/A — digital instrument" : null),
  },
  {
    key: "tilting",
    label: "Tilting",
    clause: "A.5.1.3",
    naReason: (instrument) => (!instrument.is_mobile ? "N/A — mobile instruments only" : null),
  },
  {
    key: "sensitivity",
    label: "Sensitivity",
    clause: "A.4.9",
    naReason: (instrument) =>
      instrument.indication_type !== "non_self_indicating" ? "N/A — non-self-indicating instruments only" : null,
  },
];

// A row with a `route` has a working form; the rest ("Coming soon") don't
// yet. This is the ONLY thing that changes as forms get built — nothing
// else about this function's shape does.
const IMPLEMENTED_KEYS = new Set(TEST_ROWS.filter((row) => row.route).map((row) => row.key));

// Tests are technician-selectable in ANY order — confirmed by RRSL (Deputy
// Director Sharma) and docs/plan.md's per-session test selector requirement
// ("Tests run in any order"); no test's availability may ever depend on
// another test's status (not-started/in-progress/complete). This function
// takes only `row` (which test) and `instrument` (its properties) as
// arguments — deliberately never session/reading/progress state — so a
// sequence dependency can't be reintroduced without changing this
// signature. The only two legitimate gates are: (1) applicability — the
// `naReason` check below, driven purely by instrument properties; (2) not
// yet implemented — a row with no `route` has no form built yet. Neither is
// a sequence lock, and nothing here reads any other test's progress.
export function isSelectable(row, instrument) {
  if (!IMPLEMENTED_KEYS.has(row.key)) return false;
  const naReason = instrument && row.naReason ? row.naReason(instrument) : null;
  return !naReason;
}
