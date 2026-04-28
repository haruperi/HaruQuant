"use client"

import React from "react"
import { usePerformanceData } from "@/components/performance/use-performance-data"
import { Loader2 } from "lucide-react"
import { MetricConfig } from "@/components/performance/shared/metric-grid-3way"
import { PerformancePageLayout } from "@/components/performance/shared/performance-page-layout"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"

const benchmarkMetrics: MetricConfig[] = [
  // --- Market Statistics (Alpha & Beta) ---
  { label: "Market Statistics (Alpha & Beta)", accessor: "", type: "group" as const },
  {
    label: "Alpha",
    accessor: "alpha",
    format: (val: any) => val != null ? `${val.toFixed(4)}%` : "-",
    unit: "%",
    description: "Jensen's Alpha. Risk-adjusted annualized excess return."
  },
  {
    label: "Beta",
    accessor: "beta",
    format: (val: any) => val != null ? val.toFixed(4) : "-",
    description: "Sensitivity of strategy returns to market movements."
  },
  {
    label: "R-Squared",
    accessor: "r_squared",
    format: (val: any) => val != null ? val.toFixed(4) : "-",
    description: "Proportion of strategy variance explained by the benchmark."
  },
  {
    label: "Tracking Error",
    accessor: "tracking_error",
    format: (val: any) => val != null ? `${val.toFixed(2)}%` : "-",
    unit: "%",
    description: "Annualized volatility of excess returns relative to benchmark."
  },

  // --- Relative Performance Analysis ---
  { label: "Relative Performance Analysis", accessor: "", type: "group" as const },
  {
    label: "Batting Average",
    accessor: "batting_average",
    format: (val: any) => val != null ? `${val.toFixed(2)}%` : "-",
    unit: "%",
    description: "Percentage of periods where the strategy outperformed the benchmark."
  },
  {
    label: "Up Capture Ratio",
    accessor: "up_capture",
    format: (val: any) => val != null ? `${val.toFixed(2)}%` : "-",
    unit: "%",
    description: "Strategy's performance percentage during rising benchmark periods."
  },
  {
    label: "Down Capture Ratio",
    accessor: "down_capture",
    format: (val: any) => val != null ? `${val.toFixed(2)}%` : "-",
    unit: "%",
    description: "Strategy's performance percentage during falling benchmark periods."
  },
  {
    label: "Max Relative Drawdown",
    accessor: "relative_drawdown",
    format: (val: any) => val != null ? `${val.toFixed(2)}%` : "-",
    unit: "%",
    description: "Maximum underperformance of strategy equity relative to benchmark equity."
  }
]

const benchmarkConfig = {
  title: "Benchmark Comparison",
  description: "Relative performance, market sensitivity, and benchmark comparisons.",
  metrics: benchmarkMetrics,
  charts: []
}

export default function BenchmarksPage() {
  const { analytics, loading, error, selectedBacktest } = usePerformanceData()

  if (!selectedBacktest) {
      return <div className="p-12 text-center text-slate-500">Please select a backtest based strategy.</div>
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

  // Gracefully handle missing benchmark data
  const benchmarkData = analytics?.benchmark || { all: {}, long: {}, short: {} };

  return (
    <div className="space-y-6">
        <PerformancePageLayout
            config={benchmarkConfig}
            data={{ metrics: benchmarkData as any }}
        />
    </div>
  )
}
