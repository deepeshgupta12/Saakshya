"use client";
/* Sign-up page — /signup (docs/08 §auth-screens, M7, docs/21 §consent).
   Requires explicit consent to not-advice + AI-use notices (SPEC §6.7).
   On success: stores tokens, redirects to /market. */

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { Button, Card } from "@/components/ui";
import { apiRegister } from "@/lib/auth/client";
import { useAuthStore } from "@/stores/auth";
import { cn } from "@/lib/utils";

export default function SignupPage() {
  const router    = useRouter();
  const setTokens = useAuthStore((s) => s.setTokens);

  const [email,          setEmail]          = useState("");
  const [displayName,    setDisplayName]    = useState("");
  const [password,       setPassword]       = useState("");
  const [consentAdvice,  setConsentAdvice]  = useState(false);
  const [consentAi,      setConsentAi]      = useState(false);
  const [error,          setError]          = useState<string | null>(null);
  const [loading,        setLoading]        = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!consentAdvice || !consentAi) {
      setError("Please acknowledge both notices to continue.");
      return;
    }
    if (password.length < 12) {
      setError("Password must be at least 12 characters.");
      return;
    }
    setLoading(true);
    try {
      const result = await apiRegister({
        email,
        password,
        display_name:       displayName,
        consent_not_advice: consentAdvice,
        consent_ai_use:     consentAi,
      });
      setTokens({
        accessToken:  result.access_token,
        refreshToken: result.refresh_token,
        userId:       result.user_id,
        plan:         result.plan,
        email:        result.email,
      });
      router.push("/market");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Sign-up failed.");
    } finally {
      setLoading(false);
    }
  }

  const inputClass = cn(
    "w-full min-h-[44px] rounded-(--radius-md) px-3 text-sm",
    "bg-(--surface-2) border border-(--border-subtle)",
    "text-(--text-primary) placeholder:text-(--text-muted)",
    "focus:outline-none focus:ring-2 focus:ring-(--accent) focus:ring-offset-1 focus:ring-offset-(--surface-1)",
    "transition-colors duration-(--motion-fast)",
  );

  return (
    <Card className="p-8">
      <h1 className="text-xl font-bold text-(--text-primary) mb-1">Create account</h1>
      <p className="text-sm text-(--text-muted) mb-6">Evidence-first equity analytics for NSE/BSE</p>

      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        <div className="space-y-1">
          <label htmlFor="displayName" className="text-xs font-medium text-(--text-secondary)">
            Display name <span className="text-(--text-muted)">(optional)</span>
          </label>
          <input
            id="displayName"
            type="text"
            autoComplete="name"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="Your name"
            className={inputClass}
          />
        </div>

        <div className="space-y-1">
          <label htmlFor="email" className="text-xs font-medium text-(--text-secondary)">
            Email address <span className="text-(--bearish)">*</span>
          </label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className={inputClass}
          />
        </div>

        <div className="space-y-1">
          <label htmlFor="password" className="text-xs font-medium text-(--text-secondary)">
            Password <span className="text-(--bearish)">*</span>
          </label>
          <input
            id="password"
            type="password"
            autoComplete="new-password"
            required
            minLength={12}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="At least 12 characters"
            className={inputClass}
          />
          <p className="text-[10px] text-(--text-muted)">Minimum 12 characters</p>
        </div>

        {/* Compliance consent — SPEC §6.7, docs/21 §3.1 */}
        <div className="rounded-(--radius-md) border border-(--border-subtle) bg-(--surface-2) p-4 space-y-3">
          <label className="flex items-start gap-3 cursor-pointer group">
            <input
              type="checkbox"
              checked={consentAdvice}
              onChange={(e) => setConsentAdvice(e.target.checked)}
              className="mt-0.5 h-4 w-4 rounded border border-(--border-strong) accent-(--accent) cursor-pointer"
            />
            <span className="text-xs text-(--text-secondary) leading-relaxed group-hover:text-(--text-primary) transition-colors">
              I understand that Saakshya provides <strong>market data, analytics and research tools</strong> — not investment advice, stock recommendations, or guaranteed returns.
            </span>
          </label>

          <label className="flex items-start gap-3 cursor-pointer group">
            <input
              type="checkbox"
              checked={consentAi}
              onChange={(e) => setConsentAi(e.target.checked)}
              className="mt-0.5 h-4 w-4 rounded border border-(--border-strong) accent-(--accent) cursor-pointer"
            />
            <span className="text-xs text-(--text-secondary) leading-relaxed group-hover:text-(--text-primary) transition-colors">
              I understand that <strong>AI-generated summaries</strong> are grounded in provided data but may contain errors. I will independently verify before acting on any insight.
            </span>
          </label>
        </div>

        {error && (
          <p role="alert" className="text-xs text-(--bearish)">
            {error}
          </p>
        )}

        <Button
          type="submit"
          className="w-full"
          disabled={loading || !consentAdvice || !consentAi}
        >
          {loading ? "Creating account…" : "Create account"}
        </Button>
      </form>

      <p className="mt-6 text-center text-xs text-(--text-muted)">
        Already have an account?{" "}
        <Link href="/login" className="text-(--accent) hover:underline">
          Sign in
        </Link>
      </p>
    </Card>
  );
}
