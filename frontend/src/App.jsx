import { Navigate, Route, Routes } from "react-router-dom";
import { AuthGate } from "@/components/AuthGate";
import { AppShell, FocusedShell } from "@/components/AppShell";
import { LoginPage } from "@/pages/LoginPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { InstrumentsListPage } from "@/pages/InstrumentsListPage";
import { InstrumentRegisterPage } from "@/pages/InstrumentRegisterPage";
import { InstrumentDetailPage } from "@/pages/InstrumentDetailPage";
import { SessionPage } from "@/pages/SessionPage";
import { WeighingSessionPage } from "@/pages/WeighingSessionPage";
import { ZeroTareSessionPage } from "@/pages/ZeroTareSessionPage";
import { RepeatabilitySessionPage } from "@/pages/RepeatabilitySessionPage";
import { EccentricitySessionPage } from "@/pages/EccentricitySessionPage";
import { DiscriminationSessionPage } from "@/pages/DiscriminationSessionPage";
import { SensitivitySessionPage } from "@/pages/SensitivitySessionPage";
import { TiltingSessionPage } from "@/pages/TiltingSessionPage";
import { SessionsListPage } from "@/pages/SessionsListPage";
import { DiscrepancyReportsPage } from "@/pages/DiscrepancyReportsPage";
import { AuditTrailPage } from "@/pages/AuditTrailPage";
import { VerifyPage } from "@/pages/VerifyPage";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      {/* Public, login-free — deliberately OUTSIDE AuthGate/AppShell.
          Reachable by anyone with the certificate's QR code/URL, no
          Supabase session required (docs/architecture.md, ADR-0009). */}
      <Route path="/verify/:certNumber" element={<VerifyPage />} />

      <Route element={<AuthGate />}>
        <Route element={<AppShell />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/instruments" element={<InstrumentsListPage />} />
          <Route path="/instruments/new" element={<InstrumentRegisterPage />} />
          <Route path="/instruments/:id" element={<InstrumentDetailPage />} />
          {/* One page behind both "My sessions" (technician) and
              "Sessions (all)" (approver/admin) — see SessionsListPage.jsx.
              Placed before /sessions/:id; react-router ranks static
              segments above dynamic ones regardless of order, but this
              keeps the list-then-detail reading order explicit. */}
          <Route path="/sessions" element={<SessionsListPage />} />
          <Route path="/discrepancy-reports" element={<DiscrepancyReportsPage />} />
          <Route path="/audit-trail" element={<AuditTrailPage />} />
          <Route path="/sessions/:id" element={<SessionPage />} />
        </Route>

        {/* Focused test-entry mode (docs/architecture.md, Frontend): all
            seven test-entry screens render inside FocusedShell instead of
            AppShell — no sidebar, full viewport width for the form table.
            The only way back is each page's own FocusedBackLink to the
            session overview above, which IS inside AppShell. */}
        <Route element={<FocusedShell />}>
          <Route path="/sessions/:id/weighing" element={<WeighingSessionPage />} />
          <Route path="/sessions/:id/zero-tare" element={<ZeroTareSessionPage />} />
          <Route path="/sessions/:id/repeatability" element={<RepeatabilitySessionPage />} />
          <Route path="/sessions/:id/eccentricity" element={<EccentricitySessionPage />} />
          <Route path="/sessions/:id/discrimination" element={<DiscriminationSessionPage />} />
          <Route path="/sessions/:id/sensitivity" element={<SensitivitySessionPage />} />
          <Route path="/sessions/:id/tilting" element={<TiltingSessionPage />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
