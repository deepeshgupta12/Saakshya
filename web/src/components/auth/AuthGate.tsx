"use client";

/**
 * AuthGate — client-side auth guard for the `(app)` route group (docs/06 §1, docs/23 §1).
 *
 * Auth in the local-first build is client-side (access token in-memory, refresh token in
 * localStorage — no cookies), so the session can't be checked server-side. This mirrors the
 * established per-page pattern (WatchlistClient): if not authenticated, redirect to /login.
 * A cookie-session server check is a future hardening when the auth model moves server-side.
 */

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { useAuthStore } from "@/stores/auth";

export function AuthGate({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const router = useRouter();

  useEffect(() => {
    if (!isAuthenticated()) router.replace("/login");
  }, [isAuthenticated, router]);

  return <>{children}</>;
}
