<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { Button, FormControl } from "frappe-ui";

import { useAuth } from "../composables/useAuth";

const router = useRouter();
const auth = useAuth();
const email = ref("");
const password = ref("");
const showPassword = ref(false);
const error = ref("");

async function submit() {
  error.value = "";
  try {
    await auth.login(email.value, password.value);
    await router.push("/dashboard");
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Unable to sign in.";
  }
}
</script>

<template>
  <main class="grid min-h-screen bg-background lg:grid-cols-[1fr_440px]">
    <section class="hidden border-r border-line px-10 py-12 lg:block">
      <div class="text-sm font-semibold uppercase text-primary">CRiEYA TrancheAI</div>
      <h1 class="mt-6 max-w-3xl text-5xl font-semibold leading-tight text-foreground">Intelligent Grant Disbursement Platform</h1>
      <p class="mt-5 max-w-2xl text-lg leading-8 text-muted">
        Project-first sanctions, tranche approvals, utilization tracking, reconciliation, imports and AI-assisted administrative workflows.
      </p>
      <div class="mt-12 grid max-w-3xl grid-cols-3 gap-3">
        <div class="border border-line bg-panel p-4">
          <div class="text-xs text-muted">Workflow</div>
          <div class="mt-2 text-lg font-semibold">Sanction to payment</div>
        </div>
        <div class="border border-line bg-panel p-4">
          <div class="text-xs text-muted">Controls</div>
          <div class="mt-2 text-lg font-semibold">Role-based review</div>
        </div>
        <div class="border border-line bg-panel p-4">
          <div class="text-xs text-muted">AI</div>
          <div class="mt-2 text-lg font-semibold">Persisted assistance</div>
        </div>
      </div>
    </section>

    <section class="flex items-center px-5 py-8 sm:px-10">
      <form class="w-full space-y-5" @submit.prevent="submit">
        <div>
          <div class="text-2xl font-semibold">Sign in</div>
          <p class="mt-1 text-sm text-muted">Use your fund administration account.</p>
        </div>
        <FormControl v-model="email" label="Email" type="email" required autocomplete="email" />
        <div class="space-y-2">
          <FormControl v-model="password" label="Password" :type="showPassword ? 'text' : 'password'" required autocomplete="current-password" />
          <Button :label="showPassword ? 'Hide password' : 'Show password'" icon-left="eye" @click="showPassword = !showPassword" />
        </div>
        <div v-if="error" class="border border-danger/30 bg-red-50 px-3 py-2 text-sm text-danger">{{ error }}</div>
        <Button variant="solid" type="submit" label="Sign in" icon-left="log-in" :loading="auth.state.loading" class="w-full" />
      </form>
    </section>
  </main>
</template>
