"use client";
/* Command palette — docs/07 §2.9. Cmd/Ctrl+K, keyboard-first, fuzzy search. */

import * as React from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { Search, TrendingUp, BarChart2, Globe } from "lucide-react";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { useUiStore } from "@/stores/ui-store";

const QUICK_LINKS = [
  { label: "Market dashboard",       href: "/market",              icon: Globe },
  { label: "Momentum scanner",       href: "/scanners/momentum",   icon: TrendingUp },
  { label: "Volume breakout scanner",href: "/scanners/volume-breakout", icon: BarChart2 },
  { label: "RSI scanner",            href: "/scanners/rsi",        icon: TrendingUp },
  { label: "Sectors",                href: "/sectors",             icon: Globe },
];

export function CommandPalette() {
  const open = useUiStore((s) => s.commandPaletteOpen);
  const setOpen = useUiStore((s) => s.setCommandPaletteOpen);
  const [query, setQuery] = React.useState("");
  const router = useRouter();
  const inputRef = React.useRef<HTMLInputElement>(null);

  React.useEffect(() => {
    if (open) {
      setQuery("");
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  const filtered = QUICK_LINKS.filter((l) =>
    !query || l.label.toLowerCase().includes(query.toLowerCase())
  );

  function navigate(href: string) {
    setOpen(false);
    router.push(href);
  }

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-[var(--z-modal)] bg-black/60 backdrop-blur-sm" />
        <Dialog.Content
          className="fixed left-1/2 top-[20%] z-[var(--z-palette)] w-full max-w-lg -translate-x-1/2 rounded-[--radius-xl] border border-[--border-strong] bg-[--surface-1] shadow-[--shadow-elev-3] focus:outline-none"
          aria-label="Command palette"
        >
          <Dialog.Title className="sr-only">Command palette</Dialog.Title>

          {/* Search input */}
          <div className="flex items-center gap-3 border-b border-[--border-subtle] px-4 py-3">
            <Search className="h-4 w-4 text-[--text-muted] shrink-0" aria-hidden />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search stocks, sectors, scanners…"
              className="flex-1 bg-transparent text-sm text-[--text-primary] placeholder:text-[--text-muted] focus:outline-none"
              aria-autocomplete="list"
            />
            <kbd className="text-[10px] text-[--text-muted] border border-[--border-subtle] rounded px-1">Esc</kbd>
          </div>

          {/* Results */}
          <ul role="listbox" className="max-h-80 overflow-y-auto py-2">
            {filtered.length === 0 ? (
              <li className="px-4 py-8 text-center text-sm text-[--text-muted]">No results found</li>
            ) : (
              filtered.map((item) => {
                const Icon = item.icon;
                return (
                  <li key={item.href} role="option">
                    <button
                      type="button"
                      onClick={() => navigate(item.href)}
                      className={cn(
                        "flex w-full items-center gap-3 px-4 py-2.5 text-sm text-[--text-secondary] hover:bg-[--surface-3] hover:text-[--text-primary] transition-colors text-left"
                      )}
                    >
                      <Icon className="h-4 w-4 shrink-0 text-[--text-muted]" aria-hidden />
                      {item.label}
                    </button>
                  </li>
                );
              })
            )}
          </ul>

          <div className="border-t border-[--border-subtle] px-4 py-2">
            <p className="text-[10px] text-[--text-muted]">
              Analytics and evidence only — not investment advice
            </p>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
