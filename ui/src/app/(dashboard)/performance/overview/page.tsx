"use client"

import React from "react"
import { usePerformanceData } from "@/components/performance/use-performance-data"
import { PerformancePageLayout, PageConfig } from "@/components/performance/shared/performance-page-layout"
import { Loader2 } from "lucide-react"

const overviewConfig: PageConfig = {
  title: "Overview",
  description: "Executive summary of strategy performance.",
  metrics: [
    { label: "Net Profit", accessor: "Net Profit", format: (v) => (v != null) ? `$${v.toFixed(2)}` : "-", unit: "USD", description: "Total profit or loss derived from all closed trades." },
    { label: "Total Return", accessor: "Return on Initial Capital", format: (v) => (v != null) ? `${v.toFixed(2)}%` : "-", unit: "%", description: "The percentage return relative to the initial account balance." },
    { label: "CAGR", accessor: "Annual Rate of Return", format: (v) => (v != null) ? `${v.toFixed(2)}%` : "-", unit: "%", description: "Compound Annual Growth Rate. The mean annual growth rate of the investment." },
    { label: "Max Drawdown", accessor: "Max Strategy Drawdown", format: (v) => (v != null) ? `$${v.toFixed(2)}` : "-", unit: "USD", description: "The maximum observed loss from a peak to a trough of a portfolio, before a new peak is attained." },
    { label: "Max Drawdown %", accessor: "Max Strategy Drawdown (%)", format: (v) => (v != null) ? `${v.toFixed(2)}%` : "-", unit: "%", description: "The maximum percentage drop from the highest equity peak." },
    { label: "Profit Factor", accessor: "Profit Factor", format: (v) => (v != null) ? v.toFixed(2) : "-", description: "Gross Profit divided by Gross Loss. A value > 1 indicates a profitable system." },
    { label: "Win Rate", accessor: "Percent Profitable", format: (v) => (v != null) ? `${v.toFixed(1)}%` : "-", unit: "%", description: "The percentage of trades that were profitable." },
    { label: "Expectancy", accessor: "Expectancy", format: (v) => (v != null) ? `$${v.toFixed(2)}` : "-", description: "The average amount you can expect to win (or lose) per trade." },
    { label: "R-Expectancy", accessor: "R-Expectancy", format: (v) => (v != null) ? v.toFixed(2) : "-", description: "Average R-multiple expected per trade." },
    { label: "SQN", accessor: "SQN", format: (v) => (v != null) ? v.toFixed(2) : "-", description: "System Quality Number. Measures the quality of the trading system based on expectancy and volatility." },
    { label: "Sharpe Ratio", accessor: "Sharpe Ratio", format: (v) => (v != null) ? v.toFixed(2) : "-", description: "The average return earned in excess of the risk-free rate per unit of volatility." },
    { label: "Sortino Ratio", accessor: "Sortino Ratio", format: (v) => (v != null) ? v.toFixed(2) : "-", description: "Similar to Sharpe Ratio, but penalizes only downside volatility." },
    { label: "Calmar Ratio", accessor: "Calmar Ratio", format: (v) => (v != null) ? v.toFixed(2) : "-", description: "Compound Annual Growth Rate divided by Maximum Drawdown." },
    { label: "Value at Risk (95%)", accessor: "Value at Risk (95%)", format: (v) => (v != null) ? `${(v * 100).toFixed(2)}%` : "-", unit: "%", description: "Maximum expected loss over a specific time horizon at a 95% confidence level." },
    { label: "Time in Market %", accessor: "Time in Market %", format: (v) => (v != null) ? `${v.toFixed(1)}%` : "-", unit: "%", description: "Percentage of time the strategy had at least one open position." },
    { label: "Total Trades", accessor: "Total # of Trades", description: "The total number of closed trades in the selected backtest." },
  ],
  charts: [
    {
      id: "equity_curve",
      type: "series",
      title: "Equity Curve",
      valueFormatter: (v) => `$${v.toFixed(0)}`,
    },
    {
      id: "drawdown_curve",
      type: "series",
      title: "Drawdown Series",
      valueFormatter: (v) => `$${v.toFixed(0)}`,
    }
  ]
}

export default function OverviewPage() {
  const { metrics, equityCurves, loading, error, selectedBacktest } = usePerformanceData()

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

  if (!metrics || !equityCurves) {
      return null
  }

  // Transform Series Data for Charts
  // SeriesChart3Way expects data point with { date, all, long, short }
  // We need to merge the 3 arrays by date.

  // Helper to merge 3 equity curves
  const mergeCurves = (key: "equity_close" | "drawdown_usd", all: any[], long: any[], short: any[]) => {
      const map = new Map<string, { date: string, all?: number, long?: number, short?: number }>()

      const addToMap = (arr: any[], type: "all" | "long" | "short") => {
          arr.forEach(pt => {
              const date = pt.date.split(" ")[0] // simple date key
              if (!map.has(date)) {
                  map.set(date, { date })
              }
              const entry = map.get(date)!
              entry[type] = pt[key]
          })
      }

      addToMap(all, "all")
      addToMap(long, "long")
      addToMap(short, "short")

      const sorted = Array.from(map.values()).sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())

      // Forward fill values
      let lastAll: number | undefined
      let lastLong: number | undefined
      let lastShort: number | undefined

      return sorted.map(pt => {
        // If value exists, update last known. If not, use last known.
        if (pt.all !== undefined) lastAll = pt.all
        else pt.all = lastAll

        if (pt.long !== undefined) lastLong = pt.long
        else pt.long = lastLong

        if (pt.short !== undefined) lastShort = pt.short
        else pt.short = lastShort

        return pt
      })
  }

  const equityChartData = mergeCurves("equity_close", equityCurves.all, equityCurves.long, equityCurves.short)
  const drawdownChartData = mergeCurves("drawdown_usd", equityCurves.all, equityCurves.long, equityCurves.short)

  const pageData = {
    metrics: metrics,
    charts: {
      equity_curve: equityChartData,
      drawdown_curve: drawdownChartData
    }
  }

  return <PerformancePageLayout config={overviewConfig} data={pageData} />
}
