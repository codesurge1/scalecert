import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { LogOut, Menu, X } from "lucide-react";
import { supabase, useSession } from "@/lib/supabase";
import { useProfile } from "@/hooks/useProfile";
import { navItemsForRole } from "@/lib/navigation";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

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
      <div className="border-b border-primary-foreground/10 px-4 py-4">
        <span className="text-sm font-semibold tracking-wide">ScaleCert</span>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-2 py-4">
        {items === null ? (
          <>
            <Skeleton className="h-9 w-full bg-primary-foreground/10" />
            <Skeleton className="h-9 w-full bg-primary-foreground/10" />
            <Skeleton className="h-9 w-full bg-primary-foreground/10" />
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
                    ? "bg-primary-foreground/15 text-primary-foreground"
                    : "text-primary-foreground/80 hover:bg-primary-foreground/10 hover:text-primary-foreground",
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
      <div className="border-t border-primary-foreground/10 px-3 py-4">
        {profile === undefined ? (
          <Skeleton className="mb-3 h-10 w-full bg-primary-foreground/10" />
        ) : (
          <div className="mb-3 space-y-1 text-sm">
            <div className="truncate text-primary-foreground/90">{session?.user?.email}</div>
            {profile?.role ? (
              <Badge variant="secondary" className="capitalize">
                {profile.role}
              </Badge>
            ) : null}
          </div>
        )}
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
    <div className="flex min-h-screen bg-background">
      {/* Desktop sidebar — persistent, never collapses to a hamburger. */}
      <aside className="hidden w-64 flex-col border-r bg-primary text-primary-foreground md:flex">
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
          "fixed inset-y-0 left-0 z-50 w-64 flex-col bg-primary text-primary-foreground transition-transform duration-200 md:hidden",
          mobileOpen ? "flex translate-x-0" : "hidden -translate-x-full",
        )}
      >
        <div className="flex justify-end px-2 pt-2">
          <Button
            variant="ghost"
            size="icon"
            className="text-primary-foreground hover:bg-primary-foreground/10"
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

      <div className="flex min-w-0 flex-1 flex-col">
        {/* Mobile top bar — hamburger + wordmark. Hidden on desktop, where
            the persistent sidebar already shows the wordmark. */}
        <header className="flex items-center gap-3 border-b bg-primary px-4 py-3 text-primary-foreground md:hidden">
          <Button
            variant="ghost"
            size="icon"
            className="text-primary-foreground hover:bg-primary-foreground/10"
            onClick={() => setMobileOpen(true)}
            aria-label="Open menu"
          >
            <Menu className="h-5 w-5" />
          </Button>
          <span className="text-sm font-semibold tracking-wide">ScaleCert</span>
        </header>

        <main className="flex-1 px-6 py-8">
          <div className="mx-auto max-w-6xl">
            <Outlet />
          </div>
        </main>
      </div>
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
