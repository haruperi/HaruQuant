"use client"

import { useEffect, useState } from "react"
import { PerformancePageHeader } from "@/components/performance/performance-page-header"
import { useSelectedBacktest } from "@/contexts/selected-backtest-context"
import { strategyApi } from "@/lib/api/strategies"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Loader2, AlertCircle } from "lucide-react"

interface StreakStat {
    count: number
    avg_series: number
    avg_next: number
}

interface SeriesStatsRow {
    length: number
    win_series: StreakStat
    loss_series: StreakStat
}

interface SeriesStatsResponse {
    stats: SeriesStatsRow[]
}

const formatCurrency = (val: number) => {
    const absVal = Math.abs(val)
    const str = `$${absVal.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
    return val < 0 ? <span className="text-red-500">({str})</span> : <span>{str}</span>
}

export default function SeriesStatsPage() {
    const { selectedBacktest } = useSelectedBacktest()
    const [data, setData] = useState<SeriesStatsResponse | null>(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        const fetchData = async () => {
             if (!selectedBacktest) return

             setLoading(true)
             setError(null)
             try {
                let trades = selectedBacktest.trades || []

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

                const result = await strategyApi.getSeriesStatsReport(trades)
                setData(result)

             } catch (err) {
                 console.error("Failed to fetch series stats:", err)
                 setError("Failed to load series statistics.")
             } finally {
                 setLoading(false)
             }
        }

        fetchData()
    }, [selectedBacktest])

    if (!selectedBacktest) {
        return (
            <div className="flex flex-col h-full w-full">
                <PerformancePageHeader title="Trade Series Statistics" />
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
             <PerformancePageHeader title="Trade Series Statistics" />
             <div className="flex-1 overflow-auto p-4 md:p-6 bg-muted/10">
                <Card className="min-h-full border-t-4 border-t-primary/20">
                     <CardHeader className="pb-2">
                        <CardTitle className="text-lg font-medium">Trade Series Statistics</CardTitle>
                    </CardHeader>
                    <CardContent className="p-0">
                         {loading ? (
                            <div className="flex justify-center items-center h-[200px]">
                                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                            </div>
                        ) : error ? (
                            <div className="p-6 text-center text-red-500">{error}</div>
                        ) : data && data.stats.length > 0 ? (
                            <div className="overflow-x-auto">
                                <table className="w-full text-sm border-collapse">
                                    <thead>
                                        <tr>
                                            <th className="border p-2 bg-muted/30 w-10 text-center" rowSpan={2}>#</th>
                                            <th className="border p-2 bg-blue-100 dark:bg-blue-900/30 text-center font-bold" colSpan={3}>Winning Trade Series</th>
                                            <th className="border p-2 bg-red-100 dark:bg-red-900/30 text-center font-bold" colSpan={3}>Losing Trade Series</th>
                                        </tr>
                                        <tr>
                                            {/* Winning headers */}
                                            <th className="border p-2 bg-blue-50 dark:bg-blue-900/10 text-center font-semibold"># of series</th>
                                            <th className="border p-2 bg-blue-50 dark:bg-blue-900/10 text-center font-semibold">Avg Win /<br/>Avg Series</th>
                                            <th className="border p-2 bg-blue-50 dark:bg-blue-900/10 text-center font-semibold">Avg Loss<br/>Next Trade</th>

                                            {/* Losing headers */}
                                            <th className="border p-2 bg-red-50 dark:bg-red-900/10 text-center font-semibold"># of series</th>
                                            <th className="border p-2 bg-red-50 dark:bg-red-900/10 text-center font-semibold">Avg Loss /<br/>Avg Series</th>
                                            <th className="border p-2 bg-red-50 dark:bg-red-900/10 text-center font-semibold">Avg Win<br/>Next Trade</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {data.stats.map((row) => (
                                            <tr key={row.length} className="hover:bg-muted/50 transition-colors">
                                                <td className="border p-2 text-center font-medium bg-muted/10">{row.length}</td>

                                                {/* Winning Data */}
                                                <td className="border p-2 text-center">{row.win_series.count > 0 ? row.win_series.count : ""}</td>
                                                <td className="border p-2 text-center">{row.win_series.count > 0 ? formatCurrency(row.win_series.avg_series) : ""}</td>
                                                <td className="border p-2 text-center">{row.win_series.count > 0 ? formatCurrency(row.win_series.avg_next) : ""}</td>

                                                {/* Losing Data */}
                                                <td className="border p-2 text-center">{row.loss_series.count > 0 ? row.loss_series.count : ""}</td>
                                                <td className="border p-2 text-center">{row.loss_series.count > 0 ? formatCurrency(row.loss_series.avg_series) : ""}</td>
                                                <td className="border p-2 text-center">{row.loss_series.count > 0 ? formatCurrency(row.loss_series.avg_next) : ""}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        ) : (
                            <div className="p-6 text-center text-muted-foreground">No series data available.</div>
                        )}
                    </CardContent>
                </Card>
             </div>
        </div>
    )
}
