"use client";
/* TradingView Lightweight Charts wrapper — docs/06 §8, docs/07 §2.3.
   Lazy, client-only, theme-token-driven, reduce-motion-aware.
   Plots ONLY API-supplied series — never computes values client-side. */

import * as React from "react";
import dynamic from "next/dynamic";
import { Skeleton } from "@/components/ui";

const CHART_HEIGHT = 360;

/* Actual chart implementation — only runs client-side */
const ChartImpl = dynamic(() => import("./PriceChartImpl"), {
  ssr: false,
  loading: () => <Skeleton className="w-full" style={{ height: CHART_HEIGHT }} />,
});

export interface OhlcBar {
  time: string;   /* YYYY-MM-DD */
  open: number;
  high: number;
  low:  number;
  close: number;
  volume?: number;
}

export interface PriceChartProps {
  bars: OhlcBar[];
  symbol?: string;
  sma20?: Array<{ time: string; value: number }>;
  sma50?: Array<{ time: string; value: number }>;
  sma200?: Array<{ time: string; value: number }>;
  className?: string;
}

export function PriceChart(props: PriceChartProps) {
  return (
    <div className={props.className} style={{ minHeight: CHART_HEIGHT }}>
      <ChartImpl {...props} />
    </div>
  );
}
