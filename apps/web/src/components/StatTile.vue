<script setup lang="ts">
defineProps<{
  label: string;
  value: string | number;
  tone?: "default" | "success" | "warning" | "danger";
}>();
</script>

<template>
  <div class="border border-line bg-panel p-4">
    <div class="text-xs font-medium uppercase tracking-normal text-muted">{{ label }}</div>
    <div
      class="mt-2 truncate text-2xl font-semibold"
      :class="{
        'text-success': tone === 'success',
        'text-warning': tone === 'warning',
        'text-danger': tone === 'danger',
      }"
    >
      {{ value }}
    </div>
  </div>
</template>
