import { Route, Routes } from "react-router-dom";
import { Layout } from "../components/Layout";
import { DashboardPage } from "../pages/DashboardPage";
import { ProjectDetailPage } from "../pages/ProjectDetailPage";
import { ProjectsPage } from "../pages/ProjectsPage";
import { ReconciliationPage } from "../pages/ReconciliationPage";
import { TrancheFormPage } from "../pages/TrancheFormPage";
import { AIAssistantPage } from "../pages/AiAssistantPage";
import { ImportsExportsPage } from "../pages/ImportsExportsPage";

export function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/projects" element={<ProjectsPage />} />
        <Route path="/projects/:projectId" element={<ProjectDetailPage />} />
        <Route path="/tranches/new" element={<TrancheFormPage />} />
        <Route path="/reconciliation" element={<ReconciliationPage />} />
        <Route path="/imports-exports" element={<ImportsExportsPage />} />
        <Route path="/ai" element={<AIAssistantPage />} />
      </Routes>
    </Layout>
  );
}
