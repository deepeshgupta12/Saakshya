"use client";
/* Actual TradingView Lightweight Charts v5 implementation.
   Only imported client-side via dynamic(). v5 uses chart.addSeries(Series) API. */

import * as React from "react";
import {
  createChart,
  ColorType,
  CrosshairMode,
  CandlestickSeries,
  HistogramSeries,
  LineSeries,
  type IChartApi,
} from "lightweight-charts";
import { useReducedMotion } from "framer-motion";
import type { PriceChartProps } from "./PriceChart";

const CHART_HEIGHT = 360;

export default function PriceChartImpl({ bars, sma20, sma50, sma200 }: PriceChartProps) {
  const containerRef = React.useRef<HTMLDivElement>(null);
  const chartRef = React.useRef<IChartApi | null>(null);
  const reduced = useReducedMotion();

  function cssVar(name: string): string {
    if (typeof window === "undefined") return "";
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }

  React.useEffect(() => {
    if (!containerRef.current || !bars.length) return;

    const chart = createChart(containerRef.current, {
      width:  containerRef.current.clientWidth,
      height: CHART_HEIGHT,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: cssVar("--text-muted") || "#6B7C99",
      },
      grid: {
        vertLines: { color: "rgba(255,255,255,0.04)" },
        horzLines: { color: "rgba(255,255,255,0.04)" },
      },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: "rgba(255,255,255,0.08)" },
      timeScale:       { borderColor: "rgba(255,255,255,0.08)", timeVisible: true },
    });
    chartRef.current = chart;

    /* Candlestick series — v5 API: chart.addSeries(CandlestickSeries, options) */
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor:        cssVar("--bullish") || "#2FBF71",
      downColor:      cssVar("--bearish") || "#E5484D",
      borderUpColor:  cssVar("--bullish") || "#2FBF71",
      borderDownColor:cssVar("--bearish") || "#E5484D",
      wickUpColor:    cssVar("--bullish") || "#2FBF71",
      wickDownColor:  cssVar("--bearish") || "#E5484D",
    });

    const validBars = bars.filter((b) => b.open && b.high && b.low && b.close);
    candleSeries.setData(validBars.map((b) => ({
      time:  b.time as import("lightweight-charts").Time,
      open:  b.open,
      high:  b.high,
      low:   b.low,
      close: b.close,
    })));

    /* Volume series */
    const volSeries = chart.addSeries(HistogramSeries, {
      color:       "rgba(91,141,239,0.3)",
      priceScaleId:"volume",
    });
    chart.priceScale("volume").applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
    const validVol = bars.filter((b) => b.volume != null);
    if (validVol.length) {
      volSeries.setData(validVol.map((b) => ({
        time:  b.time as import("lightweight-charts").Time,
        value: b.volume!,
        color: (b.close ?? 0) >= (b.open ?? 0) ? "rgba(47,191,113,0.3)" : "rgba(229,72,77,0.3)",
      })));
    }

    /* MA overlays */
    const maColors = {
      sma20:  cssVar("--accent")  || "#5B8DEF",
      sma50:  cssVar("--warning") || "#E8A33D",
      sma200: cssVar("--ai")      || "#9A7BFF",
    };

    function addMa(data: typeof sma20, color: string) {
      if (!data?.length) return;
      const s = chart.addSeries(LineSeries, { color, lineWidth: 1, priceLineVisible: false });
      s.setData(data.map((d) => ({ time: d.time as import("lightweight-charts").Time, value: d.value })));
    }

    addMa(sma20,  maColors.sma20);
    addMa(sma50,  maColors.sma50);
    addMa(sma200, maColors.sma200);

    chart.timeScale().fitContent();

    const ro = new ResizeObserver(() => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    });
    if (containerRef.current) ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bars, sma20, sma50, sma200, reduced]);

  return <div ref={containerRef} className="w-full" style={{ height: CHART_HEIGHT }} />;
}
