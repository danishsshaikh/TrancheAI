<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { Badge, Button, FormControl } from "frappe-ui";

import { createUser, fetchSettings, fetchUsers, updateUser } from "../api/client";
import AppShell from "../components/AppShell.vue";
import { authToken, useAuth } from "../composables/useAuth";
import type { SettingsPayload, User } from "../types/domain";
import { labelize, safeText } from "../utils/format";

const auth = useAuth();
const settings = ref<SettingsPayload | null>(null);
const users = ref<User[]>([]);
const loading = ref(true);
const saving = ref(false);
const error = ref("");
const newUser = reactive({ email: "", full_name: "", password: "", role: "viewer" });

const isAdmin = computed(() => auth.state.user?.role === "administrator");

onMounted(load);

async function load() {
  loading.value = true;
  error.value = "";
  try {
    settings.value = await fetchSettings(authToken());
    if (isAdmin.value) users.value = await fetchUsers(authToken());
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Unable to load settings.";
  } finally {
    loading.value = false;
  }
}

async function addUser() {
  saving.value = true;
  error.value = "";
  try {
    await createUser(authToken(), newUser);
    Object.assign(newUser, { email: "", full_name: "", password: "", role: "viewer" });
    users.value = await fetchUsers(authToken());
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Unable to create user.";
  } finally {
    saving.value = false;
  }
}

async function changeUser(user: User, patch: Record<string, unknown>) {
  saving.value = true;
  try {
    await updateUser(authToken(), user.id, patch);
    users.value = await fetchUsers(authToken());
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <AppShell>
    <div>
      <h1 class="text-2xl font-semibold">Settings</h1>
      <p class="mt-1 text-sm text-muted">Profile, application information, AI provider visibility and user administration.</p>
    </div>

    <div v-if="error" class="mt-4 border border-danger/30 bg-red-50 px-3 py-2 text-sm text-danger">{{ error }}</div>

    <div class="mt-5 grid gap-5 xl:grid-cols-3">
      <section class="border border-line bg-panel p-4">
        <h2 class="text-base font-semibold">Profile</h2>
        <dl class="mt-4 space-y-3 text-sm">
          <div><dt class="text-xs text-muted">Name</dt><dd>{{ auth.state.user?.fullName }}</dd></div>
          <div><dt class="text-xs text-muted">Email</dt><dd>{{ auth.state.user?.email }}</dd></div>
          <div><dt class="text-xs text-muted">Role</dt><dd><Badge :label="auth.state.user?.roleLabel || labelize(auth.state.user?.role)" /></dd></div>
        </dl>
      </section>

      <section class="border border-line bg-panel p-4">
        <h2 class="text-base font-semibold">AI provider</h2>
        <dl class="mt-4 space-y-3 text-sm">
          <div><dt class="text-xs text-muted">Enabled</dt><dd>{{ settings?.ai.enabled ? "Yes" : "No" }}</dd></div>
          <div><dt class="text-xs text-muted">Base URL configured</dt><dd>{{ settings?.ai.baseUrlConfigured ? "Yes" : "No" }}</dd></div>
          <div><dt class="text-xs text-muted">Model</dt><dd>{{ safeText(settings?.ai.model) }}</dd></div>
          <div><dt class="text-xs text-muted">Timeout</dt><dd>{{ safeText(settings?.ai.timeoutSeconds) }} seconds</dd></div>
        </dl>
      </section>

      <section class="border border-line bg-panel p-4">
        <h2 class="text-base font-semibold">Application</h2>
        <dl class="mt-4 space-y-3 text-sm">
          <div><dt class="text-xs text-muted">Name</dt><dd>{{ settings?.application.name }}</dd></div>
          <div><dt class="text-xs text-muted">Version</dt><dd>{{ settings?.application.version }}</dd></div>
          <div><dt class="text-xs text-muted">License</dt><dd>{{ settings?.application.license }}</dd></div>
        </dl>
      </section>
    </div>

    <section v-if="isAdmin" class="mt-5 border border-line bg-panel">
      <div class="border-b border-line px-4 py-3 text-sm font-semibold">Users</div>
      <div class="grid gap-3 border-b border-line p-4 md:grid-cols-[1fr_1fr_1fr_180px_auto]">
        <FormControl v-model="newUser.email" label="Email" type="email" />
        <FormControl v-model="newUser.full_name" label="Full name" />
        <FormControl v-model="newUser.password" label="Password" type="password" />
        <FormControl v-model="newUser.role" label="Role" type="select" :options="settings?.roles || []" />
        <Button variant="solid" label="Add user" icon-left="plus" :loading="saving" @click="addUser" />
      </div>
      <div class="overflow-x-auto">
        <table class="min-w-full text-left text-sm">
          <thead class="border-b border-line bg-gray-50 text-xs uppercase text-muted">
            <tr>
              <th class="px-4 py-2">User</th>
              <th class="px-4 py-2">Role</th>
              <th class="px-4 py-2">Status</th>
              <th class="px-4 py-2 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in users" :key="user.id" class="border-b border-line">
              <td class="px-4 py-3">
                <div class="font-medium">{{ user.fullName }}</div>
                <div class="text-muted">{{ user.email }}</div>
              </td>
              <td class="px-4 py-3"><Badge :label="user.roleLabel || labelize(user.role)" /></td>
              <td class="px-4 py-3">{{ user.isActive ? "Active" : "Inactive" }}</td>
              <td class="px-4 py-3 text-right">
                <Button :label="user.isActive ? 'Deactivate' : 'Activate'" @click="changeUser(user, { is_active: !user.isActive })" />
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <div v-if="loading" class="mt-5 text-sm text-muted">Loading settings...</div>
  </AppShell>
</template>
