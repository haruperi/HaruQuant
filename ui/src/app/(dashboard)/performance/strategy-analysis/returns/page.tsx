"use client"

import React from "react"
import { usePerformanceData } from "@/components/performance/use-performance-data"
import { Loader2, Download } from "lucide-react"
import { PerformancePageLayout } from "@/components/performance/shared/performance-page-layout"
import { Button } from "@/components/ui/button"

const returnsConfig = {
  title: "Returns Analysis",
  description: "Detailed breakdown of strategy returns, profitability, and growth metrics.",
  metrics: [
    // --- Basic Profit & Loss ---
    { label: "Basic Profit & Loss", accessor: "", type: "group" as const },
    { label: "Total Return", accessor: "total_return", format: (v: any) => v != null ? `${v.toFixed(2)}%` : "-", unit: "%", description: "Total profit/loss as a percentage of initial capital." },
    { label: "Total Return ($)", accessor: "total_return_usd", format: (v: any) => v != null ? `$${v.toFixed(2)}` : "-", unit: "USD", description: "Total profit/loss in currency units." },
    { label: "Net Profit", accessor: "net_profit", format: (v: any) => v != null ? `$${v.toFixed(2)}` : "-", unit: "USD", description: "Total P&L from all closed trades." },
    { label: "Gross Profit", accessor: "gross_profit", format: (v: any) => v != null ? `$${v.toFixed(2)}` : "-", unit: "USD", description: "Sum of all winning trades." },
    { label: "Gross Loss", accessor: "gross_loss", format: (v: any) => v != null ? `$${v.toFixed(2)}` : "-", unit: "USD", description: "Sum of all losing trades (negative)." },

    // --- Compounding & Growth Rates ---
    { label: "Compounding & Growth Rates", accessor: "", type: "group" as const },
    { label: "CAGR", accessor: "cagr", format: (v: any) => v != null ? `${v.toFixed(2)}%` : "-", unit: "%", description: "Compound Annual Growth Rate." },
    { label: "CMGR", accessor: "cmgr", format: (v: any) => v != null ? `${v.toFixed(2)}%` : "-", unit: "%", description: "Compound Monthly Growth Rate (CMGR). Monthly equivalent of CAGR." },
    { label: "Avg Monthly Return", accessor: "avg_monthly_return", format: (v: any) => v != null ? `${v.toFixed(2)}%` : "-", unit: "%", description: "Arithmetic mean of monthly returns." },
    { label: "Monthly Return StdDev", accessor: "monthly_return_stddev", format: (v: any) => v != null ? `${v.toFixed(2)}%` : "-", unit: "%", description: "Volatility of monthly returns." },
    { label: "Annualized Return", accessor: "annualized_return", format: (v: any) => v != null ? `${v.toFixed(2)}%` : "-", unit: "%", description: "Scale sub-annual returns to yearly terms." },
    { label: "Geometric Mean Return", accessor: "geometric_mean_return", format: (v: any) => v != null ? `${v.toFixed(2)}%` : "-", unit: "%", description: "Average growth factor per period." },
    { label: "Best Period Return", accessor: "best_return", format: (v: any) => v != null ? `${v.toFixed(2)}%` : "-", unit: "%", description: "Maximum single period return." },
    { label: "Worst Period Return", accessor: "worst_return", format: (v: any) => v != null ? `${v.toFixed(2)}%` : "-", unit: "%", description: "Minimum single period return." },

    // --- Benchmarking ---
    { label: "Benchmarking", accessor: "", type: "group" as const },
    { label: "Buy & Hold Return", accessor: "buy_and_hold_return", format: (v: any) => v != null ? `${v.toFixed(2)}%` : "-", unit: "%", description: "Return if asset was held from start to end." },
    { label: "Buy & Hold CAGR", accessor: "buy_and_hold_cagr", format: (v: any) => v != null ? `${v.toFixed(2)}%` : "-", unit: "%", description: "CAGR of a buy-and-hold position." },

    // --- Return Stability & Moments ---
    { label: "Return Stability & Moments", accessor: "", type: "group" as const },
    { label: "Return Volatility", accessor: "volatility", format: (v: any) => v != null ? `${v.toFixed(2)}%` : "-", unit: "%", description: "Standard deviation of returns." },
    { label: "Downside Return Volatility", accessor: "downside_volatility", format: (v: any) => v != null ? `${v.toFixed(2)}%` : "-", unit: "%", description: "Standard deviation of negative returns only." },
    { label: "Return Skewness", accessor: "return_skewness", format: (v: any) => v != null ? v.toFixed(2) : "-", description: "Measure of return distribution asymmetry." },
    { label: "Return Kurtosis", accessor: "return_kurtosis", format: (v: any) => v != null ? v.toFixed(2) : "-", description: "Measure of 'fat tails' in returns." },

    // --- Adjusted & Select Metrics ---
    { label: "Adjusted & Select Metrics", accessor: "", type: "group" as const },
    { label: "Adj. Net Profit", accessor: "adjusted_net_profit", format: (v: any) => v != null ? `$${v.toFixed(2)}` : "-", unit: "USD", description: "Net profit adjusted for statistical significance." },
    { label: "Select Net Profit", accessor: "select_net_profit", format: (v: any) => v != null ? `$${v.toFixed(2)}` : "-", unit: "USD", description: "Net profit after removing 3-sigma outliers." },
    { label: "Adj. Gross Profit", accessor: "adjusted_gross_profit", format: (v: any) => v != null ? `$${v.toFixed(2)}` : "-", unit: "USD", description: "Adjusted Gross Profit component." },
    { label: "Adj. Gross Loss", accessor: "adjusted_gross_loss", format: (v: any) => v != null ? `$${v.toFixed(2)}` : "-", unit: "USD", description: "Adjusted Gross Loss component." },
    { label: "Select Gross Profit", accessor: "select_gross_profit", format: (v: any) => v != null ? `$${v.toFixed(2)}` : "-", unit: "USD", description: "Outlier-removed gross profit component." },
    { label: "Select Gross Loss", accessor: "select_gross_loss", format: (v: any) => v != null ? `$${v.toFixed(2)}` : "-", unit: "USD", description: "Outlier-removed gross loss component." },

    // --- Return Ratios & Capital Relations ---
    { label: "Return Ratios & Capital Relations", accessor: "", type: "group" as const },
    { label: "Return / Max Strategy DD", accessor: "return_on_max_drawdown", format: (v: any) => v != null ? v.toFixed(2) : "-", description: "Total return relative to max peak-to-valley dip." },
    { label: "Return / Max C2C DD", accessor: "return_on_max_c2c_drawdown", format: (v: any) => v != null ? v.toFixed(2) : "-", description: "Net profit relative to trade-level max dip." },
    { label: "Return on Initial Capital", accessor: "return_on_initial_capital", format: (v: any) => v != null ? `${v.toFixed(2)}%` : "-", unit: "%", description: "Return relative to starting balance." },
    { label: "Max Run-up", accessor: "max_runup", format: (v: any) => v != null ? `$${v.toFixed(2)}` : "-", unit: "USD", description: "Maximum peak-to-valley gain." },
    { label: "Max Run-up Date", accessor: "max_runup_date", description: "Timestamp of the max run-up peak." },
  ],
  charts: [],
}

export default function ReturnsPage() {
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

  if (!analytics?.returns) {
      return null
  }

  const pageData = {
    metrics: analytics.returns as any,
    charts: {}
  }

  return <PerformancePageLayout config={returnsConfig} data={pageData} />
}
