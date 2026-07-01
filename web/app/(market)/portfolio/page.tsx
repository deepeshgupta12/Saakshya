import type { Metadata } from "next";
import { PortfolioClient } from "./PortfolioClient";

export const metadata: Metadata = {
  title: "Portfolio — Saakshya",
  description: "Track holdings, P&L, sector allocation, and portfolio health.",
};

export default function PortfolioPage() {
  return <PortfolioClient portfolioId="default" />;
}
