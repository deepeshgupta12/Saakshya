/* Sector dashboard — /sectors (docs/08 §6). Descriptive sector rankings. */

import type { Metadata } from "next";
import { SectorsClient } from "./SectorsClient";
import { NotAdviceBanner } from "@/components/compliance";

export const metadata: Metadata = {
  title: "Sectors — Saakshya",
  description: "Sector strength rankings and momentum overview for NSE/BSE equity sectors. Not investment advice.",
};

export const revalidate = 28800;

export default function SectorsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-xl font-bold text-[--text-primary]">Sectors</h1>
          <p className="text-sm text-[--text-muted] mt-1">Strength and momentum rankings — descriptive analytics only</p>
        </div>
        <NotAdviceBanner className="hidden sm:flex max-w-sm shrink-0" />
      </div>
      <SectorsClient />
    </div>
  );
}
