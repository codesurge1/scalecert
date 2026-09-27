import { PageHeader } from "@/components/AppShell";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

/**
 * Placeholder — chosen over omitting the sidebar item entirely (see
 * docs/architecture.md, Frontend), so the approver/admin nav reflects the
 * full role model without ever linking to a 404. No backing data yet:
 * `discrepancy_reports` only has a public, login-free INSERT route
 * (`POST /verify/{cert}/report-discrepancy`) — there is no read endpoint an
 * authenticated admin/approver can call, though CLAUDE.md/architecture.md
 * already say only `admin` should ever read them back once one exists.
 */
export function DiscrepancyReportsPage() {
  return (
    <div>
      <PageHeader title="Discrepancy reports" />
      <Card>
        <CardHeader>
          <CardTitle>Coming soon</CardTitle>
          <CardDescription>
            Reports submitted from a certificate's public verification page aren't readable from the app yet — the
            backend has no read endpoint for them (only the public submit route exists). This page will list them
            once that's built.
          </CardDescription>
        </CardHeader>
      </Card>
    </div>
  );
}
