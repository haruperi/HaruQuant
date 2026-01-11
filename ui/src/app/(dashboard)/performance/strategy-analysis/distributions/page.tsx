"use client"

import { useEffect, useState } from "react"
import { useSelectedBacktest } from "@/contexts/selected-backtest-context"
import { strategyApi } from "@/lib/api/strategies"
import { MetricData } from "@/components/performance/shared/metric-grid-3way"
import { PerformancePageLayout } from "@/components/performance/shared/performance-page-layout"
import { DistributionPanel3Way } from "@/components/performance/shared/distribution-panel-3way"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ScatterChart, Scatter, ZAxis } from "recharts"

const statsConfig = {
  title: "Statistical Distributions",
  description: "Analysis of return distributions, normality tests, and outliers.",
  metrics: [
    // --- Normality ---
    {
      label: "Jarque-Bera p-value",
      accessor: "Jarque-Bera p-value",
      format: (val: number) => val.toFixed(4),
      description: "p-value of JB test. < 0.05 indicates non-normal distribution."
    },
    {
      label: "Shapiro-Wilk p-value",
      accessor: "Shapiro-Wilk p-value",
      format: (val: number) => val.toFixed(4),
      description: "p-value of SW test. < 0.05 indicates non-normal distribution."
    },
    {
        label: "Is Normal (JB)",
        accessor: "Is Normal (JB)",
        format: (val: boolean) => val ? "Yes" : "No",
        description: "Based on Jarque-Bera test (p > 0.05)"
    },

    // --- Higher Moments ---
    {
      label: "Skewness",
      accessor: "Skewness",
      format: (val: number) => val.toFixed(2),
      description: "Measure of asymmetry. Negative = left tail (losses), Positive = right tail (gains)."
    },
    {
      label: "Kurtosis",
      accessor: "Kurtosis",
      format: (val: number) => val.toFixed(2),
      description: "Total kurtosis. Normal distribution has kurtosis ≈ 3."
    },
    {
      label: "Excess Kurtosis",
      accessor: "Excess Kurtosis",
      format: (val: number) => val.toFixed(2),
      description: "Kurtosis - 3. Positive values indicate fat tails (more extreme events)."
    },
    {
      label: "Fat Tail Score",
      accessor: "Fat Tail Score",
      format: (val: number) => val.toFixed(2),
      description: "Metric indicating the severity of fat tails."
    },

    // --- Outliers ---
    {
      label: "Outlier Ratio",
      accessor: "Outlier Ratio",
      format: (val: number) => `${val.toFixed(2)}%`,
      description: "Percentage of returns considered statistical outliers (> 3 IQR)."
    },

    // --- Distribution Fit ---
    {
        label: "Normal Dist Fit (Mu)",
        accessor: "Normal Fit (Mu)",
        format: (val: number) => `${val.toFixed(2)}%`,
        description: "Mean of fitted normal distribution"
    },
    {
        label: "Normal Dist Fit (Sigma)",
        accessor: "Normal Fit (Sigma)",
        format: (val: number) => `${val.toFixed(2)}%`,
        description: "Standard deviation of fitted normal distribution"
    },

    // --- R-Multiples ---
    {
        label: "R-Multiple Mean",
        accessor: "R-Multiple Mean",
        format: (val: number) => val.toFixed(2),
        description: "Average R-multiple (Risk-adjusted return per trade)"
    },
    {
        label: "R-Multiple StdDev",
        accessor: "R-Multiple StdDev",
        format: (val: number) => val.toFixed(2),
        description: "Standard deviation of R-multiples"
    },
    {
        label: "R-Multiple Skew",
        accessor: "R-Multiple Skew",
        format: (val: number) => val.toFixed(2),
        description: "Skewness of R-multiple distribution"
    }
  ],
  charts: []
}

