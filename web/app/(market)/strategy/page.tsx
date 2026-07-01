import type { Metadata } from "next";
import { StrategyBuilderClient } from "./StrategyBuilderClient";

export const metadata: Metadata = {
  title: "Screener Builder — Saakshya",
  description: "Build custom stock screeners using conditions and natural language. Outputs lists, not recommendations.",
};

export default function StrategyPage() {
  return <StrategyBuilderClient />;
}
