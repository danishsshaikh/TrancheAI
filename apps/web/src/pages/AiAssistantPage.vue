<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { Badge, Button, FormControl } from "frappe-ui";

import {
  cancelAIProposal,
  confirmAIProposal,
  createAIConversation,
  fetchAIConversation,
  listAIConversations,
  sendAIConversationMessage,
  updateAIConversation,
} from "../api/client";
import AppShell from "../components/AppShell.vue";
import { authToken } from "../composables/useAuth";
import type { AIConversation, AIMessage, AIProposal, AIResponse } from "../types/domain";
import { dateText, labelize } from "../utils/format";

const route = useRoute();
const conversations = ref<AIConversation[]>([]);
const active = ref<AIConversation | null>(null);
const prompt = ref("");
const loading = ref(false);
const sending = ref(false);
const error = ref("");

const projectContext = computed(() => ({
  project_id: route.query.projectId ? String(route.query.projectId) : undefined,
  project_code: route.query.projectCode ? String(route.query.projectCode) : undefined,
}));

onMounted(load);

async function load() {
  loading.value = true;
  error.value = "";
  try {
    conversations.value = await listAIConversations(authToken());
    const context = projectContext.value;
    const contextual = context.project_id ? conversations.value.find((item) => item.projectId === context.project_id) : null;
    if (contextual) {
      await openConversation(contextual.id);
    } else if (context.project_id || conversations.value.length === 0) {
      await newConversation();
    } else {
      await openConversation(conversations.value[0].id);
    }
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Unable to load AI history.";
  } finally {
    loading.value = false;
  }
}

async function newConversation() {
  active.value = await createAIConversation(authToken(), {
    title: projectContext.value.project_code ? `Project ${projectContext.value.project_code}` : undefined,
    ...projectContext.value,
  });
  conversations.value = await listAIConversations(authToken());
}

async function openConversation(id: string) {
  active.value = await fetchAIConversation(authToken(), id);
}

async function archiveConversation(id: string) {
  await updateAIConversation(authToken(), id, { archived: true });
  active.value = null;
  await load();
}

async function send() {
  const text = prompt.value.trim();
  if (!text || !active.value) return;
  sending.value = true;
  error.value = "";
  try {
    const result = await sendAIConversationMessage(authToken(), active.value.id, text);
    active.value = result.conversation;
    prompt.value = "";
    conversations.value = await listAIConversations(authToken());
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Unable to send message.";
  } finally {
    sending.value = false;
  }
}

async function proposalAction(proposal: AIProposal, action: "confirm" | "cancel") {
  sending.value = true;
  try {
    const response = action === "confirm" ? await confirmAIProposal(authToken(), proposal.id) : await cancelAIProposal(authToken(), proposal.id);
    const current = active.value;
    if (current) {
      current.messages = [
        ...(current.messages ?? []),
        {
          id: `local-${Date.now()}`,
          conversationId: current.id,
          role: "assistant",
          content: response.message,
          responseKind: response.kind,
          metadata: response,
        },
      ];
    }
  } finally {
    sending.value = false;
  }
}

function proposalFromMessage(message: AIMessage): AIProposal | null {
  const metadata = message.metadata as AIResponse | undefined;
  return metadata?.proposal ?? null;
}
</script>

<template>
  <AppShell>
    <div class="grid min-h-[calc(100vh-8rem)] gap-5 xl:grid-cols-[320px_1fr]">
      <aside class="border border-line bg-panel">
        <div class="flex items-center justify-between border-b border-line px-4 py-3">
          <h1 class="text-base font-semibold">AI history</h1>
          <Button icon="plus" @click="newConversation" />
        </div>
        <div class="divide-y divide-line">
          <button
            v-for="conversation in conversations"
            :key="conversation.id"
            type="button"
            class="block w-full px-4 py-3 text-left text-sm hover:bg-gray-50"
            :class="{ 'bg-gray-50': active?.id === conversation.id }"
            @click="openConversation(conversation.id)"
          >
            <span class="block truncate font-medium">{{ conversation.title }}</span>
            <span class="block text-xs text-muted">{{ conversation.projectCode || 'General' }} · {{ dateText(conversation.updatedAt) }}</span>
          </button>
          <div v-if="!loading && conversations.length === 0" class="px-4 py-8 text-center text-sm text-muted">No conversations</div>
        </div>
      </aside>

      <section class="flex min-h-0 flex-col border border-line bg-panel">
        <div class="flex flex-wrap items-start justify-between gap-3 border-b border-line px-4 py-3">
          <div>
            <h2 class="text-lg font-semibold">{{ active?.title || 'New conversation' }}</h2>
            <p class="mt-1 text-sm text-muted">{{ active?.projectCode ? `Project ${active.projectCode}` : 'General fund operations' }}</p>
          </div>
          <Button v-if="active" label="Archive" icon-left="archive" @click="archiveConversation(active.id)" />
        </div>

        <div v-if="error" class="m-4 border border-danger/30 bg-red-50 px-3 py-2 text-sm text-danger">{{ error }}</div>

        <div class="min-h-0 flex-1 space-y-4 overflow-y-auto p-4">
          <article v-for="message in active?.messages || []" :key="message.id" class="max-w-4xl border border-line p-4" :class="message.role === 'user' ? 'ml-auto bg-gray-50' : 'bg-panel'">
            <div class="mb-2 flex items-center justify-between gap-3">
              <Badge :label="message.role === 'user' ? 'You' : 'TrancheAI'" />
              <span class="text-xs text-muted">{{ dateText(message.createdAt) }}</span>
            </div>
            <p class="whitespace-pre-wrap text-sm leading-6">{{ message.content }}</p>

            <div v-if="proposalFromMessage(message)" class="mt-4 border border-line bg-gray-50 p-3 text-sm">
              <div class="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <div class="font-medium">{{ labelize(proposalFromMessage(message)?.action) }}</div>
                  <div class="text-muted">Status: {{ labelize(proposalFromMessage(message)?.status) }}</div>
                </div>
                <div class="flex gap-2">
                  <Button label="Cancel" icon-left="x" @click="proposalAction(proposalFromMessage(message)!, 'cancel')" />
                  <Button variant="solid" label="Confirm" icon-left="check" @click="proposalAction(proposalFromMessage(message)!, 'confirm')" />
                </div>
              </div>
              <pre class="mt-3 max-h-60 overflow-auto bg-white p-3 text-xs">{{ JSON.stringify(proposalFromMessage(message)?.proposedValues, null, 2) }}</pre>
            </div>
          </article>

          <div v-if="!loading && (!active || !active.messages?.length)" class="grid h-full place-items-center text-center text-sm text-muted">
            <div>
              <div class="text-base font-medium text-foreground">Start with a project or workflow question</div>
              <p class="mt-1">The full thread is stored in the TrancheAI database.</p>
            </div>
          </div>
        </div>

        <form class="border-t border-line p-4" @submit.prevent="send">
          <div class="grid gap-3 md:grid-cols-[1fr_auto]">
            <FormControl v-model="prompt" type="textarea" placeholder="Ask about a project, create a proposal, or request a reconciliation explanation" />
            <Button variant="solid" type="submit" label="Send" icon-left="send" :disabled="!active" :loading="sending" />
          </div>
        </form>
      </section>
    </div>
  </AppShell>
</template>
