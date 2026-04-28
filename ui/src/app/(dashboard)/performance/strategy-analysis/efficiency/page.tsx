"use client"

import React from "react"
import { usePerformanceData } from "@/components/performance/use-performance-data"
import { Loader2 } from "lucide-react"
import { MetricConfig } from "@/components/performance/shared/metric-grid-3way"
import { PerformancePageLayout } from "@/components/performance/shared/performance-page-layout"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"

const efficiencyMetrics: MetricConfig[] = [
  // --- Capital Efficiency ---
  { label: "Capital Efficiency", accessor: "", type: "group" as const },
  {
    label: "Capital Efficiency",
    accessor: "capital_efficiency",
    format: (val: any) => val != null ? val.toFixed(4) : "-",
    description: "Return per unit of capital deployed."
  },
  {
    label: "Return per Unit Risk",
    accessor: "return_per_unit_risk",
    format: (val: any) => val != null ? val.toFixed(4) : "-",
    description: "Return per unit of adverse movement (MAE)."
  },
  {
    label: "Risk Adjusted Efficiency",
    accessor: "risk_adjusted_efficiency",
    format: (val: any) => val != null ? val.toFixed(4) : "-",
    description: "Return per unit of initial risk defined at entry."
  },
  {
    label: "Return per R-Risk",
    accessor: "return_per_r_risk",
    format: (val: any) => val != null ? val.toFixed(4) : "-",
    description: "Net profit divided by the sum of R-multiple risk units."
  },
  {
    label: "Avg Notional Efficiency",
    accessor: "avg_trade_notional_efficiency",
    format: (val: any) => val != null ? val.toFixed(4) : "-",
    description: "Profit per unit of capital committed (weighted average)."
  },

  // --- Time & Frequency Efficiency ---
  { label: "Time & Frequency Efficiency", accessor: "", type: "group" as const },
  {
    label: "Time Efficiency",
    accessor: "time_efficiency",
    format: (val: any) => val != null ? `$${val.toFixed(2)}/hr` : "-",
    unit: "$/hr",
    description: "Return per hour spent actively in market."
  },
  {
    label: "Return per Unit Time",
    accessor: "return_per_unit_time",
    format: (val: any) => val != null ? `$${val.toFixed(2)}/hr` : "-",
    unit: "$/hr",
    description: "Return per hour of total calendar time (start to end)."
  },
  {
    label: "Trades per Day",
    accessor: "trades_per_day",
    format: (val: any) => val != null ? val.toFixed(2) : "-",
    description: "Average number of trade executions per calendar day."
  },
  {
    label: "Return per Opportunity",
    accessor: "return_per_trade_opportunity",
    format: (val: any) => val != null ? `$${val.toFixed(2)}/day` : "-",
    unit: "$/day",
    description: "Return per calendar day from start to end."
  },
  {
    label: "Return per Trade",
    accessor: "return_per_trade",
    format: (val: any) => val != null ? `$${val.toFixed(2)}` : "-",
    unit: "USD",
    description: "Average arithmetic mean profit per closed trade."
  },

  // --- Execution & Capturing Efficiency ---
  { label: "Execution & Capturing Efficiency", accessor: "", type: "group" as const },
  {
    label: "MFE Efficiency",
    accessor: "mfe_efficiency",
    format: (val: any) => val != null ? `${(val * 100).toFixed(2)}%` : "-",
    unit: "%",
    description: "Mean ratio of realized profit to maximum favorable excursion (winners)."
  },
  {
    label: "MAE Efficiency",
    accessor: "mae_efficiency",
    format: (val: any) => val != null ? `${(val * 100).toFixed(2)}%` : "-",
    unit: "%",
    description: "Mean ratio of realized loss to maximum adverse excursion (losers)."
  },
  {
    label: "Exit Efficiency",
    accessor: "exit_efficiency",
    format: (val: any) => val != null ? `${(val * 100).toFixed(2)}%` : "-",
    unit: "%",
    description: "Combined capture efficiency across both winners and losers."
  },
  {
    label: "Win Efficiency",
    accessor: "win_efficiency",
    format: (val: any) => val != null ? `${val.toFixed(2)}%` : "-",
    unit: "%",
    description: "Aggregate percentage of cumulative MFE captured as profit."
  },
    {
    label: "Loss Containment Efficiency",
    accessor: "loss_containment_efficiency",
    format: (val: any) => val != null ? `${val.toFixed(2)}%` : "-",
    unit: "%",
    description: "Measure of how well realized losses were contained above the valley (MAE)."
  },
  {
    label: "Profit per Pip Risk",
    accessor: "profit_per_pip_risk",
    format: (val: any) => val != null ? val.toFixed(4) : "-",
    description: "Reward-to-risk based on price movement efficiency (Pips)."
  },

  // --- Sizing Efficiency ---
  { label: "Sizing Efficiency", accessor: "", type: "group" as const },
  {
    label: "Position Size Efficiency",
    accessor: "position_size_efficiency",
    format: (val: any) => val != null ? val.toFixed(4) : "-",
    description: "Correlation between trade position size and trade profit outcome."
  }
]

const efficiencyConfig = {
  title: "Efficiency Analysis",
  description: "Capital and time efficiency, execution capture, and sizing metrics.",
  metrics: efficiencyMetrics,
  charts: []
}

export default function EfficiencyPage() {
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

  const efficiencyData = analytics?.efficiency || { all: {}, long: {}, short: {} };

  return (
    <div className="space-y-6">
        <PerformancePageLayout
            config={efficiencyConfig}
            data={{ metrics: efficiencyData as any }}
        />
    </div>
  )
}
