"use client";
/* Shared Framer Motion variants — docs/07 §3.
   ALL animated components import from here for consistent timing/easing
   and guaranteed reduce-motion compliance.

   Physics: "Modern Dark Cinema" style — expo-out enters (snappy, premium feel),
   spring drawers (physical, interruptible), exits faster than enters. */

import { useReducedMotion } from "framer-motion";

/* ── Easing curves (matching ui-ux-pro-max "Modern Dark Cinema") ── */
export const ease = {
  /* Expo-out: fast settle, premium feel — use for all enters */
  expOut:   [0.16, 1, 0.3, 1] as const,
  /* Standard exit: fast leave */
  exit:     [0.4, 0, 1, 1] as const,
  /* Emphasis: reveals, count-ups */
  emphasis: [0.2, 0.8, 0.2, 1] as const,
  /* Standard Material enter (fallback) */
  standard: [0.2, 0, 0, 1] as const,
} as const;

/* ── Spring configs ── */
export const spring = {
  /* Snappy — buttons, chips, scale press */
  snappy: { type: "spring" as const, damping: 28, stiffness: 400, mass: 0.7 },
  /* Drawer — physical slide, gentle overshoot */
  drawer: { type: "spring" as const, damping: 32, stiffness: 300, mass: 0.85 },
  /* Tile — heatmap scale-in, stagger */
  tile:   { type: "spring" as const, damping: 24, stiffness: 260, mass: 0.8 },
} as const;

/* ── Duration tokens (seconds) ── */
export const duration = {
  fast: 0.12,   /* hover, press, chip toggle */
  base: 0.2,    /* most enter/exits */
  slow: 0.32,   /* drawers, sheets, page transitions */
} as const;

/* ── Fade + slide up — page transitions, card reveals ── */
export const fadeUp = {
  hidden:  { opacity: 0, y: 10 },
  visible: {
    opacity: 1, y: 0,
    transition: { duration: duration.base, ease: ease.expOut },
  },
  exit: {
    opacity: 0, y: -4,
    /* Exit ~65% of enter — feels responsive */
    transition: { duration: duration.fast, ease: ease.exit },
  },
};

/* ── Stagger container — wraps rows/tiles ── */
export const staggerContainer = (staggerChildren = 0.03, delayChildren = 0) => ({
  hidden:  { opacity: 1 },
  visible: { opacity: 1, transition: { staggerChildren, delayChildren } },
});

/* ── Stagger row — individual table row / list item ── */
export const staggerRow = {
  hidden:  { opacity: 0, y: 8 },
  visible: {
    opacity: 1, y: 0,
    transition: { duration: duration.base, ease: ease.expOut },
  },
};

/* ── Stagger tile — heatmap tile, bento card ── */
export const staggerTile = {
  hidden:  { opacity: 0, scale: 0.94 },
  visible: {
    opacity: 1, scale: 1,
    transition: spring.tile,
  },
};

/* ── Drawer slide from right — desktop evidence drawer ── */
export const drawerSlideRight = {
  hidden:  { opacity: 0, x: "100%" },
  visible: {
    opacity: 1, x: 0,
    transition: spring.drawer,
  },
  exit: {
    opacity: 0, x: "100%",
    transition: { duration: duration.base, ease: ease.exit },
  },
};

/* ── Drawer slide from bottom — mobile sheet ── */
export const drawerSlideUp = {
  hidden:  { opacity: 0, y: "100%" },
  visible: {
    opacity: 1, y: 0,
    transition: spring.drawer,
  },
  exit: {
    opacity: 0, y: "100%",
    transition: { duration: duration.base, ease: ease.exit },
  },
};

/* ── Scrim fade — drawer/modal backdrop ── */
export const scrimFade = {
  hidden:  { opacity: 0 },
  visible: { opacity: 1, transition: { duration: duration.fast } },
  exit:    { opacity: 0, transition: { duration: duration.fast, ease: ease.exit } },
};

/* ── AI card reveal — single block fade, no typewriter ── */
export const aiReveal = {
  hidden:  { opacity: 0, y: 6 },
  visible: {
    opacity: 1, y: 0,
    transition: { duration: duration.slow, ease: ease.emphasis },
  },
};

/* ── Risk pulse — one-shot amber glow, never loops ── */
export const riskPulse = {
  initial: { boxShadow: "none" },
  pulse: {
    boxShadow: "var(--glow-risk)",
    transition: { duration: 0.8, ease: ease.exit, repeat: 0 },
  },
};

/* ── Scale press feedback — tappable cards/buttons ── */
export const scaleTap = {
  whileTap: { scale: 0.97 },
  transition: spring.snappy,
};

/* ── Score count-up spring — used once on mount ── */
export const countUpTransition = { duration: 0.6, ease: ease.emphasis };

/**
 * Hook: returns whether reduce-motion is active.
 * Usage: const { reduced } = useMotion();
 *        animate={reduced ? "visible" : undefined}
 */
export function useMotion() {
  const reduced = useReducedMotion();
  return { reduced: !!reduced };
}
