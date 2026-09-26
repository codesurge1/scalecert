import { Navigate, Route, Routes } from "react-router-dom";
import { AuthGate } from "@/components/AuthGate";
import { AppShell } from "@/components/AppShell";
import { LoginPage } from "@/pages/LoginPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { InstrumentsListPage } from "@/pages/InstrumentsListPage";
import { InstrumentRegisterPage } from "@/pages/InstrumentRegisterPage";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route element={<AuthGate />}>
        <Route element={<AppShell />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/instruments" element={<InstrumentsListPage />} />
          <Route path="/instruments/new" element={<InstrumentRegisterPage />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
