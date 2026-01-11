"use client"

import { useEffect, useState } from "react"
import { useSelectedBacktest } from "@/contexts/selected-backtest-context"
import { strategyApi } from "@/lib/api/strategies"
import { MetricConfig, MetricData } from "@/components/performance/shared/metric-grid-3way"
import { PerformancePageLayout } from "@/components/performance/shared/performance-page-layout"

const ratioMetrics: MetricConfig[] = [
  // --- Profit Factors ---
  {
    label: "Profit Factor",
    accessor: "Profit Factor",
    format: (val) => val.toFixed(2),
    description: "Gross Profit divided by Gross Loss."
  },
  {
    label: "Adjusted Profit Factor",
    accessor: "Adjusted Profit Factor",
    format: (val) => val.toFixed(2),
    description: "Adjusted Gross Profit divided by Adjusted Gross Loss."
  },
  {
    label: "Select Profit Factor",
    accessor: "Select Profit Factor",
    format: (val) => val.toFixed(2),
    description: "Select Gross Profit divided by Select Gross Loss."
  },

  // --- Risk-Adjusted Return Ratios ---
  {
    label: "Sharpe Ratio",
    accessor: "Sharpe Ratio",
    format: (val) => val.toFixed(2),
    description: "The average return earned in excess of the risk-free rate per unit of volatility or total risk."
  },
  {
    label: "Annualized Sharpe Ratio",
    accessor: "Annualized Sharpe Ratio",
    format: (val) => val.toFixed(2),
    description: "A measure of risk-adjusted return, annualized."
  },
  {
    label: "Sortino Ratio",
    accessor: "Sortino Ratio",
    format: (val) => val.toFixed(2),
    description: "Differentiates harmful volatility from total overall volatility by using the asset's standard deviation of negative portfolio returns."
  },
  {
    label: "Calmar Ratio",
    accessor: "Calmar Ratio",
    format: (val) => val.toFixed(2),
    description: "Compound Annual Growth Rate divided by Maximum Drawdown."
  },
  {
    label: "Sterling Ratio",
    accessor: "Sterling Ratio",
    format: (val) => val.toFixed(2),
    description: "Risk-adjusted return ratio, using average annual drawdown."
  },
  {
    label: "Omega Ratio",
    accessor: "Omega Ratio",
    format: (val) => val.toFixed(2),
    description: "Probability-weighted ratio of gains versus losses for a given threshold return."
  },
  {
    label: "Kappa Ratio",
    accessor: "Kappa Ratio",
    format: (val) => val.toFixed(2),
    description: "Generalization of the Sortino ratio using lower partial moments."
  },
  {
    label: "Information Ratio",
    accessor: "Information Ratio",
    format: (val) => val.toFixed(2),
    description: "Returns of the portfolio in excess of the benchmark returns divided by the tracking error."
  },
  {
    label: "Fouse Ratio",
    accessor: "Fouse Ratio",
    format: (val) => val.toFixed(2),
    description: "Risk-adjusted performance measure accounting for risk tolerance."
  },

  // --- Expectancy & Edge ---
  {
    label: "Expectancy ($)",
    accessor: "Expectancy",
    format: (val) => `$${val.toFixed(2)}`,
    description: "The average amount you can expect to win (or lose) per trade."
  },
  {
    label: "Expectancy (R)",
    accessor: "Expectancy (R)",
    format: (val) => `${val.toFixed(2)}R`,
    description: "The average R-multiple you can expect to win (or lose) per trade."
  },
  {
    label: "Expectancy over Variance",
    accessor: "Expectancy over Variance",
    format: (val) => val.toFixed(2),
    description: "Expectancy divided by the variance of returns, indicating stability."
  },
  {
    label: "Edge Ratio",
    accessor: "Edge Ratio",
    format: (val) => val.toFixed(2),
    description: "Measures the trading edge by combining win rate and risk-reward ratio."
  },
  {
    label: "Payoff Ratio",
    accessor: "Payoff Ratio",
    format: (val) => val.toFixed(2),
    description: "Ratio of average win to average loss."
  },

  // --- Trade Efficiency Ratios ---
  {
    label: "Gain to Pain Ratio",
    accessor: "Gain to Pain Ratio",
    format: (val) => val.toFixed(2),
    description: "Sum of all returns divided by the absolute value of sum of all negative returns."
  },
  {
    label: "Return Over Drawdown",
    accessor: "Return Over Drawdown",
    format: (val) => val.toFixed(2),
    description: "Total Return divided by Maximum Drawdown."
  },
  {
    label: "Profit to MAE Ratio",
    accessor: "Profit to MAE Ratio",
    format: (val) => val.toFixed(2),
    description: "Ratio of Net Profit to Maximum Adverse Excursion."
  },
  {
    label: "MFE to MAE Ratio",
    accessor: "MFE to MAE Ratio",
    format: (val) => val.toFixed(2),
    description: "Ratio of Maximum Favorable Excursion to Maximum Adverse Excursion."
  },
  {
    label: "RINA Index",
    accessor: "RINA Index",
    format: (val) => val.toFixed(2),
    description: "Select Net Profit divided by (Average Drawdown * Percent Time in Market)."
  },
  {
    label: "Upside Potential Ratio",
    accessor: "Upside Potential Ratio",
    format: (val) => val.toFixed(2),
    description: "Upside potential divided by downside risk."
  },

  // --- Net Profit Percentages ---
  {
    label: "Net Profit % of Largest Loss",
    accessor: "Net Profit % of Largest Loss",
    format: (val) => `${val.toFixed(2)}%`,
    description: "Net Profit as a percentage of the largest single loss."
  },
  {
    label: "Net Profit % of Max Strategy Drawdown",
    accessor: "Net Profit % of Max Strategy Drawdown",
    format: (val) => `${val.toFixed(2)}%`,
    description: "Net Profit as a percentage of the maximum strategy drawdown."
  },
  {
    label: "Net Profit % of Max Trade Drawdown",
    accessor: "Net Profit % of Max Trade Drawdown",
    format: (val) => `${val.toFixed(2)}%`,
    description: "Net Profit as a percentage of the maximum trade drawdown."
  },

  // --- Adjusted Net Profit Percentages ---
  {
    label: "Adj Net Profit % of Largest Loss",
    accessor: "Adj Net Profit % of Largest Loss",
    format: (val) => `${val.toFixed(2)}%`,
    description: "Adjusted Net Profit as a percentage of the largest single loss."
  },
  {
    label: "Adj Net Profit % of Max Strategy Drawdown",
    accessor: "Adj Net Profit % of Max Strategy Drawdown",
    format: (val) => `${val.toFixed(2)}%`,
    description: "Adjusted Net Profit as a percentage of the maximum strategy drawdown."
  },
  {
    label: "Adj Net Profit % of Max Trade Drawdown",
    accessor: "Adj Net Profit % of Max Trade Drawdown",
    format: (val) => `${val.toFixed(2)}%`,
    description: "Adjusted Net Profit as a percentage of the maximum trade drawdown."
  },

  // --- Select Net Profit Percentages ---
  {
    label: "Select Net Profit % of Largest Loss",
    accessor: "Select Net Profit % of Largest Loss",
    format: (val) => `${val.toFixed(2)}%`,
    description: "Select Net Profit as a percentage of the largest single loss."
  },
  {
    label: "Select Net Profit % of Max Strategy Drawdown",
    accessor: "Select Net Profit % of Max Strategy Drawdown",
    format: (val) => `${val.toFixed(2)}%`,
    description: "Select Net Profit as a percentage of the maximum strategy drawdown."
  },
  {
    label: "Select Net Profit % of Max Trade Drawdown",
    accessor: "Select Net Profit % of Max Trade Drawdown",
    format: (val) => `${val.toFixed(2)}%`,
    description: "Select Net Profit as a percentage of the maximum trade drawdown."
  },
]

const ratioConfig = {
  title: "Performance Ratios",
  description: "Comprehensive list of risk-adjusted return ratios and efficiency metrics.",
  metrics: ratioMetrics,
  charts: []
}

export default function PerformanceRatiosPage() {
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
        console.error("Failed to load performance ratios", err)
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
     return <div className="p-12 text-center text-slate-500">Loading performance ratios...</div>
  }

  if (!data) {
      return <div className="p-12 text-center text-slate-500">No data available.</div>
  }

  return (
    <PerformancePageLayout
        config={ratioConfig}
        data={{ metrics: data }}
    />
  )
}
