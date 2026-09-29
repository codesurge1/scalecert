import { describe, expect, it } from "vitest";
import { THEME_PREFERENCES, nextPreference, normalizePreference, resolveTheme } from "./theme";

describe("normalizePreference", () => {
  it("keeps every known preference", () => {
    for (const pref of THEME_PREFERENCES) expect(normalizePreference(pref)).toBe(pref);
  });

  it("falls back to system for missing or garbled values", () => {
    expect(normalizePreference(null)).toBe("system");
    expect(normalizePreference(undefined)).toBe("system");
    expect(normalizePreference("")).toBe("system");
    expect(normalizePreference("Dark")).toBe("system");
  });
});

describe("resolveTheme", () => {
  it("an explicit choice ignores the OS setting", () => {
    expect(resolveTheme("light", true)).toBe("light");
    expect(resolveTheme("dark", false)).toBe("dark");
  });

  it("system follows the OS setting", () => {
    expect(resolveTheme("system", true)).toBe("dark");
    expect(resolveTheme("system", false)).toBe("light");
  });

  it("an unknown preference behaves as system", () => {
    expect(resolveTheme("sepia", true)).toBe("dark");
    expect(resolveTheme(null, false)).toBe("light");
  });
});

describe("nextPreference", () => {
  it("cycles light → dark → system → light", () => {
    expect(nextPreference("light")).toBe("dark");
    expect(nextPreference("dark")).toBe("system");
    expect(nextPreference("system")).toBe("light");
  });

  it("starts from system for an unknown value", () => {
    expect(nextPreference("bogus")).toBe("light");
  });
});
