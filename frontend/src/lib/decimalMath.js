// Decimal-safe string arithmetic for the guided-entry panel's quick-adjust
// buttons (CLAUDE.md's Decimal-as-string discipline: a value that could
// round-trip into a submitted reading must never pass through
// Number()/parseFloat()). BigInt-based, scaled to a shared exponent —
// mirrors the parse/scale/format shape already established in
// lib/accuracyClass.js, extended to handle SIGNED values, since both a
// running input ("-2.5") and a quick-adjust amount ("-10") can be negative,
// which that module's own parser deliberately doesn't need to support.

// "-12.340" -> { negative: true, digits: "12340", exponent: -3 }. No digit
// normalization (unlike accuracyClass.js's parser) — trailing zeros are
// kept as part of the fractional digit count, which is exactly what's
// needed to scale two operands to a shared exponent for addition. Returns
// null for anything that isn't a plain signed decimal numeral.
function parseSignedDecimal(value) {
  const trimmed = String(value ?? "").trim();
  const match = /^(-?)(\d+)(?:\.(\d+))?$/.exec(trimmed);
  if (!match) return null;
  const [, sign, intPart, fracPart = ""] = match;
  const digits = intPart + fracPart;
  const negative = sign === "-" && BigInt(digits) !== 0n;
  return { negative, digits, exponent: -fracPart.length };
}

function toSignedBigIntAtExponent(parsed, exponent) {
  const shift = parsed.exponent - exponent;
  const magnitude = BigInt(parsed.digits) * 10n ** BigInt(shift);
  return parsed.negative ? -magnitude : magnitude;
}

function formatSignedBigInt(intValue, exponent) {
  const negative = intValue < 0n;
  const digits = (negative ? -intValue : intValue).toString();
  let out;
  if (exponent >= 0) {
    out = digits + "0".repeat(exponent);
  } else {
    const point = digits.length + exponent;
    out = point <= 0 ? "0." + "0".repeat(-point) + digits : digits.slice(0, point) + "." + digits.slice(point);
  }
  if (out.includes(".")) {
    out = out.replace(/0+$/, "").replace(/\.$/, "");
  }
  if (out === "") out = "0";
  return negative && out !== "0" ? `-${out}` : out;
}

/** True iff `value` is a plain signed decimal numeral this module can add. */
export function isValidDecimalString(value) {
  return parseSignedDecimal(value) !== null;
}

/**
 * `a + b`, both plain decimal strings (either may be negative), exact —
 * scales to the finer of the two operands' exponents via BigInt before
 * adding, so e.g. "200" + "0.5" -> "200.5" never risks a float artifact.
 * Returns `null` if either operand isn't a plain decimal numeral (an empty
 * or in-progress input, most commonly) — callers treat that as "can't
 * adjust yet" rather than guessing a value.
 */
export function addDecimalStrings(a, b) {
  const pa = parseSignedDecimal(a);
  const pb = parseSignedDecimal(b);
  if (!pa || !pb) return null;
  const exponent = Math.min(pa.exponent, pb.exponent);
  const sum = toSignedBigIntAtExponent(pa, exponent) + toSignedBigIntAtExponent(pb, exponent);
  return formatSignedBigInt(sum, exponent);
}

/**
 * True iff `a` and `b` denote the same exact decimal value, regardless of
 * formatting (e.g. "10" and "10.0"). Used to tell a real amendment (the
 * technician actually changed what the instrument read) from a resubmit
 * that happens to round-trip through slightly different string formatting
 * — the latter should never write a spurious "amended" audit entry.
 */
export function equalDecimalStrings(a, b) {
  const pa = parseSignedDecimal(a);
  const pb = parseSignedDecimal(b);
  if (!pa || !pb) return String(a) === String(b);
  const exponent = Math.min(pa.exponent, pb.exponent);
  return toSignedBigIntAtExponent(pa, exponent) === toSignedBigIntAtExponent(pb, exponent);
}

/**
 * `value * multiplier`, where `multiplier` is a small exact JS integer
 * (e.g. -5, -2, -1, 1, 2, 5 — the scale-division quick-adjust steps), never
 * a parsed/decimal amount — safe to multiply directly since a small
 * integer literal has no float-precision risk. Used to turn an instrument's
 * `e_value` into "the gram amount +2e means right now."
 */
export function multiplyDecimalStringBySmallInt(value, multiplier) {
  const p = parseSignedDecimal(value);
  if (!p || !Number.isInteger(multiplier)) return null;
  const magnitude = BigInt(p.digits) * BigInt(multiplier);
  const signed = p.negative ? -magnitude : magnitude;
  return formatSignedBigInt(signed, p.exponent);
}
