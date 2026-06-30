/* Sector detail — /sectors/[slug] (docs/08 §6). Constituents + breadth. */

import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { SectorDetailClient } from "./SectorDetailClient";
import { NotAdviceBanner } from "@/components/compliance";

type Props = { params: Promise<{ slug: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  return {
    title: `${slug} Sector — Saakshya`,
    description: `Sector-level analytics for ${slug}. Breadth, constituents, descriptive momentum. Not investment advice.`,
  };
}

export default async function SectorDetailPage({ params }: Props) {
  const { slug } = await params;
  if (!slug) notFound();
  return (
    <div className="space-y-6">
      <NotAdviceBanner />
      <SectorDetailClient slug={slug} />
    </div>
  );
}
