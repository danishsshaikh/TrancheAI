<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Badge, Button, Dialog, FormControl } from "frappe-ui";

import {
  approveRevision,
  approveSanction,
  createRevision,
  createSanction,
  createTranche,
  fetchProject,
  fetchProjectAudit,
  submitRevision,
  submitSanction,
  trancheAction,
  updateProject,
} from "../api/client";
import AppShell from "../components/AppShell.vue";
import StatTile from "../components/StatTile.vue";
import { authToken } from "../composables/useAuth";
import type { AuditEvent, Participant, ProjectDetail, TrancheRow } from "../types/domain";
import { dateText, labelize, money, moneyOrNotApplicable, safeText } from "../utils/format";

const route = useRoute();
const router = useRouter();
const project = ref<ProjectDetail | null>(null);
const audit = ref<AuditEvent[]>([]);
const loading = ref(true);
const saving = ref(false);
const error = ref("");
const activeTab = ref(String(route.params.tab || "overview"));

const projectDialog = ref(false);
const sanctionDialog = ref(false);
const revisionDialog = ref(false);
const trancheDialog = ref(false);
const actionDialog = ref(false);
const selectedTranche = ref<TrancheRow | null>(null);
const selectedAction = ref("");

const projectForm = reactive<Record<string, string>>({});
const sanctionForm = reactive({ sanction_reference: "", amount: "", sanction_date: "", funding_source: "", financial_year: "", remarks: "" });
const revisionForm = reactive({ revision_number: "1", revision_type: "increase", amount: "", revision_date: "", approval_reference: "", reason: "", remarks: "" });
const trancheForm = reactive({
  sequence_number: "1",
  transaction_type: "advance",
  requested_amount: "",
  approved_amount: "",
  request_date: "",
  approval_date: "",
  expected_disbursement_date: "",
  payment_mode: "",
  payment_reference: "",
  purchase_order_number: "",
  bill_status: "",
  utilization_certificate_status: "",
  remarks: "",
});
const actionForm = reactive({ amount: "", payment_reference: "", payment_date: "", payment_mode: "", reason: "" });

const tabs = [
  "overview",
  "information",
  "participants",
  "sanction",
  "revisions",
  "tranches",
  "payments",
  "reconciliation",
  "activity",
];

watch(
  () => route.params.tab,
  (tab) => {
    activeTab.value = String(tab || "overview");
  }
);

onMounted(load);

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const id = String(route.params.id);
    const [projectPayload, auditRows] = await Promise.all([fetchProject(authToken(), id), fetchProjectAudit(authToken(), id).catch(() => [])]);
    project.value = projectPayload;
    audit.value = auditRows;
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Unable to load project.";
  } finally {
    loading.value = false;
  }
}

function openProjectDialog() {
  const p = project.value;
  if (!p) return;
  Object.assign(projectForm, {
    title: p.title,
    short_title: p.shortTitle ?? "",
    description: p.description ?? "",
    institution: p.institution ?? "",
    school: p.school ?? "",
    department: p.department ?? "",
    academic_year: p.academicYear ?? "",
    cohort: p.cohort ?? "",
    category: p.category ?? "",
    domain: p.domain ?? "",
    technology_readiness_level: p.technologyReadinessLevel ?? "",
    prototype_status: p.prototypeStatus ?? "",
    publication_status: p.publicationStatus ?? "",
    patent_status: p.patentStatus ?? "",
    startup_status: p.startupStatus ?? "",
    project_status: p.projectStatus || p.status,
    funding_status: p.fundingStatus,
    start_date: p.startDate ?? "",
    expected_completion_date: p.expectedCompletionDate ?? "",
    actual_completion_date: p.actualCompletionDate ?? "",
    closure_notes: p.closureNotes ?? "",
    remarks: p.remarks ?? "",
    participants: serializeParticipants(p.participants ?? []),
  });
  projectDialog.value = true;
}

async function saveProject() {
  if (!project.value) return;
  saving.value = true;
  try {
    const payload = {
      ...projectForm,
      start_date: projectForm.start_date || null,
      expected_completion_date: projectForm.expected_completion_date || null,
      actual_completion_date: projectForm.actual_completion_date || null,
      participants: parseParticipants(projectForm.participants || ""),
      version: project.value.version,
    };
    await updateProject(authToken(), project.value.id, payload);
    projectDialog.value = false;
    await load();
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Unable to update project.";
  } finally {
    saving.value = false;
  }
}

