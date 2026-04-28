"use client"

import React from "react"
import { usePerformanceData } from "@/components/performance/use-performance-data"
import { Loader2, Download } from "lucide-react"
import { Button } from "@/components/ui/button"
import { MetricConfig } from "@/components/performance/shared/metric-grid-3way"
import { PerformancePageLayout } from "@/components/performance/shared/performance-page-layout"

const ratioMetrics: MetricConfig[] = [
  // --- Classical Risk-Adjusted Ratios ---
  { label: "Classical Risk-Adjusted Ratios", accessor: "", type: "group" as const },
  {
    label: "Sharpe Ratio",
    accessor: "sharpe_ratio",
    format: (val: any) => val != null ? val.toFixed(2) : "-",
    description: "Excess return per unit of volatility."
  },
  {
    label: "Sortino Ratio",
    accessor: "sortino_ratio",
    format: (val: any) => val != null ? val.toFixed(2) : "-",
    description: "Excess return per unit of downside volatility."
  },
  {
    label: "Calmar Ratio",
    accessor: "calmar_ratio",
    format: (val: any) => val != null ? val.toFixed(2) : "-",
    description: "Compound Annual Growth Rate divided by Maximum Drawdown."
  },
  {
    label: "Information Ratio",
    accessor: "information_ratio",
    format: (val: any) => val != null ? val.toFixed(2) : "-",
    description: "Excess return per unit of tracking error relative to benchmark."
  },

  // --- Modern & Specialized Ratios ---
  { label: "Modern & Specialized Ratios", accessor: "", type: "group" as const },
  {
    label: "Fouse Ratio",
    accessor: "fouse_ratio",
    format: (val: any) => val != null ? val.toFixed(2) : "-",
    description: "Risk-adjusted return considering risk tolerance."
  },
  {
    label: "Upside Potential Ratio",
    accessor: "upside_potential_ratio",
    format: (val: any) => val != null ? val.toFixed(2) : "-",
    description: "Upside potential relative to downside risk."
  },
  {
    label: "Omega Ratio",
    accessor: "omega_ratio",
    format: (val: any) => val != null ? val.toFixed(2) : "-",
    description: "Probability-weighted ratio of gains vs losses."
  },
  {
    label: "Gain to Pain Ratio",
    accessor: "gain_to_pain_ratio",
    format: (val: any) => val != null ? val.toFixed(2) : "-",
    description: "Total returns relative to absolute negative returns."
  },
  {
    label: "Kappa Ratio",
    accessor: "kappa_ratio",
    format: (val: any) => val != null ? val.toFixed(2) : "-",
    description: "Generalization of Sortino using higher moments."
  },
  {
    label: "Sterling Ratio",
    accessor: "sterling_ratio",
    format: (val: any) => val != null ? val.toFixed(2) : "-",
    description: "CAGR relative to average yearly max drawdown."
  },
  {
    label: "RINA Index",
    accessor: "rina_index",
    format: (val: any) => val != null ? val.toFixed(2) : "-",
    description: "Select net profit relative to time-adjusted drawdown."
  },

  // --- Trade-Based Performance Ratios ---
  { label: "Trade-Based Performance Ratios", accessor: "", type: "group" as const },
  {
    label: "Profit Factor",
    accessor: "profit_factor",
    format: (val: any) => val != null ? val.toFixed(2) : "-",
    description: "Gross Profit / |Gross Loss|."
  },
  {
    label: "Payoff Ratio",
    accessor: "payoff_ratio",
    format: (val: any) => val != null ? val.toFixed(2) : "-",
    description: "|Avg Win| / |Avg Loss|."
  },
  {
    label: "Edge Ratio",
    accessor: "edge_ratio",
    format: (val: any) => val != null ? val.toFixed(2) : "-",
    description: "(Avg Win / |Avg Loss|) x Win Rate."
  },
  {
    label: "Profit to MAE Ratio",
    accessor: "profit_to_mae_ratio",
    format: (val: any) => val != null ? val.toFixed(2) : "-",
    description: "Efficiency of profit capture relative to adverse excursion."
  },
  {
    label: "MFE to MAE Ratio",
    accessor: "mfe_to_mae_ratio",
    format: (val: any) => val != null ? val.toFixed(2) : "-",
    description: "Favorable excursion vs adverse excursion."
  },
  {
    label: "Return Over Drawdown",
    accessor: "return_over_drawdown",
    format: (val: any) => val != null ? val.toFixed(2) : "-",
    description: "Total return / max trade drawdown."
  },
  {
    label: "Expectancy Over Std",
    accessor: "expectancy_over_std",
    format: (val: any) => val != null ? val.toFixed(2) : "-",
    description: "Stability of the trading edge."
  },

  // --- Net Profit Performance Relations ---
  { label: "Net Profit Performance Relations", accessor: "", type: "group" as const },
  {
    label: "Recovery Factor",
    accessor: "recovery_factor",
    format: (val: any) => val != null ? val.toFixed(2) : "-",
    description: "Net profit divided by maximum strategy drawdown depth."
  },
  {
    label: "Net Profit to Max DD",
    accessor: "net_profit_to_max_dd",
    format: (val: any) => val != null ? `${val.toFixed(2)}%` : "-",
    unit: "%",
    description: "Net profit as percent of max strategy drawdown."
  },

  // --- Advanced Profit Factors ---
  { label: "Advanced Profit Factors", accessor: "", type: "group" as const },
  {
    label: "Adjusted Profit Factor",
    accessor: "adjusted_profit_factor",
    format: (val: any) => val != null ? val.toFixed(2) : "-",
    description: "Adjusted Gross Profit / |Adjusted Gross Loss|."
  },
  {
    label: "Select Profit Factor",
    accessor: "select_profit_factor",
    format: (val: any) => val != null ? val.toFixed(2) : "-",
    description: "Select Gross Profit / |Select Gross Loss|."
  },

  // --- Expectancy & Edge ---
  { label: "Expectancy & Edge", accessor: "", type: "group" as const },
  {
    label: "Expectancy",
    accessor: "expectancy",
    format: (val: any) => val != null ? `$${val.toFixed(2)}` : "-",
    unit: "USD",
    description: "Expected value per trade."
  },
  {
    label: "Expectancy (R)",
    accessor: "expectancy_r",
    format: (val: any) => val != null ? `${val.toFixed(2)}R` : "-",
    description: "Expectancy in terms of R-multiples."
  },
]

const ratioConfig = {
  title: "Performance Ratios",
  description: "Comprehensive list of risk-adjusted return ratios and efficiency metrics.",
  metrics: ratioMetrics,
  charts: []
}

export default function PerformanceRatiosPage() {
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

  if (!analytics?.ratios) {
      return <div className="p-12 text-center text-slate-500">No data available.</div>
  }

  return (
    <PerformancePageLayout
        config={ratioConfig}
        data={{ metrics: analytics.ratios as any }}
    />
  )
}
