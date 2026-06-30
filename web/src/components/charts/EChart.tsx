"use client";
/* ECharts wrapper — docs/06 §8, docs/07 §2.3.
   Client-only, lazy, theme-token-driven. */

import * as React from "react";
import dynamic from "next/dynamic";
import { Skeleton } from "@/components/ui";
import type { EChartsOption } from "echarts";

const EChartImpl = dynamic(() => import("./EChartImpl"), {
  ssr: false,
  loading: () => <Skeleton className="w-full h-64" />,
});

export interface EChartProps {
  option: EChartsOption;
  height?: number;
  className?: string;
}

export function EChart(props: EChartProps) {
  return (
    <div className={props.className} style={{ minHeight: props.height ?? 256 }}>
      <EChartImpl {...props} />
    </div>
  );
}
