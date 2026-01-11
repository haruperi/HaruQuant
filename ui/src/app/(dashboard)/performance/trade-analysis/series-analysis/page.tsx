"use client"

import { useEffect, useState } from "react"
import { PerformancePageHeader } from "@/components/performance/performance-page-header"
import { useSelectedBacktest } from "@/contexts/selected-backtest-context"
import { strategyApi } from "@/lib/api/strategies"
import { Card, CardContent } from "@/components/ui/card"
import { Loader2, AlertCircle } from "lucide-react"

interface SeriesAnalysisResponse {
    z_score: number
    confidence_limits: string
    strategy_me: number
    max_consec_winners: number
    max_consec_losers: number
    largest_consec_profit: number
    largest_consec_loss: number
    largest_consec_profit_pct: number
    largest_consec_loss_pct: number
}

const formatCurrency = (val: number) => {
    const absVal = Math.abs(val)
    const str = `$${absVal.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
    return val < 0 ? <span className="text-red-500">({str})</span> : <span>{str}</span>
}

const formatPercent = (val: number) => {
    const absVal = Math.abs(val)
    const str = `${absVal.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`
     return val < 0 ? <span className="text-red-500">({str})</span> : <span>{str}</span>
}

export default function SeriesAnalysisPage() {
    const { selectedBacktest } = useSelectedBacktest()
    const [data, setData] = useState<SeriesAnalysisResponse | null>(null)
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

                const result = await strategyApi.getSeriesAnalysisReport(trades, selectedBacktest.initial_balance || 10000)
                setData(result)

             } catch (err) {
                 console.error("Failed to fetch series analysis:", err)
                 setError("Failed to load series analysis.")
             } finally {
                 setLoading(false)
             }
        }

        fetchData()
    }, [selectedBacktest])

    if (!selectedBacktest) {
        return (
            <div className="flex flex-col h-full w-full">
                <PerformancePageHeader title="Series Analysis" />
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
             <PerformancePageHeader title="Trade Series Analysis" />
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
                            <div className="flex flex-col h-full">
                                <table className="w-full text-sm caption-bottom border-b">
                                    <tbody className="[&_tr]:border-b [&_tr:last-child]:border-0">
                                         <tr className="transition-colors hover:bg-muted/50">
                                            <td className="p-2 px-4 align-middle font-medium w-1/3">Z-score</td>
                                            <td className="p-2 px-4 align-middle">{data.z_score.toFixed(2)}</td>
                                        </tr>
                                        <tr className="transition-colors hover:bg-muted/50">
                                            <td className="p-2 px-4 align-middle font-medium">Confidence Limits</td>
                                            <td className="p-2 px-4 align-middle">{data.confidence_limits}</td>
                                        </tr>
                                        <tr className="transition-colors hover:bg-muted/50">
                                            <td className="p-2 px-4 align-middle font-medium">Strategy ME</td>
                                            <td className="p-2 px-4 align-middle">{formatCurrency(data.strategy_me)}</td>
                                        </tr>
                                        <tr className="transition-colors hover:bg-muted/50">
                                            <td className="p-2 px-4 align-middle font-medium">Max Consec. Winners</td>
                                            <td className="p-2 px-4 align-middle">{data.max_consec_winners}</td>
                                        </tr>
                                        <tr className="transition-colors hover:bg-muted/50">
                                            <td className="p-2 px-4 align-middle font-medium">Max Consec. Losers</td>
                                            <td className="p-2 px-4 align-middle">{data.max_consec_losers}</td>
                                        </tr>
                                        <tr className="transition-colors hover:bg-muted/50">
                                            <td className="p-2 px-4 align-middle font-medium">Largest Consec. Profit</td>
                                            <td className="p-2 px-4 align-middle">{formatCurrency(data.largest_consec_profit)}</td>
                                        </tr>
                                        <tr className="transition-colors hover:bg-muted/50">
                                            <td className="p-2 px-4 align-middle font-medium">Largest Consec. Loss</td>
                                            <td className="p-2 px-4 align-middle">{formatCurrency(data.largest_consec_loss)}</td>
                                        </tr>
                                         <tr className="transition-colors hover:bg-muted/50">
                                            <td className="p-2 px-4 align-middle font-medium">Largest Consec. Profit (%)</td>
                                            <td className="p-2 px-4 align-middle">{formatPercent(data.largest_consec_profit_pct)}</td>
                                        </tr>
                                         <tr className="transition-colors hover:bg-muted/50">
                                            <td className="p-2 px-4 align-middle font-medium">Largest Consec. Loss (%)</td>
                                            <td className="p-2 px-4 align-middle">{formatPercent(data.largest_consec_loss_pct)}</td>
                                        </tr>
                                    </tbody>
                                </table>

                                {/* Descriptions */}
                                <div className="p-4 bg-muted/20 border-t">
                                     <h3 className="font-semibold mb-2 flex items-center gap-2">
                                        Description
                                    </h3>
                                    <div className="space-y-4 text-xs text-muted-foreground">
                                        <div>
                                            <h4 className="font-semibold text-foreground mb-1">Z-score</h4>
                                            <p>The runs test will tell us if our system has more (or fewer) streaks of consecutive wins and losses than a random distribution. The runs test is essentially a matter of obtaining the Z scores for the win and loss streaks of a systems trades. A Z score is how many standard deviations you are away from the mean of a distribution. Thus, a Z score of 2.00 is 2.00 standard deviations away from the mean (the expectation of a random distribution of streaks of wins and losses).</p>
                                        </div>
                                         <div>
                                            <h4 className="font-semibold text-foreground mb-1">Confidence Limits</h4>
                                            <p>The Z score is then converted into a confidence limit, sometimes also called a degree of certainty. The area under the curve of the Normal Probability Function at 1 standard deviation on either side of the mean equals 68% of the total area under the curve. So we take our Z score and convert it to a confidence limit, the relationship being that the Z score is a number of standard deviations from the mean and the confidence limit is the percentage of area under the curve occupied at so many standard deviations.</p>
                                        </div>
                                         <div>
                                            <h4 className="font-semibold text-foreground mb-1">Strategy ME</h4>
                                            <p>By the same token, you are better off not to trade unless there is absolutely overwhelming evidence that the market system you are contemplating trading will be profitable-that is, unless you fully expect the market system in question to have a positive mathematical expectation when you trade it realtime. Mathematical expectation is the amount you expect to make or lose, on average, each bet.</p>
                                        </div>
                                    </div>
                                </div>
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
