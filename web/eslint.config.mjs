import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";
import { createRequire } from "module";

const require = createRequire(import.meta.url);
const noBlockedPhrases = require("./src/lib/eslint/no-blocked-phrases.js");

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  globalIgnores([
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    "node_modules/**",
  ]),
  {
    plugins: {
      /* Custom Saakshya compliance rules — docs/06 §13–§14, SPEC §6.9 */
      saakshya: { rules: { "no-blocked-phrases": noBlockedPhrases } },
    },
    rules: {
      "saakshya/no-blocked-phrases": "error",
    },
  },
]);

export default eslintConfig;
