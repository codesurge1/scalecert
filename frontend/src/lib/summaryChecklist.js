// The OIML R 76-2 page-9 "Summary of type evaluation" master checklist —
// all ~18 numbered clauses (1-17, with clause 1 and several others having
// their own multi-line sub-structure), reproduced with the form's own
// numbering, labels, and row grouping. Read as a rendered image (page 9,
// poppler-utils/pdftoppm — same method used for pages 6/10/12/14/15/16/20)
// to match its exact structure. This is a faithful reproduction of the
// FORM'S LAYOUT for data-entry fidelity, not a copy of the copyrighted
// OIML document itself — no OIML explanatory/normative text beyond the
// form's own row labels and structural chrome.
//
// A leaf row (or sub-row) carries `testKey` when it maps onto one of this
// app's seven implemented checklist tests (`testChecklist.js`'s
// TEST_ROWS) — `SessionSummaryTable.jsx` looks up that key's live
// progress the exact same way `SessionPage` always has, unchanged. Every
// other leaf row has no `testKey` and is marked `placeholder: true`: a
// REAL page-9 line item this app has never built an engine/form for
// (CLAUDE.md scopes this app to the 8.3.3 seven-item checklist — "Creep
// and the other full-battery tests are stretch/out-of-scope"). Rendered
// as a clearly-marked "not implemented" row, never silently blank and
// never phrased as merely "not started" — that phrase is reserved for an
// IMPLEMENTED test nobody has entered data for yet, a materially
// different, more honest claim.
//
// One deliberate deviation from the page's own printed structure: page 9
// has no line item for "Zero/tare device accuracy" — CLAUDE.md groups it
// under clause 1 ("Weighing (incl. zero/tare device accuracy)"), since
// both are the same A.4.4 clause, but this app tracks them as two
// separate tests (separate routes, separate submitted data, separate
// forms). Rather than cramming two different tests' statuses into the
// form's single "Initial" line (confusing — one line, two different
// pass/fail verdicts) or inventing a same-looking NUMBERED row the real
// form doesn't have (dishonestly implying it's part of the OIML
// original), an extra sub-row is appended under clause 1's own group,
// flagged `appAddition: true` so `SessionSummaryTable.jsx` can style it
// as visibly this app's own addition rather than the form's.
export const SUMMARY_ROWS = [
  {
    number: "1",
    label: "Weighing performance",
    subRows: [
      { label: "Initial", testKey: "weighing" },
      { label: "°C", placeholder: true },
      { label: "°C", placeholder: true },
      { label: "°C", placeholder: true },
      { label: "°C", placeholder: true },
      { label: "°C", placeholder: true },
      { label: "°C", placeholder: true },
      { label: "Zero / tare device accuracy", testKey: "zero_tare", appAddition: true },
    ],
  },
  { number: "2", label: "Temperature effect on no-load indication", placeholder: true },
  { number: "3.1", label: "Eccentricity using weights", testKey: "eccentricity" },
  { number: "3.2", label: "Eccentricity using a rolling load", placeholder: true },
  { number: "4.1", label: "Discrimination", testKey: "discrimination" },
  { number: "4.2", label: "Sensitivity", testKey: "sensitivity" },
  { number: "5", label: "Repeatability", testKey: "repeatability" },
  { number: "6.1", label: "Zero return", placeholder: true },
  { number: "6.2", label: "Creep", placeholder: true },
  {
    number: "7",
    label: "Stability of equilibrium",
    subRows: [
      { label: "Printing, storage", placeholder: true },
      { label: "Zero-setting, tare balancing", placeholder: true },
    ],
  },
  { number: "8", label: "Tilting", testKey: "tilting" },
  { number: "9", label: "Tare", placeholder: true },
  { number: "10", label: "Warm-up time", placeholder: true },
  { number: "11", label: "Voltage variations", testKey: "voltage_variations" },
  { number: "12.1", label: "AC mains voltage dips and short interruptions", testKey: "ac_mains_dips" },
  {
    number: "12.2",
    label: "Electrical bursts",
    // Both sub-rows open the SAME test/route — this app builds 12.2 as one
    // combined form covering both (a) and (b) (app/services/disturbance.py),
    // not two separately-routed tests, so both page-9 lines point at it.
    subRows: [
      { label: "a) Mains power supply lines", testKey: "electrical_bursts" },
      { label: "b) I/O circuits and communication lines", testKey: "electrical_bursts" },
    ],
  },
  {
    number: "12.3",
    label: "Surges",
    subRows: [
      { label: "a) AC mains power supply", placeholder: true },
      { label: "b) Any other kind of power supply lines", placeholder: true },
    ],
  },
  {
    number: "12.4",
    label: "Electrostatic discharges",
    // Same reasoning as 12.2 above — one combined form for (a) and (b).
    subRows: [
      { label: "a) Direct application", testKey: "electrostatic_discharges" },
      { label: "b) Indirect application (contact discharges only)", testKey: "electrostatic_discharges" },
    ],
  },
  { number: "12.5", label: "Immunity to radiated electromagnetic fields", placeholder: true },
  { number: "12.6", label: "Immunity to conducted radio-frequency fields", placeholder: true },
  {
    number: "12.7",
    label: "Electrical transients on instruments powered from a road vehicle power supply",
    subRows: [
      { label: "a) Conduction along supply lines of external 12 V and 24 V batteries", placeholder: true },
      { label: "b) Capacitive and inductive coupling via lines other than supply lines", placeholder: true },
    ],
  },
  {
    number: "13",
    label: "Damp heat, steady state",
    // Added feat/damp-heat-endurance. All three sub-rows open the SAME
    // test/route — one page with three labelled runs (a/b/c), not three
    // separately-routed tests, same "one combined form" convention
    // 12.2/12.4 already established.
    subRows: [
      { label: "a) Initial test (at reference temperature)", testKey: "damp_heat" },
      { label: "b) Test at high temperature and 85 % relative humidity", testKey: "damp_heat" },
      { label: "c) Final test (at reference temperature)", testKey: "damp_heat" },
    ],
  },
  { number: "14", label: "Span stability", placeholder: true },
  {
    number: "15",
    label: "Endurance",
    subRows: [
      { label: "a) Initial test", testKey: "endurance" },
      { label: "c) Final test", testKey: "endurance" },
    ],
  },
  { sectionHeader: "EXAMINATIONS" },
  { number: "16", label: "Examination of the construction", placeholder: true },
  { number: "17", label: "Checklist", placeholder: true },
];
