<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { Button, Badge } from "frappe-ui";

import { fetchProjects, fetchReconciliation, fetchTranches } from "../api/client";
import AppShell from "../components/AppShell.vue";
import StatTile from "../components/StatTile.vue";
import { authToken } from "../composables/useAuth";
import type { ProjectRow, ReconciliationIssue, TrancheRow } from "../types/domain";
import { labelize, money, toNumber } from "../utils/format";

const projects = ref<ProjectRow[]>([]);
const tranches = ref<TrancheRow[]>([]);
const issues = ref<ReconciliationIssue[]>([]);
const loading = ref(true);
const error = ref("");

const totals = computed(() => {
  const sanctioned = projects.value.reduce((sum, project) => sum + toNumber(project.summary.totalSanctionedAmount), 0);
  const disbursed = projects.value.reduce((sum, project) => sum + toNumber(project.summary.netDisbursedAmount), 0);
  const pending = projects.value.reduce((sum, project) => sum + toNumber(project.summary.pendingApprovedAmount), 0);
  return { sanctioned, disbursed, pending };
});

const pendingTranches = computed(() => tranches.value.filter((tranche) => !["disbursed", "utilized", "cancelled", "rejected"].includes(tranche.status)));
const severeIssues = computed(() => issues.value.filter((issue) => ["high", "critical"].includes(issue.severity)));

onMounted(load);

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const token = authToken();
    const [projectRows, trancheRows, reconciliationRows] = await Promise.all([fetchProjects(token), fetchTranches(token), fetchReconciliation(token)]);
    projects.value = projectRows;
    tranches.value = trancheRows;
    issues.value = reconciliationRows;
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Unable to load dashboard.";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <AppShell>
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold">Dashboard</h1>
        <p class="mt-1 text-sm text-muted">Project funding, tranche movement and reconciliation health.</p>
      </div>
      <Button label="Refresh" icon-left="refresh-cw" @click="load" />
    </div>

    <div v-if="error" class="mt-4 border border-danger/30 bg-red-50 px-3 py-2 text-sm text-danger">{{ error }}</div>

    <div class="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
      <StatTile label="Projects" :value="projects.length" />
      <StatTile label="Sanctioned" :value="money(totals.sanctioned)" />
      <StatTile label="Net disbursed" :value="money(totals.disbursed)" tone="success" />
      <StatTile label="Pending approved" :value="money(totals.pending)" tone="warning" />
      <StatTile label="Open issues" :value="issues.length" :tone="severeIssues.length ? 'danger' : 'default'" />
    </div>

    <div class="mt-6 grid gap-5 xl:grid-cols-[1.5fr_1fr]">
      <section class="border border-line bg-panel">
        <div class="border-b border-line px-4 py-3 text-sm font-semibold">Recent projects</div>
        <div class="overflow-x-auto">
          <table class="min-w-full text-left text-sm">
            <thead class="border-b border-line bg-gray-50 text-xs uppercase text-muted">
              <tr>
                <th class="px-4 py-2">Project</th>
                <th class="px-4 py-2">Department</th>
                <th class="px-4 py-2">Status</th>
                <th class="px-4 py-2 text-right">Balance</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="project in projects.slice(0, 8)" :key="project.id" class="border-b border-line">
                <td class="px-4 py-3">
                  <RouterLink :to="`/projects/${project.id}`" class="font-medium text-primary">{{ project.projectCode }}</RouterLink>
                  <div class="text-muted">{{ project.title }}</div>
                </td>
                <td class="px-4 py-3">{{ project.department || project.school || "-" }}</td>
                <td class="px-4 py-3"><Badge :label="labelize(project.status)" /></td>
                <td class="px-4 py-3 text-right">{{ money(project.summary.availableSanctionedBalance) }}</td>
              </tr>
              <tr v-if="!loading && projects.length === 0">
                <td colspan="4" class="px-4 py-8 text-center text-muted">No projects found</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="border border-line bg-panel">
        <div class="border-b border-line px-4 py-3 text-sm font-semibold">Attention queue</div>
        <div class="divide-y divide-line">
          <RouterLink v-for="tranche in pendingTranches.slice(0, 6)" :key="tranche.id" :to="`/projects/${tranche.projectId}/tranches`" class="block px-4 py-3 text-sm hover:bg-gray-50">
            <div class="flex items-center justify-between gap-3">
              <span class="font-medium">{{ tranche.projectCode || "Project" }} · Tranche {{ tranche.sequenceNumber }}</span>
              <Badge :label="tranche.statusLabel || labelize(tranche.status)" />
            </div>
            <div class="mt-1 text-muted">{{ money(tranche.approvedAmount) }}</div>
          </RouterLink>
          <RouterLink v-for="issue in severeIssues.slice(0, 3)" :key="`${issue.projectCode}-${issue.issueType}`" :to="`/projects/${issue.projectId}`" class="block px-4 py-3 text-sm hover:bg-gray-50">
            <div class="font-medium">{{ issue.projectCode }} · {{ labelize(issue.issueType) }}</div>
            <div class="mt-1 text-muted">{{ issue.description }}</div>
          </RouterLink>
          <div v-if="!loading && pendingTranches.length === 0 && severeIssues.length === 0" class="px-4 py-8 text-center text-sm text-muted">No pending action</div>
        </div>
      </section>
    </div>
  </AppShell>
</template>