export default function DistributionsPage() {
  const { selectedBacktest } = useSelectedBacktest()
  const [data, setData] = useState<MetricData | null>(null)
  const [pnlData, setPnlData] = useState<{ all: number[], long: number[], short: number[] } | null>(null)
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

        // Process trades for DistributionPanel3Way
        const getPnl = (t: any) => Number(t.profit_loss ?? t.pnl ?? t.profit ?? 0)
        const getType = (t: any) => (t.type || t.side || "").toString().toLowerCase()

        const pnl = {
            all: trades.map(getPnl),
            long: trades.filter(t => {
                const type = getType(t)
                return type === "buy" || type === "long"
            }).map(getPnl),
            short: trades.filter(t => {
                const type = getType(t)
                return type === "sell" || type === "short"
            }).map(getPnl)
        }
        setPnlData(pnl)
      } catch (err) {
        console.error("Failed to load distribution analysis", err)
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
     return <div className="p-12 text-center text-slate-500">Loading distribution analysis...</div>
  }

  if (!data) {
      return <div className="p-12 text-center text-slate-500">No data available.</div>
  }

  // Extract chart data
  const chartData = data.all.chart_data || {}
  const returnsHist = chartData.returns_histogram || []
  const pnlHist = chartData.trade_pnl_histogram || []
  const rMultipleHist = chartData.r_multiple_histogram || []
  const qqData = chartData.qq_plot || []
  const outlierData = chartData.outliers_plot || []

  return (
    <div className="space-y-6">
        {/* Statistical Tests Table */}
        <PerformancePageLayout
            config={statsConfig}
            data={{ metrics: data }}
        />

        {/* Charts Grid */}
        <div className="grid grid-cols-1 gap-6 pb-8">
            {/* Returns Histogram */}
            <Card>
                <CardHeader>
                    <CardTitle>Returns Distribution</CardTitle>
                    <CardDescription>Histogram of daily returns</CardDescription>
                </CardHeader>
                <CardContent className="h-[300px]">
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={returnsHist}>
                            <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                            <XAxis dataKey="label" fontSize={10} tickFormatter={(val) => val.split(" - ")[0]} />
                            <YAxis />
                            <Tooltip
                                contentStyle={{ backgroundColor: "#1f2937", borderColor: "#374151" }}
                                formatter={(val: number) => [val, "Count"]}
                            />
                            <Bar dataKey="count" fill="#3b82f6" />
                        </BarChart>
                    </ResponsiveContainer>
                </CardContent>
            </Card>

            {/* Trade PnL Histogram - Replaced with DistributionPanel3Way */}
            {pnlData && (
                <DistributionPanel3Way
                    title="Trade P&L Distribution"
                    data={pnlData}
                    unit="USD"
                />
            )}

            {/* R-Multiple Histogram */}
            <Card>
                <CardHeader>
                    <CardTitle>R-Multiple Distribution</CardTitle>
                    <CardDescription>Histogram of risk-multiples (Return / Risk)</CardDescription>
                </CardHeader>
                 <CardContent className="h-[300px]">
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={rMultipleHist}>
                            <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                            <XAxis dataKey="label" fontSize={10} tickFormatter={(val) => val.split(" - ")[0]} />
                            <YAxis />
                             <Tooltip
                                contentStyle={{ backgroundColor: "#1f2937", borderColor: "#374151" }}
                                formatter={(val: number) => [val, "Count"]}
                            />
                            <Bar dataKey="count" fill="#f59e0b" />
                        </BarChart>
                    </ResponsiveContainer>
                </CardContent>
            </Card>

            {/* Q-Q Plot */}
            <Card>

                <CardHeader>
                    <CardTitle>Q-Q Plot vs Normal Distribution</CardTitle>
                    <CardDescription>Sample quantities vs Theoretical normal quantiles. Straight line indicates normality.</CardDescription>
                </CardHeader>
                <CardContent className="h-[400px]">
                     <ResponsiveContainer width="100%" height="100%">
                        <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                            <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                            <XAxis type="number" dataKey="theoretical" name="Theoretical" label={{ value: 'Theoretical Quantiles', position: 'bottom', offset: 0 }} />
                            <YAxis type="number" dataKey="sample" name="Sample" label={{ value: 'Sample Quantiles', angle: -90, position: 'insideLeft' }} />
                            <Tooltip
                                cursor={{ strokeDasharray: '3 3' }}
                                contentStyle={{ backgroundColor: "#1f2937", borderColor: "#374151" }}
                            />
                            <Scatter name="Q-Q Data" data={qqData} fill="#8884d8" shape="circle" />
                        </ScatterChart>
                    </ResponsiveContainer>
                </CardContent>
            </Card>
            {/* Outliers Over Time */}
            <Card>
                <CardHeader>
                    <CardTitle>Outliers Over Time</CardTitle>
                    <CardDescription>Returns identified as statistical outliers</CardDescription>
                </CardHeader>
                <CardContent className="h-[300px]">
                     <ResponsiveContainer width="100%" height="100%">
                        <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                            <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                            <XAxis dataKey="date" fontSize={10} />
                            <YAxis dataKey="return" name="Return" unit="%" />
                            <Tooltip
                                cursor={{ strokeDasharray: '3 3' }}
                                contentStyle={{ backgroundColor: "#1f2937", borderColor: "#374151" }}
                                formatter={(val: number) => [`${(val * 100).toFixed(2)}%`, "Return"]}
                            />
                            <Scatter name="Outliers" data={outlierData} fill="#ef4444" shape="cross" />
                        </ScatterChart>
                    </ResponsiveContainer>
                </CardContent>
            </Card>
        </div>
    </div>
  )
}
