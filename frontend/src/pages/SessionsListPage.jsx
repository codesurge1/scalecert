import { Link } from "react-router-dom";
import { useSession as useAuthSession } from "@/lib/supabase";
import { useProfile } from "@/hooks/useProfile";
import { useAllSessions } from "@/hooks/useAllSessions";
import { PageHeader } from "@/components/AppShell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const VERIFICATION_TYPE_LABELS = {
  initial: "Initial verification",
  subsequent: "Subsequent verification",
  in_service: "In-service verification",
};

function StatusBadge({ status }) {
  const variant = status === "draft" ? "secondary" : status === "issued" || status === "approved" ? "success" : "outline";
  return <Badge variant={variant} className="capitalize">{status}</Badge>;
}

// approved_by/created_by are UUIDs with no profile-name-lookup route
// exposed to every viewer (docs/architecture.md, SessionLifecyclePanel.jsx
// uses the same shortening) — good enough to distinguish rows without a
// new read endpoint.
function shortId(id) {
  return id ? `${id.slice(0, 8)}…` : "—";
}

/**
 * One shared page behind two sidebar items: a technician's "My sessions"
 * and an approver/admin's "Sessions (all)" both route here. RLS already
 * scopes `useAllSessions()`'s underlying calls correctly per role (a
 * technician only ever gets their own sessions back), so the same data
 * fetch is correct for either — only the title/description reflect which
 * one this caller is actually seeing.
 */
export function SessionsListPage() {
  const authSession = useAuthSession();
  const profile = useProfile(authSession);
  const { status, sessions, error, reload } = useAllSessions();

  const isApproverRole = profile?.role === "approver" || profile?.role === "admin";
  const sorted = [...sessions].sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

  return (
    <div>
      <PageHeader
        title={isApproverRole ? "Sessions (all)" : "My sessions"}
        description={
          isApproverRole
            ? "Every verification session visible to you, across every instrument."
            : "Verification sessions you've opened."
        }
      />

      {status === "loading" ? (
        <div className="space-y-2">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      ) : status === "error" ? (
        <Card className="border-destructive/50 bg-destructive/5">
          <CardContent className="flex items-center justify-between py-4 text-sm text-destructive">
            <span>Couldn't load sessions: {error}</span>
            <Button variant="outline" size="sm" onClick={reload}>
              Retry
            </Button>
          </CardContent>
        </Card>
      ) : sorted.length === 0 ? (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            {isApproverRole ? "No verification sessions exist yet." : "You haven't opened any verification sessions yet."}
          </CardContent>
        </Card>
      ) : (
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Instrument</TableHead>
                <TableHead>Verification type</TableHead>
                <TableHead>Status</TableHead>
                {isApproverRole ? <TableHead>Created by</TableHead> : null}
                <TableHead>Started</TableHead>
                <TableHead className="text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sorted.map((session) => (
                <TableRow key={session.id}>
                  <TableCell className="font-medium">
                    {session.instrument?.type_designation || session.instrument?.model || "—"}
                  </TableCell>
                  <TableCell>{VERIFICATION_TYPE_LABELS[session.verification_type] ?? session.verification_type}</TableCell>
                  <TableCell>
                    <StatusBadge status={session.status} />
                  </TableCell>
                  {isApproverRole ? (
                    <TableCell className="text-muted-foreground">
                      {session.created_by === profile?.id ? "You" : shortId(session.created_by)}
                    </TableCell>
                  ) : null}
                  <TableCell className="text-muted-foreground">
                    {new Date(session.created_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button asChild size="sm" variant="outline">
                      <Link to={`/sessions/${session.id}`}>Open</Link>
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}
    </div>
  );
}
