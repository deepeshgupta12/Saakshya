/* Auth API calls — register, login, refresh, logout (docs/10 §1, M7).
   Does not import the auth store to avoid circular deps.
   Callers are responsible for storing/clearing tokens via useAuthStore. */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface TokenPair {
  access_token:  string;
  refresh_token: string;
  expires_in:    number;
  plan:          string;
}

export interface RegisterResult extends TokenPair {
  user_id: string;
  email:   string;
}

async function authFetch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify(body),
  });
  const raw: { data?: T; error?: { message?: string } } = await res.json();
  if (!res.ok) {
    throw new Error(raw.error?.message ?? `Auth error ${res.status}`);
  }
  return raw.data as T;
}

export async function apiRegister(params: {
  email:              string;
  password:           string;
  display_name?:      string;
  consent_not_advice: boolean;
  consent_ai_use:     boolean;
}): Promise<RegisterResult> {
  return authFetch<RegisterResult>("/api/auth/register", params);
}

export async function apiLogin(email: string, password: string): Promise<TokenPair> {
  return authFetch<TokenPair>("/api/auth/login", { email, password });
}

export async function apiRefresh(refresh_token: string): Promise<TokenPair> {
  return authFetch<TokenPair>("/api/auth/refresh", { refresh_token });
}

export async function apiLogout(accessToken: string, refresh_token: string): Promise<void> {
  await fetch(`${API_BASE}/api/auth/logout`, {
    method:  "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${accessToken}` },
    body:    JSON.stringify({ refresh_token }),
  });
}

export interface OAuthResult extends TokenPair {
  user_id: string;
  email:   string;
}

export async function apiOAuthGoogle(id_token: string): Promise<OAuthResult> {
  return authFetch<OAuthResult>("/api/auth/oauth/google", { id_token });
}
