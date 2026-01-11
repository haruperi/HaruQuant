"use client"

import { useEffect, useState } from "react"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { PerformancePageHeader } from "@/components/performance/performance-page-header"
import { useSelectedBacktest } from "@/contexts/selected-backtest-context"
import { strategyApi } from "@/lib/api/strategies"
import { Loader2, AlertCircle } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"

interface PeriodReturnsDrawdown {
    period: string
    timestamp: string
    equity: number
    profit_loss: number
    return_pct: number
    runup: number
    runup_pct: number
    drawdown: number
    drawdown_pct: number
}

const formatCurrency = (value: number) => {
    if (value === undefined || value === null || isNaN(value)) return "$0.00"
    return `$${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

const formatPercent = (value: number) => {
    if (value === undefined || value === null || isNaN(value)) return "0.00%"
    return `${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`
}

const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
        const data = payload[0].payload
        return (
            <div className="bg-slate-900 border border-slate-700 rounded p-3 text-sm text-white">
                <p className="font-semibold">{data.period}</p>
                {payload.map((entry: any, index: number) => (
                    <p key={index} style={{ color: entry.color }}>
                        {entry.name}: {entry.dataKey.includes('_pct') ? formatPercent(entry.value) : formatCurrency(entry.value)}
                    </p>
                ))}
            </div>
        )
    }
    return null
}

export default function Page() {
    const { selectedBacktest } = useSelectedBacktest()
    const [data, setData] = useState<PeriodReturnsDrawdown[] | null>(null)
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

            if (trades.length === 0) {
                setError("No trade data available in selected backtest.")
                setLoading(false)
                return
            }

            try {
                setLoading(true)
                setError(null)
                const result = await strategyApi.getPeriodReturnsDrawdowns(
                    'monthly',
                    trades,
                    initialBalance
                )
                setData(result)
            } catch (err) {
                console.error(err)
                setError("Failed to fetch monthly returns and drawdowns data.")
            } finally {
                setLoading(false)
            }
        }

        fetchData()
    }, [selectedBacktest])

    if (!selectedBacktest) {
        return (
            <div className="flex flex-col h-full w-full">
                <PerformancePageHeader title="Monthly Returns & Drawdowns" />
                <div className="flex-1 flex items-center justify-center p-6 bg-muted/10">
                    <div className="text-center">
                        <AlertCircle className="mx-auto h-10 w-10 text-muted-foreground mb-4" />
                        <h3 className="text-lg font-medium text-muted-foreground">No Backtest Selected</h3>
                        <p className="text-sm text-muted-foreground mt-2">Please select a backtest run to view monthly returns and drawdowns.</p>
                    </div>
                </div>
            </div>
        )
    }

    return (
        <div className="flex flex-col h-full w-full overflow-hidden">
            <PerformancePageHeader title="Monthly Returns & Drawdowns" />
            <div className="flex-1 overflow-auto p-4 md:p-6 bg-muted/10">
                <Card className="border-t-4 border-t-primary/20">
                    <CardContent className="p-6">
                        {error && (
                            <div className="mb-6">
                                <Alert variant="destructive">
                                    <AlertCircle className="h-4 w-4" />
                                    <AlertTitle>Error</AlertTitle>
                                    <AlertDescription>{error}</AlertDescription>
                                </Alert>
                            </div>
                        )}

                        {loading ? (
                            <div className="flex items-center justify-center h-[400px]">
                                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                            </div>
                        ) : data && data.length > 0 ? (
                            <div className="w-full h-[500px]">
                                <ResponsiveContainer width="100%" height="100%">
                                    <LineChart data={data}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                                        <XAxis
                                            dataKey="period"
                                            stroke="#999"
                                            style={{ fontSize: '12px' }}
                                        />
                                        <YAxis
                                            stroke="#999"
                                            style={{ fontSize: '12px' }}
                                            tickFormatter={formatCurrency}
                                        />
                                        <Tooltip content={<CustomTooltip />} />
                                        <Legend />
                                        <Line
                                            type="monotone"
                                            dataKey="profit_loss"
                                            stroke="#10b981"
                                            strokeWidth={2}
                                            dot={false}
                                            name="Profit/Loss"
                                        />
                                        <Line
                                            type="monotone"
                                            dataKey="runup"
                                            stroke="#3b82f6"
                                            strokeWidth={2}
                                            dot={false}
                                            name="Runup"
                                        />
                                        <Line
                                            type="monotone"
                                            dataKey="drawdown"
                                            stroke="#ef4444"
                                            strokeWidth={2}
                                            dot={false}
                                            name="Drawdown"
                                        />
                                    </LineChart>
                                </ResponsiveContainer>
                            </div>
                        ) : (
                            <div className="flex items-center justify-center h-[400px]">
                                <div className="text-center">
                                    <h3 className="text-lg font-medium text-muted-foreground">No Data Available</h3>
                                    <p className="text-sm text-muted-foreground mt-2">No monthly returns and drawdowns data to display.</p>
                                </div>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}
