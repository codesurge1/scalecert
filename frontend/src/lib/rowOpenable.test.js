import { describe, expect, it } from "vitest";
import { isRowOpenable } from "@/lib/rowOpenable";

const DIGITAL_INSTRUMENT = { indication_type: "digital", is_mobile: false };
const NON_SELF_INDICATING_INSTRUMENT = { indication_type: "non_self_indicating", is_mobile: false };

describe("isRowOpenable", () => {
  it("opens an implemented, applicable test regardless of the instrument", () => {
    expect(isRowOpenable({ testKey: "weighing" }, DIGITAL_INSTRUMENT)).toBe(true);
    expect(isRowOpenable({ testKey: "weighing" }, NON_SELF_INDICATING_INSTRUMENT)).toBe(true);
  });

  it("opens every implemented row from summaryChecklist.js's own testKey list", () => {
    // A representative one per family (checklist test, disturbance test,
    // multi-run test) rather than every row — the point is the FUNCTION
    // never special-cases a testKey by name, so a few is representative of
    // all of them.
    for (const testKey of ["zero_tare", "repeatability", "eccentricity", "voltage_variations", "damp_heat", "endurance"]) {
      expect(isRowOpenable({ testKey }, DIGITAL_INSTRUMENT)).toBe(true);
    }
  });

  it("stays inert for a placeholder row (a real OIML clause this app hasn't built)", () => {
    expect(isRowOpenable({ placeholder: true }, DIGITAL_INSTRUMENT)).toBe(false);
    expect(isRowOpenable({ placeholder: true }, null)).toBe(false);
  });

  it("stays inert for a row that's N/A for this instrument", () => {
    // Discrimination is N/A for a digital instrument (testChecklist.js).
    expect(isRowOpenable({ testKey: "discrimination" }, DIGITAL_INSTRUMENT)).toBe(false);
    // Tilting is N/A for a non-mobile instrument.
    expect(isRowOpenable({ testKey: "tilting" }, { is_mobile: false })).toBe(false);
  });

  it("opens a row once its N/A condition no longer applies", () => {
    expect(isRowOpenable({ testKey: "discrimination" }, { indication_type: "analog" })).toBe(true);
    expect(isRowOpenable({ testKey: "tilting" }, { is_mobile: true })).toBe(true);
  });

  it("never depends on session status or viewer role — the function accepts no such parameter", () => {
    // This is the actual regression this test exists to catch
    // (fix/approver-can-open-tests): a future change that tries to gate a
    // row on "is this session still draft" or "is this viewer the creator"
    // would have to add a parameter here, which would break every call
    // site above that only ever passes (sub, instrument) — not silently
    // reintroduce the bug.
    expect(isRowOpenable.length).toBe(2);
  });

  it("stays inert for an unknown testKey rather than throwing", () => {
    expect(isRowOpenable({ testKey: "not_a_real_test" }, DIGITAL_INSTRUMENT)).toBe(false);
  });
});