async function saveSanction() {
  if (!project.value) return;
  saving.value = true;
  try {
    await createSanction(authToken(), project.value.id, normalizePayload(sanctionForm));
    sanctionDialog.value = false;
    await load();
  } finally {
    saving.value = false;
  }
}

async function saveRevision() {
  if (!project.value) return;
  saving.value = true;
  try {
    await createRevision(authToken(), project.value.id, { ...normalizePayload(revisionForm), revision_number: Number(revisionForm.revision_number) });
    revisionDialog.value = false;
    await load();
  } finally {
    saving.value = false;
  }
}

async function saveTranche() {
  if (!project.value) return;
  saving.value = true;
  try {
    await createTranche(authToken(), project.value.id, { ...normalizePayload(trancheForm), sequence_number: Number(trancheForm.sequence_number) });
    trancheDialog.value = false;
    await load();
  } finally {
    saving.value = false;
  }
}

async function sanctionWorkflow(row: Record<string, unknown>, action: "submit" | "approve") {
  const id = String(row.id);
  if (action === "submit") await submitSanction(authToken(), id);
  if (action === "approve") await approveSanction(authToken(), id);
  await load();
}

async function revisionWorkflow(row: Record<string, unknown>, action: "submit" | "approve") {
  const id = String(row.id);
  if (action === "submit") await submitRevision(authToken(), id);
  if (action === "approve") await approveRevision(authToken(), id);
  await load();
}

function openTrancheAction(tranche: TrancheRow, action: string) {
  selectedTranche.value = tranche;
  selectedAction.value = action;
  Object.assign(actionForm, { amount: tranche.approvedAmount || "", payment_reference: tranche.paymentReference || "", payment_date: "", payment_mode: tranche.paymentMode || "", reason: "" });
  actionDialog.value = true;
}

async function runTrancheAction() {
  if (!selectedTranche.value) return;
  saving.value = true;
  const action = selectedAction.value;
  const payload =
    action === "disburse"
      ? { amount: actionForm.amount, payment_reference: actionForm.payment_reference, payment_date: actionForm.payment_date, payment_mode: actionForm.payment_mode || null }
      : action === "record-refund" || action === "record-utilization"
        ? { amount: actionForm.amount }
        : action === "reject" || action === "cancel"
          ? { reason: actionForm.reason || null }
          : undefined;
  try {
    await trancheAction(authToken(), selectedTranche.value.id, action, payload);
    actionDialog.value = false;
    await load();
  } finally {
    saving.value = false;
  }
}

function normalizePayload(source: Record<string, string>) {
  return Object.fromEntries(Object.entries(source).map(([key, value]) => [key, value === "" ? null : value]));
}

function field(row: Record<string, unknown>, key: string, fallback = "-") {
  return safeText(row[key], fallback);
}

function availableActions(tranche: TrancheRow) {
  if (tranche.status === "draft") return ["submit", "cancel"];
  if (["submitted", "under_review"].includes(tranche.status)) return ["approve", "reject"];
  if (["approved", "scheduled", "partially_disbursed"].includes(tranche.status)) return ["disburse", "cancel"];
  if (["disbursed", "partially_utilized"].includes(tranche.status)) return ["record-refund", "record-utilization"];
  return [];
}

function serializeParticipants(participants: Participant[]) {
  return participants.map((item) => `${item.fullName} | ${item.role} | ${item.email ?? ""} | ${item.department ?? ""}`).join("\n");
}

function parseParticipants(value: string): Participant[] {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line, index) => {
      const [fullName, role = "participant", email = "", department = ""] = line.split("|").map((part) => part.trim());
      return { fullName, role, email: email || null, department: department || null, isPrimary: index === 0 };
    });
}

const projectIssues = computed(() => {
  const status = project.value?.summary.reconciliationStatus;
  if (!status || status === "balanced") return [];
  return [{ issueType: status, description: "Project financials require review against sanctioned, disbursed, refunded and utilized amounts.", financialImpact: project.value?.summary.pendingApprovedAmount }];
});
</script>

