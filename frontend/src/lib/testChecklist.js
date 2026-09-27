// The OIML clause 8.3.3 seven-item checklist (CLAUDE.md), shared between the
// session overview (which lists added/started tests) and the "Add test"
// picker (which lets a technician pick one to open). All seven now have
// working forms (`route` below) — `zero_tare` has no own `test_type` in the
// schema — it's stored as a Weighing variant (db/schema.sql's test_type
// enum comment; distinguished by `direction` being null — see
// backend/app/contracts/zero_tare.py) — but IS its own selectable row and
// form here, same as any other test. Applicability for the three
// conditional tests (Discrimination/Tilting/Sensitivity) is computed from
// the instrument here rather than from `session_test_selections`, since no
// selection rows are created for any test but Weighing yet — the
// per-session test selector is a later task (docs/plan.md Phase 3), not
// built here.
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
    // N/A only for digital instruments (clause 8.3.3) — analog and
    // non-self-indicating instruments both get a working (different)
    // sub-procedure, derived server-side from indication_type, never
    // chosen here.
    naReason: (instrument) => (instrument.indication_type === "digital" ? "N/A — digital instrument" : null),
    route: (sessionId) => `/sessions/${sessionId}/discrimination`,
  },
  {
    key: "tilting",
    label: "Tilting",
    clause: "A.5.1.3",
    naReason: (instrument) => (!instrument.is_mobile ? "N/A — mobile instruments only" : null),
    route: (sessionId) => `/sessions/${sessionId}/tilting`,
  },
  {
    key: "sensitivity",
    label: "Sensitivity",
    clause: "A.4.9",
    naReason: (instrument) =>
      instrument.indication_type !== "non_self_indicating" ? "N/A — non-self-indicating instruments only" : null,
    route: (sessionId) => `/sessions/${sessionId}/sensitivity`,
  },
  // Added feat/disturbance-test-forms — clause 11 and clause 12.x. All
  // four are N/A for a non-self-indicating instrument: there's no
  // electronics for a voltage variation or an electrical disturbance to
  // act on (a mechanical beam balance has no power supply to vary or
  // disturb). Digital and analog instruments are both electronic, so
  // both are applicable to all four. Surges (12.3), radiated EM (12.5),
  // conducted RF (12.6), and road-vehicle transients (12.7) are real
  // OIML clauses this app has not built yet (docs/architecture.md) — no
  // row for them here, same "a row with no route has no form" rule every
  // other not-yet-implemented row already followed before this task.
  {
    key: "voltage_variations",
    label: "Voltage variations",
    clause: "A.5.4",
    naReason: (instrument) =>
      instrument.indication_type === "non_self_indicating" ? "N/A — no electronic indication to test" : null,
    route: (sessionId) => `/sessions/${sessionId}/voltage-variations`,
  },
  {
    key: "ac_mains_dips",
    label: "AC mains voltage dips & short interruptions",
    clause: "B.3.1",
    naReason: (instrument) =>
      instrument.indication_type === "non_self_indicating" ? "N/A — no electronic indication to test" : null,
    route: (sessionId) => `/sessions/${sessionId}/ac-mains-dips`,
  },
  {
    key: "electrical_bursts",
    label: "Electrical bursts",
    clause: "B.3.2",
    naReason: (instrument) =>
      instrument.indication_type === "non_self_indicating" ? "N/A — no electronic indication to test" : null,
    route: (sessionId) => `/sessions/${sessionId}/electrical-bursts`,
  },
  {
    key: "electrostatic_discharges",
    label: "Electrostatic discharges",
    clause: "B.3.4",
    naReason: (instrument) =>
      instrument.indication_type === "non_self_indicating" ? "N/A — no electronic indication to test" : null,
    route: (sessionId) => `/sessions/${sessionId}/electrostatic-discharges`,
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
