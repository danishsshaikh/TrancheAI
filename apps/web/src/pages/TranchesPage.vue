<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { Badge, Button, FormControl } from "frappe-ui";

import { fetchTranches } from "../api/client";
import AppShell from "../components/AppShell.vue";
import { authToken } from "../composables/useAuth";
import type { TrancheRow } from "../types/domain";
import { dateText, labelize, money } from "../utils/format";

const rows = ref<TrancheRow[]>([]);
const search = ref("");
const statusFilter = ref("");
const loading = ref(true);
const error = ref("");

const filtered = computed(() =>
  rows.value.filter((row) => {
    const haystack = `${row.projectCode ?? ""} ${row.projectTitle ?? ""} ${row.paymentReference ?? ""} ${row.status}`.toLowerCase();
    return (!search.value || haystack.includes(search.value.toLowerCase())) && (!statusFilter.value || row.status === statusFilter.value);
  })
);

onMounted(load);

async function load() {
  loading.value = true;
  error.value = "";
  try {
    rows.value = await fetchTranches(authToken());
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Unable to load tranches.";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <AppShell>
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold">Tranches</h1>
        <p class="mt-1 text-sm text-muted">Global tranche register with project context.</p>
      </div>
      <Button label="Refresh" icon-left="refresh-cw" @click="load" />
    </div>

    <div class="mt-5 grid gap-3 md:grid-cols-[1fr_220px]">
      <FormControl v-model="search" placeholder="Filter by project or payment reference" />
      <FormControl
        v-model="statusFilter"
        type="select"
        :options="[
          { label: 'All statuses', value: '' },
          { label: 'Draft', value: 'draft' },
          { label: 'Submitted', value: 'submitted' },
          { label: 'Approved', value: 'approved' },
          { label: 'Disbursed', value: 'disbursed' },
          { label: 'Utilized', value: 'utilized' },
        ]"
      />
    </div>

    <div v-if="error" class="mt-4 border border-danger/30 bg-red-50 px-3 py-2 text-sm text-danger">{{ error }}</div>

    <section class="mt-5 overflow-x-auto border border-line bg-panel">
      <table class="min-w-full text-left text-sm">
        <thead class="border-b border-line bg-gray-50 text-xs uppercase text-muted">
          <tr>
            <th class="px-4 py-2">Project</th>
            <th class="px-4 py-2">Tranche</th>
            <th class="px-4 py-2 text-right">Approved</th>
            <th class="px-4 py-2 text-right">Disbursed</th>
            <th class="px-4 py-2">Expected</th>
            <th class="px-4 py-2">Payment reference</th>
            <th class="px-4 py-2">Status</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in filtered" :key="row.id" class="border-b border-line hover:bg-gray-50">
            <td class="px-4 py-3">
              <RouterLink :to="`/projects/${row.projectId}/tranches`" class="font-medium text-primary">{{ row.projectCode || "Project" }}</RouterLink>
              <div class="max-w-sm truncate text-muted">{{ row.projectTitle || "-" }}</div>
            </td>
            <td class="px-4 py-3">Tranche {{ row.sequenceNumber }}<div class="text-muted">{{ row.transactionTypeLabel || labelize(row.transactionType) }}</div></td>
            <td class="px-4 py-3 text-right">{{ money(row.approvedAmount) }}</td>
            <td class="px-4 py-3 text-right">{{ money(row.disbursedAmount) }}</td>
            <td class="px-4 py-3">{{ dateText(row.expectedDisbursementDate) }}</td>
            <td class="px-4 py-3">{{ row.paymentReference || "-" }}</td>
            <td class="px-4 py-3"><Badge :label="row.statusLabel || labelize(row.status)" /></td>
          </tr>
          <tr v-if="!loading && filtered.length === 0">
            <td colspan="7" class="px-4 py-10 text-center text-muted">No tranches found</td>
          </tr>
        </tbody>
      </table>
    </section>
  </AppShell>
</template>
