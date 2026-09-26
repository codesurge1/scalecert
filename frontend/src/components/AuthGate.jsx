import { Navigate, Outlet } from "react-router-dom";
import { useSession } from "@/lib/supabase";
import { Skeleton } from "@/components/ui/skeleton";

/**
 * Wraps every authenticated route (react-router layout route). `session`
 * is `undefined` during the initial check — render a loading skeleton, not
 * a redirect, so a signed-in user never flashes the login screen on reload.
 */
export function AuthGate() {
  const session = useSession();

  if (session === undefined) {
    return (
      <div className="flex min-h-screen items-center justify-center p-8">
        <div className="w-full max-w-sm space-y-3">
          <Skeleton className="h-4 w-2/3" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-5/6" />
        </div>
      </div>
    );
  }

  if (session === null) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
