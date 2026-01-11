"use client"

import { useEffect, useState } from "react"
import { PerformancePageHeader } from "@/components/performance/performance-page-header"
import { useSelectedBacktest } from "@/contexts/selected-backtest-context"
import { strategyApi } from "@/lib/api/strategies"
import { Loader2, AlertCircle } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import {
    ResponsiveContainer,
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
} from "recharts"

interface PeriodData {
    period: string
    timestamp: string
    return_pct: number
    runup_pct: number
    drawdown_pct: number
}

const formatPercent = (value: number) => {
    return `${value.toFixed(2)}%`
}

// Custom Tooltip
const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
        const data = payload[0].payload
        return (
            <div className="bg-slate-950 border border-slate-800 p-3 rounded-lg shadow-xl text-sm">
                <p className="font-medium text-slate-200">{data.period}</p>
                <div className="mt-2 space-y-1">
                    {payload.map((entry: any, index: number) => (
                        <div key={index} className="flex items-center justify-between gap-4">
                            <span style={{ color: entry.color }} className="text-slate-400">
                                {entry.name}:
                            </span>
                            <span className="font-mono" style={{ color: entry.color }}>
                                {formatPercent(entry.value)}
                            </span>
                        </div>
                    ))}
                </div>
            </div>
        )
    }
    return null
}

export default function HourlyReturnsPercentPage() {
    const { selectedBacktest } = useSelectedBacktest()
    const [data, setData] = useState<PeriodData[] | null>(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        const fetchData = async () => {
            if (!selectedBacktest) {
                setData(null)
                return
            }

            let trades = selectedBacktest.trades || []
            let initialBalance = selectedBacktest.initial_balance || 10000

            // If trades are missing, try to fetch full backtest details
            if (trades.length === 0 && selectedBacktest.backtest_id) {
                try {
                    setLoading(true)
                    const fullBacktest = await strategyApi.getBacktestById(
                        selectedBacktest.backtest_id
                    )
                    if (fullBacktest.trades) {
                        trades = fullBacktest.trades
                        initialBalance = fullBacktest.initial_balance || initialBalance
                    }
                } catch (err) {
                    console.error("Failed to fetch full backtest details:", err)
                }
            }

            if (trades.length === 0 && !loading) {
                if (!selectedBacktest.trades) {
                    setError("No trade data available in selected backtest.")
                    setLoading(false)
                    return
                }
            }

            try {
                setLoading(true)
                setError(null)
                const result = await strategyApi.getPeriodReturnsDrawdownsPercent(
                    'hourly',
                    trades,
                    initialBalance
                )

                setData(result)
            } catch (err) {
                console.error(err)
                setError("Failed to generate hourly returns & drawdowns chart.")
            } finally {
                setLoading(false)
            }
        }

        fetchData()
    }, [selectedBacktest])

    if (!selectedBacktest) {
        return (
            <div className="flex flex-col h-full w-full">
                <PerformancePageHeader title="Hourly Returns & Drawdowns (%)" />
                <div className="flex-1 flex items-center justify-center p-6 bg-muted/10">
                    <div className="text-center">
                        <AlertCircle className="mx-auto h-10 w-10 text-muted-foreground mb-4" />
                        <h3 className="text-lg font-medium text-muted-foreground">No Backtest Selected</h3>
                        <p className="text-sm text-muted-foreground mt-2">Please select a backtest run to view the chart.</p>
                    </div>
                </div>
            </div>
        )
    }

    return (
        <div className="flex flex-col h-full w-full overflow-hidden">
            <PerformancePageHeader title="Hourly Returns & Drawdowns (%)" />
            <div className="flex-1 overflow-auto p-4 md:p-6 bg-muted/10">
                <Card className="h-full border-t-4 border-t-blue-500/50 flex flex-col">
                    <CardContent className="flex-1 p-4 min-h-[400px]">
                        {error && (
                            <div className="mb-4">
                                <Alert variant="destructive">
                                    <AlertCircle className="h-4 w-4" />
                                    <AlertTitle>Error</AlertTitle>
                                    <AlertDescription>{error}</AlertDescription>
                                </Alert>
                            </div>
                        )}

                        {loading ? (
                            <div className="flex items-center justify-center h-full">
                                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                            </div>
                        ) : data && data.length > 0 ? (
                            <ResponsiveContainer width="100%" height="100%">
                                <LineChart
                                    data={data}
                                    margin={{ top: 20, right: 30, left: 20, bottom: 60 }}
                                >
                                    <CartesianGrid strokeDasharray="3 3" vertical={true} horizontal={true} stroke="#334155" opacity={0.5} />
                                    <XAxis
                                        dataKey="period"
                                        label={{ value: "Period", position: "insideBottom", offset: -10 }}
                                        tick={{ fontSize: 12, fill: '#94a3b8' }}
                                        angle={-45}
                                        textAnchor="end"
                                        height={80}
                                    />
                                    <YAxis
                                        tickFormatter={(val) => formatPercent(val)}
                                        label={{ value: "Percentage (%)", angle: -90, position: "insideLeft" }}
                                        tick={{ fontSize: 12, fill: '#94a3b8' }}
                                        width={80}
                                    />
                                    <Tooltip content={<CustomTooltip />} cursor={{ strokeDasharray: '3 3' }} />
                                    <Legend
                                        verticalAlign="bottom"
                                        height={36}
                                        wrapperStyle={{ paddingTop: '20px' }}
                                    />

                                    {/* Return Percentage - Green/Red */}
                                    <Line
                                        type="monotone"
                                        dataKey="return_pct"
                                        name="Return %"
                                        stroke="#22c55e"
                                        strokeWidth={2}
                                        dot={false}
                                        isAnimationActive={false}
                                    />

                                    {/* Runup Percentage - Blue */}
                                    <Line
                                        type="monotone"
                                        dataKey="runup_pct"
                                        name="Runup %"
                                        stroke="#3b82f6"
                                        strokeWidth={2}
                                        dot={false}
                                        isAnimationActive={false}
                                    />

                                    {/* Drawdown Percentage - Red */}
                                    <Line
                                        type="monotone"
                                        dataKey="drawdown_pct"
                                        name="Drawdown %"
                                        stroke="#ef4444"
                                        strokeWidth={2}
                                        dot={false}
                                        isAnimationActive={false}
                                    />
                                </LineChart>
                            </ResponsiveContainer>
                        ) : (
                            !loading && <div className="flex items-center justify-center h-full text-muted-foreground">No data available for this period.</div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}
