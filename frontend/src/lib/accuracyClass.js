// OIML R76-1 Table 3 accuracy-class derivation — a client-side MIRROR of
// engine/classification.py's classify_instrument, for instant feedback as
// the technician types e/Max/Min. This must stay in exact sync with that
// module (same rows, same bounds, same 1/2/5x10^k rule) — if you change
// one, change the other. The server is the actual source of truth: the
// real POST /api/instruments call re-derives the class itself and is what
// persists it, so a bug here only affects how quickly the UI can show a
// wrong preview, never what gets stored.
//
// Decimal-as-string discipline (CLAUDE.md): every value here is parsed
// from the raw input strings using string-based digit manipulation, never
// Number()/parseFloat() — a float risks exactly the 0.1-style rounding
// artifacts this project avoids everywhere else.

// One row of Table 3: a (class, e-range) combination with its own n-range
// and Min-capacity-as-a-multiple-of-e requirement. e bounds are in grams,
// null = unbounded. n_max mirrors engine.mpe.BAND_TABLE's top band edge
// per class, same reasoning as the Python module's _n_max_for_class.
const TABLE_3 = [
  { accuracyClass: "I", eMin: "0.001", eMax: null, nMin: "50000", nMax: null, minMultipleOfE: "100" },
  { accuracyClass: "II", eMin: "0.001", eMax: "0.05", nMin: "100", nMax: "100000", minMultipleOfE: "20" },
  { accuracyClass: "II", eMin: "0.1", eMax: null, nMin: "5000", nMax: "100000", minMultipleOfE: "50" },
  { accuracyClass: "III", eMin: "0.1", eMax: "2", nMin: "100", nMax: "10000", minMultipleOfE: "20" },
  { accuracyClass: "III", eMin: "5", eMax: null, nMin: "500", nMax: "10000", minMultipleOfE: "20" },
  { accuracyClass: "IIII", eMin: "5", eMax: null, nMin: "100", nMax: "1000", minMultipleOfE: "10" },
];

// Parses a plain (non-negative, non-exponential) decimal string "123.450"
// into { digits: "12345", exponent: -2 } — i.e. value = digits * 10^exponent,
// with leading/trailing zeros stripped, mirroring Python's
// Decimal.normalize().as_tuple(). Returns null for anything that isn't a
// simple decimal numeral.
function parseDecimalString(value) {
  const trimmed = String(value).trim();
  if (!/^\d+(\.\d+)?$/.test(trimmed)) return null;
  const [intPart, fracPart = ""] = trimmed.split(".");
  let exponent = -fracPart.length;
  let digits = intPart + fracPart;
  digits = digits.replace(/^0+(?=\d)/, "");
  const strippedTrailing = digits.replace(/0+$/, "");
  exponent += digits.length - strippedTrailing.length;
  digits = strippedTrailing === "" ? "0" : strippedTrailing;
  return { digits, exponent };
}

// True iff e = m x 10^k for m in {1, 2, 5} — clause 3.4.2.
export function isValidE(eStr) {
  const parsed = parseDecimalString(eStr);
  if (!parsed) return false;
  return parsed.digits === "1" || parsed.digits === "2" || parsed.digits === "5";
}

// Exact decimal string comparison/arithmetic via BigInt, scaled to a shared
// exponent — avoids float entirely for the n/Min comparisons below.
function toScaled(value, exponent) {
  const parsed = typeof value === "string" ? parseDecimalString(value) : { digits: value.toString(), exponent: 0 };
  if (!parsed) return null;
  const shift = parsed.exponent - exponent;
  if (shift < 0) throw new Error("precision loss"); // never hit: exponent is always the min of the two
  return BigInt(parsed.digits) * 10n ** BigInt(shift);
}

function compareDecimalStrings(a, b) {
  const pa = parseDecimalString(a);
  const pb = parseDecimalString(b);
  const exponent = Math.min(pa.exponent, pb.exponent);
  const scaledA = toScaled(a, exponent);
  const scaledB = toScaled(b, exponent);
  return scaledA < scaledB ? -1 : scaledA > scaledB ? 1 : 0;
}

function divideDecimalStrings(numerator, denominator) {
  // Only used for display (n = Max/e) — not for any pass/fail branch, so
  // ordinary floating-point division is fine here (the actual n_min/n_max
  // comparisons below are done on Max directly, as an exact multiple of e,
  // never on this divided value).
  return Number(numerator) / Number(denominator);
}

