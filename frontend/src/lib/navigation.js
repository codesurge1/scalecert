import {
  AlertTriangle,
  ClipboardList,
  History,
  LayoutDashboard,
  Scale,
} from "lucide-react";

/**
 * The one list every role-aware nav surface (currently just the sidebar)
 * reads from — a technician never sees an item they can't act on, because
 * the item is filtered OUT here, not disabled/greyed at render time.
 *
 * `to` for "my-sessions"/"all-sessions" is deliberately the SAME route
 * (`/sessions`) — one page (`SessionsListPage`), whose title/scope adapts
 * to the caller's role (RLS already scopes a technician's own GET to only
 * their sessions, so the underlying data is correct either way — see
 * `useAllSessions.js`). Only one of the two ever renders for a given role,
 * so there's never a duplicate link to the same place in one sidebar.
 */
const NAV_ITEMS = [
  { key: "dashboard", label: "Dashboard", to: "/", icon: LayoutDashboard, roles: ["technician", "approver", "admin"] },
  { key: "instruments", label: "Instruments", to: "/instruments", icon: Scale, roles: ["technician", "approver", "admin"] },
  { key: "my-sessions", label: "My sessions", to: "/sessions", icon: ClipboardList, roles: ["technician"] },
  { key: "all-sessions", label: "Sessions (all)", to: "/sessions", icon: ClipboardList, roles: ["approver", "admin"] },
  { key: "discrepancy-reports", label: "Discrepancy reports", to: "/discrepancy-reports", icon: AlertTriangle, roles: ["approver", "admin"] },
  { key: "audit-trail", label: "Audit trail", to: "/audit-trail", icon: History, roles: ["approver", "admin"] },
  // "Users & roles" deliberately omitted — no such page exists yet
  // (role promotion is seed-script-only, ADR-0004). Add it here, gated to
  // ["admin"], the day that page is actually built — never link to a 404.
];

/**
 * `role` is `undefined` (profile still loading — caller should render a
 * skeleton instead of calling this), or a known role string. An
 * unrecognized/`null` role (no visible `profiles` row — CLAUDE.md: RLS
 * returning zero rows is a valid outcome, not an error) falls back to the
 * items every role shares, rather than guessing — never approver/admin-only
 * items for an unknown role.
 */
export function navItemsForRole(role) {
  const safeRole = ["technician", "approver", "admin"].includes(role) ? role : "technician";
  return NAV_ITEMS.filter((item) => item.roles.includes(safeRole));
}
