"use client"

import { useEffect, useState } from "react"
import { useSelectedBacktest } from "@/contexts/selected-backtest-context"
import { strategyApi } from "@/lib/api/strategies"
import { MetricData } from "@/components/performance/shared/metric-grid-3way"
import { PerformancePageLayout } from "@/components/performance/shared/performance-page-layout"

const riskConfig = {
  title: "Risk Analysis",
  description: "Detailed breakdown of strategy risks including volatility, tail risk, ruin probability, and market exposure.",
  metrics: [
    // --- Volatility ---
    {
      label: "Volatility",
      accessor: "Volatility",
      format: (val: number) => `${val.toFixed(2)}%`,
      description: "Standard deviation of returns (daily)"
    },
    {
      label: "Annualized Volatility",
      accessor: "Annualized Volatility",
      format: (val: number) => `${val.toFixed(2)}%`,
      description: "Annualized standard deviation of returns (assuming 252 trading days)"
    },
    {
      label: "Downside Volatility",
      accessor: "Downside Volatility",
      format: (val: number) => `${val.toFixed(2)}%`,
      description: "Standard deviation of negative returns only (semi-deviation)"
    },

    // --- Tail Risk ---
    {
      label: "Value at Risk (95%)",
      accessor: "Value at Risk (95%)",
      format: (val: number) => `${(val * 100).toFixed(2)}%`,
      description: "Maximum expected loss with 95% confidence over a single period"
    },
    {
      label: "Conditional VaR (95%)",
      accessor: "Conditional VaR (95%)",
      format: (val: number) => `${(val * 100).toFixed(2)}%`,
      description: "Expected loss given that the loss exceeds the VaR threshold (Expected Shortfall)"
    },
    {
      label: "Expected Shortfall (95%)",
      accessor: "Expected Shortfall (95%)",
      format: (val: number) => `${(val * 100).toFixed(2)}%`,
      description: "Average loss in the worst 5% of cases (Alias for CVaR)"
    },
    {
      label: "Max Loss Probability",
      accessor: "Max Loss Probability",
      format: (val: number) => `${val.toFixed(2)}%`,
      description: "Probability of a trade resulting in a loss greater than the specified threshold"
    },
    {
      label: "Drawdown Probability (10%)",
      accessor: "Drawdown Probability (10%)",
      format: (val: number) => `${val.toFixed(2)}%`,
      description: "Probability of the strategy experiencing a drawdown greater than 10%"
    },

    // --- Capital Risk ---
    {
      label: "Risk of Ruin",
      accessor: "Risk of Ruin",
      format: (val: number) => `${val.toFixed(2)}%`,
      description: "Probability of hitting a 50% drawdown given 1% risk per trade (Monte Carlo simulation)"
    },

    // --- Exposure ---
    {
      label: "Max Exposure",
      accessor: "Max Exposure",
      format: (val: number) => val != null ? `$${val.toLocaleString()}` : "-",
      unit: "USD",
      description: "Maximum capital exposed to the market at any single time"
    },
    {
      label: "Avg Exposure",
      accessor: "Avg Exposure",
      format: (val: number) => val != null ? `$${val.toLocaleString()}` : "-",
      unit: "USD",
      description: "Average capital exposed to the market per trade"
    },
    {
      label: "Exposure Time Ratio",
      accessor: "Exposure Time Ratio",
      format: (val: number) => `${val.toFixed(2)}%`,
      description: "Percentage of total time the strategy has open positions in the market"
    },
  ],
  charts: []
}

export default function RiskPage() {
  const { selectedBacktest } = useSelectedBacktest()
  const [data, setData] = useState<MetricData | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    async function fetchData() {
      if (!selectedBacktest) return

      try {
        setLoading(true)
        // Check if we have trades locally, else fetch full backtest
        let trades = selectedBacktest.trades || []
        let initialBalance = selectedBacktest.initial_balance || 10000

        if (trades.length === 0) {
            const full = await strategyApi.getBacktestById(selectedBacktest.backtest_id)
            trades = full.trades || []
            initialBalance = full.initial_balance || 10000
        }

        const stats = await strategyApi.getPerformanceSummary(trades, initialBalance)
        setData(stats)
      } catch (err) {
        console.error("Failed to load risk analysis", err)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [selectedBacktest])

  if (!selectedBacktest) {
      return <div className="p-12 text-center text-slate-500">Please select a backtest based strategy.</div>
  }

  if (loading) {
     return <div className="p-12 text-center text-slate-500">Loading risk analysis...</div>
  }

  if (!data) {
      return <div className="p-12 text-center text-slate-500">No data available.</div>
  }

  return (
    <PerformancePageLayout
        config={riskConfig}
        data={{ metrics: data }}
    />
  )
}
