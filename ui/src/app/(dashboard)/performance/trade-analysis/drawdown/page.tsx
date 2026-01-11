"use client"

import React from "react"
import { usePerformanceData } from "@/components/performance/use-performance-data"
import { PerformancePageLayout, PageConfig } from "@/components/performance/shared/performance-page-layout"
import { Loader2 } from "lucide-react"

const drawdownConfig: PageConfig = {
  title: "Drawdown",
  description: "Detailed analysis of drawdown depth, duration, and recovery.",
  metrics: [
    // Drawdowns & Recovery group
    { label: "Max Strategy Drawdown", accessor: "Max Strategy Drawdown", format: (v) => (v != null) ? `$${v.toFixed(2)}` : "-", unit: "USD", description: "Deepest peak-to-valley decline in account equity." },
    { label: "Max Strategy Drawdown %", accessor: "Max Strategy Drawdown (%)", format: (v) => (v != null) ? `${v.toFixed(2)}%` : "-", unit: "%", description: "Maximum percentage decline from peak equity." },
    { label: "Max Strategy Drawdown Date", accessor: "Max Strategy Drawdown Date", description: "Date when the maximum strategy drawdown occurred." },
    { label: "Avg Drawdown", accessor: "Avg Drawdown", format: (v) => (v != null) ? `$${v.toFixed(2)}` : "-", unit: "USD", description: "Average depth of all drawdowns." },
    { label: "Avg Yearly Max Drawdown", accessor: "Avg Yearly Max Drawdown", format: (v) => (v != null) ? `$${v.toFixed(2)}` : "-", unit: "USD", description: "Average of the maximum drawdowns experienced each year." },

    { label: "Max Drawdown Duration", accessor: "Max Drawdown Duration", unit: "Bars", description: "Maximum number of periods the strategy was in drawdown." },
    { label: "Avg Drawdown Duration", accessor: "Avg Drawdown Duration", format: (v) => (v != null) ? v.toFixed(2) : "-", unit: "Bars", description: "Average length of time (in bars) spent in drawdown." },
    { label: "Max Time to Recovery", accessor: "Max Time to Recovery", unit: "Bars", description: "Longest time taken to recover from a drawdown to a new equity high." },

    { label: "Ulcer Index", accessor: "Ulcer Index", format: (v) => (v != null) ? v.toFixed(2) : "-", description: "Measure of downside risk (depth and duration of drawdowns)." },
    { label: "Pain Index", accessor: "Pain Index", format: (v) => (v != null) ? v.toFixed(2) : "-", description: "Quantifies the capital loss felt by the investor." },
    { label: "Pain Ratio", accessor: "Pain Ratio", format: (v) => (v != null) ? v.toFixed(2) : "-", description: "Return per unit of 'pain' (drawdown risk)." },

    { label: "Avg Trade Drawdown", accessor: "Avg Trade Drawdown", format: (v) => (v != null) ? `$${v.toFixed(2)}` : "-", unit: "USD", description: "Average drawdown experienced during individual trades." },

    { label: "Max Trade Drawdown", accessor: "Max Close To Close Drawdown", format: (v) => (v != null) ? `$${v.toFixed(2)}` : "-", unit: "USD", description: "Maximum drawdown calculated on a close-to-close basis." },
    { label: "Max Trade Drawdown %", accessor: "Max Close To Close Drawdown (%)", format: (v) => (v != null) ? `${v.toFixed(2)}%` : "-", unit: "%", description: "Max close-to-close drawdown as a percentage." },
    { label: "Max Trade Drawdown Date", accessor: "Max Close To Close Drawdown Date", description: "Date of the maximum close-to-close drawdown." },

    { label: "Account Size Required", accessor: "Account Size Required", format: (v) => (v != null) ? `$${v.toFixed(2)}` : "-", unit: "USD", description: "Minimum capital required to survive the historical drawdowns." },
  ],
  charts: [
    {
      id: "drawdown_series",
      type: "series",
      title: "Drawdown Series",
      valueFormatter: (v) => `$${v.toFixed(2)}`,
    },
    {
      id: "drawdown_duration",
      type: "series",
      title: "Drawdown Duration Series",
      valueFormatter: (v) => `${v} bars`,
    },
    {
      id: "drawdown_distribution",
      type: "distribution",
      title: "Drawdown Distribution",
      unit: "USD"
    },
    {
      id: "trade_level_drawdowns",
      type: "series",
      title: "Trade Level Drawdowns",
      valueFormatter: (v) => `$${v.toFixed(2)}`,
    }
  ]
}

