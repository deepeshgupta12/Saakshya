"use client";

/**
 * Landing — the public home page at `/` (docs/08 §1, docs/07).
 *
 * Evidence-led, premium, dark-first. Communicates "best Indian-equity screener + best
 * explanations, evidence-first" and converts to signup — never "what to buy". A subtle
 * 3D data-orb anchors the hero (client-only; static gradient fallback for reduced motion).
 * All copy is descriptive and pairs with a not-advice note (SPEC §3, §5).
 */

import dynamic from "next/dynamic";
import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import {
  ArrowRight,
  BarChart3,
  ScanLine,
  ShieldCheck,
  Sparkles,
  TrendingUp,
} from "lucide-react";

import { Button, Card, ScoreBadge } from "@/components/ui";
import { NotAdviceBanner } from "@/components/compliance";
import { fadeUp, staggerContainer } from "@/lib/motion/variants";

const HeroCanvas = dynamic(() => import("./HeroCanvas"), { ssr: false });

const FEATURES = [
  {
    Icon: ScanLine,
    title: "Validated scanners",
    body: "Momentum, volume, RSI and moving-average scanners across NSE/BSE — each result shown with a score, the reasons behind it, and its risk flags. Point-in-time and corporate-action aware.",
  },
  {
    Icon: Sparkles,
    title: "AI that explains, never invents",
    body: "Every summary is grounded in computed metrics from a structured payload. A runtime verifier blocks any number or fact that can't be traced — and suppresses rather than guesses.",
  },
  {
    Icon: ShieldCheck,
    title: "Trustworthy by construction",
    body: "As-of versioned data, a data-confidence indicator, and an audit trail behind every AI generation. Descriptive analytics only — never a buy, sell, target or stop.",
  },
] as const;

const SAMPLE_ROWS = [
  { symbol: "TATAMOTORS", score: 87, reasons: ["Momentum strong", "Above 50-DMA"] },
  { symbol: "SBIN", score: 74, reasons: ["Volume 2.1× avg", "Above 200-DMA"] },
  { symbol: "INFY", score: 68, reasons: ["RSI 61", "MA stacking"] },
] as const;

