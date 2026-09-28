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
import { VoltageVariationsSessionPage } from "@/pages/VoltageVariationsSessionPage";
import { AcMainsDipsSessionPage } from "@/pages/AcMainsDipsSessionPage";
import { ElectricalBurstsSessionPage } from "@/pages/ElectricalBurstsSessionPage";
import { ElectrostaticDischargesSessionPage } from "@/pages/ElectrostaticDischargesSessionPage";
import { SurgesSessionPage } from "@/pages/SurgesSessionPage";
import { RadiatedEmImmunitySessionPage } from "@/pages/RadiatedEmImmunitySessionPage";
import { ConductedRfImmunitySessionPage } from "@/pages/ConductedRfImmunitySessionPage";
import { RoadVehicleTransientsSessionPage } from "@/pages/RoadVehicleTransientsSessionPage";
import { DampHeatSessionPage } from "@/pages/DampHeatSessionPage";
import { EnduranceSessionPage } from "@/pages/EnduranceSessionPage";
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
            The only way back is each page's own FocusedPageHeader (the
            merged back-link + title row) to the session overview above,
            which IS inside AppShell. */}
        <Route element={<FocusedShell />}>
          <Route path="/sessions/:id/weighing" element={<WeighingSessionPage />} />
          <Route path="/sessions/:id/zero-tare" element={<ZeroTareSessionPage />} />
          <Route path="/sessions/:id/repeatability" element={<RepeatabilitySessionPage />} />
          <Route path="/sessions/:id/eccentricity" element={<EccentricitySessionPage />} />
          <Route path="/sessions/:id/discrimination" element={<DiscriminationSessionPage />} />
          <Route path="/sessions/:id/sensitivity" element={<SensitivitySessionPage />} />
          <Route path="/sessions/:id/tilting" element={<TiltingSessionPage />} />
          {/* Clause 11 + clause 12.x — voltage variations is computed
              (reuses the Weighing engine); every clause-12.x test below is
              record-only (no engine — physical EMC equipment required,
              docs/architecture.md). feat/remaining-disturbance-forms
              completed 12.3/12.5/12.6/12.7, so all seven clause-12.x tests
              (12.1-12.7) are now live. */}
          <Route path="/sessions/:id/voltage-variations" element={<VoltageVariationsSessionPage />} />
          <Route path="/sessions/:id/ac-mains-dips" element={<AcMainsDipsSessionPage />} />
          <Route path="/sessions/:id/electrical-bursts" element={<ElectricalBurstsSessionPage />} />
          <Route path="/sessions/:id/electrostatic-discharges" element={<ElectrostaticDischargesSessionPage />} />
          <Route path="/sessions/:id/surges" element={<SurgesSessionPage />} />
          <Route path="/sessions/:id/radiated-em-immunity" element={<RadiatedEmImmunitySessionPage />} />
          <Route path="/sessions/:id/conducted-rf-immunity" element={<ConductedRfImmunitySessionPage />} />
          <Route path="/sessions/:id/road-vehicle-transients" element={<RoadVehicleTransientsSessionPage />} />
          {/* Clause 13 (Damp heat) + clause 15 (Endurance) —
              feat/damp-heat-endurance. Both reuse WeighingFormTable
              verbatim, one run at a time, via the runs/conditions
              infrastructure (feat/test-runs-conditions). */}
          <Route path="/sessions/:id/damp-heat" element={<DampHeatSessionPage />} />
          <Route path="/sessions/:id/endurance" element={<EnduranceSessionPage />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
