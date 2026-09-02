<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Button, Dropdown, FormControl } from "frappe-ui";

import { globalSearch } from "../api/client";
import { authToken, useAuth } from "../composables/useAuth";
import type { SearchResult } from "../types/domain";

const route = useRoute();
const router = useRouter();
const { state, loadCurrentUser, logout } = useAuth();
const query = ref("");
const searchResults = ref<SearchResult[]>([]);
const searching = ref(false);

const nav = [
  { label: "Dashboard", to: "/dashboard" },
  { label: "Projects", to: "/projects" },
  { label: "Tranches", to: "/tranches" },
  { label: "Reconciliation", to: "/reconciliation" },
  { label: "Imports / Exports", to: "/imports-exports" },
  { label: "AI", to: "/ai" },
  { label: "Settings", to: "/settings" },
];

const accountOptions = computed(() => [
  { label: "Profile", onClick: () => router.push("/settings") },
  { label: "Settings", onClick: () => router.push("/settings") },
  { label: "Sign out", onClick: signOut },
]);

const initials = computed(() =>
  String(state.user?.fullName || state.user?.email || "TA")
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase()
);

onMounted(async () => {
  if (!state.user && state.token) {
    try {
      await loadCurrentUser();
    } catch {
      await router.push("/login");
    }
  }
});

watch(query, async (value) => {
  const term = value.trim();
  if (term.length < 2) {
    searchResults.value = [];
    return;
  }
  searching.value = true;
  try {
    searchResults.value = await globalSearch(authToken(), term);
  } finally {
    searching.value = false;
  }
});

async function openResult(result: SearchResult) {
  query.value = "";
  searchResults.value = [];
  await router.push(result.to);
}

async function signOut() {
  await logout();
  await router.push("/login");
}
</script>

<template>
  <div class="min-h-screen bg-background text-foreground">
    <aside class="fixed inset-y-0 left-0 hidden w-64 border-r border-line bg-panel px-4 py-5 lg:block">
      <div class="mb-8 flex items-center gap-3">
        <div class="grid size-10 place-items-center rounded bg-foreground text-sm font-semibold text-white">TA</div>
        <div>
          <div class="text-base font-semibold leading-tight">TrancheAI</div>
          <div class="text-xs text-muted">Grant disbursement</div>
        </div>
      </div>
      <nav class="space-y-1">
        <RouterLink
          v-for="item in nav"
          :key="item.to"
          :to="item.to"
          class="flex h-9 items-center rounded px-3 text-sm text-muted transition hover:bg-gray-100 hover:text-foreground"
          :class="{ 'bg-gray-100 font-medium text-foreground': route.path.startsWith(item.to) }"
        >
          {{ item.label }}
        </RouterLink>
      </nav>
    </aside>

    <div class="lg:pl-64">
      <header class="sticky top-0 z-20 border-b border-line bg-panel/95 backdrop-blur">
        <div class="flex min-h-16 items-center gap-3 px-4 sm:px-6">
          <div class="lg:hidden">
            <Dropdown :options="nav.map((item) => ({ label: item.label, onClick: () => router.push(item.to) }))">
              <Button icon="menu" />
            </Dropdown>
          </div>

          <div class="relative min-w-0 flex-1">
            <FormControl v-model="query" placeholder="Search projects, departments, payment references" />
            <div v-if="query.length > 1" class="absolute left-0 right-0 top-11 z-30 border border-line bg-panel shadow-sm">
              <div v-if="searching" class="px-3 py-3 text-sm text-muted">Searching...</div>
              <button
                v-for="result in searchResults"
                :key="`${result.type}-${result.to}`"
                type="button"
                class="block w-full border-b border-line px-3 py-2 text-left text-sm hover:bg-gray-50"
                @click="openResult(result)"
              >
                <span class="block font-medium">{{ result.label }}</span>
                <span class="block text-xs text-muted">{{ result.description || result.type }}</span>
              </button>
              <div v-if="!searching && searchResults.length === 0" class="px-3 py-3 text-sm text-muted">No results</div>
            </div>
          </div>

          <Dropdown :options="accountOptions">
            <Button :label="initials" icon-right="chevron-down" />
          </Dropdown>
        </div>
      </header>

      <main class="px-4 py-5 sm:px-6">
        <slot />
      </main>
    </div>
  </div>
</template>