export function Landing() {
  const reduce = useReducedMotion();

  return (
    <div className="min-h-dvh bg-surface-base text-text-primary">
      {/* ── Glass header ─────────────────────────────────────────────── */}
      <header className="sticky top-0 z-40 glass border-b border-border-subtle">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6">
          <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight">
            <span className="grid h-8 w-8 place-items-center rounded-md bg-accent/15 text-accent">
              <TrendingUp className="h-4 w-4" />
            </span>
            <span>Saakshya</span>
          </Link>
          <nav className="hidden items-center gap-6 text-sm text-text-secondary md:flex">
            <Link href="/market" className="hover:text-text-primary">Market</Link>
            <Link href="/scanners" className="hover:text-text-primary">Scanners</Link>
            <Link href="/sectors" className="hover:text-text-primary">Sectors</Link>
          </nav>
          <div className="flex items-center gap-2">
            <Link href="/login">
              <Button variant="ghost" className="min-h-[44px]">Log in</Button>
            </Link>
            <Link href="/signup">
              <Button className="min-h-[44px]">Start free</Button>
            </Link>
          </div>
        </div>
      </header>

      {/* ── Hero ─────────────────────────────────────────────────────── */}
      <section className="relative overflow-hidden">
        {/* 3D orb (motion) or static gradient (reduced motion) */}
        <div className="pointer-events-none absolute inset-0 -z-0" aria-hidden="true">
          {reduce ? (
            <div className="absolute right-[-10%] top-1/2 h-[40rem] w-[40rem] -translate-y-1/2 rounded-full bg-[radial-gradient(circle_at_center,rgba(91,141,239,0.28),rgba(154,123,255,0.12)_45%,transparent_70%)] blur-2xl" />
          ) : (
            <div className="absolute right-0 top-0 h-full w-full opacity-90 md:w-3/5 md:left-auto">
              <HeroCanvas />
            </div>
          )}
        </div>

        <div className="relative z-10 mx-auto grid max-w-7xl gap-10 px-4 py-24 sm:px-6 md:py-32">
          <motion.div
            initial="hidden"
            animate="visible"
            variants={staggerContainer(0.08, 0.05)}
            className="max-w-2xl"
          >
            <motion.div variants={fadeUp}>
              <span className="inline-flex items-center gap-2 rounded-full border border-border-subtle bg-surface-1/60 px-3 py-1 text-xs font-medium text-text-secondary">
                <span className="h-1.5 w-1.5 rounded-full bg-bullish" />
                EOD analytics for NSE / BSE · not investment advice
              </span>
            </motion.div>
            <motion.h1
              variants={fadeUp}
              className="mt-5 text-4xl font-bold leading-tight tracking-tight sm:text-5xl md:text-6xl"
            >
              The <span className="text-accent">evidence</span> behind every move.
            </motion.h1>
            <motion.p variants={fadeUp} className="mt-5 max-w-xl text-lg text-text-secondary">
              Saakshya surfaces technically strong setups, sector strength and risk across
              Indian equities — and uses AI to explain the data in plain language. Every
              output traces to visible evidence. You draw your own conclusions.
            </motion.p>
            <motion.div variants={fadeUp} className="mt-8 flex flex-wrap items-center gap-3">
              <Link href="/signup">
                <Button className="min-h-[44px] gap-2 px-5 text-base">
                  Start free <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
              <Link href="/scanners/momentum">
                <Button variant="outline" className="min-h-[44px] gap-2 px-5 text-base">
                  <ScanLine className="h-4 w-4" /> See a live scanner
                </Button>
              </Link>
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* ── Feature bands ────────────────────────────────────────────── */}
      <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-80px" }}
          variants={staggerContainer(0.08)}
          className="grid gap-5 md:grid-cols-3"
        >
          {FEATURES.map(({ Icon, title, body }) => (
            <motion.div key={title} variants={fadeUp}>
              <Card className="h-full p-6">
                <span className="grid h-10 w-10 place-items-center rounded-lg bg-accent/12 text-accent">
                  <Icon className="h-5 w-5" />
                </span>
                <h3 className="mt-4 text-lg font-semibold">{title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-text-secondary">{body}</p>
              </Card>
            </motion.div>
          ))}
        </motion.div>
      </section>

      {/* ── Scanner preview (descriptive, evidence-led) ──────────────── */}
      <section className="mx-auto max-w-7xl px-4 pb-16 sm:px-6">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-80px" }}
          variants={fadeUp}
        >
          <Card className="overflow-hidden">
            <div className="flex items-center justify-between border-b border-border-subtle p-5">
              <div className="flex items-center gap-2">
                <BarChart3 className="h-4 w-4 text-accent" />
                <span className="text-sm font-semibold">Momentum scanner — sample</span>
              </div>
              <span className="text-xs text-text-muted">score + reasons, never a buy call</span>
            </div>
            <ul className="divide-y divide-border-subtle">
              {SAMPLE_ROWS.map((r) => (
                <li key={r.symbol} className="flex items-center gap-4 p-4">
                  <span className="w-28 font-mono text-sm tabular-nums">{r.symbol}</span>
                  <ScoreBadge score={r.score} />
                  <span className="flex flex-wrap gap-2 text-xs text-text-secondary">
                    {r.reasons.map((reason) => (
                      <span
                        key={reason}
                        className="rounded-full border border-border-subtle px-2 py-0.5"
                      >
                        {reason}
                      </span>
                    ))}
                  </span>
                </li>
              ))}
            </ul>
          </Card>
        </motion.div>
      </section>

      {/* ── Closing CTA ──────────────────────────────────────────────── */}
      <section className="mx-auto max-w-7xl px-4 pb-20 sm:px-6">
        <Card className="flex flex-col items-center gap-5 bg-surface-1 p-10 text-center">
          <h2 className="max-w-xl text-2xl font-bold sm:text-3xl">
            Make better-informed decisions — backed by evidence you can trace.
          </h2>
          <div className="flex flex-wrap justify-center gap-3">
            <Link href="/signup">
              <Button className="min-h-[44px] gap-2 px-5 text-base">
                Create a free account <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
            <Link href="/market">
              <Button variant="ghost" className="min-h-[44px] px-5 text-base">
                Explore the market
              </Button>
            </Link>
          </div>
          <div className="w-full max-w-xl">
            <NotAdviceBanner />
          </div>
        </Card>
      </section>

      <footer className="border-t border-border-subtle py-8">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-3 px-4 text-xs text-text-muted sm:flex-row sm:px-6">
          <span>© {2026} Saakshya — evidence-first equity analytics. Not investment advice.</span>
          <div className="flex gap-4">
            <Link href="/market" className="hover:text-text-secondary">Market</Link>
            <Link href="/scanners" className="hover:text-text-secondary">Scanners</Link>
            <Link href="/login" className="hover:text-text-secondary">Log in</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
