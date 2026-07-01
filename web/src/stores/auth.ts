/* Auth store — JWT access token + refresh token persistence (docs/23 §1, M7).
   Access token: in-memory only (never localStorage).
   Refresh token: localStorage (30-day rotating; revoked on logout).
   Note: localStorage is unavailable during SSR — guards ensure window check. */

"use client";

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

export interface AuthState {
  accessToken:  string | null;
  refreshToken: string | null;
  userId:       string | null;
  plan:         string | null;
  email:        string | null;
  setTokens: (params: {
    accessToken: string;
    refreshToken: string;
    userId?: string;
    plan?: string;
    email?: string;
  }) => void;
  setAccessToken: (token: string) => void;
  clearAuth: () => void;
  isAuthenticated: () => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      accessToken:  null,
      refreshToken: null,
      userId:       null,
      plan:         null,
      email:        null,

      setTokens: ({ accessToken, refreshToken, userId, plan, email }) =>
        set({ accessToken, refreshToken, userId: userId ?? null, plan: plan ?? null, email: email ?? null }),

      setAccessToken: (token) => set({ accessToken: token }),

      clearAuth: () => set({ accessToken: null, refreshToken: null, userId: null, plan: null, email: null }),

      isAuthenticated: () => get().accessToken !== null,
    }),
    {
      name:    "saakshya-auth",
      storage: createJSONStorage(() => (typeof window !== "undefined" ? localStorage : { getItem: () => null, setItem: () => {}, removeItem: () => {} })),
      // Only persist the refresh token + metadata — keep access token in memory.
      partialize: (s) => ({
        refreshToken: s.refreshToken,
        userId:       s.userId,
        plan:         s.plan,
        email:        s.email,
      }),
    }
  )
);
