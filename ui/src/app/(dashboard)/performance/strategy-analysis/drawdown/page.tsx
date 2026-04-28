"use client"

import React from "react"
import { usePerformanceData } from "@/components/performance/use-performance-data"
import { Loader2 } from "lucide-react"
import { MetricConfig } from "@/components/performance/shared/metric-grid-3way"
import { PerformancePageLayout } from "@/components/performance/shared/performance-page-layout"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"

const drawdownMetrics: MetricConfig[] = [
  // --- Core Equity Drawdowns ---
  { label: "Core Equity Drawdowns", accessor: "", type: "group" as const },
  {
    label: "Max Strategy Drawdown",
    accessor: "max_drawdown_usd",
    format: (val: any) => val != null ? `$${val.toFixed(2)}` : "-",
    unit: "USD",
    description: "Deepest peak-to-valley decline in the equity curve."
  },
  {
    label: "Max Strategy Drawdown %",
    accessor: "max_drawdown_pct",
    format: (val: any) => val != null ? `${val.toFixed(2)}%` : "-",
    unit: "%",
    description: "Deepest percentage decline relative to running peak."
  },
  {
    label: "Avg Drawdown",
    accessor: "avg_drawdown_usd",
    format: (val: any) => val != null ? `$${val.toFixed(2)}` : "-",
    unit: "USD",
    description: "Average depth of drawdown periods."
  },
  {
    label: "Drawdown Dist. Max",
    accessor: "drawdown_distribution.max",
    format: (val: any) => val != null ? `$${val.toFixed(2)}` : "-",
    unit: "USD",
    description: "Maximum drawdown from distribution stats."
  },
  {
    label: "Drawdown Dist. Avg",
    accessor: "drawdown_distribution.avg",
    format: (val: any) => val != null ? `$${val.toFixed(2)}` : "-",
    unit: "USD",
    description: "Average drawdown from distribution stats."
  },

  // --- Drawdown Duration & Recovery ---
  { label: "Drawdown Duration & Recovery", accessor: "", type: "group" as const },
  {
    label: "Max Drawdown Duration",
    accessor: "max_drawdown_duration",
    format: (val: any) => val != null ? String(val) : "-",
    description: "Longest period spent in drawdown."
  },
  {
    label: "Avg Drawdown Duration",
    accessor: "avg_drawdown_duration",
    format: (val: any) => val != null ? String(val) : "-",
    description: "Average length of time spent in drawdown."
  },
  {
    label: "Recovery Factor",
    accessor: "recovery_factor",
    format: (val: any) => val != null ? val.toFixed(4) : "-",
    description: "Net profit relative to maximum drawdown."
  },
  {
    label: "Max Cons. DD Trades",
    accessor: "max_consecutive_drawdown_trades",
    description: "Maximum number of consecutive trades within a single strategy drawdown."
  },

  // --- Trade-Level Drawdowns ---
  { label: "Trade-Level Drawdowns", accessor: "", type: "group" as const },
  {
    label: "Max Close-to-Close DD",
    accessor: "max_close_to_close_drawdown",
    format: (val: any) => val != null ? `$${val.toFixed(2)}` : "-",
    unit: "USD",
    description: "Max drawdown using MFE/MAE excursions."
  },
  {
    label: "Max Close-to-Close DD %",
    accessor: "max_close_to_close_drawdown_pct",
    format: (val: any) => val != null ? `${val.toFixed(2)}%` : "-",
    unit: "%",
    description: "Percentage version of close-to-close drawdown."
  },
  {
    label: "Avg Trade Drawdown",
    accessor: "avg_trade_drawdown",
    format: (val: any) => val != null ? `$${val.toFixed(2)}` : "-",
    unit: "USD",
    description: "Mean depth of trade-level drawdowns."
  },
  {
    label: "Account Size Required",
    accessor: "account_size_required",
    format: (val: any) => val != null ? `$${val.toFixed(2)}` : "-",
    unit: "USD",
    description: "Capital required to withstand max close-to-close dips."
  },

  // --- Periodic & Time-Based Metrics ---
  { label: "Periodic & Time-Based Metrics", accessor: "", type: "group" as const },
  {
    label: "Avg Yearly Max Drawdown",
    accessor: "avg_yearly_max_drawdown",
    format: (val: any) => val != null ? `$${val.toFixed(2)}` : "-",
    unit: "USD",
    description: "Average of the maximum drawdowns for each year."
  },
  {
    label: "Max Strategy DD Date",
    accessor: "max_drawdown_date",
    format: (val: any) => val != null ? String(val).split('T')[0] : "-",
    description: "Timestamp of the deepest strategy valley."
  },
  {
    label: "Max Trade DD Date",
    accessor: "max_close_to_close_drawdown_date",
    format: (val: any) => val != null ? String(val).split('T')[0] : "-",
    description: "Timestamp of the deepest trade-level valley."
  },

  // --- Pain & Volatility Indices ---
  { label: "Pain & Volatility Indices", accessor: "", type: "group" as const },
  {
    label: "Ulcer Index",
    accessor: "ulcer_index",
    format: (val: any) => val != null ? val.toFixed(4) : "-",
    description: "Quadratic mean of percentage drawdowns (Square root of mean squared drawdown percentage)."
  },
  {
    label: "Pain Index",
    accessor: "pain_index",
    format: (val: any) => val != null ? val.toFixed(4) : "-",
    description: "Mean absolute percentage drawdown across the full period."
  },
  {
    label: "Pain Ratio",
    accessor: "pain_ratio",
    format: (val: any) => val != null ? val.toFixed(4) : "-",
    description: "Total return relative to the Pain Index."
  }
]

const drawdownConfig = {
  title: "Drawdown Analysis",
  description: "Detailed analysis of drawdown depth, duration, recovery, and pain indices.",
  metrics: drawdownMetrics,
  charts: []
}

export default function DrawdownPage() {
  const { analytics, loading, error, selectedBacktest } = usePerformanceData()

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

  // Merge drawdowns and ratios for the drawdown analysis page (needs recovery_factor)
  const drawdownData = {
    all: { ...(analytics?.drawdowns?.all || {}), ...(analytics?.ratios?.all || {}) },
    long: { ...(analytics?.drawdowns?.long || {}), ...(analytics?.ratios?.long || {}) },
    short: { ...(analytics?.drawdowns?.short || {}), ...(analytics?.ratios?.short || {}) },
  };

  return (
    <div className="space-y-6">
        <PerformancePageLayout
            config={drawdownConfig}
            data={{ metrics: drawdownData as any }}
        />
    </div>
  )
}
