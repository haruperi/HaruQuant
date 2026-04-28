"use client"

import React from "react"
import { usePerformanceData } from "@/components/performance/use-performance-data"
import { Loader2, Download } from "lucide-react"
import { Button } from "@/components/ui/button"
import { MetricConfig } from "@/components/performance/shared/metric-grid-3way"
import { PerformancePageLayout } from "@/components/performance/shared/performance-page-layout"

const riskMetrics: MetricConfig[] = [
  // --- Volatility Metrics ---
  { label: "Volatility Metrics", accessor: "", type: "group" as const },
  {
    label: "Volatility",
    accessor: "volatility",
    format: (val: any) => val != null ? `${val.toFixed(2)}%` : "-",
    unit: "%",
    description: "Standard deviation of returns."
  },
  {
    label: "Annualized Volatility",
    accessor: "annualized_volatility",
    format: (val: any) => val != null ? `${val.toFixed(2)}%` : "-",
    unit: "%",
    description: "Volatility scaled to yearly terms."
  },
  {
    label: "Downside Volatility",
    accessor: "downside_volatility_risk", // Note: mapped to 'downside_volatility_risk' from backend overview.py
    format: (val: any) => val != null ? `${val.toFixed(2)}%` : "-",
    unit: "%",
    description: "Standard deviation of negative returns (semi-deviation)."
  },

  // --- Tail Risk & Loss Thresholds ---
  { label: "Tail Risk & Loss Thresholds", accessor: "", type: "group" as const },
  {
    label: "Value at Risk (95%)",
    accessor: "value_at_risk_95",
    format: (val: any) => val != null ? `${val.toFixed(2)}%` : "-",
    unit: "%",
    description: "Maximum expected loss at a 95% confidence level."
  },
  {
    label: "Expected Shortfall (95%)",
    accessor: "expected_shortfall_95",
    format: (val: any) => val != null ? `${val.toFixed(2)}%` : "-",
    unit: "%",
    description: "Average loss beyond the VaR threshold (also known as CVaR)."
  },
  {
    label: "Max Loss Probability",
    accessor: "max_loss_probability",
    format: (val: any) => val != null ? `${val.toFixed(2)}%` : "-",
    unit: "%",
    description: "Probability of a single trade loss exceeding a threshold (-5.0 default)."
  },
  {
    label: "Drawdown Probability (>10%)",
    accessor: "drawdown_probability_10pct",
    format: (val: any) => val != null ? `${val.toFixed(2)}%` : "-",
    unit: "%",
    description: "Probability of equity drawdown exceeding 10%."
  },

  // --- Capital Risk & Ruin ---
  { label: "Capital Risk & Ruin", accessor: "", type: "group" as const },
  {
    label: "Risk of Ruin",
    accessor: "risk_of_ruin",
    format: (val: any) => val != null ? `${val.toFixed(2)}%` : "-",
    unit: "%",
    description: "Monte Carlo simulation to estimate the probability of hitting a 50% drawdown ruin threshold."
  },

  // --- Market Exposure ---
  { label: "Market Exposure", accessor: "", type: "group" as const },
  {
    label: "Max Exposure",
    accessor: "max_exposure",
    format: (val: any) => val != null ? `$${val.toLocaleString()}` : "-",
    unit: "USD",
    description: "Maximum capital allocated to open positions (simplified scaling)."
  },
  {
    label: "Avg Exposure",
    accessor: "avg_exposure",
    format: (val: any) => val != null ? `$${val.toLocaleString(undefined, {maximumFractionDigits: 2})}` : "-",
    unit: "USD",
    description: "Average capital exposure over time."
  },
  {
    label: "Exposure Time Ratio",
    accessor: "exposure_time_ratio",
    format: (val: any) => val != null ? `${val.toFixed(2)}%` : "-",
    unit: "%",
    description: "Percentage of the total period spent in the market."
  },
  {
    label: "Max Gross Exposure",
    accessor: "max_gross_exposure",
    format: (val: any) => val != null ? `$${val.toLocaleString()}` : "-",
    unit: "USD",
    description: "Highest combined value of all open positions."
  },

  // --- Downside Pain ---
  { label: "Downside Pain", accessor: "", type: "group" as const },
  {
    label: "Ulcer Index",
    accessor: "ulcer_index",
    format: (val: any) => val != null ? val.toFixed(2) : "-",
    description: "Measures the depth and duration of drawdowns. Lower is better."
  },
]

const riskConfig = {
  title: "Risk Analysis",
  description: "Volatility, tail risk, and capital risk metrics.",
  metrics: riskMetrics,
  charts: []
}

export default function RiskPage() {
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

  if (!analytics?.risks) {
      return null
  }

  const riskData = {
    all: { ...(analytics?.risks?.all || {}), ulcer_index: analytics?.drawdowns?.all?.ulcer_index },
    long: { ...(analytics?.risks?.long || {}), ulcer_index: analytics?.drawdowns?.long?.ulcer_index },
    short: { ...(analytics?.risks?.short || {}), ulcer_index: analytics?.drawdowns?.short?.ulcer_index },
  };

  return (
    <PerformancePageLayout
        config={riskConfig}
        data={{ metrics: riskData as any }}
    />
  )
}
