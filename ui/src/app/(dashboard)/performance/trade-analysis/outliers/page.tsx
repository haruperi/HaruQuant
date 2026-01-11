"use client"

import { useEffect, useState } from "react"
import { PerformancePageHeader } from "@/components/performance/performance-page-header"
import { useSelectedBacktest } from "@/contexts/selected-backtest-context"
import { strategyApi } from "@/lib/api/strategies"
import { Card, CardContent } from "@/components/ui/card"
import { Loader2, AlertCircle } from "lucide-react"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"

// Interface matching the API response structure
interface OutlierStats {
    std_dev: number
    mean: number
    upper_bound: number
    lower_bound: number
    outlier_count: number
    outlier_pnl: number
}

interface OutliersResponse {
    total: OutlierStats
    positive: OutlierStats
    negative: OutlierStats
}

// Formatting helpers
const formatCurrency = (val: number) => {
    const absVal = Math.abs(val)
    const str = `$${absVal.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
    return val < 0 ? <span className="text-red-500">({str})</span> : <span>{str}</span>
}

const formatNumber = (val: number) => {
    return val.toLocaleString("en-US")
}

// Helper component for cells with tooltips
const HeaderWithTooltip = ({ text, tooltip }: { text: string; tooltip: string }) => (
    <Tooltip>
        <TooltipTrigger asChild>
            <span className="cursor-help decoration-dotted underline underline-offset-4 decoration-muted-foreground/30">{text}</span>
        </TooltipTrigger>
        <TooltipContent>
            <p className="max-w-xs">{tooltip}</p>
        </TooltipContent>
    </Tooltip>
)

export default function OutliersPage() {
    const { selectedBacktest } = useSelectedBacktest()
    const [data, setData] = useState<OutliersResponse | null>(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        const fetchData = async () => {
             if (!selectedBacktest) return

             setLoading(true)
             setError(null)
             try {
                let trades = selectedBacktest.trades || []

                // Fetch full backtest if trades missing
                if (trades.length === 0 && selectedBacktest.backtest_id) {
                     try {
                        const full = await strategyApi.getBacktestById(selectedBacktest.backtest_id)
                        trades = full.trades || []
                     } catch (e) {
                         console.error("Failed to fetch full backtest", e)
                     }
                }

                if (trades.length === 0) {
                    setLoading(false)
                    return
                }

                const result = await strategyApi.getOutliersReport(trades, selectedBacktest.initial_balance || 10000)
                setData(result)

             } catch (err) {
                 console.error("Failed to fetch outliers:", err)
                 setError("Failed to load outliers analysis.")
             } finally {
                 setLoading(false)
             }
        }

        fetchData()
    }, [selectedBacktest])

    if (!selectedBacktest) {
        return (
            <div className="flex flex-col h-full w-full">
                <PerformancePageHeader title="Outliers" />
                <div className="flex-1 flex items-center justify-center p-6 bg-muted/10">
                    <div className="text-center">
                         <AlertCircle className="mx-auto h-10 w-10 text-muted-foreground mb-4" />
                        <h3 className="text-lg font-medium text-muted-foreground">No Backtest Selected</h3>
                    </div>
                </div>
            </div>
        )
    }

    return (
        <div className="flex flex-col h-full w-full overflow-hidden">
            <PerformancePageHeader title="Outliers" />
            <div className="flex-1 overflow-auto p-4 md:p-6 bg-muted/10">
                <Card className="min-h-full border-t-4 border-t-primary/20">
                     <CardContent className="p-0">
                        {loading ? (
                            <div className="flex justify-center items-center h-[200px]">
                                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                            </div>
                        ) : error ? (
                            <div className="p-6 text-center text-red-500">{error}</div>
                        ) : data ? (
                            <div className="relative w-full overflow-auto">
                                <TooltipProvider>
                                    <table className="w-full text-sm caption-bottom">
                                        <thead className="[&_tr]:border-b">
                                            <tr className="border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted">
                                                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground w-1/3"></th>
                                                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Total</th>
                                                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Positive</th>
                                                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Negative</th>
                                            </tr>
                                        </thead>
                                        <tbody className="[&_tr:last-child]:border-0">
                                            {/* 1 Std. Deviation of Avg. Trade */}
                                            <tr className="border-b transition-colors hover:bg-muted/50">
                                                <td className="p-4 align-middle font-medium">
                                                    <HeaderWithTooltip
                                                        text="1 Std. Deviation of Avg. Trade"
                                                        tooltip="Measures 1 standard deviation of average trade."
                                                    />
                                                </td>
                                                <td className="p-4 align-middle">{formatCurrency(data.total.std_dev)}</td>
                                                <td className="p-4 align-middle">{formatCurrency(data.positive.std_dev)}</td>
                                                <td className="p-4 align-middle">{formatCurrency(data.negative.std_dev)}</td>
                                            </tr>
                                            {/* Avg. Trade + 1 Std. Deviation */}
                                            <tr className="border-b transition-colors hover:bg-muted/50">
                                                <td className="p-4 align-middle font-medium">
                                                    <HeaderWithTooltip
                                                        text="Avg. Trade + 1 Std. Deviation"
                                                        tooltip="Measures extreme positive range of trades."
                                                    />
                                                </td>
                                                <td className="p-4 align-middle">{formatCurrency(data.total.upper_bound)}</td>
                                                <td className="p-4 align-middle">{formatCurrency(data.positive.upper_bound)}</td>
                                                <td className="p-4 align-middle">{formatCurrency(data.negative.upper_bound)}</td>
                                            </tr>
                                            {/* Avg. Trade - 1 Std. Deviation */}
                                            <tr className="border-b transition-colors hover:bg-muted/50">
                                                <td className="p-4 align-middle font-medium">
                                                    <HeaderWithTooltip
                                                        text="Avg. Trade - 1 Std. Deviation"
                                                        tooltip="Measures extreme negative range of trades."
                                                    />
                                                </td>
                                                <td className="p-4 align-middle">{formatCurrency(data.total.lower_bound)}</td>
                                                <td className="p-4 align-middle">{formatCurrency(data.positive.lower_bound)}</td>
                                                <td className="p-4 align-middle">{formatCurrency(data.negative.lower_bound)}</td>
                                            </tr>
                                            {/* Number of Outliers */}
                                            <tr className="border-b transition-colors hover:bg-muted/50">
                                                <td className="p-4 align-middle font-medium">
                                                    <HeaderWithTooltip
                                                        text="Number of Outliers"
                                                        tooltip="Displays the total number of trades not within the normal range of Profit or Loss for the Strategy. An outlier is defined as a trade which does not appear to fall within the expected range (of the specified standard deviations) for all trades."
                                                    />
                                                </td>
                                                <td className="p-4 align-middle">{formatNumber(data.total.outlier_count)}</td>
                                                <td className="p-4 align-middle">{formatNumber(data.positive.outlier_count)}</td>
                                                <td className="p-4 align-middle">{formatNumber(data.negative.outlier_count)}</td>
                                            </tr>
                                            {/* Outlier Profit/Loss */}
                                            <tr className="border-b transition-colors hover:bg-muted/50">
                                                <td className="p-4 align-middle font-medium">
                                                    <HeaderWithTooltip
                                                        text="Outlier Profit/Loss"
                                                        tooltip="Displays the profit or loss for all outliers during the specified period."
                                                    />
                                                </td>
                                                <td className="p-4 align-middle">{formatCurrency(data.total.outlier_pnl)}</td>
                                                <td className="p-4 align-middle">{formatCurrency(data.positive.outlier_pnl)}</td>
                                                <td className="p-4 align-middle">{formatCurrency(data.negative.outlier_pnl)}</td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </TooltipProvider>
                            </div>
                        ) : (
                            <div className="p-6 text-center text-muted-foreground">No data available.</div>
                        )}
                     </CardContent>
                </Card>
            </div>
        </div>
    )
}
