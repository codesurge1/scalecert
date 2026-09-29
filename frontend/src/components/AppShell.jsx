import { useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { ArrowLeft, LogOut, Menu, X } from "lucide-react";
import { supabase, useSession } from "@/lib/supabase";
import { useProfile } from "@/hooks/useProfile";
import { navItemsForRole } from "@/lib/navigation";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "@/components/ThemeToggle";

/**
 * The sidebar's nav list + pinned identity/logout footer — shared between
 * the persistent desktop `<aside>` and the mobile drawer `<aside>` so the
 * two can't drift. `profile === undefined` (still loading) renders
 * skeletons in place of both the nav list and the identity block, never a
 * guessed role's items.
 */
function SidebarContent({ profile, session, onNavigate, onLogout }) {
  const items = profile === undefined ? null : navItemsForRole(profile?.role);

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-sidebar-foreground/10 px-4 py-4">
        <span className="text-sm font-semibold tracking-wide">ScaleCert</span>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-2 py-4">
        {items === null ? (
          <>
            <Skeleton className="h-9 w-full bg-sidebar-foreground/10" />
            <Skeleton className="h-9 w-full bg-sidebar-foreground/10" />
            <Skeleton className="h-9 w-full bg-sidebar-foreground/10" />
          </>
        ) : (
          items.map((item) => (
            <NavLink
              key={item.key}
              to={item.to}
              end={item.to === "/"}
              onClick={onNavigate}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-sidebar-foreground/15 text-sidebar-foreground"
                    : "text-sidebar-foreground/80 hover:bg-sidebar-foreground/10 hover:text-sidebar-foreground",
                )
              }
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          ))
        )}
      </nav>

      {/* Pinned bottom: identity, role badge, log out — never scrolls away
          with a long nav list (nav above is the only scrollable region). */}
      <div className="border-t border-sidebar-foreground/10 px-3 py-4">
        {profile === undefined ? (
          <Skeleton className="mb-3 h-10 w-full bg-sidebar-foreground/10" />
        ) : (
          <div className="mb-3 space-y-1 text-sm">
            <div className="truncate text-sidebar-foreground/90">{session?.user?.email}</div>
            {profile?.role ? (
              <Badge variant="secondary" className="capitalize">
                {profile.role}
              </Badge>
            ) : null}
          </div>
        )}
        <ThemeToggle
          showLabel
          className="mb-2 w-full text-sidebar-foreground/80 hover:bg-sidebar-foreground/10 hover:text-sidebar-foreground"
        />
        <Button variant="secondary" size="sm" className="w-full" onClick={onLogout}>
          <LogOut className="h-4 w-4" />
          Log out
        </Button>
      </div>
    </div>
  );
}

/**
 * The one layout every authenticated screen renders inside: a persistent
 * left sidebar (role-driven nav + pinned identity/logout) and a main
 * content area. New screens slot into the content area via nested routes
 * (<Outlet/>) — they never need to rebuild the sidebar themselves.
 *
 * Replaces the previous top-bar nav (docs/architecture.md). On narrow
 * screens the persistent sidebar (`md:flex`, hidden below `md`) is replaced
 * by a hamburger-triggered drawer over a backdrop, rather than squeezing
 * the same nav into a top bar or letting it break the layout.
 */
export function AppShell() {
  const session = useSession();
  const profile = useProfile(session);
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);

  async function handleLogout() {
    await supabase.auth.signOut();
    navigate("/login", { replace: true });
  }

  return (
    // `md:h-dvh md:overflow-hidden` (new, `fix/sticky-sidebar`) — same
    // fixed-viewport-frame technique `FocusedShell` below already proved
    // (there gated at `lg`, here at `md` — the breakpoint the persistent
    // sidebar itself switches on, since below it there's no sidebar to
    // keep pinned; the mobile drawer is already `fixed`-positioned and
    // wholly unaffected either way). Below `md`, this stays plain
    // `min-h-screen` — normal document flow, content stacks, the whole
    // page scrolls — the pre-existing mobile behavior, untouched. At `md`+,
    // this container becomes exactly one viewport tall and non-scrolling
    // itself, so `<main>` below (not the document) is the one thing that
    // scrolls, and the sidebar — sized by the SAME flex-row `align-items:
    // stretch` default `WeighingFormTable`'s own two-column layout already
    // relies on (docs/architecture.md) — now genuinely fills that fixed
    // height instead of being only as tall as its own content.
    <div className="flex min-h-screen bg-background md:h-dvh md:overflow-hidden">
      {/* Desktop sidebar — persistent, never collapses to a hamburger. */}
      <aside className="hidden w-64 shrink-0 flex-col border-r bg-sidebar text-sidebar-foreground md:flex">
        <SidebarContent profile={profile} session={session} onLogout={handleLogout} />
      </aside>

      {/* Mobile backdrop + drawer — both md:hidden, so neither ever renders
          at desktop widths regardless of `mobileOpen`. */}
      {mobileOpen ? (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={() => setMobileOpen(false)}
          aria-hidden="true"
        />
      ) : null}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 w-64 flex-col bg-sidebar text-sidebar-foreground transition-transform duration-200 md:hidden",
          mobileOpen ? "flex translate-x-0" : "hidden -translate-x-full",
        )}
      >
        <div className="flex justify-end px-2 pt-2">
          <Button
            variant="ghost"
            size="icon"
            className="text-sidebar-foreground hover:bg-sidebar-foreground/10"
            onClick={() => setMobileOpen(false)}
            aria-label="Close menu"
          >
            <X className="h-5 w-5" />
          </Button>
        </div>
        <SidebarContent
          profile={profile}
          session={session}
          onLogout={handleLogout}
          onNavigate={() => setMobileOpen(false)}
        />
      </aside>

      {/* `md:min-h-0` — without it, this flex column defaults to a min
          height equal to its own content (`<main>`'s full, unclamped
          height), which would silently defeat the parent's `md:h-dvh`
          constraint above and bring back document-level scrolling — the
          same CSS Flexbox gotcha `FocusedShell`'s own comment already
          documents for its `lg:min-h-0` chain. */}
      <div className="flex min-w-0 flex-1 flex-col md:min-h-0">
        {/* Mobile top bar — hamburger + wordmark. Hidden on desktop, where
            the persistent sidebar already shows the wordmark. */}
        <header className="flex items-center gap-3 border-b bg-sidebar px-4 py-3 text-sidebar-foreground md:hidden">
          <Button
            variant="ghost"
            size="icon"
            className="text-sidebar-foreground hover:bg-sidebar-foreground/10"
            onClick={() => setMobileOpen(true)}
            aria-label="Open menu"
          >
            <Menu className="h-5 w-5" />
          </Button>
          <span className="text-sm font-semibold tracking-wide">ScaleCert</span>
        </header>

        {/* The one scrolling region at `md`+ (`md:overflow-y-auto`, paired
            with `md:min-h-0` so it can actually shrink to its share of the
            fixed-height row instead of growing to content size first) —
            every AppShell page (dashboard, instruments list, session
            overview, …) scrolls HERE now, never the document, so the
            sidebar beside it never moves. Below `md`, plain normal-flow
            scrolling, unchanged. */}
        <main className="flex-1 px-6 py-8 md:min-h-0 md:overflow-y-auto">
          <div className="mx-auto max-w-6xl">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}

