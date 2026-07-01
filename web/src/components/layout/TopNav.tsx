"use client";
/* TopNav — docs/07 §2, docs/08. Glass-on-scroll, skip link, active state. */

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Search, BarChart2, ScanLine, Grid3x3, Bookmark, Briefcase, Layers } from "lucide-react";
import { cn } from "@/lib/utils";
import { useUiStore } from "@/stores/ui-store";
import { useAuthStore } from "@/stores/auth";

/* Nav items with icons — icon + label per ui-ux-pro-max nav rules */
const NAV_ITEMS_PUBLIC = [
  { href: "/market",   label: "Market",   Icon: BarChart2 },
  { href: "/scanners", label: "Scanners", Icon: ScanLine  },
  { href: "/sectors",  label: "Sectors",  Icon: Grid3x3   },
] as const;

const NAV_ITEMS_AUTH = [
  { href: "/watchlist", label: "Watchlist", Icon: Bookmark  },
  { href: "/portfolio", label: "Portfolio", Icon: Briefcase },
  { href: "/strategy",  label: "Screeners", Icon: Layers    },
] as const;

export function TopNav() {
  const togglePalette = useUiStore((s) => s.toggleCommandPalette);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const pathname = usePathname();
  const [scrolled, setScrolled] = React.useState(false);

  const navItems = isAuthenticated()
    ? [...NAV_ITEMS_PUBLIC, ...NAV_ITEMS_AUTH]
    : NAV_ITEMS_PUBLIC;

  /* Glassmorphism activates after 8px scroll */
  React.useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 8);
    window.addEventListener("scroll", handler, { passive: true });
    return () => window.removeEventListener("scroll", handler);
  }, []);

  /* Cmd+K → command palette */
  React.useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        togglePalette();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [togglePalette]);

  return (
    <>
      {/* Skip link — keyboard a11y first ── */}
      <a
        href="#main-content"
        className={cn(
          "sr-only focus:not-sr-only",
          "fixed top-2 left-2 z-[var(--z-toast)]",
          "rounded-(--radius-md) bg-(--accent) px-4 py-2 text-sm font-medium text-(--text-inverse)",
          "focus:outline-none focus:ring-2 focus:ring-(--accent-strong)"
        )}
      >
        Skip to content
      </a>

      <header
        className={cn(
          "sticky top-0 z-[var(--z-sticky)] w-full transition-all duration-200",
          scrolled
            ? "glass border-b border-(--border-subtle)"
            : "bg-(--surface-base) border-b border-transparent"
        )}
      >
        <div className="mx-auto flex h-14 max-w-[1440px] items-center gap-4 px-4 md:px-6">

          {/* Logo / wordmark */}
          <Link
            href="/market"
            className="group flex items-baseline gap-1.5 shrink-0"
            aria-label="Saakshya — go to market dashboard"
          >
            <span className="text-[15px] font-bold tracking-[-0.01em] text-(--text-primary) group-hover:text-(--accent) transition-colors">
              Saakshya
            </span>
            <span className="hidden sm:inline text-[10px] text-(--text-muted) font-normal tracking-wide uppercase">
              evidence
            </span>
          </Link>

          {/* Primary nav */}
          <nav
            className="hidden md:flex items-center gap-0.5 flex-1"
            aria-label="Main navigation"
          >
            {navItems.map(({ href, label, Icon }) => {
              /* Active if exact or starts-with for nested routes */
              const active = pathname === href || pathname.startsWith(href + "/");
              return (
                <Link
                  key={href}
                  href={href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "flex items-center gap-1.5 rounded-(--radius-md) px-3 py-1.5 text-sm transition-all duration-(--motion-fast)",
                    active
                      ? "bg-(--accent)/10 text-(--accent) font-medium"
                      : "text-(--text-secondary) hover:bg-(--surface-3) hover:text-(--text-primary)"
                  )}
                >
                  <Icon className="h-3.5 w-3.5 shrink-0" aria-hidden />
                  {label}
                  {active && (
                    <span className="ml-0.5 h-1 w-1 rounded-full bg-(--accent)" aria-hidden />
                  )}
                </Link>
              );
            })}
          </nav>

          {/* Search / Command palette trigger */}
          <button
            type="button"
            onClick={togglePalette}
            aria-label="Open command palette — search stocks, sectors, scanners (Cmd+K)"
            className={cn(
              "ml-auto flex items-center gap-2",
              "min-h-[36px] rounded-(--radius-md) border border-(--border-subtle) bg-(--surface-2)",
              "px-3 py-1.5 text-xs text-(--text-muted)",
              "hover:border-(--border-strong) hover:text-(--text-secondary)",
              "cursor-pointer touch-action-manipulation select-none",
              "transition-colors duration-(--motion-fast)",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-(--accent)"
            )}
          >
            <Search className="h-3.5 w-3.5 shrink-0" aria-hidden />
            <span className="hidden sm:inline">Search stocks, sectors…</span>
            <kbd
              className="hidden sm:inline ml-1 rounded border border-(--border-subtle) bg-(--surface-3) px-1.5 text-[10px] font-mono"
              aria-hidden
            >
              ⌘K
            </kbd>
          </button>
        </div>

        {/* Mobile bottom border indicator for active route */}
        <div className="md:hidden flex items-center gap-0 overflow-x-auto border-t border-(--border-subtle) px-2 pb-1 pt-0.5">
          {navItems.map(({ href, label, Icon }) => {
            const active = pathname === href || pathname.startsWith(href + "/");
            return (
              <Link
                key={href}
                href={href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex items-center gap-1.5 whitespace-nowrap px-3 py-1.5 text-xs transition-all",
                  active
                    ? "text-(--accent) font-medium border-b-2 border-(--accent)"
                    : "text-(--text-muted) border-b-2 border-transparent"
                )}
              >
                <Icon className="h-3 w-3 shrink-0" aria-hidden />
                {label}
              </Link>
            );
          })}
        </div>
      </header>
    </>
  );
}
