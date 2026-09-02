import { createRouter, createWebHistory } from "vue-router";

import { hasToken } from "./composables/useAuth";
import AiAssistantPage from "./pages/AiAssistantPage.vue";
import DashboardPage from "./pages/DashboardPage.vue";
import ImportsExportsPage from "./pages/ImportsExportsPage.vue";
import LoginPage from "./pages/LoginPage.vue";
import ProjectDetailPage from "./pages/ProjectDetailPage.vue";
import ProjectsPage from "./pages/ProjectsPage.vue";
import ReconciliationPage from "./pages/ReconciliationPage.vue";
import SettingsPage from "./pages/SettingsPage.vue";
import TranchesPage from "./pages/TranchesPage.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/dashboard" },
    { path: "/login", component: LoginPage, meta: { public: true } },
    { path: "/dashboard", component: DashboardPage },
    { path: "/projects", component: ProjectsPage },
    { path: "/projects/:id", component: ProjectDetailPage },
    { path: "/projects/:id/:tab", component: ProjectDetailPage },
    { path: "/tranches", component: TranchesPage },
    { path: "/reconciliation", component: ReconciliationPage },
    { path: "/imports-exports", component: ImportsExportsPage },
    { path: "/ai", component: AiAssistantPage },
    { path: "/settings", component: SettingsPage },
  ],
});

router.beforeEach((to) => {
  if (!to.meta.public && !hasToken()) return "/login";
  if (to.path === "/login" && hasToken()) return "/dashboard";
  return true;
});

export default router;