export default function Page() {
  const { metrics, loading, error, selectedBacktest } = usePerformanceData()

  if (!selectedBacktest) {
    return <div className="p-8 text-center text-muted-foreground">Select a backtest to view performance.</div>
  }

  if (loading) {
    return (
      <div className="flex h-[400px] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (error) {
    return <div className="p-8 text-red-500">Error: {error}</div>
  }

  if (!metrics) {
      return null
  }

  // Helper to merge 3 data arrays by date for Charts
  // Similar to overview page logic
  const mergeChartData = (chartKey: string, valKey: string, all: any, long: any, short: any) => {
      const map = new Map<string, { date: string, all?: number, long?: number, short?: number }>()

      const addToMap = (sourceMetrics: any, type: "all" | "long" | "short") => {
          if (sourceMetrics?.chart_data?.[chartKey]) {
              sourceMetrics.chart_data[chartKey].forEach((pt: any) => {
                  const date = pt.date.split(" ")[0]
                  if (!map.has(date)) {
                      map.set(date, { date })
                  }
                  const entry = map.get(date)!
                  entry[type] = pt[valKey]
              })
          }
      }

      addToMap(all, "all")
      addToMap(long, "long")
      addToMap(short, "short")

      const sorted = Array.from(map.values()).sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())

      // Forward fill?
      // For drawdown duration/series, forward fill makes sense if dates are missing for one side but present for others
      // But typically dates should align if derived from equity curve which has filled dates.
      // Trade level drawdowns might be sparse. Sparse lines in Recharts might be disconnected if connectNulls={false},
      // but SeriesChart3Way has connectNulls={true} (implied or default usually, let's assume fine).

      return sorted
  }

  // Helper to extract values array for Distribution
  const extractDistributionValues = (chartKey: string, valKey: string, metricsObj: any) => {
      if (!metricsObj?.chart_data?.[chartKey]) return []
      return metricsObj.chart_data[chartKey].map((pt: any) => pt[valKey])
  }

  // 1. Drawdown Series (Graph)
  const drawdownSeriesData = mergeChartData("drawdown_series", "drawdown", metrics.all, metrics.long, metrics.short)

  // 2. Drawdown Duration Series (Graph)
  const durationSeriesData = mergeChartData("drawdown_duration", "duration", metrics.all, metrics.long, metrics.short)

  // 3. Trade Level Drawdowns (Graph)
  const tradeDrawdownData = mergeChartData("trade_level_drawdowns", "drawdown", metrics.all, metrics.long, metrics.short)

  // 4. Drawdown Distribution (Graph + Table)
  // We feed raw values arrays to distribution panel
  const distributionData = {
      all: extractDistributionValues("drawdown_series", "drawdown", metrics.all),
      long: extractDistributionValues("drawdown_series", "drawdown", metrics.long),
      short: extractDistributionValues("drawdown_series", "drawdown", metrics.short)
  }

  const pageData = {
    metrics: metrics,
    charts: {
      drawdown_series: drawdownSeriesData,
      drawdown_duration: durationSeriesData,
      trade_level_drawdowns: tradeDrawdownData,
      drawdown_distribution: distributionData
    }
  }

  return <PerformancePageLayout config={drawdownConfig} data={pageData} />
}
