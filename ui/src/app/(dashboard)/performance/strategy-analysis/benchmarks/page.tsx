"use client"

import { useEffect, useState } from "react"
import { useSelectedBacktest } from "@/contexts/selected-backtest-context"
import { strategyApi } from "@/lib/api/strategies"
import { MetricData } from "@/components/performance/shared/metric-grid-3way"
import { PerformancePageLayout } from "@/components/performance/shared/performance-page-layout"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts"

const benchmarksConfig = {
  title: "Benchmark Comparison",
  description: "Relative performance versus benchmark equity/returns.",
  metrics: [
    // --- Market Statistics ---
    {
      label: "Alpha",
      accessor: "Alpha",
      format: (val: number) => val.toFixed(4),
      description: "Jensen's Alpha. Risk-adjusted excess return over benchmark."
    },
    {
      label: "Beta",
      accessor: "Beta",
      format: (val: number) => val.toFixed(2),
      description: "Measure of volatility relative to the benchmark. Beta > 1 implies higher volatility."
    },
    {
      label: "R-Squared",
      accessor: "R-Squared",
      format: (val: number) => val.toFixed(4),
      description: "Proportion of strategy's variance explained by the benchmark."
    },
    {
      label: "Tracking Error",
      accessor: "Tracking Error",
      format: (val: number) => `${(val * 100).toFixed(2)}%`,
      description: "Standard deviation of excess returns."
    },

    // --- Relative Performance ---
    {
      label: "Batting Average",
      accessor: "Batting Average",
      format: (val: number) => `${val.toFixed(2)}%`,
      description: "Percentage of periods where strategy outperforms benchmark."
    },
    {
      label: "Up Capture Ratio",
      accessor: "Up Capture Ratio",
      format: (val: number) => `${val.toFixed(2)}%`,
      description: "Strategy's performance percentage during benchmark's positive periods."
    },
    {
      label: "Down Capture Ratio",
      accessor: "Down Capture Ratio",
      format: (val: number) => `${val.toFixed(2)}%`,
      description: "Strategy's performance percentage during benchmark's negative periods."
    },
    {
      label: "Max Relative Drawdown",
      accessor: "Max Relative Drawdown",
      format: (val: number) => `${val.toFixed(2)}%`,
      description: "Maximum underperformance relative to benchmark equity."
    }
  ],
  charts: []
}

export default function BenchmarksPage() {
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
        console.error("Failed to load benchmark analysis", err)
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
     return <div className="p-12 text-center text-slate-500">Loading benchmark analysis...</div>
  }

  if (!data) {
      return <div className="p-12 text-center text-slate-500">No data available.</div>
  }

  // Extract chart data
  const chartData = data.all.chart_data || {}
  const comparisonData = chartData.benchmark_comparison || []
  const excessData = chartData.excess_returns || []

  return (
    <div className="space-y-6">
        {/* Metrics Grid */}
        <PerformancePageLayout
            config={benchmarksConfig}
            data={{ metrics: data }}
        />

        {/* Charts Grid */}
        <div className="grid grid-cols-1 gap-6 pb-8">
            {/* Benchmark Comparison Chart */}
            <Card>
                <CardHeader>
                    <CardTitle>Strategy vs Benchmark</CardTitle>
                    <CardDescription>Equity curve comparison</CardDescription>
                </CardHeader>
                <CardContent className="h-[400px]">
                    <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={comparisonData}>
                            <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                            <XAxis dataKey="date" fontSize={10} tickFormatter={(val) => new Date(val).toLocaleDateString()} />
                            <YAxis domain={['auto', 'auto']} />
                            <Tooltip
                                contentStyle={{ backgroundColor: "#1f2937", borderColor: "#374151" }}
                                labelFormatter={(label) => new Date(label).toLocaleDateString()}
                            />
                            <Legend />
                            <Line type="monotone" dataKey="strategy" name="Strategy Equity" stroke="#3b82f6" dot={false} strokeWidth={2} />
                            <Line type="monotone" dataKey="benchmark" name="Benchmark Equity" stroke="#9ca3af" dot={false} strokeWidth={2} strokeDasharray="5 5" />
                        </LineChart>
                    </ResponsiveContainer>
                </CardContent>
            </Card>

            {/* Excess Returns Chart */}
            <Card>
                <CardHeader>
                    <CardTitle>Excess Returns</CardTitle>
                    <CardDescription>Strategy Return - Benchmark Return (per period)</CardDescription>
                </CardHeader>
                 <CardContent className="h-[300px]">
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={excessData}>
                            <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                            <XAxis dataKey="date" fontSize={10} tickFormatter={(val) => new Date(val).toLocaleDateString()} />
                            <YAxis />
                             <Tooltip
                                contentStyle={{ backgroundColor: "#1f2937", borderColor: "#374151" }}
                                labelFormatter={(label) => new Date(label).toLocaleDateString()}
                                formatter={(val: number) => [`${(val * 100).toFixed(4)}%`, "Excess Return"]}
                            />
                            <Bar dataKey="excess_return" name="Excess Return" fill="#10b981" />
                        </BarChart>
                    </ResponsiveContainer>
                </CardContent>
            </Card>
        </div>
    </div>
  )
}
