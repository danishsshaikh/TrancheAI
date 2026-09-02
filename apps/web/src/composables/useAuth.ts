import { computed, reactive } from "vue";

import { currentUser, login as apiLogin, logout as apiLogout } from "../api/client";
import type { User } from "../types/domain";

const STORAGE_KEY = "trancheai.auth";

interface AuthState {
  token: string;
  user: User | null;
  loading: boolean;
}

const saved = readSaved();
const state = reactive<AuthState>({
  token: saved?.token ?? "",
  user: saved?.user ?? null,
  loading: false,
});

export function useAuth() {
  const isAuthenticated = computed(() => Boolean(state.token));

  async function login(email: string, password: string) {
    state.loading = true;
    try {
      const session = await apiLogin(email, password);
      state.token = session.accessToken;
      state.user = session.user;
      persist();
    } finally {
      state.loading = false;
    }
  }

  async function loadCurrentUser() {
    if (!state.token) return null;
    state.loading = true;
    try {
      state.user = await currentUser(state.token);
      persist();
      return state.user;
    } catch (error) {
      clearAuth();
      throw error;
    } finally {
      state.loading = false;
    }
  }

  async function logout() {
    const token = state.token;
    clearAuth();
    if (token) {
      try {
        await apiLogout(token);
      } catch {
        // Local sign-out should finish even if the server token was already invalid.
      }
    }
  }

  function clearAuth() {
    state.token = "";
    state.user = null;
    localStorage.removeItem(STORAGE_KEY);
  }

  function persist() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ token: state.token, user: state.user }));
  }

  return { state, isAuthenticated, login, loadCurrentUser, logout, clearAuth };
}

export function authToken(): string {
  return state.token;
}

export function hasToken(): boolean {
  return Boolean(state.token);
}

function readSaved(): { token: string; user: User | null } | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}
