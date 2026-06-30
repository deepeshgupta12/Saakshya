"use client";
/* UI primitives — docs/07 §2.2–§2.6.
   Only React, Tailwind tokens, and design utilities imported here.
   No hooks (except motion), stores, or domain logic. */

import * as React from "react";
import { motion, useMotionValue, useTransform, animate } from "framer-motion";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";
import { spring, useMotion } from "@/lib/motion/variants";

/* ── Button ────────────────────────────────────────────────────────── */
const buttonVariants = cva(
  /* Base: min 44px touch target, cursor-pointer, touch-action for 300ms tap-delay fix */
  [
    "inline-flex items-center justify-center gap-2 rounded-[--radius-md] text-sm font-medium",
    "min-h-[44px] px-4 cursor-pointer touch-action-manipulation",
    "transition-colors duration-[--motion-fast]",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[--accent] focus-visible:ring-offset-1 focus-visible:ring-offset-[--surface-base]",
    "disabled:pointer-events-none disabled:opacity-40",
    "select-none",
  ].join(" "),
  {
    variants: {
      variant: {
        default:  "bg-[--accent] text-[--text-inverse] hover:bg-[--accent-strong] active:opacity-90",
        outline:  "border border-[--border-strong] text-[--text-primary] hover:bg-[--surface-3] active:bg-[--surface-3]",
        ghost:    "text-[--text-secondary] hover:bg-[--surface-3] hover:text-[--text-primary]",
        danger:   "bg-[--bearish] text-white hover:opacity-90 active:opacity-80",
      },
      size: {
        sm:  "min-h-[36px] px-3 text-xs",
        md:  "min-h-[44px] px-4",
        lg:  "min-h-[48px] px-6 text-base",
        icon: "min-h-[44px] w-[44px] p-0",
      },
    },
    defaultVariants: { variant: "default", size: "md" },
  }
);

interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

/* ── Card ────────────────────────────────────────────────────────── */
export const Card = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "rounded-[--radius-lg] border border-[--border-subtle] bg-[--surface-1]",
        "p-5 shadow-[--shadow-elev-1]",
        "transition-shadow duration-[--motion-base]",
        /* Interactive card lift — only when onClick or tabIndex present */
        className
      )}
      {...props}
    />
  )
);
Card.displayName = "Card";

export const CardHeader = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("flex items-center justify-between mb-4 gap-2", className)} {...props} />
);

export const CardTitle = ({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => (
  <h3 className={cn("text-sm font-semibold text-[--text-primary] leading-snug", className)} {...props} />
);

/* ── Badge ────────────────────────────────────────────────────────── */
const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-[--radius-sm] px-2 py-0.5 text-xs font-medium select-none",
  {
    variants: {
      variant: {
        default:  "bg-[--surface-2] text-[--text-secondary]",
        accent:   "bg-[--accent]/15 text-[--accent]",
        bullish:  "bg-[--bullish]/15 text-[--bullish]",
        bearish:  "bg-[--bearish]/15 text-[--bearish]",
        warning:  "bg-[--warning]/15 text-[--warning]",
        ai:       "bg-[--ai]/15 text-[--ai]",
        neutral:  "bg-[--surface-2] text-[--neutral]",
      },
    },
    defaultVariants: { variant: "default" },
  }
);

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant, className }))} {...props} />;
}

/* ── ScoreBadge — count-up animation, evidence-linked ── */
function scoreBand(score: number): { label: string; className: string } {
  if (score >= 80) return { label: "High",     className: "bg-[--bullish]/15 text-[--bullish]" };
  if (score >= 60) return { label: "Moderate", className: "bg-[--accent]/15 text-[--accent]" };
  if (score >= 40) return { label: "Neutral",  className: "bg-[--neutral]/15 text-[--neutral]" };
  return               { label: "Low",      className: "bg-[--bearish]/15 text-[--bearish]" };
}

interface ScoreBadgeProps {
  score: number;
  onClick?: () => void;
  className?: string;
}

export function ScoreBadge({ score, onClick, className }: ScoreBadgeProps) {
  const rounded = Math.round(score);
  const { label, className: bandClass } = scoreBand(rounded);
  const { reduced } = useMotion();

  /* Count-up: 0 → score on mount, once, respects reduce-motion */
  const motionVal = useMotionValue(reduced ? rounded : 0);
  const displayed = useTransform(motionVal, (v) => Math.round(v));

  React.useEffect(() => {
    if (reduced) { motionVal.set(rounded); return; }
    const controls = animate(motionVal, rounded, { duration: 0.6, ease: [0.2, 0.8, 0.2, 1] });
    return controls.stop;
  }, [rounded, reduced, motionVal]);

  return (
    <motion.button
      type="button"
      onClick={onClick}
      whileTap={{ scale: 0.96 }}
      transition={spring.snappy}
      aria-label={`Score ${rounded} out of 100 — ${label}. Click to view evidence.`}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-[--radius-sm] px-2.5 py-1",
        "font-mono tabular-nums text-xs font-semibold",
        "cursor-pointer touch-action-manipulation select-none",
        "transition-opacity duration-[--motion-fast] hover:opacity-80",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[--accent]",
        bandClass,
        className
      )}
    >
      <motion.span>{displayed}</motion.span>
      <span className="opacity-60 text-[10px] font-sans not-italic">{label}</span>
    </motion.button>
  );
}

