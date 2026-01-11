"use client"

import { useEffect, useState } from "react"
import { PerformancePageHeader } from "@/components/performance/performance-page-header"
import { useSelectedBacktest } from "@/contexts/selected-backtest-context"
import { strategyApi } from "@/lib/api/strategies"
import { Loader2, AlertCircle } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"

interface MonthlyAvgData {
    month: string
    month_num: number
    avg_profit: number
    total_profit: number
    num_trades: number
    win_rate: number
}

const formatCurrency = (value: number) => {
    if (value === undefined || value === null || isNaN(value)) return "n/a"
    const absVal = Math.abs(value)
    const formatted = `$${absVal.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
    return value < 0 ? `(${formatted.slice(1)})` : formatted
}

const formatPercent = (value: number) => {
    if (value === undefined || value === null || isNaN(value)) return "n/a"
    if (value === Infinity || value === -Infinity) return "inf"
    const absVal = Math.abs(value)
    const formatted = `${absVal.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`
    return value < 0 ? `(${formatted})` : formatted
}

const getTextColor = (value: number) => {
    if (value < 0) return "text-red-500"
    if (value > 0) return "text-green-600"
    return ""
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
                setError("Failed to calculate monthly analysis.")
            } finally {
                setLoading(false)
            }
        }

        fetchData()
    }, [selectedBacktest])

    if (!selectedBacktest) {
        return (
            <div className="flex flex-col h-full w-full">
                <PerformancePageHeader title="Monthly Analysis" />
                <div className="flex-1 flex items-center justify-center p-6 bg-muted/10">
                    <div className="text-center">
                        <AlertCircle className="mx-auto h-10 w-10 text-muted-foreground mb-4" />
                        <h3 className="text-lg font-medium text-muted-foreground">No Backtest Selected</h3>
                        <p className="text-sm text-muted-foreground mt-2">Please select a backtest run to view monthly analysis.</p>
                    </div>
                </div>
            </div>
        )
    }

    return (
        <div className="flex flex-col h-full w-full overflow-hidden">
            <PerformancePageHeader title="Monthly Analysis" />
            <div className="flex-1 overflow-auto p-4 md:p-6 bg-muted/10">
                <Card className="min-h-full border-t-4 border-t-primary/20">
                    <CardContent className="p-0">
                        {error && (
                            <div className="p-4">
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
                        ) : data ? (
                            <div className="relative w-full overflow-auto">
                                <table className="w-full text-sm caption-bottom">
                                    <thead className="[&_tr]:border-b sticky top-0 bg-background z-10">
                                        <tr className="border-b transition-colors hover:bg-muted/50">
                                            <th className="h-12 px-3 text-left align-middle font-medium text-muted-foreground">Month</th>
                                            <th className="h-12 px-3 text-right align-middle font-medium text-muted-foreground">Avg Profit</th>
                                            <th className="h-12 px-3 text-right align-middle font-medium text-muted-foreground">Total Profit</th>
                                            <th className="h-12 px-3 text-right align-middle font-medium text-muted-foreground">Num Trades</th>
                                            <th className="h-12 px-3 text-right align-middle font-medium text-muted-foreground">Win Rate</th>
                                        </tr>
                                    </thead>
                                    <tbody className="[&_tr:last-child]:border-0">
                                        {data.map((row, index) => (
                                            <tr key={index} className="border-b transition-colors hover:bg-muted/50">
                                                <td className="p-2 px-3 align-middle font-medium">{row.month}</td>
                                                <td className={`p-2 px-3 align-middle text-right font-mono ${getTextColor(row.avg_profit)}`}>
                                                    {formatCurrency(row.avg_profit)}
                                                </td>
                                                <td className={`p-2 px-3 align-middle text-right font-mono ${getTextColor(row.total_profit)}`}>
                                                    {formatCurrency(row.total_profit)}
                                                </td>
                                                <td className="p-2 px-3 align-middle text-right font-mono">
                                                    {row.num_trades}
                                                </td>
                                                <td className="p-2 px-3 align-middle text-right font-mono">
                                                    {formatPercent(row.win_rate)}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        ) : null}
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}
