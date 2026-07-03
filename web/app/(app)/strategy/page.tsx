import type { Metadata } from "next";
import { StrategyBuilderClient } from "./StrategyBuilderClient";
import { NotAdviceBanner } from "@/components/compliance";

export const metadata: Metadata = {
  title: "Screener Builder — Saakshya",
  description: "Build custom stock screeners using conditions and natural language. Outputs lists, not recommendations.",
};

export default function StrategyPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-xl font-bold text-(--text-primary)">Screener Builder</h1>
          <p className="text-sm text-(--text-muted) mt-1">
            Build screeners that produce a list of matching stocks — never buy/sell calls.
          </p>
        </div>
        <NotAdviceBanner className="hidden sm:flex max-w-sm shrink-0" />
      </div>
      <StrategyBuilderClient />
    </div>
  );
}
