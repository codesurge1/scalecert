import { PageHeader } from "@/components/AppShell";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

// Placeholder — session/reading/verify screens land here in later tasks.
export function DashboardPage() {
  return (
    <div>
      <PageHeader title="Dashboard" description="Overview — more here as later screens land." />
      <Card>
        <CardHeader>
          <CardTitle>Getting started</CardTitle>
          <CardDescription>
            Register an instrument to begin. Weighing verification sessions are a later screen.
          </CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          Use the Instruments page in the top navigation.
        </CardContent>
      </Card>
    </div>
  );
}
