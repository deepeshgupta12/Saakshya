"use client";
/* Watchlist screen — WatchlistTabs + WatchlistTable + AddSymbolDialog + CreateListDialog.
   docs/08 §8: tabs (Free=1, Premium=unlimited), table with per-symbol metrics + scanner tags,
   optimistic remove, evidence-led (no buy/sell CTA). Mode A: descriptive only. */

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Plus, X, Bookmark, ExternalLink, Loader2, AlertCircle, Trash2 } from "lucide-react";

import { useAuthStore } from "@/stores/auth";
import { Button } from "@/components/ui";
import { cn } from "@/lib/utils";
import {
  fetchWatchlists, createWatchlist, deleteWatchlist,
  fetchWatchlistDetail, addWatchlistItem, removeWatchlistItem,
  type WatchlistMeta, type WatchlistItem, type WatchlistDetail,
} from "@/lib/api/watchlists";

const FREE_LIST_LIMIT = 1;

/* ── Skeleton ──────────────────────────────────────────────────────── */
function SkeletonRow() {
  return (
    <tr className="border-b border-(--border-subtle) animate-pulse">
      {[1, 2, 3, 4, 5, 6].map((i) => (
        <td key={i} className="px-4 py-3">
          <div className="h-3.5 rounded bg-(--surface-3)" style={{ width: `${40 + i * 10}%` }} />
        </td>
      ))}
    </tr>
  );
}

/* ── Toast ─────────────────────────────────────────────────────────── */
function Toast({ message, onClose }: { message: string; onClose: () => void }) {
  React.useEffect(() => {
    const t = setTimeout(onClose, 3500);
    return () => clearTimeout(t);
  }, [onClose]);
  return (
    <motion.div
      role="status" aria-live="polite"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 16 }}
      transition={{ duration: 0.2 }}
      className="fixed bottom-6 left-1/2 -translate-x-1/2 z-[var(--z-toast)] flex items-center gap-2 rounded-(--radius-lg) bg-(--surface-2) border border-(--border-subtle) px-4 py-2.5 text-sm text-(--text-primary) shadow-lg"
    >
      <span className="h-2 w-2 rounded-full bg-(--bullish) shrink-0" aria-hidden />
      {message}
      <button
        type="button" onClick={onClose} aria-label="Dismiss"
        className="ml-1 text-(--text-muted) hover:text-(--text-primary) transition-colors"
      >
        <X className="h-3.5 w-3.5" aria-hidden />
      </button>
    </motion.div>
  );
}

/* ── AddSymbolDialog ───────────────────────────────────────────────── */
interface AddSymbolDialogProps {
  onClose:  () => void;
  onAdd:    (symbol: string) => Promise<void>;
  loading:  boolean;
  error:    string | null;
}

function AddSymbolDialog({ onClose, onAdd, loading, error }: AddSymbolDialogProps) {
  const [symbol, setSymbol] = React.useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const s = symbol.trim().toUpperCase();
    if (s) await onAdd(s);
  }

  /* Trap focus + close on Escape */
  React.useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  return (
    <div
      role="dialog" aria-modal="true" aria-labelledby="add-symbol-title"
      className="fixed inset-0 z-[var(--z-modal)] flex items-center justify-center p-4"
    >
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden
      />
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        transition={{ duration: 0.15 }}
        className="relative z-10 w-full max-w-sm rounded-(--radius-lg) bg-(--surface-1) border border-(--border-subtle) p-6 shadow-xl"
      >
        <div className="flex items-center justify-between mb-4">
          <h2 id="add-symbol-title" className="text-base font-semibold text-(--text-primary)">
            Add symbol
          </h2>
          <button
            type="button" onClick={onClose} aria-label="Close"
            className="text-(--text-muted) hover:text-(--text-primary) transition-colors cursor-pointer"
          >
            <X className="h-4 w-4" aria-hidden />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="space-y-1">
            <label htmlFor="symbol-input" className="text-xs font-medium text-(--text-secondary)">
              NSE / BSE symbol
            </label>
            <input
              id="symbol-input"
              type="text"
              autoFocus
              autoComplete="off"
              autoCapitalize="characters"
              spellCheck={false}
              value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              placeholder="e.g. RELIANCE"
              className={cn(
                "w-full min-h-[44px] rounded-(--radius-md) px-3 text-sm font-mono",
                "bg-(--surface-2) border border-(--border-subtle)",
                "text-(--text-primary) placeholder:text-(--text-muted) placeholder:font-sans",
                "focus:outline-none focus:ring-2 focus:ring-(--accent) focus:ring-offset-1 focus:ring-offset-(--surface-1)",
                "transition-colors duration-(--motion-fast)",
              )}
            />
          </div>

          {error && (
            <p role="alert" className="flex items-center gap-1.5 text-xs text-(--bearish)">
              <AlertCircle className="h-3.5 w-3.5 shrink-0" aria-hidden />
              {error}
            </p>
          )}

          <div className="flex gap-2 pt-1">
            <Button type="button" variant="outline" size="sm" onClick={onClose} className="flex-1">
              Cancel
            </Button>
            <Button
              type="submit" size="sm" disabled={loading || !symbol.trim()}
              className="flex-1"
            >
              {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden /> : "Add"}
            </Button>
          </div>
        </form>
      </motion.div>
    </div>
  );
}

