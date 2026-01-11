"use client"

import React from "react"
import { usePerformanceData } from "@/components/performance/use-performance-data"
import { PerformancePageLayout, PageConfig } from "@/components/performance/shared/performance-page-layout"
import { Loader2 } from "lucide-react"

const efficiencyConfig: PageConfig = {
  title: "Efficiency Analysis",
  description: "KPIs and metrics measuring capital usage, time efficiency, and execution quality.",
  metrics: [
      // Capital
      { label: "Capital Efficiency", accessor: "Capital Efficiency", format: (v) => (v != null) ? v.toFixed(3) : "-", description: "Return per unit of capital deployed." },
      { label: "Return per Unit Risk", accessor: "Return per Unit Risk", format: (v) => (v != null) ? v.toFixed(3) : "-", description: "Total Return divided by total MAE (Risk)." },
      { label: "Risk Adjusted Efficiency", accessor: "Risk Adjusted Efficiency", format: (v) => (v != null) ? v.toFixed(3) : "-", description: "Return per unit of initial risk taken." },

      // Time
      { label: "Time Efficiency", accessor: "Time Efficiency", format: (v) => (v != null) ? v.toFixed(3) : "-", unit: "$/hr", description: "Return per hour spent in the market." },
      { label: "Return per Unit Time", accessor: "Return per Unit Time", format: (v) => (v != null) ? v.toFixed(3) : "-", unit: "$/hr", description: "Return per hour of calendar time." },
      { label: "Return per Opportunity", accessor: "Return per Trade Opportunity", format: (v) => (v != null) ? `$${v.toFixed(2)}` : "-", unit: "$/day", description: "Average return per calendar day." },
      { label: "Trades per Day", accessor: "Trades per Day", format: (v) => (v != null) ? v.toFixed(2) : "-", unit: "Trades/Day" },

      // Execution
      { label: "MFE Efficiency", accessor: "MFE Efficiency", format: (v) => (v != null) ? `${(v * 100).toFixed(1)}%` : "-", unit: "%", description: "Percentage of potential profit (MFE) captured." },
      { label: "MAE Efficiency", accessor: "MAE Efficiency", format: (v) => (v != null) ? v.toFixed(3) : "-", description: "Ratio of Loss to MAE (Lower is better)." },
      { label: "Loss Containment", accessor: "Loss Containment Efficiency", format: (v) => (v != null) ? `${v.toFixed(1)}%` : "-", unit: "%", description: "Efficiency of limiting losses relative to MAE (Higher is better)." },
      { label: "Exit Efficiency", accessor: "Exit Efficiency", format: (v) => (v != null) ? `${(v * 100).toFixed(1)}%` : "-", unit: "%", description: "Overall quality of exits (combining MFE capture and MAE avoidance)." },

      { label: "Win Efficiency", accessor: "Win Efficiency", format: (v) => (v != null) ? `${v.toFixed(1)}%` : "-", unit: "%", description: "Percentage of maximum potential profit captured on winning trades." },

      { label: "Position Size Efficiency", accessor: "Position Size Efficiency", format: (v) => (v != null) ? v.toFixed(3) : "-", description: "Correlation between position size and P/L (1.0 = perfect alignment)." },

      { label: "Return per Trade", accessor: "Return per Trade", format: (v) => (v != null) ? `$${v.toFixed(2)}` : "-", unit: "USD" },
  ],
  charts: [
      {
          id: "size_vs_pnl",
          type: "scatter",
          title: "Position Size vs P/L",
          unit: "USD"
      }
  ]
}

export default function EfficiencyPage() {
  const { metrics, loading, error, selectedBacktest } = usePerformanceData()

  if (!selectedBacktest) {
    return <div className="p-8 text-center text-muted-foreground">Select a backtest to view efficiency analysis.</div>
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

  // Prepare chart data. MetricGrid expects `metrics.all` etc.
  // PerformancePageLayout -> SeriesChart3Way / DistributionPanel.
  // We need a SCATTER chart component.
  // `SeriesChart3Way` handles Lines.
  // `DistributionPanel3Way` handles Bars.
  // We don't have a shared Scatter component yet?
  // I will check `PerformancePageLayout`.
  // If it doesn't support scatter, I might have to add it or implement a custom chart here.
  // Given user asked for "Table + Graph", and `position_size_efficiency` returns correlation (Table).
  // The Graph is "Scatter: size vs profit_loss".

  // I'll check `performance-page-layout.tsx` capabilities next.
  // For now I create the page assuming I can hook it up.

  const pageData = {
    metrics: metrics,
    charts: metrics.all.chart_data || {}
  }

  return <PerformancePageLayout config={efficiencyConfig} data={pageData} />
}
