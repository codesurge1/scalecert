import { useSyncExternalStore } from "react";
import { THEME_STORAGE_KEY, normalizePreference, resolveTheme } from "@/lib/theme";

/**
 * The browser half of the theme (pure logic: `lib/theme.js`). One
 * module-level store rather than a React context, so every `ThemeToggle`
 * (sidebar, focused header, login, public verify page) and the Toaster stay
 * in sync without a provider having to wrap routes that live outside
 * AuthGate/AppShell.
 *
 * Storage is best-effort: private windows and blocked site data can throw
 * on access, in which case the choice simply lasts for this page load.
 */

const media =
  typeof window !== "undefined" && window.matchMedia
    ? window.matchMedia("(prefers-color-scheme: dark)")
    : null;

function readStoredPreference() {
  try {
    return normalizePreference(window.localStorage.getItem(THEME_STORAGE_KEY));
  } catch {
    return "system";
  }
}

let preference = typeof window !== "undefined" ? readStoredPreference() : "system";
const listeners = new Set();

function currentState() {
  return { preference, resolved: resolveTheme(preference, media?.matches ?? false) };
}

let snapshot = currentState();

function apply() {
  snapshot = currentState();
  const root = document.documentElement;
  root.classList.toggle("dark", snapshot.resolved === "dark");
  root.style.colorScheme = snapshot.resolved;
  for (const listener of listeners) listener();
}

if (typeof document !== "undefined") {
  apply();
  // Only matters while the preference is "system", but re-applying is
  // harmless for an explicit choice (resolveTheme ignores the OS then).
  media?.addEventListener("change", apply);
  // Another tab changed the preference — follow it.
  window.addEventListener("storage", (event) => {
    if (event.key !== THEME_STORAGE_KEY) return;
    preference = normalizePreference(event.newValue);
    apply();
  });
}

export function setThemePreference(next) {
  preference = normalizePreference(next);
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, preference);
  } catch {
    // Storage unavailable — keep the in-memory choice for this page load.
  }
  apply();
}

function subscribe(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** `{ preference: "light"|"dark"|"system", resolved: "light"|"dark", setPreference }` */
export function useTheme() {
  const state = useSyncExternalStore(subscribe, () => snapshot);
  return { ...state, setPreference: setThemePreference };
}
