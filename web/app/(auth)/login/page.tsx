"use client";
/* Login page — /login (docs/08 §auth-screens, M7, docs/23 §1).
   Client component: accesses localStorage (via Zustand persist) post-hydration.
   On success: stores tokens, redirects to /market. */

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { Button, Card } from "@/components/ui";
import { apiLogin, apiOAuthGoogle } from "@/lib/auth/client";
import { useAuthStore } from "@/stores/auth";
import { GoogleSignInButton } from "@/components/auth/GoogleSignInButton";
import { cn } from "@/lib/utils";

const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID ?? "";

export default function LoginPage() {
  const router    = useRouter();
  const setTokens = useAuthStore((s) => s.setTokens);

  const [email,    setEmail]    = useState("");
  const [password, setPassword] = useState("");
  const [error,    setError]    = useState<string | null>(null);
  const [loading,  setLoading]  = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const tokens = await apiLogin(email, password);
      setTokens({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token, plan: tokens.plan, email });
      router.push("/market");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed.");
    } finally {
      setLoading(false);
    }
  }

  async function handleGoogleSuccess(idToken: string) {
    setError(null);
    setLoading(true);
    try {
      const result = await apiOAuthGoogle(idToken);
      setTokens({
        accessToken:  result.access_token,
        refreshToken: result.refresh_token,
        plan:         result.plan,
        email:        result.email,
      });
      router.push("/market");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Google sign-in failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card className="p-8">
      <h1 className="text-xl font-bold text-(--text-primary) mb-1">Sign in</h1>
      <p className="text-sm text-(--text-muted) mb-6">Welcome back to Saakshya</p>

      {/* Google sign-in — shown only when NEXT_PUBLIC_GOOGLE_CLIENT_ID is set */}
      {GOOGLE_CLIENT_ID && (
        <div className="mb-4">
          <GoogleSignInButton clientId={GOOGLE_CLIENT_ID} onSuccess={handleGoogleSuccess} onError={setError} />
          <div className="relative my-4 flex items-center">
            <div className="flex-1 border-t border-(--border-subtle)" />
            <span className="mx-3 text-[10px] text-(--text-muted) uppercase tracking-wider">or</span>
            <div className="flex-1 border-t border-(--border-subtle)" />
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        <div className="space-y-1">
          <label htmlFor="email" className="text-xs font-medium text-(--text-secondary)">
            Email address
          </label>
          <input
            id="email" type="email" autoComplete="email" required
            value={email} onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className={cn(
              "w-full min-h-[44px] rounded-(--radius-md) px-3 text-sm",
              "bg-(--surface-2) border border-(--border-subtle)",
              "text-(--text-primary) placeholder:text-(--text-muted)",
              "focus:outline-none focus:ring-2 focus:ring-(--accent) focus:ring-offset-1 focus:ring-offset-(--surface-1)",
              "transition-colors duration-(--motion-fast)",
            )}
          />
        </div>

        <div className="space-y-1">
          <label htmlFor="password" className="text-xs font-medium text-(--text-secondary)">
            Password
          </label>
          <input
            id="password" type="password" autoComplete="current-password" required
            value={password} onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••••••"
            className={cn(
              "w-full min-h-[44px] rounded-(--radius-md) px-3 text-sm",
              "bg-(--surface-2) border border-(--border-subtle)",
              "text-(--text-primary) placeholder:text-(--text-muted)",
              "focus:outline-none focus:ring-2 focus:ring-(--accent) focus:ring-offset-1 focus:ring-offset-(--surface-1)",
              "transition-colors duration-(--motion-fast)",
            )}
          />
        </div>

        {error && <p role="alert" className="text-xs text-(--bearish)">{error}</p>}

        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? "Signing in…" : "Sign in"}
        </Button>
      </form>

      <p className="mt-6 text-center text-xs text-(--text-muted)">
        No account?{" "}
        <Link href="/signup" className="text-(--accent) hover:underline">Create one</Link>
      </p>
      <p className="mt-4 text-center text-[10px] text-(--text-muted)">
        Saakshya provides analytics only — not investment advice.
      </p>
    </Card>
  );
}
