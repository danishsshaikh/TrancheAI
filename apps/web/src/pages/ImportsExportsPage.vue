<script setup lang="ts">
import { computed, ref } from "vue";
import { Badge, Button, FormControl } from "frappe-ui";

import { commitImport, downloadFile, previewImport } from "../api/client";
import AppShell from "../components/AppShell.vue";
import StatTile from "../components/StatTile.vue";
import { authToken } from "../composables/useAuth";
import type { ImportBatch } from "../types/domain";
import { labelize } from "../utils/format";

const importType = ref("projects");
const selectedFile = ref<File | null>(null);
const batch = ref<ImportBatch | null>(null);
const loading = ref(false);
const error = ref("");

const rows = computed(() => batch.value?.rows ?? []);

async function preview() {
  if (!selectedFile.value) {
    error.value = "Choose a CSV file first.";
    return;
  }
  loading.value = true;
  error.value = "";
  try {
    batch.value = await previewImport(authToken(), importType.value, selectedFile.value);
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Unable to preview import.";
  } finally {
    loading.value = false;
  }
}

async function commit() {
  if (!batch.value) return;
  loading.value = true;
  error.value = "";
  try {
    batch.value = await commitImport(authToken(), batch.value.id);
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Unable to commit import.";
  } finally {
    loading.value = false;
  }
}

function chooseFile(event: Event) {
  selectedFile.value = (event.target as HTMLInputElement).files?.[0] ?? null;
}

function exportFile(path: string, filename: string) {
  return downloadFile(authToken(), path, filename);
}
</script>

<template>
  <AppShell>
    <div>
      <h1 class="text-2xl font-semibold">Imports / Exports</h1>
      <p class="mt-1 text-sm text-muted">Preview, validate and commit project funding data without bypassing workflow controls.</p>
    </div>

    <div v-if="error" class="mt-4 border border-danger/30 bg-red-50 px-3 py-2 text-sm text-danger">{{ error }}</div>

    <div class="mt-5 grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
      <section class="border border-line bg-panel p-4">
        <h2 class="text-base font-semibold">CSV import</h2>
        <div class="mt-4 grid gap-3 md:grid-cols-[220px_1fr_auto_auto]">
          <FormControl
            v-model="importType"
            label="Import type"
            type="select"
            :options="[
              { label: 'Projects', value: 'projects' },
              { label: 'Sanctions', value: 'funding_sanctions' },
              { label: 'Funding revisions', value: 'funding_revisions' },
              { label: 'Tranches', value: 'tranches' },
            ]"
          />
          <label class="block">
            <span class="mb-1 block text-sm text-muted">CSV file</span>
            <input type="file" accept=".csv,text/csv" class="block w-full border border-line px-3 py-2 text-sm" @change="chooseFile" />
          </label>
          <Button label="Download template" icon-left="download" @click="exportFile(`/api/v1/imports/templates/${importType}.csv`, `${importType}-template.csv`)" />
          <Button variant="solid" label="Preview" icon-left="eye" :loading="loading" @click="preview" />
        </div>

        <div v-if="batch" class="mt-5 grid gap-3 md:grid-cols-5">
          <StatTile label="Rows" :value="batch.rowsDetected" />
          <StatTile label="Valid" :value="batch.validRows" tone="success" />
          <StatTile label="Invalid" :value="batch.invalidRows" :tone="batch.invalidRows ? 'danger' : 'default'" />
          <StatTile label="Duplicates" :value="batch.duplicateRows" />
          <StatTile label="Updates" :value="batch.proposedUpdates" />
        </div>

        <div v-if="batch" class="mt-5 flex justify-end">
          <Button variant="solid" label="Commit valid rows" icon-left="check" :disabled="batch.invalidRows > 0 || batch.status === 'committed'" :loading="loading" @click="commit" />
        </div>
      </section>

      <section class="border border-line bg-panel p-4">
        <h2 class="text-base font-semibold">Exports</h2>
        <div class="mt-4 grid gap-2">
          <Button label="Project master CSV" icon-left="download" @click="exportFile('/api/v1/exports/project-master.csv', 'project-master.csv')" />
          <Button label="Tranche register CSV" icon-left="download" @click="exportFile('/api/v1/exports/tranche-register.csv', 'tranche-register.csv')" />
          <Button label="Project master XLSX" icon-left="download" @click="exportFile('/api/v1/exports/project-master.xlsx', 'project-master.xlsx')" />
          <Button label="Tranche register XLSX" icon-left="download" @click="exportFile('/api/v1/exports/tranche-register.xlsx', 'tranche-register.xlsx')" />
        </div>
      </section>
    </div>

    <section v-if="batch" class="mt-5 overflow-x-auto border border-line bg-panel">
      <table class="min-w-full text-left text-sm">
        <thead class="border-b border-line bg-gray-50 text-xs uppercase text-muted">
          <tr>
            <th class="px-4 py-2">Row</th>
            <th class="px-4 py-2">Action</th>
            <th class="px-4 py-2">Status</th>
            <th class="px-4 py-2">Errors</th>
            <th class="px-4 py-2">Warnings</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.id" class="border-b border-line">
            <td class="px-4 py-3">{{ row.rowNumber }}</td>
            <td class="px-4 py-3">{{ labelize(row.proposedAction) }}</td>
            <td class="px-4 py-3"><Badge :label="labelize(row.status)" /></td>
            <td class="px-4 py-3 text-danger">{{ row.errors.join(', ') || '-' }}</td>
            <td class="px-4 py-3 text-muted">{{ row.warnings.join(', ') || '-' }}</td>
          </tr>
        </tbody>
      </table>
    </section>
  </AppShell>
</template>
