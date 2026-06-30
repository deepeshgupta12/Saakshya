/* Scanner directory — /scanners (docs/08 §3). Lists all scanners with counts. */

import type { Metadata } from "next";
import { ScannerDirectoryClient } from "./ScannerDirectoryClient";

export const metadata: Metadata = {
  title: "Scanners — Saakshya",
  description: "Browse all equity scanners: momentum, volume breakout, RSI, moving average. Evidence-based results, not picks.",
};

export const revalidate = 28800;

export default function ScannersPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-[--text-primary]">Scanners</h1>
        <p className="text-sm text-[--text-muted] mt-1">
          Scan results identify stocks that meet specific evidence-based criteria — not recommendations.
        </p>
      </div>
      <ScannerDirectoryClient />
    </div>
  );
}
