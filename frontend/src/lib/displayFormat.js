// Display-only rounding for a computed Decimal-as-string value (E, Ec, mpe,
// margin, a difference/threshold/extra-load/spread/deviation figure, or a
// derived load) — used ONLY when putting a number on screen. It must never
// touch a value on its way to or from the API: CLAUDE.md's Decimal-as-string
// discipline (never Number()/parseFloat() on a value that gets sent or
// stored) still applies everywhere else — the exact string the backend
// returns is what stays in component state and what gets POSTed back.
//
// The backend/engine intentionally return the EXACT Decimal result (e.g.
// "1.2857142857142857143" from a 1/3-of-Max load fraction, or a genuine
// repeating decimal from a division) — CLAUDE.md: no calculated verdict is
// trusted until the boundary-value tests pass, so the STORED value must
// stay exact. Rounding only ever happens here, once, at the point a value
// is about to be rendered as text, so it reads like a real report figure
// instead of a ~19-digit fraction.
//
// Uses Number()/toFixed() — safe here specifically because the result is
// thrown away after rendering, never fed back into a request or persisted;
// float64 has far more precision than the 0-2 decimal places this rounds
// to, so no visible error is introduced at gram-scale magnitudes.
export function roundForDisplay(value, decimals = 2) {
  if (value === undefined || value === null || value === "") return "";
  const n = Number(value);
  if (!Number.isFinite(n)) return String(value);
  return n.toFixed(decimals);
}

// A derived/generated load (L) — the same shared rounding, at a precision
// that reads like a real test weight rather than an error figure.
export function roundLoadForDisplay(value) {
  return roundForDisplay(value, 1);
}
