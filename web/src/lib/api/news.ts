/* News API client — GET /api/stocks/{symbol}/news (docs/10 §4, M7).
   Requires access token (Premium gate — free users get empty array, not error). */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface NewsArticle {
  article_id:      string;
  headline:        string;
  url:             string;
  published_at:    string | null;
  source_id:       string;
  symbol:          string;
  link_confidence: number;
  sentiment: {
    label:         "positive" | "neutral" | "negative";
    score:         number | null;
    model_version: string;
  } | null;
  impact_score: number | null;
  category:     string | null;
  disclaimer:   string;
}

async function newsFetch<T>(path: string, token: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
    next: { revalidate: 0 },
  });
  const raw: { data?: T; error?: { message?: string } } = await res.json();
  if (!res.ok) throw new Error(raw.error?.message ?? `API ${res.status}`);
  return raw.data as T;
}

export async function fetchStockNews(
  token: string,
  symbol: string,
  limit = 10,
): Promise<NewsArticle[]> {
  return newsFetch<NewsArticle[]>(
    `/api/stocks/${symbol}/news?limit=${limit}`,
    token,
  );
}
