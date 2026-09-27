import { PageHeader } from "@/components/AppShell";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

/**
 * Placeholder — chosen over omitting the sidebar item entirely (see
 * docs/architecture.md, Frontend), so the approver/admin nav reflects the
 * full role model without ever linking to a 404. No backing data yet:
 * every session-lifecycle action already writes to `audit_log`
 * (`readings_repo.insert_audit_log`), but no route exposes it for reading.
 */
export function AuditTrailPage() {
  return (
    <div>
      <PageHeader title="Audit trail" />
      <Card>
        <CardHeader>
          <CardTitle>Coming soon</CardTitle>
          <CardDescription>
            Every session action (submit, return, approve, issue) is already recorded in the database, but there's
            no read endpoint yet to show it here. This page will list the trail once that's built.
          </CardDescription>
        </CardHeader>
      </Card>
    </div>
  );
}
