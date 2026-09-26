// The OIML clause 8.3.3 seven-item checklist (CLAUDE.md), shared between the
// session overview (which lists added/started tests) and the "Add test"
// picker (which lets a technician pick one to open). Only Weighing has a
// working form so far; `zero_tare` has no own `test_type` in the schema yet
// — it's tracked as a Weighing variant (docs/plan.md Phase 3) — so it's
// listed for completeness but is never itself selectable. The other five
// map onto real `test_type` values that will get their own forms in later
// tasks; applicability for the conditional three is computed from the
// instrument here rather than from `session_test_selections`, since no
// selection rows are created for them yet (only `weighing` is, at session
// creation) — the per-session test selector is a later task (docs/plan.md
// Phase 3), not built here.
export const TEST_ROWS = [
  { key: "weighing", label: "Weighing", clause: "A.4.4 / A.5.3.1" },
  {
    key: "zero_tare",
    label: "Zero / tare device accuracy",
    clause: "A.4.4 variant",
    note: "Tracked as part of Weighing in this build — not yet its own form.",
  },
  { key: "repeatability", label: "Repeatability", clause: "A.4.5" },
  { key: "eccentricity", label: "Eccentricity (3.1 weights)", clause: "A.4.6" },
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

// Only Weighing has a working table today, and only when it isn't N/A for
// this instrument (it never is — Weighing is universal — but the check is
// symmetric with every other row's gating, not special-cased).
//
// Tests are technician-selectable in ANY order — confirmed by RRSL (Deputy
// Director Sharma) and docs/plan.md's per-session test selector requirement
// ("Tests run in any order"); no test's availability may ever depend on
// another test's status (not-started/in-progress/complete). This function
// takes only `row` (which test) and `instrument` (its properties) as
// arguments — deliberately never session/reading/progress state — so a
// sequence dependency can't be reintroduced without changing this
// signature. The only two legitimate gates are: (1) applicability — the
// `naReason` check below, driven purely by instrument properties; (2) not
// yet implemented — `row.key !== "weighing"`, since no other test has a
// form built yet. Neither is a sequence lock, and nothing here reads any
// other test's progress.
export function isSelectable(row, instrument) {
  if (row.key !== "weighing") return false;
  const naReason = instrument && row.naReason ? row.naReason(instrument) : null;
  return !naReason;
}
