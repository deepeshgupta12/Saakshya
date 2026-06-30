/**
 * Custom ESLint rule: no-blocked-phrases
 * Fails the build if any JSX string literal contains advisory / blocked phrases.
 * docs/06 §13–§14, SPEC §6.9.
 */

const BLOCKED = [
  "buy now", "sell now", "buy this", "sell this",
  "guaranteed", "assured", "confirmed target", "sure-shot", "sure shot",
  "risk-free", "risk free", "multibagger", "must invest",
  "best stock for you", "will definitely", "100% sure",
  "buy the breakout", "sell the breakdown",
  "entry point", "stop loss", "target price",
  "buy at", "sell at", "expected return", "assured return",
  "no risk", "make money", "profit guaranteed",
];

/** @type {import("eslint").Rule.RuleModule} */
module.exports = {
  meta: {
    type: "problem",
    docs: {
      description: "Disallow advisory/blocked phrases in JSX string literals (SPEC §6.9)",
    },
    schema: [],
    messages: {
      blocked: "Blocked phrase \"{{phrase}}\" found. Remove advisory/directional language (SPEC §6.9).",
    },
  },
  create(context) {
    function checkText(text, node) {
      const lower = text.toLowerCase();
      for (const phrase of BLOCKED) {
        if (lower.includes(phrase)) {
          context.report({ node, messageId: "blocked", data: { phrase } });
          return;
        }
      }
    }

    return {
      /* JSX text nodes */
      JSXText(node) {
        checkText(node.value, node);
      },
      /* String literals and template literals in JSX attribute values */
      JSXAttribute(node) {
        const val = node.value;
        if (!val) return;
        if (val.type === "StringLiteral" || val.type === "Literal") {
          checkText(String(val.value), node);
        }
        if (val.type === "JSXExpressionContainer") {
          const expr = val.expression;
          if (expr.type === "Literal") checkText(String(expr.value), node);
          if (expr.type === "TemplateLiteral") {
            expr.quasis?.forEach((q) => checkText(q.value.raw, node));
          }
        }
      },
    };
  },
};
