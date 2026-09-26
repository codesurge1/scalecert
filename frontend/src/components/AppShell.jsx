import { Link, Outlet, useNavigate } from "react-router-dom";
import { supabase, useSession } from "@/lib/supabase";
import { useProfile } from "@/hooks/useProfile";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

/**
 * The one layout every authenticated screen renders inside: a top bar
 * (wordmark, nav, identity + logout) and a content area. New screens slot
 * into the content area via nested routes (<Outlet/>) — they never need to
 * rebuild the top bar themselves.
 */
export function AppShell() {
  const session = useSession();
  const profile = useProfile(session);
  const navigate = useNavigate();

  async function handleLogout() {
    await supabase.auth.signOut();
    navigate("/login", { replace: true });
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-primary text-primary-foreground">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
          <div className="flex items-center gap-8">
            <span className="text-sm font-semibold tracking-wide">ScaleCert</span>
            <nav className="flex items-center gap-4 text-sm">
              <Link to="/" className="opacity-90 hover:opacity-100">
                Dashboard
              </Link>
              <Link to="/instruments" className="opacity-90 hover:opacity-100">
                Instruments
              </Link>
            </nav>
          </div>

          <div className="flex items-center gap-3 text-sm">
            {profile === undefined ? (
              <Skeleton className="h-4 w-32 bg-primary-foreground/20" />
            ) : (
              <span className="opacity-90">
                {session?.user?.email}
                {profile?.role ? (
                  <Badge variant="secondary" className="ml-2 align-middle">
                    {profile.role}
                  </Badge>
                ) : null}
              </span>
            )}
            <Button variant="secondary" size="sm" onClick={handleLogout}>
              Log out
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-8">
        <Outlet />
      </main>
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
