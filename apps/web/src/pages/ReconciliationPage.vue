<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { Badge, Button, FormControl } from "frappe-ui";

import { fetchReconciliation } from "../api/client";
import AppShell from "../components/AppShell.vue";
import StatTile from "../components/StatTile.vue";
import { authToken } from "../composables/useAuth";
import type { ReconciliationIssue } from "../types/domain";
import { labelize, moneyOrNotApplicable } from "../utils/format";

const issues = ref<ReconciliationIssue[]>([]);
const search = ref("");
const severity = ref("");
const loading = ref(true);
const error = ref("");

const filtered = computed(() =>
  issues.value.filter((issue) => {
    const haystack = `${issue.projectCode} ${issue.projectTitle ?? ""} ${issue.issueType} ${issue.description}`.toLowerCase();
    return (!search.value || haystack.includes(search.value.toLowerCase())) && (!severity.value || issue.severity === severity.value);
  })
);

const critical = computed(() => issues.value.filter((issue) => issue.severity === "critical").length);
const high = computed(() => issues.value.filter((issue) => issue.severity === "high").length);

onMounted(load);

async function load() {
  loading.value = true;
  error.value = "";
  try {
    issues.value = await fetchReconciliation(authToken());
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Unable to load reconciliation.";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <AppShell>
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold">Reconciliation</h1>
        <p class="mt-1 text-sm text-muted">Deterministic exceptions from sanctioned, approved, disbursed, refunded and utilized amounts.</p>
      </div>
      <Button label="Refresh" icon-left="refresh-cw" @click="load" />
    </div>

    <div class="mt-5 grid gap-3 md:grid-cols-3">
      <StatTile label="Issues" :value="issues.length" />
      <StatTile label="Critical" :value="critical" :tone="critical ? 'danger' : 'default'" />
      <StatTile label="High severity" :value="high" :tone="high ? 'warning' : 'default'" />
    </div>

    <div class="mt-5 grid gap-3 md:grid-cols-[1fr_220px]">
      <FormControl v-model="search" placeholder="Filter by project or issue" />
      <FormControl
        v-model="severity"
        type="select"
        :options="[
          { label: 'All severities', value: '' },
          { label: 'Critical', value: 'critical' },
          { label: 'High', value: 'high' },
          { label: 'Medium', value: 'medium' },
          { label: 'Low', value: 'low' },
        ]"
      />
    </div>

    <div v-if="error" class="mt-4 border border-danger/30 bg-red-50 px-3 py-2 text-sm text-danger">{{ error }}</div>

    <section class="mt-5 border border-line bg-panel">
      <div class="overflow-x-auto">
        <table class="min-w-full text-left text-sm">
          <thead class="border-b border-line bg-gray-50 text-xs uppercase text-muted">
            <tr>
              <th class="px-4 py-2">Project</th>
              <th class="px-4 py-2">Issue</th>
              <th class="px-4 py-2">Severity</th>
              <th class="px-4 py-2 text-right">Financial impact</th>
              <th class="px-4 py-2">Suggested action</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="issue in filtered" :key="`${issue.projectCode}-${issue.issueType}`" class="border-b border-line">
              <td class="px-4 py-3">
                <RouterLink :to="`/projects/${issue.projectId}`" class="font-medium text-primary">{{ issue.projectCode }}</RouterLink>
                <div class="max-w-sm truncate text-muted">{{ issue.projectTitle || "-" }}</div>
              </td>
              <td class="px-4 py-3">
                <div class="font-medium">{{ labelize(issue.issueType) }}</div>
                <div class="text-muted">{{ issue.description }}</div>
              </td>
              <td class="px-4 py-3"><Badge :label="labelize(issue.severity)" /></td>
              <td class="px-4 py-3 text-right">{{ moneyOrNotApplicable(issue.financialImpact) }}</td>
              <td class="px-4 py-3">{{ issue.suggestedAction || "-" }}</td>
            </tr>
            <tr v-if="!loading && filtered.length === 0">
              <td colspan="5" class="px-4 py-10 text-center text-muted">Balanced</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </AppShell>
</template>
