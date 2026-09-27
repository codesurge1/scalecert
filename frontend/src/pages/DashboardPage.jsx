import { Link } from "react-router-dom";
import { useSession as useAuthSession } from "@/lib/supabase";
import { useProfile } from "@/hooks/useProfile";
import { useAllSessions } from "@/hooks/useAllSessions";
import { PageHeader } from "@/components/AppShell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

const VERIFICATION_TYPE_LABELS = {
  initial: "Initial verification",
  subsequent: "Subsequent verification",
  in_service: "In-service verification",
};

function StatusBadge({ status }) {
  const variant = status === "draft" ? "secondary" : status === "issued" || status === "approved" ? "success" : "outline";
  return <Badge variant={variant} className="capitalize">{status}</Badge>;
}

function StatCard({ label, value }) {
  return (
    <Card>
      <CardContent className="py-4">
        <div className="text-2xl font-semibold">{value === undefined ? <Skeleton className="h-7 w-10" /> : value}</div>
        <div className="text-xs text-muted-foreground">{label}</div>
      </CardContent>
    </Card>
  );
}

/** A deliberately styled "nothing here" state — CLAUDE.md-adjacent task
 * note: an empty queue should look intentional, not like a broken load. */
function EmptyState({ message }) {
  return (
    <Card className="border-dashed">
      <CardContent className="py-8 text-center text-sm text-muted-foreground">{message}</CardContent>
    </Card>
  );
}

function SessionListItem({ session }) {
  const instrumentLabel =
    session.instrument?.type_designation || session.instrument?.model || "Instrument";
  return (
    <div className="border-b py-3 last:border-b-0">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-sm font-medium">{instrumentLabel}</div>
          <div className="text-xs text-muted-foreground">
            {VERIFICATION_TYPE_LABELS[session.verification_type] ?? session.verification_type}
          </div>
        </div>
        <div className="flex items-center gap-3">
          <StatusBadge status={session.status} />
          <Button asChild size="sm" variant="outline">
            <Link to={`/sessions/${session.id}`}>Open</Link>
          </Button>
        </div>
      </div>
      {session.status === "returned" && session.return_reason ? (
        <div className="mt-2 rounded-md border border-warning/50 bg-warning/10 px-3 py-2 text-xs">
          <span className="font-medium">Returned: </span>
          {session.return_reason}
        </div>
      ) : null}
    </div>
  );
}

function SessionListLoading() {
  return (
    <div className="space-y-2">
      <Skeleton className="h-14 w-full" />
      <Skeleton className="h-14 w-full" />
    </div>
  );
}

