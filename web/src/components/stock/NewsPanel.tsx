"use client";
/* NewsPanel — per-stock news feed with sentiment classification (docs/08 §5, docs/18 §9, M7).
   Mode A: sentiment is a classification label ("classified positive"), never a directive.
   Below-threshold items are never shown (is_surfaced filter on backend).
   Free-tier users see an upgrade prompt — no 403. */

import * as React from "react";
import { ExternalLink, Newspaper } from "lucide-react";
import { useAuthStore } from "@/stores/auth";
import { fetchStockNews, type NewsArticle } from "@/lib/api/news";
import { cn } from "@/lib/utils";

/* ── Sentiment chip ────────────────────────────────────────────────── */
function SentimentChip({ label, score }: { label: string; score: number | null }) {
  const isLowConf = score != null && score < 0.6;
  const display = isLowConf ? "neutral / uncertain" : `classified ${label}`;
  return (
    <span
      aria-label={`News sentiment: ${display}`}
      title={score != null ? `Confidence: ${(score * 100).toFixed(0)}%` : undefined}
      className={cn(
        "inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium border",
        label === "positive" && !isLowConf
          ? "bg-(--bullish)/10 text-(--bullish) border-(--bullish)/20"
          : label === "negative" && !isLowConf
          ? "bg-(--bearish)/10 text-(--bearish) border-(--bearish)/20"
          : "bg-(--surface-3) text-(--text-muted) border-(--border-subtle)",
      )}
    >
      {display}
    </span>
  );
}

/* ── NewsCard ───────────────────────────────────────────────────────── */
function NewsCard({ article }: { article: NewsArticle }) {
  const published = article.published_at
    ? new Date(article.published_at).toLocaleString("en-IN", {
        day:    "2-digit",
        month:  "short",
        hour:   "2-digit",
        minute: "2-digit",
        hour12: false,
      })
    : null;

  return (
    <article className="flex flex-col gap-1.5 py-3 border-b border-(--border-subtle) last:border-0">
      <a
        href={article.url}
        target="_blank"
        rel="noopener noreferrer"
        className="group flex items-start gap-1.5 text-sm font-medium text-(--text-primary) hover:text-(--accent) transition-colors"
      >
        <span className="flex-1 leading-snug">{article.headline}</span>
        <ExternalLink className="mt-0.5 h-3 w-3 shrink-0 text-(--text-muted) group-hover:text-(--accent)" aria-hidden />
      </a>

      <div className="flex flex-wrap items-center gap-2">
        {article.sentiment && (
          <SentimentChip label={article.sentiment.label} score={article.sentiment.score} />
        )}
        {published && (
          <time className="text-[10px] text-(--text-muted)" dateTime={article.published_at ?? ""}>
            {published}
          </time>
        )}
        {article.link_confidence != null && (
          <span className="text-[10px] text-(--text-muted)">
            confidence {(article.link_confidence * 100).toFixed(0)}%
          </span>
        )}
      </div>
    </article>
  );
}

/* ── NewsPanel (exported) ──────────────────────────────────────────── */
export function NewsPanel({ symbol }: { symbol: string }) {
  const accessToken = useAuthStore((s) => s.accessToken);
  const plan        = useAuthStore((s) => s.plan);

  const [articles, setArticles] = React.useState<NewsArticle[]>([]);
  const [loading,  setLoading]  = React.useState(false);
  const [error,    setError]    = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!accessToken) return;
    setLoading(true);
    fetchStockNews(accessToken, symbol)
      .then(setArticles)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [accessToken, symbol]);

  /* Not authenticated — silent: the stock page is public */
  if (!accessToken) return null;

  return (
    <section aria-label="News for this stock">
      <h2 className="text-xs font-semibold text-(--text-muted) uppercase tracking-wide mb-3">
        News &amp; Sentiment
      </h2>

      {loading && (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="animate-pulse space-y-1.5 py-3 border-b border-(--border-subtle)">
              <div className="h-3.5 w-3/4 rounded bg-(--surface-3)" />
              <div className="h-2.5 w-1/3 rounded bg-(--surface-3)" />
            </div>
          ))}
        </div>
      )}

      {!loading && error && (
        <p className="text-xs text-(--text-muted)">{error}</p>
      )}

      {!loading && !error && plan === "free" && (
        <div className="rounded-(--radius-md) border border-(--border-subtle) bg-(--surface-2) px-4 py-3 text-xs text-(--text-muted)">
          News &amp; sentiment requires a Premium plan.
        </div>
      )}

      {!loading && !error && plan !== "free" && articles.length === 0 && (
        <div className="flex flex-col items-center gap-2 py-8 text-center">
          <Newspaper className="h-6 w-6 text-(--text-muted)" aria-hidden />
          <p className="text-xs text-(--text-muted)">No recent news found for {symbol}.</p>
        </div>
      )}

      {!loading && !error && articles.length > 0 && (
        <>
          <div>
            {articles.map((a) => (
              <NewsCard key={a.article_id} article={a} />
            ))}
          </div>
          <p className="mt-3 text-[10px] text-(--text-muted)">
            Sentiment is a classification only — not a trading signal. Saakshya provides analytics only — not investment advice.
          </p>
        </>
      )}
    </section>
  );
}
