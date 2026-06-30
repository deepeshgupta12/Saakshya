"use client";
import * as React from "react";
import * as echarts from "echarts/core";
import { HeatmapChart, BarChart, LineChart } from "echarts/charts";
import {
  GridComponent, TooltipComponent, VisualMapComponent,
  TitleComponent, LegendComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import type { EChartsOption } from "echarts";

echarts.use([
  HeatmapChart, BarChart, LineChart,
  GridComponent, TooltipComponent, VisualMapComponent,
  TitleComponent, LegendComponent,
  CanvasRenderer,
]);

interface Props { option: EChartsOption; height?: number; className?: string; }

export default function EChartImpl({ option, height = 256, className }: Props) {
  const containerRef = React.useRef<HTMLDivElement>(null);
  const chartRef = React.useRef<echarts.ECharts | null>(null);

  React.useEffect(() => {
    if (!containerRef.current) return;
    const chart = echarts.init(containerRef.current, null, { renderer: "canvas" });
    chartRef.current = chart;
    chart.setOption(option);

    const ro = new ResizeObserver(() => chart.resize());
    ro.observe(containerRef.current);
    return () => { ro.disconnect(); chart.dispose(); };
  }, []);

  React.useEffect(() => {
    chartRef.current?.setOption(option, { notMerge: false });
  }, [option]);

  return <div ref={containerRef} className={className} style={{ width: "100%", height }} />;
}