function TechnicianDashboard({ profile, allSessions, instruments, status, error, reload }) {
  const ownSessions = allSessions.filter((s) => s.created_by === profile.id);
  const needingWork = ownSessions
    .filter((s) => s.status === "draft" || s.status === "returned")
    // Returned sessions surfaced first — they need a reason read, not just
    // "continue where I left off" like a draft does.
    .sort((a, b) => (a.status === "returned" ? -1 : 0) - (b.status === "returned" ? -1 : 0));
  const inProgressCount = ownSessions.filter((s) =>
    ["draft", "submitted", "returned", "approved"].includes(s.status),
  ).length;
  const issuedCount = ownSessions.filter((s) => s.status === "issued").length;
  const registeredCount = instruments.filter((i) => i.registered_by === profile.id).length;

  return (
    <div className="grid gap-6">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <StatCard label="Instruments registered" value={status === "loaded" ? registeredCount : undefined} />
        <StatCard label="Sessions in progress" value={status === "loaded" ? inProgressCount : undefined} />
        <StatCard label="Certificates issued" value={status === "loaded" ? issuedCount : undefined} />
      </div>

      <div className="flex flex-wrap gap-3">
        <Button asChild>
          <Link to="/instruments/new">Register instrument</Link>
        </Button>
        <Button asChild variant="outline">
          <Link to="/instruments">Start verification</Link>
        </Button>
      </div>

      <div>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Needs your attention
        </h2>
        {status === "loading" ? (
          <SessionListLoading />
        ) : status === "error" ? (
          <Card className="border-destructive/50 bg-destructive/5">
            <CardContent className="flex items-center justify-between py-4 text-sm text-destructive">
              <span>Couldn't load your sessions: {error}</span>
              <Button variant="outline" size="sm" onClick={reload}>
                Retry
              </Button>
            </CardContent>
          </Card>
        ) : needingWork.length === 0 ? (
          <EmptyState message="Nothing needs your attention — every draft is either submitted or you're all caught up." />
        ) : (
          <Card>
            <CardContent className="py-2">
              {needingWork.map((session) => (
                <SessionListItem key={session.id} session={session} />
              ))}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

function ApproverDashboard({ profile, allSessions, status, error, reload }) {
  const awaitingApproval = allSessions.filter((s) => s.status === "submitted" && s.created_by !== profile.id);
  const ownSessions = allSessions.filter((s) => s.created_by === profile.id);
  const issuedCount = allSessions.filter((s) => s.status === "issued").length;

  return (
    <div className="grid gap-6">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-2">
        <StatCard label="Pending approvals" value={status === "loaded" ? awaitingApproval.length : undefined} />
        <StatCard label="Certificates issued" value={status === "loaded" ? issuedCount : undefined} />
      </div>
      {/* Discrepancy-report counts are NOT shown here — there is no read
          endpoint for discrepancy_reports yet (only the public POST at
          /verify/{cert}/report-discrepancy exists; CLAUDE.md/architecture.md:
          only admin may ever read them back, and that read route isn't
          built). Flagged rather than faked with a client-side guess. */}
      <p className="-mt-2 text-xs text-muted-foreground">
        Discrepancy-report counts aren't shown yet — no read endpoint exists for them (see "Discrepancy reports").
      </p>

      <div>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Awaiting your approval
        </h2>
        {status === "loading" ? (
          <SessionListLoading />
        ) : status === "error" ? (
          <Card className="border-destructive/50 bg-destructive/5">
            <CardContent className="flex items-center justify-between py-4 text-sm text-destructive">
              <span>Couldn't load sessions: {error}</span>
              <Button variant="outline" size="sm" onClick={reload}>
                Retry
              </Button>
            </CardContent>
          </Card>
        ) : awaitingApproval.length === 0 ? (
          <EmptyState message="Nothing awaiting your approval right now." />
        ) : (
          <Card>
            <CardContent className="py-2">
              {awaitingApproval.map((session) => (
                <SessionListItem key={session.id} session={session} />
              ))}
            </CardContent>
          </Card>
        )}
      </div>

      <div>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Your own sessions
        </h2>
        <p className="mb-3 text-xs text-muted-foreground">
          You cannot approve these yourself — separation of duties requires a different approver or an admin to act
          on them.
        </p>
        {status === "loading" ? (
          <SessionListLoading />
        ) : status === "error" ? null : ownSessions.length === 0 ? (
          <EmptyState message="You haven't opened any verification sessions yourself." />
        ) : (
          <Card>
            <CardContent className="py-2">
              {ownSessions.map((session) => (
                <SessionListItem key={session.id} session={session} />
              ))}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

/**
 * The role-aware landing screen — "what needs my attention," not a generic
 * welcome page. Technician and approver/admin see structurally different
 * content (docs/architecture.md, Frontend); admin currently reuses the
 * approver view unchanged, per this task's own scope.
 */
export function DashboardPage() {
  const authSession = useAuthSession();
  const profile = useProfile(authSession);
  const { status, sessions, instruments, error, reload } = useAllSessions();

  const isApproverRole = profile?.role === "approver" || profile?.role === "admin";

  return (
    <div>
      <PageHeader
        title="Dashboard"
        description={isApproverRole ? "What needs your approval, and your own work." : "What needs your attention."}
      />

      {profile === undefined ? (
        <div className="space-y-3">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      ) : profile === null ? (
        <Card>
          <CardHeader>
            <CardTitle>No profile found</CardTitle>
            <CardDescription>
              Your account has no visible profile row, so a role-specific dashboard can't be shown. Contact an
              admin.
            </CardDescription>
          </CardHeader>
        </Card>
      ) : isApproverRole ? (
        <ApproverDashboard profile={profile} allSessions={sessions} status={status} error={error} reload={reload} />
      ) : (
        <TechnicianDashboard
          profile={profile}
          allSessions={sessions}
          instruments={instruments}
          status={status}
          error={error}
          reload={reload}
        />
      )}
    </div>
  );
}