/* ── CreateListDialog ──────────────────────────────────────────────── */
function CreateListDialog({
  onClose, onCreate,
}: { onClose: () => void; onCreate: (name: string) => Promise<void> }) {
  const [name, setName]     = React.useState("");
  const [loading, setLoading] = React.useState(false);
  const [error, setError]   = React.useState<string | null>(null);

  React.useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [onClose]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const n = name.trim();
    if (!n) return;
    setLoading(true); setError(null);
    try { await onCreate(n); }
    catch (err) { setError(err instanceof Error ? err.message : "Failed to create list."); }
    finally { setLoading(false); }
  }

  return (
    <div role="dialog" aria-modal="true" aria-labelledby="create-list-title"
      className="fixed inset-0 z-[var(--z-modal)] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} aria-hidden />
      <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }} transition={{ duration: 0.15 }}
        className="relative z-10 w-full max-w-sm rounded-(--radius-lg) bg-(--surface-1) border border-(--border-subtle) p-6 shadow-xl"
      >
        <div className="flex items-center justify-between mb-4">
          <h2 id="create-list-title" className="text-base font-semibold text-(--text-primary)">
            New watchlist
          </h2>
          <button type="button" onClick={onClose} aria-label="Close"
            className="text-(--text-muted) hover:text-(--text-primary) transition-colors cursor-pointer">
            <X className="h-4 w-4" aria-hidden />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="space-y-1">
            <label htmlFor="list-name-input" className="text-xs font-medium text-(--text-secondary)">
              List name
            </label>
            <input id="list-name-input" type="text" autoFocus value={name}
              onChange={(e) => setName(e.target.value)} placeholder="e.g. Core Holdings"
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
          <div className="flex gap-2 pt-1">
            <Button type="button" variant="outline" size="sm" onClick={onClose} className="flex-1">Cancel</Button>
            <Button type="submit" size="sm" disabled={loading || !name.trim()} className="flex-1">
              {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden /> : "Create"}
            </Button>
          </div>
        </form>
      </motion.div>
    </div>
  );
}

