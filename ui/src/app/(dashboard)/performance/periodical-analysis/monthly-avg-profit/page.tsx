"use client"

import { useEffect, useState } from "react"
import { PerformancePageHeader } from "@/components/performance/performance-page-header"
import { useSelectedBacktest } from "@/contexts/selected-backtest-context"
import { strategyApi } from "@/lib/api/strategies"
import { Loader2, AlertCircle } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from "recharts"

interface MonthlyAvgData {
    month: string
    month_num: number
    avg_profit: number
    total_profit: number
    num_trades: number
    win_rate: number
}

export default function Page() {
    const { selectedBacktest } = useSelectedBacktest()
    const [data, setData] = useState<MonthlyAvgData[] | null>(null)
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

            if (trades.length === 0) {
                if (!selectedBacktest.trades) {
                    setError("No trade data available in selected backtest.")
                    setLoading(false)
                    return
                }
            }

            try {
                setLoading(true)
                setError(null)
                const result = await strategyApi.getMonthlyAvgProfit(trades, initialBalance)
                setData(result)
            } catch (err) {
                console.error(err)
                setError("Failed to calculate monthly average profit.")
            } finally {
                setLoading(false)
            }
        }

        fetchData()
    }, [selectedBacktest])

    const CustomTooltip = ({ active, payload }: any) => {
        if (active && payload && payload.length) {
            const data = payload[0].payload
            return (
                <div className="bg-background border border-border p-3 rounded-md shadow-lg">
                    <p className="font-semibold mb-2">{data.month}</p>
                    <p className="text-sm">
                        <span className="text-muted-foreground">Avg Profit: </span>
                        <span className={data.avg_profit >= 0 ? "text-green-600" : "text-red-500"}>
                            ${Math.abs(data.avg_profit).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </span>
                    </p>
                    <p className="text-sm">
                        <span className="text-muted-foreground">Total Profit: </span>
                        <span className={data.total_profit >= 0 ? "text-green-600" : "text-red-500"}>
                            ${Math.abs(data.total_profit).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </span>
                    </p>
                    <p className="text-sm">
                        <span className="text-muted-foreground">Trades: </span>
                        {data.num_trades}
                    </p>
                    <p className="text-sm">
                        <span className="text-muted-foreground">Win Rate: </span>
                        {data.win_rate.toFixed(2)}%
                    </p>
                </div>
            )
        }
        return null
    }

    if (!selectedBacktest) {
        return (
            <div className="flex flex-col h-full w-full">
                <PerformancePageHeader title="Average Profit By Month" />
                <div className="flex-1 flex items-center justify-center p-6 bg-muted/10">
                    <div className="text-center">
                        <AlertCircle className="mx-auto h-10 w-10 text-muted-foreground mb-4" />
                        <h3 className="text-lg font-medium text-muted-foreground">No Backtest Selected</h3>
                        <p className="text-sm text-muted-foreground mt-2">Please select a backtest run to view monthly average profit.</p>
                    </div>
                </div>
            </div>
        )
    }

    return (
        <div className="flex flex-col h-full w-full overflow-hidden">
            <PerformancePageHeader title="Average Profit By Month" />
            <div className="flex-1 overflow-auto p-4 md:p-6 bg-muted/10">
                <Card className="min-h-full border-t-4 border-t-primary/20">
                    <CardContent className="p-6">
                        {error && (
                            <Alert variant="destructive" className="mb-4">
                                <AlertCircle className="h-4 w-4" />
                                <AlertTitle>Error</AlertTitle>
                                <AlertDescription>{error}</AlertDescription>
                            </Alert>
                        )}

                        {loading ? (
                            <div className="flex items-center justify-center h-[500px]">
                                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                            </div>
                        ) : data && data.length > 0 ? (
                            <ResponsiveContainer width="100%" height={500}>
                                <BarChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 50 }}>
                                    <CartesianGrid strokeDasharray="3 3" />
                                    <XAxis
                                        dataKey="month"
                                        angle={-45}
                                        textAnchor="end"
                                        height={80}
                                    />
                                    <YAxis
                                        tickFormatter={(value) => `$${value.toLocaleString()}`}
                                    />
                                    <Tooltip content={<CustomTooltip />} />
                                    <Legend />
                                    <Bar dataKey="avg_profit" name="Average Profit" radius={[8, 8, 0, 0]}>
                                        {data.map((entry, index) => (
                                            <Cell key={`cell-${index}`} fill={entry.avg_profit >= 0 ? "#22c55e" : "#ef4444"} />
                                        ))}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        ) : (
                            <div className="flex items-center justify-center h-[500px]">
                                <div className="text-center">
                                    <AlertCircle className="mx-auto h-10 w-10 text-muted-foreground mb-4" />
                                    <h3 className="text-lg font-medium text-muted-foreground">No Data Available</h3>
                                    <p className="text-sm text-muted-foreground mt-2">No monthly profit data to display.</p>
                                </div>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}
