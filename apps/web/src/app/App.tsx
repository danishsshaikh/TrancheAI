import type { PropsWithChildren } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "./AuthContext";
import { Layout } from "../components/Layout";
import { AiAssistantPage } from "../pages/AiAssistantPage";
import { DashboardPage } from "../pages/DashboardPage";
import { ProjectDetailPage } from "../pages/ProjectDetailPage";
import { ProjectsPage } from "../pages/ProjectsPage";
import { ReconciliationPage } from "../pages/ReconciliationPage";
import { TrancheFormPage } from "../pages/TrancheFormPage";
import { ImportsExportsPage } from "../pages/ImportsExportsPage";
import { LoginPage } from "../pages/LoginPage";

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/*" element={<ProtectedApp />} />
    </Routes>
  );
}

function ProtectedApp() {
  return (
    <RequireAuth>
      <Layout>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/ai" element={<AiAssistantPage />} />
          <Route path="/projects" element={<ProjectsPage />} />
          <Route path="/projects/:projectId" element={<ProjectDetailPage />} />
          <Route path="/tranches/new" element={<TrancheFormPage />} />
          <Route path="/reconciliation" element={<ReconciliationPage />} />
          <Route path="/imports-exports" element={<ImportsExportsPage />} />
        </Routes>
      </Layout>
    </RequireAuth>
  );
}

function RequireAuth({ children }: PropsWithChildren) {
  const auth = useAuth();
  const location = useLocation();
  if (!auth.token) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  return children;
}
