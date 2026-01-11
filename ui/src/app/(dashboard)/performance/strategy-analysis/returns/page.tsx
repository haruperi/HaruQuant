"use client"

import React from "react"
import { usePerformanceData } from "@/components/performance/use-performance-data"
import { Loader2 } from "lucide-react"
import { PerformancePageLayout } from "@/components/performance/shared/performance-page-layout"

const returnsConfig = {
  title: "Returns Analysis",
  description: "Detailed breakdown of strategy returns, profitability, and baseline comparisons.",
  metrics: [
    // --- Profitability (Absolute) ---
    { label: "Net Profit", accessor: "Net Profit", format: (v: any) => v != null ? `$${v.toFixed(2)}` : "-", unit: "USD", description: "Net profit from all trades" },
    { label: "Gross Profit", accessor: "Gross Profit", format: (v: any) => v != null ? `$${v.toFixed(2)}` : "-", unit: "USD", description: "Gross profit (sum of winning trades)" },
    { label: "Gross Loss", accessor: "Gross Loss", format: (v: any) => v != null ? `$${v.toFixed(2)}` : "-", unit: "USD", description: "Gross loss (sum of losing trades, negative value)" },
    { label: "Total Return", accessor: "Total Return", format: (v: any) => v != null ? `$${v.toFixed(2)}` : "-", unit: "USD", description: "Total return from equity curve" },

    // --- Profitability (Adjusted & Select) ---
    { label: "Adj. Net Profit", accessor: "Adjusted Net Profit", format: (v: any) => v != null ? `$${v.toFixed(2)}` : "-", unit: "USD", description: "The difference between the adjusted gross loss and the adjusted gross profit." },
    { label: "Adj. Gross Profit", accessor: "Adjusted Gross Profit", format: (v: any) => v != null ? `$${v.toFixed(2)}` : "-", unit: "USD", description: "(N_Winning_Trades - Sqrt(N_Winning_Trades)) * Avg_Winning_Trade" },
    { label: "Adj. Gross Loss", accessor: "Adjusted Gross Loss", format: (v: any) => v != null ? `$${v.toFixed(2)}` : "-", unit: "USD", description: "(N_Losing_Trades + Sqrt(N_Losing_Trades)) * Avg_Losing_Trade" },
    { label: "Select Net Profit", accessor: "Select Net Profit", format: (v: any) => v != null ? `$${v.toFixed(2)}` : "-", unit: "USD", description: "Net Profit with outlier trades removed. A trade is an outlier if its PnL is > 3 std devs from the mean." },
    { label: "Select Gross Profit", accessor: "Select Gross Profit", format: (v: any) => v != null ? `$${v.toFixed(2)}` : "-", unit: "USD", description: "Gross Profit consisting only of non-outlier trades." },
    { label: "Select Gross Loss", accessor: "Select Gross Loss", format: (v: any) => v != null ? `$${v.toFixed(2)}` : "-", unit: "USD", description: "Gross Loss consisting only of non-outlier trades." },

    // --- Growth Rates ---
    { label: "CAGR", accessor: "CAGR", format: (v: any) => v != null ? `${v.toFixed(2)}%` : "-", unit: "%", description: "Compound Annual Growth Rate" },
    { label: "Annualized Return", accessor: "Annualized Return", format: (v: any) => v != null ? `${v.toFixed(2)}%` : "-", unit: "%", description: "Annualized return from returns series" },
    { label: "CMGR", accessor: "Monthly Rate of Return", format: (v: any) => v != null ? `${v.toFixed(2)}%` : "-", unit: "%", description: "Compound Monthly Growth Rate (CMGR). Equivalent to CAGR but for monthly periods." },
    { label: "Geometric Mean Return", accessor: "Geometric Mean Return", format: (v: any) => v != null ? `${v.toFixed(2)}%` : "-", unit: "%", description: "Geometric mean return" },

    // --- Buy & Hold ---
    { label: "Buy & Hold Return", accessor: "Buy & Hold Return", format: (v: any) => v != null ? `${v.toFixed(2)}%` : "-", unit: "%", description: "Return achieved if asset was bought at start and held to end." },
    { label: "Buy & Hold CAGR", accessor: "Buy & Hold CAGR", format: (v: any) => v != null ? `${v.toFixed(2)}%` : "-", unit: "%", description: "Buy & Hold CAGR" },

    // --- Average Period Returns ---
    { label: "Avg Daily Return", accessor: "Avg Daily Return", format: (v: any) => v != null ? `${v.toFixed(2)}%` : "-", unit: "%", description: "Average daily return." },
    { label: "Avg Weekly Return", accessor: "Avg Weekly Return", format: (v: any) => v != null ? `${v.toFixed(2)}%` : "-", unit: "%", description: "Average weekly return." },
    { label: "Avg Monthly Return", accessor: "Avg Monthly Return", format: (v: any) => v != null ? `${v.toFixed(2)}%` : "-", unit: "%", description: "Average Monthly Return. Arithmetic mean of monthly returns." },
    { label: "Avg Annual Return", accessor: "Avg Annual Return", format: (v: any) => v != null ? `${v.toFixed(2)}%` : "-", unit: "%", description: "Average annual return." },

    // --- Volatility & Risk Stats ---
    { label: "Return Volatility", accessor: "Return Volatility", format: (v: any) => v != null ? `${v.toFixed(2)}%` : "-", unit: "%", description: "Return volatility (standard deviation)" },
    { label: "Downside Return Volatility", accessor: "Downside Return Volatility", format: (v: any) => v != null ? `${v.toFixed(2)}%` : "-", unit: "%", description: "Downside volatility (semi-deviation). Only considers returns below target." },
    { label: "Monthly Return StdDev", accessor: "Monthly Return StdDev", format: (v: any) => v != null ? `${v.toFixed(2)}%` : "-", unit: "%", description: "Standard deviation of monthly returns." },
    { label: "Return Skewness", accessor: "Return Skewness", format: (v: any) => v != null ? v.toFixed(2) : "-", description: "Skewness of returns distribution. Negative: More extreme losses. Positive: More extreme gains." },
    { label: "Return Kurtosis", accessor: "Return Kurtosis", format: (v: any) => v != null ? v.toFixed(2) : "-", description: "Kurtosis of returns distribution. High value indicates fat tails (more extreme events)." },

    // --- Return Efficiency ---
    { label: "Return on Account", accessor: "Return on Account", format: (v: any) => v != null ? v.toFixed(2) : "-", description: "Net Profit / Account Size Required." },
    { label: "Return on Initial Capital", accessor: "Return on Initial Capital", format: (v: any) => v != null ? `${v.toFixed(2)}%` : "-", unit: "%", description: "Net Profit / Initial Capital." },
    { label: "Return on Max Strategy Drawdown", accessor: "Return on Max Strategy Drawdown", format: (v: any) => v != null ? v.toFixed(2) : "-", description: "Total Return / Max Strategy Drawdown." },
    { label: "Return on Max Close To Close DD", accessor: "Return on Max Close To Close Drawdown", format: (v: any) => v != null ? v.toFixed(2) : "-", description: "Net Profit / Max Close To Close Drawdown." },
  ],
  charts: [], // No charts for this specific page requested, only table
}

export default function ReturnsPage() {
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

  const pageData = {
    metrics: metrics,
    charts: {}
  }

  return <PerformancePageLayout config={returnsConfig} data={pageData} />
}
