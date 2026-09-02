<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { Badge, Button, Dialog, FormControl } from "frappe-ui";

import { createProject, fetchProjects } from "../api/client";
import AppShell from "../components/AppShell.vue";
import { authToken } from "../composables/useAuth";
import type { ProjectRow } from "../types/domain";
import { labelize, money } from "../utils/format";

const projects = ref<ProjectRow[]>([]);
const search = ref("");
const statusFilter = ref("");
const loading = ref(true);
const saving = ref(false);
const dialogOpen = ref(false);
const error = ref("");
const form = reactive({
  project_code: "",
  title: "",
  short_title: "",
  institution: "MIT Art, Design and Technology University",
  school: "",
  department: "",
  academic_year: "2026-27",
  cohort: "",
  category: "",
  domain: "",
  project_status: "active",
  funding_status: "not_sanctioned",
  expected_completion_date: "",
  remarks: "",
  principal_investigator: "",
});

const filteredProjects = computed(() =>
  projects.value.filter((project) => {
    const haystack = `${project.projectCode} ${project.title} ${project.department ?? ""} ${project.school ?? ""}`.toLowerCase();
    return (!search.value || haystack.includes(search.value.toLowerCase())) && (!statusFilter.value || project.status === statusFilter.value);
  })
);

onMounted(load);

async function load() {
  loading.value = true;
  error.value = "";
  try {
    projects.value = await fetchProjects(authToken());
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Unable to load projects.";
  } finally {
    loading.value = false;
  }
}

async function saveProject() {
  saving.value = true;
  error.value = "";
  try {
    await createProject(authToken(), {
      ...form,
      expected_completion_date: form.expected_completion_date || null,
      participants: form.principal_investigator
        ? [{ role: "principal_investigator", full_name: form.principal_investigator, department: form.department || null, is_primary: true }]
        : [],
    });
    dialogOpen.value = false;
    await load();
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Unable to create project.";
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <AppShell>
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold">Projects</h1>
        <p class="mt-1 text-sm text-muted">Canonical CRiEYA project records with sanctions, revisions and tranches attached.</p>
      </div>
      <Button variant="solid" label="New project" icon-left="plus" @click="dialogOpen = true" />
    </div>

    <div class="mt-5 grid gap-3 md:grid-cols-[1fr_220px]">
      <FormControl v-model="search" placeholder="Filter projects" />
      <FormControl
        v-model="statusFilter"
        type="select"
        :options="[
          { label: 'All statuses', value: '' },
          { label: 'Active', value: 'active' },
          { label: 'Draft', value: 'draft' },
          { label: 'Completed', value: 'completed' },
          { label: 'Closed', value: 'closed' },
        ]"
      />
    </div>

    <div v-if="error" class="mt-4 border border-danger/30 bg-red-50 px-3 py-2 text-sm text-danger">{{ error }}</div>

    <section class="mt-5 overflow-x-auto border border-line bg-panel">
      <table class="min-w-full text-left text-sm">
        <thead class="border-b border-line bg-gray-50 text-xs uppercase text-muted">
          <tr>
            <th class="px-4 py-2">Project</th>
            <th class="px-4 py-2">School</th>
            <th class="px-4 py-2">Status</th>
            <th class="px-4 py-2 text-right">Sanctioned</th>
            <th class="px-4 py-2 text-right">Available</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="project in filteredProjects" :key="project.id" class="border-b border-line hover:bg-gray-50">
            <td class="px-4 py-3">
              <RouterLink :to="`/projects/${project.id}`" class="font-medium text-primary">{{ project.projectCode }}</RouterLink>
              <div class="max-w-xl truncate text-muted">{{ project.title }}</div>
            </td>
            <td class="px-4 py-3">
              <div>{{ project.school || "-" }}</div>
              <div class="text-muted">{{ project.department || "" }}</div>
            </td>
            <td class="px-4 py-3">
              <Badge :label="labelize(project.status)" />
            </td>
            <td class="px-4 py-3 text-right">{{ money(project.summary.totalSanctionedAmount) }}</td>
            <td class="px-4 py-3 text-right">{{ money(project.summary.availableSanctionedBalance) }}</td>
          </tr>
          <tr v-if="!loading && filteredProjects.length === 0">
            <td colspan="5" class="px-4 py-10 text-center text-muted">No matching projects</td>
          </tr>
        </tbody>
      </table>
    </section>

    <Dialog v-model="dialogOpen" :options="{ title: 'New project', size: '2xl' }">
      <template #body-content>
        <div class="grid gap-3 md:grid-cols-2">
          <FormControl v-model="form.project_code" label="Project code" required />
          <FormControl v-model="form.academic_year" label="Academic year" />
          <FormControl v-model="form.title" label="Title" required class="md:col-span-2" />
          <FormControl v-model="form.short_title" label="Short title" />
          <FormControl v-model="form.principal_investigator" label="Principal investigator" />
          <FormControl v-model="form.school" label="School" />
          <FormControl v-model="form.department" label="Department" />
          <FormControl v-model="form.category" label="Category" />
          <FormControl v-model="form.domain" label="Domain" />
          <FormControl v-model="form.expected_completion_date" label="Expected completion date" type="date" />
          <FormControl v-model="form.remarks" label="Remarks" type="textarea" class="md:col-span-2" />
        </div>
      </template>
      <template #actions>
        <Button label="Cancel" @click="dialogOpen = false" />
        <Button variant="solid" label="Create project" icon-left="save" :loading="saving" @click="saveProject" />
      </template>
    </Dialog>
  </AppShell>
</template>
