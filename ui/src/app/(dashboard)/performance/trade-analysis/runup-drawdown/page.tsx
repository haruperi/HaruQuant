"use client"

import { useEffect, useState } from "react"
import { PerformancePageHeader } from "@/components/performance/performance-page-header"
import { useSelectedBacktest } from "@/contexts/selected-backtest-context"
import { strategyApi } from "@/lib/api/strategies"
import { Card, CardContent } from "@/components/ui/card"
import { Loader2, AlertCircle } from "lucide-react"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"

interface Stats {
    max: number
    max_date: string | null
    avg: number
    max_pct: number
    max_pct_date: string | null
    avg_pct: number
    std: number
    mean: number
    upper_bound: number
    lower_bound: number
}

interface RunupDrawdownResponse {
    runup: Stats
    drawdown: Stats
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

const formatPercent = (val: number) => {
    const absVal = Math.abs(val)
    const str = `${absVal.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`
     return val < 0 ? <span className="text-red-500">({str})</span> : <span>{str}</span>
}

const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "N/A"
    const date = new Date(dateStr)
    return date.toLocaleString("en-US", {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: 'numeric',
        minute: 'numeric',
        second: 'numeric',
        hour12: true
    })
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

export default function RunupDrawdownPage() {
    const { selectedBacktest } = useSelectedBacktest()
    const [data, setData] = useState<RunupDrawdownResponse | null>(null)
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

                const result = await strategyApi.getRunupDrawdownReport(trades, selectedBacktest.initial_balance || 10000)
                setData(result)

             } catch (err) {
                 console.error("Failed to fetch runup/drawdown:", err)
                 setError("Failed to load runup/drawdown analysis.")
             } finally {
                 setLoading(false)
             }
        }

        fetchData()
    }, [selectedBacktest])

    if (!selectedBacktest) {
        return (
            <div className="flex flex-col h-full w-full">
                <PerformancePageHeader title="Run-up/Drawdown" />
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
            <PerformancePageHeader title="Run-up/Drawdown" />
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
                                                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Run-up</th>
                                                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Drawdown</th>
                                            </tr>
                                        </thead>
                                        <tbody className="[&_tr:last-child]:border-0">
                                            <tr className="border-b transition-colors hover:bg-muted/50">
                                                <td className="p-4 align-middle font-medium">
                                                    <HeaderWithTooltip text="Max Value" tooltip="Displays the maximum profit or loss that occurred across all the trades." />
                                                </td>
                                                <td className="p-4 align-middle">{formatCurrency(data.runup.max)}</td>
                                                <td className="p-4 align-middle">{formatCurrency(data.drawdown.max)}</td>
                                            </tr>
                                            <tr className="border-b transition-colors hover:bg-muted/50">
                                                <td className="p-4 align-middle font-medium">
                                                    <HeaderWithTooltip text="Max Value Date" tooltip="Displays the date on which maximum profit or loss occurred across all the trades." />
                                                </td>
                                                <td className="p-4 align-middle">{formatDate(data.runup.max_date)}</td>
                                                <td className="p-4 align-middle">{formatDate(data.drawdown.max_date)}</td>
                                            </tr>
                                            <tr className="border-b transition-colors hover:bg-muted/50">
                                                <td className="p-4 align-middle font-medium">
                                                    <HeaderWithTooltip text="Avg Value" tooltip="Displays the average profit or loss that occurred across all the trades." />
                                                </td>
                                                <td className="p-4 align-middle">{formatCurrency(data.runup.avg)}</td>
                                                <td className="p-4 align-middle">{formatCurrency(data.drawdown.avg)}</td>
                                            </tr>
                                            <tr className="border-b transition-colors hover:bg-muted/50">
                                                <td className="p-4 align-middle font-medium">
                                                    <HeaderWithTooltip text="Max Value (%)" tooltip="Displays the maximum run-up/drawdown percentage." />
                                                </td>
                                                <td className="p-4 align-middle">{formatPercent(data.runup.max_pct)}</td>
                                                <td className="p-4 align-middle">{formatPercent(data.drawdown.max_pct)}</td>
                                            </tr>
                                            <tr className="border-b transition-colors hover:bg-muted/50">
                                                <td className="p-4 align-middle font-medium">
                                                    <HeaderWithTooltip text="Max Value (%) Date" tooltip="Displays the date of maximum run-up/drawdown percentage." />
                                                </td>
                                                <td className="p-4 align-middle">{formatDate(data.runup.max_pct_date)}</td>
                                                <td className="p-4 align-middle">{formatDate(data.drawdown.max_pct_date)}</td>
                                            </tr>
                                            <tr className="border-b transition-colors hover:bg-muted/50">
                                                <td className="p-4 align-middle font-medium">
                                                    <HeaderWithTooltip text="Avg Value (%)" tooltip="Displays the average run-up/drawdown percentage." />
                                                </td>
                                                <td className="p-4 align-middle">{formatPercent(data.runup.avg_pct)}</td>
                                                <td className="p-4 align-middle">{formatPercent(data.drawdown.avg_pct)}</td>
                                            </tr>
                                            <tr className="border-b transition-colors hover:bg-muted/50">
                                                <td className="p-4 align-middle font-medium">
                                                    <HeaderWithTooltip text="1 Std. Deviation" tooltip="Measures 1 standard deviation of average trade." />
                                                </td>
                                                <td className="p-4 align-middle">{formatCurrency(data.runup.std)}</td>
                                                <td className="p-4 align-middle">{formatCurrency(data.drawdown.std)}</td>
                                            </tr>
                                            <tr className="border-b transition-colors hover:bg-muted/50">
                                                <td className="p-4 align-middle font-medium">
                                                    <HeaderWithTooltip text="Avg. Trade + 1 Std. Deviation" tooltip="Avg trade plus 1 standard deviation." />
                                                </td>
                                                <td className="p-4 align-middle">{formatCurrency(data.runup.upper_bound)}</td>
                                                <td className="p-4 align-middle">{formatCurrency(data.drawdown.upper_bound)}</td>
                                            </tr>
                                            <tr className="border-b transition-colors hover:bg-muted/50">
                                                <td className="p-4 align-middle font-medium">
                                                    <HeaderWithTooltip text="Avg. Trade - 1 Std. Deviation" tooltip="Avg trade minus 1 standard deviation." />
                                                </td>
                                                <td className="p-4 align-middle">{formatCurrency(data.runup.lower_bound)}</td>
                                                <td className="p-4 align-middle">{formatCurrency(data.drawdown.lower_bound)}</td>
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