/* ── WatchlistTable ────────────────────────────────────────────────── */
function WatchlistTable({
  items, loading, onRemove,
}: {
  items:    WatchlistItem[];
  loading:  boolean;
  onRemove: (itemId: string, symbol: string) => void;
}) {
  if (loading) {
    return (
      <div className="overflow-x-auto rounded-(--radius-lg) border border-(--border-subtle)">
        <table className="w-full text-sm">
          <thead className="bg-(--surface-2) text-xs text-(--text-muted) uppercase tracking-wide">
            <tr>
              {["Symbol", "Company", "Sector", "Close", "Chg %", "Scanner tags", ""].map((h) => (
                <th key={h} className="px-4 py-2.5 text-left font-medium whitespace-nowrap">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-(--surface-1) divide-y divide-(--border-subtle)">
            {Array.from({ length: 4 }).map((_, i) => <SkeletonRow key={i} />)}
          </tbody>
        </table>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 rounded-(--radius-lg) border border-(--border-subtle) bg-(--surface-1) py-16 text-center">
        <Bookmark className="h-8 w-8 text-(--text-muted)" aria-hidden />
        <p className="text-sm font-medium text-(--text-secondary)">No symbols yet</p>
        <p className="text-xs text-(--text-muted)">Use "Add symbol" to track NSE / BSE equities here.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-(--radius-lg) border border-(--border-subtle)">
      <table className="w-full text-sm">
        <thead className="bg-(--surface-2) text-xs text-(--text-muted) uppercase tracking-wide">
          <tr>
            <th className="px-4 py-2.5 text-left font-medium">Symbol</th>
            <th className="px-4 py-2.5 text-left font-medium">Company</th>
            <th className="px-4 py-2.5 text-left font-medium hidden md:table-cell">Sector</th>
            <th className="px-4 py-2.5 text-right font-medium">Close</th>
            <th className="px-4 py-2.5 text-right font-medium">Chg %</th>
            <th className="px-4 py-2.5 text-left font-medium hidden lg:table-cell">Scanner tags</th>
            <th className="px-4 py-2.5 w-10" aria-label="Actions" />
          </tr>
        </thead>
        <tbody className="bg-(--surface-1) divide-y divide-(--border-subtle)">
          <AnimatePresence initial={false}>
            {items.map((item) => (
              <motion.tr
                key={item.item_id}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0, x: -16 }}
                transition={{ duration: 0.15 }}
                className="hover:bg-(--surface-2) transition-colors"
              >
                <td className="px-4 py-3">
                  <Link
                    href={`/stocks/${item.symbol}`}
                    className="flex items-center gap-1.5 font-medium text-(--text-primary) hover:text-(--accent) transition-colors"
                  >
                    {item.symbol}
                    <ExternalLink className="h-3 w-3 text-(--text-muted)" aria-hidden />
                  </Link>
                </td>
                <td className="px-4 py-3 text-(--text-secondary) max-w-[160px] truncate">
                  {item.company_name ?? "—"}
                </td>
                <td className="px-4 py-3 text-(--text-muted) hidden md:table-cell">
                  {item.sector ?? "—"}
                </td>
                <td className="px-4 py-3 text-right font-mono text-(--text-secondary)">
                  {item.last_close != null ? `₹${item.last_close.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "—"}
                </td>
                <td className={cn(
                  "px-4 py-3 text-right font-mono font-medium",
                  item.change_pct == null    ? "text-(--text-muted)"
                  : item.change_pct > 0     ? "text-(--bullish)"
                  : item.change_pct < 0     ? "text-(--bearish)"
                  : "text-(--text-secondary)"
                )}>
                  {item.change_pct != null
                    ? `${item.change_pct > 0 ? "+" : ""}${item.change_pct.toFixed(2)}%`
                    : "—"}
                </td>
                <td className="px-4 py-3 hidden lg:table-cell">
                  {item.scanner_tags.length > 0 ? (
                    <div className="flex flex-wrap gap-1">
                      {item.scanner_tags.slice(0, 3).map((tag) => (
                        <span key={tag}
                          className="inline-block rounded px-1.5 py-0.5 text-[10px] font-medium bg-(--surface-3) text-(--text-secondary) border border-(--border-subtle)">
                          {tag.replace(/_/g, " ")}
                        </span>
                      ))}
                      {item.scanner_tags.length > 3 && (
                        <span className="text-[10px] text-(--text-muted)">+{item.scanner_tags.length - 3}</span>
                      )}
                    </div>
                  ) : (
                    <span className="text-(--text-muted) text-xs">—</span>
                  )}
                </td>
                <td className="px-4 py-3 text-right">
                  <button
                    type="button"
                    aria-label={`Remove ${item.symbol} from watchlist`}
                    onClick={() => onRemove(item.item_id, item.symbol)}
                    className="p-1.5 rounded-(--radius-sm) text-(--text-muted) hover:text-(--bearish) hover:bg-(--surface-3) transition-colors cursor-pointer"
                  >
                    <X className="h-3.5 w-3.5" aria-hidden />
                  </button>
                </td>
              </motion.tr>
            ))}
          </AnimatePresence>
        </tbody>
      </table>
    </div>
  );
}

/* ── WatchlistClient (root) ────────────────────────────────────────── */
export default function WatchlistClient() {
  const router      = useRouter();
  const accessToken = useAuthStore((s) => s.accessToken);
  const plan        = useAuthStore((s) => s.plan);
  const isAuth      = useAuthStore((s) => s.isAuthenticated);

  /* Auth guard — redirect to login if not authenticated */
  React.useEffect(() => {
    if (!isAuth()) router.replace("/login");
  }, [isAuth, router]);

  const [lists,        setLists]        = React.useState<WatchlistMeta[]>([]);
  const [activeId,     setActiveId]     = React.useState<string | null>(null);
  const [detail,       setDetail]       = React.useState<WatchlistDetail | null>(null);
  const [listsLoading, setListsLoading] = React.useState(true);
  const [detailLoading, setDetailLoading] = React.useState(false);
  const [listError,    setListError]    = React.useState<string | null>(null);

  const [showAddSymbol,  setShowAddSymbol]  = React.useState(false);
  const [showCreateList, setShowCreateList] = React.useState(false);
  const [addLoading,     setAddLoading]     = React.useState(false);
  const [addError,       setAddError]       = React.useState<string | null>(null);
  const [toast,          setToast]          = React.useState<string | null>(null);

  /* Load watchlist index */
  React.useEffect(() => {
    if (!accessToken) return;
    setListsLoading(true);
    fetchWatchlists(accessToken)
      .then((data) => {
        setLists(data);
        if (data.length > 0) setActiveId(data[0].watchlist_id);
      })
      .catch((e) => setListError(e.message))
      .finally(() => setListsLoading(false));
  }, [accessToken]);

  /* Load detail whenever active tab changes */
  React.useEffect(() => {
    if (!accessToken || !activeId) return;
    setDetailLoading(true);
    fetchWatchlistDetail(accessToken, activeId)
      .then(setDetail)
      .catch((e) => setListError(e.message))
      .finally(() => setDetailLoading(false));
  }, [accessToken, activeId]);

  async function handleAddSymbol(symbol: string) {
    if (!accessToken || !activeId) return;
    setAddLoading(true); setAddError(null);
    try {
      const result = await addWatchlistItem(accessToken, activeId, symbol);
      if (result.already_present) {
        setAddError(`${symbol} is already in this list.`);
        return;
      }
      /* Refresh detail to get hydrated item */
      const updated = await fetchWatchlistDetail(accessToken, activeId);
      setDetail(updated);
      setShowAddSymbol(false);
      setToast(`${symbol} added`);
    } catch (err) {
      setAddError(err instanceof Error ? err.message : "Failed to add symbol.");
    } finally {
      setAddLoading(false);
    }
  }

  async function handleRemoveItem(itemId: string, symbol: string) {
    if (!accessToken || !activeId) return;
    /* Optimistic remove */
    setDetail((d) => d ? { ...d, items: d.items.filter((i) => i.item_id !== itemId) } : d);
    try {
      await removeWatchlistItem(accessToken, activeId, itemId);
      setToast(`${symbol} removed`);
    } catch {
      /* Revert on failure */
      const updated = await fetchWatchlistDetail(accessToken, activeId).catch(() => null);
      if (updated) setDetail(updated);
    }
  }

  async function handleCreateList(name: string) {
    if (!accessToken) return;
    const created = await createWatchlist(accessToken, name);
    setLists((prev) => [...prev, created]);
    setActiveId(created.watchlist_id);
    setDetail({ ...created, items: [] });
    setShowCreateList(false);
    setToast(`"${name}" created`);
  }

  async function handleDeleteList() {
    if (!accessToken || !activeId || !detail) return;
    const name = detail.name;
    if (!confirm(`Delete watchlist "${name}"? This cannot be undone.`)) return;
    await deleteWatchlist(accessToken, activeId);
    const remaining = lists.filter((l) => l.watchlist_id !== activeId);
    setLists(remaining);
    setActiveId(remaining[0]?.watchlist_id ?? null);
    setDetail(remaining.length > 0 ? null : null);
    setToast(`"${name}" deleted`);
  }

  const canCreateList = plan !== "free" || lists.length < FREE_LIST_LIMIT;

  if (!accessToken) return null;

  return (
    <div className="flex flex-col gap-6">

      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-(--text-primary)">Watchlist</h1>
          <p className="text-xs text-(--text-muted) mt-0.5">
            Track NSE / BSE equities with EOD metrics and scanner memberships. Not investment advice.
          </p>
        </div>
        <Button
          size="sm"
          onClick={() => setShowCreateList(true)}
          disabled={!canCreateList}
          title={!canCreateList ? "Upgrade to Premium for unlimited watchlists" : undefined}
          className="gap-1.5"
        >
          <Plus className="h-3.5 w-3.5" aria-hidden />
          New list
        </Button>
      </div>

      {/* Error state */}
      {listError && (
        <div role="alert" className="flex items-center gap-2 rounded-(--radius-md) border border-(--bearish)/30 bg-(--bearish)/10 px-4 py-3 text-sm text-(--bearish)">
          <AlertCircle className="h-4 w-4 shrink-0" aria-hidden />
          {listError}
          <button
            type="button"
            className="ml-auto text-xs underline cursor-pointer"
            onClick={() => { setListError(null); window.location.reload(); }}
          >
            Retry
          </button>
        </div>
      )}

      {/* Loading state for list index */}
      {listsLoading && (
        <div className="flex items-center gap-2 text-sm text-(--text-muted)">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
          Loading watchlists…
        </div>
      )}

      {/* Empty state — no lists yet */}
      {!listsLoading && lists.length === 0 && !listError && (
        <div className="flex flex-col items-center justify-center gap-4 rounded-(--radius-lg) border border-(--border-subtle) bg-(--surface-1) py-20 text-center">
          <Bookmark className="h-10 w-10 text-(--text-muted)" aria-hidden />
          <div>
            <p className="text-sm font-medium text-(--text-secondary)">No watchlists yet</p>
            <p className="text-xs text-(--text-muted) mt-1">Create your first list to start tracking equities.</p>
          </div>
          <Button size="sm" onClick={() => setShowCreateList(true)} className="gap-1.5">
            <Plus className="h-3.5 w-3.5" aria-hidden />
            Create your first list
          </Button>
        </div>
      )}

      {/* Tabs + content */}
      {!listsLoading && lists.length > 0 && (
        <div className="flex flex-col gap-4">

          {/* Tab row */}
          <div className="flex items-center gap-1 overflow-x-auto border-b border-(--border-subtle) pb-0 -mb-px">
            {lists.map((wl) => {
              const active = wl.watchlist_id === activeId;
              return (
                <button
                  key={wl.watchlist_id}
                  type="button"
                  role="tab"
                  aria-selected={active}
                  onClick={() => setActiveId(wl.watchlist_id)}
                  className={cn(
                    "flex-shrink-0 px-4 py-2 text-sm font-medium border-b-2 transition-colors cursor-pointer whitespace-nowrap",
                    active
                      ? "border-(--accent) text-(--accent)"
                      : "border-transparent text-(--text-muted) hover:text-(--text-secondary) hover:border-(--border-strong)"
                  )}
                >
                  {wl.name}
                </button>
              );
            })}
          </div>

          {/* Toolbar */}
          <div className="flex items-center justify-between gap-3">
            <p className="text-xs text-(--text-muted)">
              {detailLoading
                ? "Loading…"
                : detail
                ? `${detail.items.length} symbol${detail.items.length !== 1 ? "s" : ""} · EOD data`
                : ""}
            </p>
            <div className="flex items-center gap-2">
              {detail && detail.items.length > 0 && (
                <Button
                  variant="ghost" size="sm"
                  onClick={handleDeleteList}
                  className="gap-1.5 text-(--text-muted) hover:text-(--bearish)"
                  aria-label="Delete this watchlist"
                >
                  <Trash2 className="h-3.5 w-3.5" aria-hidden />
                  <span className="hidden sm:inline">Delete list</span>
                </Button>
              )}
              <Button
                size="sm"
                onClick={() => { setAddError(null); setShowAddSymbol(true); }}
                className="gap-1.5"
              >
                <Plus className="h-3.5 w-3.5" aria-hidden />
                Add symbol
              </Button>
            </div>
          </div>

          {/* Table */}
          <WatchlistTable
            items={detail?.items ?? []}
            loading={detailLoading}
            onRemove={handleRemoveItem}
          />

          {/* Disclaimer */}
          <p className="text-[10px] text-(--text-muted)">
            Prices are end-of-day (T+1). Scanner memberships are as of last scan run.
            This is analytics only — not investment advice (SEBI Mode A).
          </p>
        </div>
      )}

      {/* Dialogs */}
      <AnimatePresence>
        {showAddSymbol && (
          <AddSymbolDialog
            key="add-symbol"
            onClose={() => setShowAddSymbol(false)}
            onAdd={handleAddSymbol}
            loading={addLoading}
            error={addError}
          />
        )}
        {showCreateList && (
          <CreateListDialog
            key="create-list"
            onClose={() => setShowCreateList(false)}
            onCreate={handleCreateList}
          />
        )}
        {toast && (
          <Toast key="toast" message={toast} onClose={() => setToast(null)} />
        )}
      </AnimatePresence>
    </div>
  );
}