<template>
  <AppShell>
    <div v-if="project" class="space-y-5">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div class="flex flex-wrap items-center gap-2">
            <h1 class="text-2xl font-semibold">{{ project.projectCode }}</h1>
            <Badge :label="labelize(project.status)" />
            <Badge :label="labelize(project.fundingStatus)" />
          </div>
          <p class="mt-1 max-w-4xl text-sm text-muted">{{ project.title }}</p>
        </div>
        <div class="flex flex-wrap gap-2">
          <Button label="Ask AI" icon-left="sparkles" @click="router.push(`/ai?projectId=${project.id}&projectCode=${project.projectCode}`)" />
          <Button label="Edit" icon-left="edit-3" @click="openProjectDialog" />
        </div>
      </div>

      <div v-if="error" class="border border-danger/30 bg-red-50 px-3 py-2 text-sm text-danger">{{ error }}</div>

      <div class="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        <StatTile label="Sanctioned" :value="money(project.summary.totalSanctionedAmount)" />
        <StatTile label="Net disbursed" :value="money(project.summary.netDisbursedAmount)" tone="success" />
        <StatTile label="Utilized" :value="money(project.summary.totalUtilizedAmount)" />
        <StatTile label="Available balance" :value="money(project.summary.availableSanctionedBalance)" />
        <StatTile label="Pending approved" :value="money(project.summary.pendingApprovedAmount)" tone="warning" />
      </div>

      <nav class="flex gap-1 overflow-x-auto border-b border-line">
        <RouterLink
          v-for="tab in tabs"
          :key="tab"
          :to="tab === 'overview' ? `/projects/${project.id}` : `/projects/${project.id}/${tab}`"
          class="whitespace-nowrap px-3 py-2 text-sm text-muted"
          :class="{ 'border-b-2 border-primary font-medium text-foreground': activeTab === tab }"
        >
          {{ labelize(tab) }}
        </RouterLink>
      </nav>

      <section v-if="activeTab === 'overview'" class="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
        <div class="border border-line bg-panel p-4">
          <h2 class="text-base font-semibold">Project summary</h2>
          <dl class="mt-4 grid gap-3 sm:grid-cols-2">
            <div><dt class="text-xs text-muted">School</dt><dd>{{ project.school || "-" }}</dd></div>
            <div><dt class="text-xs text-muted">Department</dt><dd>{{ project.department || "-" }}</dd></div>
            <div><dt class="text-xs text-muted">Domain</dt><dd>{{ project.domain || "-" }}</dd></div>
            <div><dt class="text-xs text-muted">Expected completion</dt><dd>{{ dateText(project.expectedCompletionDate) }}</dd></div>
          </dl>
          <p class="mt-4 text-sm leading-6 text-muted">{{ project.description || project.remarks || "No description recorded." }}</p>
        </div>
        <div class="border border-line bg-panel p-4">
          <h2 class="text-base font-semibold">Workflow position</h2>
          <div class="mt-4 space-y-3 text-sm">
            <div class="flex justify-between"><span>Original sanction</span><span>{{ project.sanctions.length ? "Recorded" : "Pending" }}</span></div>
            <div class="flex justify-between"><span>Funding revisions</span><span>{{ project.fundingRevisions.length }}</span></div>
            <div class="flex justify-between"><span>Tranches</span><span>{{ project.tranches.length }}</span></div>
            <div class="flex justify-between"><span>Reconciliation</span><span>{{ labelize(project.summary.reconciliationStatus) }}</span></div>
          </div>
        </div>
      </section>

      <section v-if="activeTab === 'information'" class="border border-line bg-panel p-4">
        <dl class="grid gap-4 md:grid-cols-3">
          <div v-for="item in [
            ['Institution', project.institution],
            ['Academic year', project.academicYear],
            ['Cohort', project.cohort],
            ['Category', project.category],
            ['Technology readiness', project.technologyReadinessLevel],
            ['Prototype', project.prototypeStatus],
            ['Publication', project.publicationStatus],
            ['Patent', project.patentStatus],
            ['Startup', project.startupStatus],
            ['Start date', dateText(project.startDate)],
            ['Actual completion', dateText(project.actualCompletionDate)],
            ['Closure notes', project.closureNotes],
          ]" :key="item[0]">
            <dt class="text-xs text-muted">{{ item[0] }}</dt>
            <dd class="mt-1 text-sm">{{ item[1] || "-" }}</dd>
          </div>
        </dl>
      </section>

      <section v-if="activeTab === 'participants'" class="border border-line bg-panel">
        <div class="border-b border-line px-4 py-3 text-sm font-semibold">Participants</div>
        <div class="divide-y divide-line">
          <div v-for="person in project.participants" :key="person.id || person.fullName" class="grid gap-2 px-4 py-3 text-sm md:grid-cols-[1fr_180px_1fr]">
            <div><span class="font-medium">{{ person.fullName }}</span><span v-if="person.isPrimary" class="ml-2 text-xs text-primary">Primary</span></div>
            <div>{{ person.roleLabel || labelize(person.role) }}</div>
            <div class="text-muted">{{ person.email || person.department || "-" }}</div>
          </div>
          <div v-if="!project.participants?.length" class="px-4 py-8 text-center text-sm text-muted">No participants recorded</div>
        </div>
      </section>

      <section v-if="activeTab === 'sanction'" class="border border-line bg-panel">
        <div class="flex items-center justify-between border-b border-line px-4 py-3">
          <h2 class="text-sm font-semibold">Original sanction</h2>
          <Button label="Add sanction" icon-left="plus" @click="sanctionDialog = true" />
        </div>
        <div class="overflow-x-auto">
          <table class="min-w-full text-left text-sm">
            <tbody>
              <tr v-for="row in project.sanctions" :key="String(row.id)" class="border-b border-line">
                <td class="px-4 py-3 font-medium">{{ field(row, 'sanctionReference') }}</td>
                <td class="px-4 py-3">{{ dateText(row.sanctionDate) }}</td>
                <td class="px-4 py-3 text-right">{{ money(row.amount) }}</td>
                <td class="px-4 py-3"><Badge :label="field(row, 'statusLabel', labelize(row.status))" /></td>
                <td class="px-4 py-3 text-right">
                  <Button v-if="row.status === 'draft'" label="Submit" icon-left="send" @click="sanctionWorkflow(row, 'submit')" />
                  <Button v-if="row.status === 'submitted'" label="Approve" icon-left="check" @click="sanctionWorkflow(row, 'approve')" />
                </td>
              </tr>
              <tr v-if="project.sanctions.length === 0"><td colspan="5" class="px-4 py-8 text-center text-muted">No sanction recorded</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <section v-if="activeTab === 'revisions'" class="border border-line bg-panel">
        <div class="flex items-center justify-between border-b border-line px-4 py-3">
          <h2 class="text-sm font-semibold">Funding revisions</h2>
          <Button label="Add revision" icon-left="plus" @click="revisionDialog = true" />
        </div>
        <div class="overflow-x-auto">
          <table class="min-w-full text-left text-sm">
            <tbody>
              <tr v-for="row in project.fundingRevisions" :key="String(row.id)" class="border-b border-line">
                <td class="px-4 py-3">Revision {{ field(row, 'revisionNumber') }}</td>
                <td class="px-4 py-3">{{ field(row, 'revisionTypeLabel') }}</td>
                <td class="px-4 py-3 text-right">{{ money(row.amount) }}</td>
                <td class="px-4 py-3"><Badge :label="field(row, 'statusLabel')" /></td>
                <td class="px-4 py-3 text-right">
                  <Button v-if="row.status === 'draft'" label="Submit" icon-left="send" @click="revisionWorkflow(row, 'submit')" />
                  <Button v-if="row.status === 'submitted'" label="Approve" icon-left="check" @click="revisionWorkflow(row, 'approve')" />
                </td>
              </tr>
              <tr v-if="project.fundingRevisions.length === 0"><td colspan="5" class="px-4 py-8 text-center text-muted">No revisions recorded</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <section v-if="activeTab === 'tranches' || activeTab === 'payments'" class="border border-line bg-panel">
        <div class="flex items-center justify-between border-b border-line px-4 py-3">
          <h2 class="text-sm font-semibold">{{ activeTab === 'payments' ? 'Payments' : 'Tranches' }}</h2>
          <Button label="Add tranche" icon-left="plus" @click="trancheDialog = true" />
        </div>
        <div class="overflow-x-auto">
          <table class="min-w-full text-left text-sm">
            <thead class="border-b border-line bg-gray-50 text-xs uppercase text-muted">
              <tr>
                <th class="px-4 py-2">Tranche</th>
                <th class="px-4 py-2">Type</th>
                <th class="px-4 py-2 text-right">Approved</th>
                <th class="px-4 py-2 text-right">Disbursed</th>
                <th class="px-4 py-2">Reference</th>
                <th class="px-4 py-2">Status</th>
                <th class="px-4 py-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in project.tranches" :key="row.id" class="border-b border-line">
                <td class="px-4 py-3">Tranche {{ row.sequenceNumber }}</td>
                <td class="px-4 py-3">{{ row.transactionTypeLabel || labelize(row.transactionType) }}</td>
                <td class="px-4 py-3 text-right">{{ money(row.approvedAmount) }}</td>
                <td class="px-4 py-3 text-right">{{ money(row.disbursedAmount) }}</td>
                <td class="px-4 py-3">{{ row.paymentReference || "-" }}</td>
                <td class="px-4 py-3"><Badge :label="row.statusLabel || labelize(row.status)" /></td>
                <td class="px-4 py-3">
                  <div class="flex justify-end gap-1">
                    <Button v-for="action in availableActions(row)" :key="action" :label="labelize(action)" @click="openTrancheAction(row, action)" />
                  </div>
                </td>
              </tr>
              <tr v-if="project.tranches.length === 0"><td colspan="7" class="px-4 py-8 text-center text-muted">No tranches recorded</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <section v-if="activeTab === 'reconciliation'" class="border border-line bg-panel">
        <div class="border-b border-line px-4 py-3 text-sm font-semibold">Reconciliation</div>
        <div v-for="issue in projectIssues" :key="issue.issueType" class="grid gap-2 border-b border-line px-4 py-3 text-sm md:grid-cols-[180px_1fr_160px]">
          <div class="font-medium">{{ labelize(issue.issueType) }}</div>
          <div class="text-muted">{{ issue.description }}</div>
          <div class="text-right">{{ moneyOrNotApplicable(issue.financialImpact) }}</div>
        </div>
        <div v-if="projectIssues.length === 0" class="px-4 py-8 text-center text-sm text-muted">Balanced</div>
      </section>

      <section v-if="activeTab === 'activity'" class="border border-line bg-panel">
        <div class="border-b border-line px-4 py-3 text-sm font-semibold">Audit history</div>
        <div class="divide-y divide-line">
          <div v-for="event in audit" :key="event.id" class="grid gap-2 px-4 py-3 text-sm md:grid-cols-[180px_1fr_160px]">
            <div class="font-medium">{{ labelize(event.action) }}</div>
            <div class="text-muted">{{ labelize(event.entityType) }} {{ event.reason || "" }}</div>
            <div class="text-muted">{{ dateText(event.timestamp) }}</div>
          </div>
          <div v-if="audit.length === 0" class="px-4 py-8 text-center text-sm text-muted">No audit events available</div>
        </div>
      </section>
    </div>

    <div v-else-if="loading" class="text-sm text-muted">Loading project...</div>
    <div v-else class="border border-danger/30 bg-red-50 px-3 py-2 text-sm text-danger">{{ error || "Project not found." }}</div>

    <Dialog v-model:open="projectDialog" title="Edit project" size="3xl">
      <div class="grid gap-3 md:grid-cols-2">
        <FormControl v-model="projectForm.title" label="Title" class="md:col-span-2" />
        <FormControl v-model="projectForm.short_title" label="Short title" />
        <FormControl v-model="projectForm.academic_year" label="Academic year" />
        <FormControl v-model="projectForm.institution" label="Institution" />
        <FormControl v-model="projectForm.school" label="School" />
        <FormControl v-model="projectForm.department" label="Department" />
        <FormControl v-model="projectForm.cohort" label="Cohort" />
        <FormControl v-model="projectForm.category" label="Category" />
        <FormControl v-model="projectForm.domain" label="Domain" />
        <FormControl v-model="projectForm.technology_readiness_level" label="Technology readiness" />
        <FormControl v-model="projectForm.prototype_status" label="Prototype status" />
        <FormControl v-model="projectForm.publication_status" label="Publication status" />
        <FormControl v-model="projectForm.patent_status" label="Patent status" />
        <FormControl v-model="projectForm.startup_status" label="Startup status" />
        <FormControl v-model="projectForm.project_status" label="Project status" />
        <FormControl v-model="projectForm.funding_status" label="Funding status" />
        <FormControl v-model="projectForm.expected_completion_date" label="Expected completion" type="date" />
        <FormControl v-model="projectForm.description" label="Description" type="textarea" class="md:col-span-2" />
        <FormControl v-model="projectForm.participants" label="Participants" type="textarea" class="md:col-span-2" />
      </div>
      <template #actions>
        <Button label="Cancel" @click="projectDialog = false" />
        <Button variant="solid" label="Save" icon-left="save" :loading="saving" @click="saveProject" />
      </template>
    </Dialog>

    <Dialog v-model:open="sanctionDialog" title="Original sanction" size="xl">
      <div class="grid gap-3 md:grid-cols-2">
        <FormControl v-model="sanctionForm.sanction_reference" label="Sanction reference" />
        <FormControl v-model="sanctionForm.amount" label="Amount" type="number" />
        <FormControl v-model="sanctionForm.sanction_date" label="Sanction date" type="date" />
        <FormControl v-model="sanctionForm.funding_source" label="Funding source" />
        <FormControl v-model="sanctionForm.financial_year" label="Financial year" />
        <FormControl v-model="sanctionForm.remarks" label="Remarks" type="textarea" />
      </div>
      <template #actions>
        <Button label="Cancel" @click="sanctionDialog = false" />
        <Button variant="solid" label="Save" icon-left="save" :loading="saving" @click="saveSanction" />
      </template>
    </Dialog>

    <Dialog v-model:open="revisionDialog" title="Funding revision" size="xl">
      <div class="grid gap-3 md:grid-cols-2">
        <FormControl v-model="revisionForm.revision_number" label="Revision number" type="number" />
        <FormControl v-model="revisionForm.revision_type" label="Revision type" />
        <FormControl v-model="revisionForm.amount" label="Amount" type="number" />
        <FormControl v-model="revisionForm.revision_date" label="Revision date" type="date" />
        <FormControl v-model="revisionForm.approval_reference" label="Approval reference" />
        <FormControl v-model="revisionForm.reason" label="Reason" type="textarea" />
      </div>
      <template #actions>
        <Button label="Cancel" @click="revisionDialog = false" />
        <Button variant="solid" label="Save" icon-left="save" :loading="saving" @click="saveRevision" />
      </template>
    </Dialog>

    <Dialog v-model:open="trancheDialog" title="Tranche" size="2xl">
      <div class="grid gap-3 md:grid-cols-2">
        <FormControl v-model="trancheForm.sequence_number" label="Sequence number" type="number" />
        <FormControl v-model="trancheForm.transaction_type" label="Transaction type" />
        <FormControl v-model="trancheForm.requested_amount" label="Requested amount" type="number" />
        <FormControl v-model="trancheForm.approved_amount" label="Approved amount" type="number" />
        <FormControl v-model="trancheForm.request_date" label="Request date" type="date" />
        <FormControl v-model="trancheForm.approval_date" label="Approval date" type="date" />
        <FormControl v-model="trancheForm.expected_disbursement_date" label="Expected disbursement" type="date" />
        <FormControl v-model="trancheForm.purchase_order_number" label="Purchase order" />
        <FormControl v-model="trancheForm.payment_mode" label="Payment mode" />
        <FormControl v-model="trancheForm.payment_reference" label="Payment reference" />
        <FormControl v-model="trancheForm.bill_status" label="Bill status" />
        <FormControl v-model="trancheForm.utilization_certificate_status" label="Utilization certificate" />
      </div>
      <template #actions>
        <Button label="Cancel" @click="trancheDialog = false" />
        <Button variant="solid" label="Save" icon-left="save" :loading="saving" @click="saveTranche" />
      </template>
    </Dialog>

    <Dialog v-model:open="actionDialog" :title="labelize(selectedAction)" size="xl">
      <div class="grid gap-3 md:grid-cols-2">
        <FormControl v-if="selectedAction === 'disburse' || selectedAction === 'record-refund' || selectedAction === 'record-utilization'" v-model="actionForm.amount" label="Amount" type="number" />
        <FormControl v-if="selectedAction === 'disburse'" v-model="actionForm.payment_reference" label="Payment reference" />
        <FormControl v-if="selectedAction === 'disburse'" v-model="actionForm.payment_date" label="Payment date" type="date" />
        <FormControl v-if="selectedAction === 'disburse'" v-model="actionForm.payment_mode" label="Payment mode" />
        <FormControl v-if="selectedAction === 'reject' || selectedAction === 'cancel'" v-model="actionForm.reason" label="Reason" type="textarea" class="md:col-span-2" />
      </div>
      <template #actions>
        <Button label="Cancel" @click="actionDialog = false" />
        <Button variant="solid" :label="labelize(selectedAction)" icon-left="check" :loading="saving" @click="runTrancheAction" />
      </template>
    </Dialog>
  </AppShell>
</template>
