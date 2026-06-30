/* Blocked phrases — mirrored from backend app/ai/guardrails.py.
   Used by the custom ESLint rule to fail the build on advisory language.
   NEVER emit these in JSX string literals or user-facing copy. */

export const BLOCKED_PHRASES: readonly string[] = [
  "buy now",
  "sell now",
  "buy this",
  "sell this",
  "guaranteed",
  "assured",
  "confirmed target",
  "sure-shot",
  "sure shot",
  "risk-free",
  "risk free",
  "multibagger",
  "must invest",
  "best stock for you",
  "will definitely",
  "100% sure",
  "buy the breakout",
  "sell the breakdown",
  "entry point",
  "stop loss",
  "target price",
  "buy at",
  "sell at",
  "expected return",
  "assured return",
  "no risk",
  "make money",
  "profit guaranteed",
];