/**
 * The layout every TEST-ENTRY screen renders inside instead of `AppShell` —
 * no sidebar at all (not hidden via CSS, literally not mounted, so it never
 * fetches a profile or takes up a DOM node). Data entry is a workstation
 * task, not a browsing task: the technician needs the full viewport width
 * for the form table, not a 256px nav rail they aren't using while heads-down
 * on one session. The only way back is the breadcrumb every test page
 * already renders via `FocusedPageHeader`, kept deliberately prominent since
 * it's now the sole navigation affordance on screen (docs/architecture.md,
 * focused test-entry mode).
 *
 * `lg:h-dvh lg:overflow-hidden` (new, `fix/vertical-fit-no-page-scroll`) —
 * gated at the SAME `lg` breakpoint the two-column table+panel layout
 * already switches on, deliberately: below `lg` this reverts to the
 * original `min-h-screen` document flow (page scrolls normally, content
 * stacks) — the existing narrow-viewport fallback is untouched. At `lg`+,
 * the shell becomes a fixed-height, non-scrolling frame — `<header>` and
 * `<main>`'s own padding are the only page-level chrome, and `<main>`
 * hands its exact remaining height down to whatever `<Outlet/>` renders
 * (`lg:flex lg:min-h-0 lg:flex-col`, so a `lg:flex-1 lg:min-h-0` child
 * gets a real, definite height to size itself against) — each test page is
 * then responsible for turning that into "chrome fixed, one region
 * scrolls," not the page itself. `WeighingSessionPage`/`WeighingFormTable`
 * carry that all the way down to the table's own row-scrolling region
 * (docs/architecture.md); the other six pages get the same fixed frame
 * plus a simpler whole-sheet scroll fallback, since their content is
 * short enough that it rarely engages.
 */
export function FocusedShell() {
  return (
    <div className="flex min-h-screen flex-col bg-background lg:h-dvh lg:overflow-hidden">
      <header className="flex shrink-0 items-center justify-between border-b bg-sidebar px-4 py-1.5 text-sidebar-foreground">
        <span className="text-sm font-semibold tracking-wide">ScaleCert</span>
        <ThemeToggle className="size-7 text-sidebar-foreground hover:bg-sidebar-foreground/10 hover:text-sidebar-foreground" />
      </header>
      <main className="flex-1 px-4 py-3 sm:px-6 lg:flex lg:min-h-0 lg:flex-col lg:overflow-hidden lg:py-2">
        <Outlet />
      </main>
    </div>
  );
}

/**
 * The way back AND the page title, on one slim row — merged
 * (`fix/vertical-fit-no-page-scroll`) from what used to be a full-width
 * bordered back-link pill followed by a separate `PageHeader` (a 2xl
 * heading with its own `mb-6`), which together cost ~115px of vertical
 * chrome on every test-entry screen before any table content. One line —
 * back-link pill, a middle dot, the title — costs ~30px instead, and is
 * still exactly as prominent a wayfinding affordance (same pill styling,
 * same destination) since it's still the only nav element on an otherwise
 * sidebar-free screen.
 */
export function FocusedPageHeader({ title, sessionId }) {
  return (
    <div className="flex shrink-0 flex-wrap items-center gap-2">
      <Link
        to={`/sessions/${sessionId}`}
        className="inline-flex items-center gap-1 rounded-md border bg-card px-2 py-1 text-xs font-medium text-foreground shadow-sm transition-colors hover:bg-accent"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Session overview
      </Link>
      <span className="text-muted-foreground" aria-hidden="true">
        &middot;
      </span>
      <h1 className="text-sm font-semibold text-foreground">{title}</h1>
    </div>
  );
}

/** The title area every page starts with — consistent across screens. */
export function PageHeader({ title, description, actions }) {
  return (
    <div className="mb-6 flex items-start justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">{title}</h1>
        {description ? <p className="mt-1 text-sm text-muted-foreground">{description}</p> : null}
      </div>
      {actions ? <div className="flex-shrink-0">{actions}</div> : null}
    </div>
  );
}
