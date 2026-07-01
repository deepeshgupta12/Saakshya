/* Watchlist API client — typed functions for watchlist CRUD (docs/10 §8, M7).
   All calls require an access token; callers source it from useAuthStore.
   DELETE routes return 204 with no body — do not parse JSON. */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface WatchlistMeta {
  watchlist_id: string;
  name:         string;
  created_at:   string;
}

export interface WatchlistItem {
  item_id:      string;
  symbol:       string;
  company_name: string | null;
  sector:       string | null;
  last_close:   number | null;
  change_pct:   number | null;
  scanner_tags: string[];
  added_at:     string;
}

export interface WatchlistDetail extends WatchlistMeta {
  items: WatchlistItem[];
}

async function wlFetch<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(init?.headers ?? {}),
    },
  });
  const raw: { data?: T; error?: { message?: string } } = await res.json();
  if (!res.ok) {
    throw new Error(raw.error?.message ?? `API ${res.status}`);
  }
  return raw.data as T;
}

async function wlDelete(path: string, token: string): Promise<void> {
  const res = await fetch(`${API_BASE}${path}`, {
    method:  "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok && res.status !== 204) {
    const raw: { error?: { message?: string } } = await res.json().catch(() => ({}));
    throw new Error(raw.error?.message ?? `Delete failed ${res.status}`);
  }
}

export async function fetchWatchlists(token: string): Promise<WatchlistMeta[]> {
  return wlFetch<WatchlistMeta[]>("/api/watchlists", token);
}

export async function createWatchlist(token: string, name: string): Promise<WatchlistMeta> {
  return wlFetch<WatchlistMeta>("/api/watchlists", token, {
    method: "POST",
    body:   JSON.stringify({ name }),
  });
}

export async function renameWatchlist(token: string, id: string, name: string): Promise<WatchlistMeta> {
  return wlFetch<WatchlistMeta>(`/api/watchlists/${id}`, token, {
    method: "PATCH",
    body:   JSON.stringify({ name }),
  });
}

export async function deleteWatchlist(token: string, id: string): Promise<void> {
  return wlDelete(`/api/watchlists/${id}`, token);
}

export async function fetchWatchlistDetail(token: string, id: string): Promise<WatchlistDetail> {
  return wlFetch<WatchlistDetail>(`/api/watchlists/${id}`, token);
}

export async function addWatchlistItem(
  token: string, watchlistId: string, symbol: string,
): Promise<{ item_id: string; symbol: string; already_present: boolean }> {
  return wlFetch(`/api/watchlists/${watchlistId}/items`, token, {
    method: "POST",
    body:   JSON.stringify({ symbol }),
  });
}

export async function removeWatchlistItem(
  token: string, watchlistId: string, itemId: string,
): Promise<void> {
  return wlDelete(`/api/watchlists/${watchlistId}/items/${itemId}`, token);
}