function multiplyDecimalStrings(a, b) {
  const pa = parseDecimalString(a);
  const pb = parseDecimalString(b);
  const digits = (BigInt(pa.digits) * BigInt(pb.digits)).toString();
  const exponent = pa.exponent + pb.exponent;
  return formatScaled(digits, exponent);
}

function formatScaled(digits, exponent) {
  if (exponent >= 0) return digits + "0".repeat(exponent);
  const point = digits.length + exponent;
  if (point <= 0) return "0." + "0".repeat(-point) + digits;
  return digits.slice(0, point) + "." + digits.slice(point);
}

/**
 * Derive the OIML R76-1 Table 3 accuracy class(es) for e/Max/Min (all raw
 * strings, never numbers — Decimal-as-string discipline). Mirrors
 * engine.classification.classify_instrument's return shape:
 * `{ n, qualifiedClasses, reason }`. `n` is a plain JS number for display
 * only. `d` (optional) is checked against clause 3.4.2's d < e <= 10d.
 */
export function classifyInstrument({ e, maxCapacity, minCapacity, d }) {
  if (!e || !maxCapacity || !minCapacity) {
    return { n: null, qualifiedClasses: [], reason: null }; // incomplete input, not yet a rejection
  }
  if (!/^\d+(\.\d+)?$/.test(e) || !/^\d+(\.\d+)?$/.test(maxCapacity) || !/^\d+(\.\d+)?$/.test(minCapacity)) {
    return { n: null, qualifiedClasses: [], reason: "e, Max, and Min must be plain positive numbers." };
  }

  const n = divideDecimalStrings(maxCapacity, e);

  if (!isValidE(e)) {
    return {
      n,
      qualifiedClasses: [],
      reason: `e=${e}g is not a valid verification scale interval — clause 3.4.2 requires e = 1, 2, or 5 × 10^k grams.`,
    };
  }

  if (d && d.trim() !== "") {
    const dValid = /^\d+(\.\d+)?$/.test(d);
    const ok = dValid && compareDecimalStrings(d, e) < 0 && compareDecimalStrings(e, multiplyDecimalStrings("10", d)) <= 0;
    if (!ok) {
      return {
        n,
        qualifiedClasses: [],
        reason: `d=${d}g and e=${e}g do not satisfy clause 3.4.2's d < e ≤ 10d.`,
      };
    }
  }

  const applicableRows = TABLE_3.filter((row) => {
    if (compareDecimalStrings(e, row.eMin) < 0) return false;
    if (row.eMax !== null && compareDecimalStrings(e, row.eMax) > 0) return false;
    return true;
  });

  if (applicableRows.length === 0) {
    return { n, qualifiedClasses: [], reason: `No Table 3 accuracy class defines a range for e=${e}g.` };
  }

  const qualified = [];
  const failures = [];
  for (const row of applicableRows) {
    const nOkMin = compareDecimalStrings(maxCapacity, multiplyDecimalStrings(row.nMin, e)) >= 0;
    const nOkMax = row.nMax === null || compareDecimalStrings(maxCapacity, multiplyDecimalStrings(row.nMax, e)) <= 0;
    const minRequired = multiplyDecimalStrings(row.minMultipleOfE, e);
    const minOk = compareDecimalStrings(minCapacity, minRequired) >= 0;

    if (nOkMin && nOkMax && minOk) {
      if (!qualified.includes(row.accuracyClass)) qualified.push(row.accuracyClass);
      continue;
    }
    if (!nOkMin || !nOkMax) {
      failures.push(`Class ${row.accuracyClass} requires n between ${row.nMin} and ${row.nMax ?? "unbounded"} (got n=${n})`);
    }
    if (!minOk) {
      failures.push(`Class ${row.accuracyClass} requires Min ≥ ${row.minMultipleOfE}e = ${minRequired}g (got Min=${minCapacity}g)`);
    }
  }

  if (qualified.length > 0) {
    return { n, qualifiedClasses: qualified, reason: null };
  }
  return {
    n,
    qualifiedClasses: [],
    reason: `No accuracy class fits e=${e}g, Max=${maxCapacity}g (n=${n}), Min=${minCapacity}g: ${failures.join("; ")}.`,
  };
}