/* ── Chip ────────────────────────────────────────────────────────── */
export function Chip({ className, ...props }: React.HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-[--radius-sm]",
        "border border-[--border-subtle] bg-[--surface-2]",
        "px-2 py-0.5 text-xs text-[--text-secondary]",
        className
      )}
      {...props}
    />
  );
}

/* ── Skeleton — shimmer per docs/07 §2.6 ── */
export function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-[--radius-md] bg-[--surface-3]",
        className
      )}
      {...props}
    />
  );
}

/* ── EmptyState ────────────────────────────────────────────────────── */
interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({ icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div className={cn("flex flex-col items-center justify-center py-16 text-center gap-2", className)}>
      {icon && (
        <div className="mb-2 text-[--text-muted] opacity-50 text-3xl">{icon}</div>
      )}
      <p className="text-sm font-medium text-[--text-secondary]">{title}</p>
      {description && (
        <p className="text-xs text-[--text-muted] max-w-xs leading-relaxed">{description}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

/* ── ErrorState ────────────────────────────────────────────────────── */
interface ErrorStateProps {
  message?: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorState({ message = "Something went wrong.", onRetry, className }: ErrorStateProps) {
  return (
    <div
      role="alert"
      className={cn("flex flex-col items-center justify-center py-12 text-center gap-2", className)}
    >
      <p className="text-sm text-[--bearish]">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-1 text-xs text-[--accent] hover:underline cursor-pointer"
          aria-label="Retry loading data"
        >
          Try again
        </button>
      )}
    </div>
  );
}

/* ── DataTable — a11y: scope, aria-sort ── */
type SortDir = "ascending" | "descending" | "none";

interface Column<T> {
  key: string;
  header: string;
  cell: (row: T) => React.ReactNode;
  align?: "left" | "right" | "center";
  sortable?: boolean;
  className?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  getRowKey: (row: T) => string;
  onRowClick?: (row: T) => void;
  sortKey?: string;
  sortDir?: SortDir;
  onSort?: (key: string) => void;
  className?: string;
}

export function DataTable<T>({
  columns, data, getRowKey, onRowClick,
  sortKey, sortDir = "none", onSort,
  className,
}: DataTableProps<T>) {
  return (
    <div className={cn("w-full overflow-x-auto rounded-[--radius-lg] border border-[--border-subtle]", className)}>
      <table className="w-full border-collapse text-sm" role="grid">
        <thead className="sticky top-0 bg-[--surface-2] z-10">
          <tr>
            {columns.map((col) => {
              const isSorted = col.sortable && sortKey === col.key;
              const ariaSort: SortDir | undefined = col.sortable
                ? isSorted ? sortDir : "none"
                : undefined;
              return (
                <th
                  key={col.key}
                  scope="col"
                  aria-sort={ariaSort}
                  onClick={col.sortable && onSort ? () => onSort(col.key) : undefined}
                  className={cn(
                    "border-b border-[--border-subtle] px-3 py-3 text-xs font-medium text-[--text-muted] whitespace-nowrap",
                    col.align === "right" ? "text-right" : col.align === "center" ? "text-center" : "text-left",
                    col.sortable && "cursor-pointer select-none hover:text-[--text-secondary] transition-colors"
                  )}
                >
                  <span className="inline-flex items-center gap-1">
                    {col.header}
                    {col.sortable && (
                      <span className="text-[--text-muted] opacity-50" aria-hidden>
                        {isSorted && sortDir === "ascending" ? "↑" : isSorted && sortDir === "descending" ? "↓" : "↕"}
                      </span>
                    )}
                  </span>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {data.map((row) => (
            <tr
              key={getRowKey(row)}
              onClick={() => onRowClick?.(row)}
              className={cn(
                "border-b border-[--border-subtle] transition-colors",
                onRowClick && "cursor-pointer hover:bg-[--surface-3]"
              )}
              tabIndex={onRowClick ? 0 : undefined}
              onKeyDown={onRowClick ? (e) => {
                if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onRowClick(row); }
              } : undefined}
            >
              {columns.map((col) => (
                <td
                  key={col.key}
                  className={cn(
                    "px-3 py-3 text-[--text-primary]",
                    col.align === "right" ? "text-right tabular-nums" : col.align === "center" ? "text-center" : "text-left",
                    col.className
                  )}
                >
                  {col.cell(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
