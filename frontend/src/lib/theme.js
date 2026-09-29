/**
 * Light/dark theme — the pure, DOM-free half (docs/architecture.md,
 * Frontend → Theme). `hooks/useTheme.js` owns the browser side (storage,
 * `matchMedia`, the `<html>` class); everything that can be decided without
 * a browser lives here so Vitest can cover it in `environment: 'node'`.
 *
 * `index.html` carries an inline copy of `resolveTheme` + the storage read,
 * run before first paint so a dark-mode user never sees a white flash while
 * the bundle loads. Keep THEME_STORAGE_KEY and the three preference values
 * in sync with that script.
 */

export const THEME_STORAGE_KEY = "scalecert-theme";

/** What the user chose. "system" follows the OS `prefers-color-scheme`. */
export const THEME_PREFERENCES = ["light", "dark", "system"];

/** Anything unrecognised (missing key, stale/garbled storage) → "system". */
export function normalizePreference(value) {
  return THEME_PREFERENCES.includes(value) ? value : "system";
}

/** The theme actually painted: always "light" or "dark", never "system". */
export function resolveTheme(preference, systemPrefersDark) {
  const pref = normalizePreference(preference);
  if (pref === "system") return systemPrefersDark ? "dark" : "light";
  return pref;
}

/** Toggle order: light → dark → system → light. */
export function nextPreference(preference) {
  const pref = normalizePreference(preference);
  return THEME_PREFERENCES[(THEME_PREFERENCES.indexOf(pref) + 1) % THEME_PREFERENCES.length];
}
