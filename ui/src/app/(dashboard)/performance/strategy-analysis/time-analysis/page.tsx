"use client"

import { useEffect, useState } from "react"
import { PerformancePageHeader } from "@/components/performance/performance-page-header"
import { useSelectedBacktest } from "@/contexts/selected-backtest-context"
import { strategyApi } from "@/lib/api/strategies"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Loader2 } from "lucide-react"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

export default function TimeAnalysisPage() {
    const { selectedBacktest } = useSelectedBacktest()
    const [data, setData] = useState<Record<string, string> | null>(null)
    const [loading, setLoading] = useState(false)

    useEffect(() => {
        const fetchData = async () => {
            if (!selectedBacktest) return

            setLoading(true)
            try {
                let trades = selectedBacktest.trades || []

                // If trades are missing but we have an ID, fetch them
                if (trades.length === 0 && selectedBacktest.backtest_id) {
                     try {
                        const fullBacktest = await strategyApi.getBacktestById(selectedBacktest.backtest_id)
                        trades = fullBacktest.trades || []
                     } catch (err) {
                        console.error("Failed to fetch full backtest details", err)
                     }
                }

                const response = await strategyApi.getTimeAnalysis(trades, selectedBacktest.initial_balance || 10000)
                setData(response)
            } catch (error) {
                console.error("Failed to fetch time analysis:", error)
            } finally {
                setLoading(false)
            }
        }

        fetchData()
    }, [selectedBacktest])

    if (!selectedBacktest) {
         return (
            <div className="flex flex-col h-full w-full">
                <PerformancePageHeader title="Time Analysis" />
                <div className="flex-1 flex items-center justify-center p-6">
                    <div className="text-center text-muted-foreground ml-4">
                        Please select a backtest to view time analysis.
                    </div>
                </div>
            </div>
         )
    }

    return (
        <div className="flex flex-col h-full w-full">
            <PerformancePageHeader title="Time Analysis" />
            <div className="container max-w-4xl p-6 mx-auto">
                 {loading ? (
                    <div className="flex justify-center p-12">
                        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                    </div>
                 ) : data ? (
                    <Card>
                        <CardHeader className="py-3 bg-muted/50 border-b">
                            <CardTitle className="text-sm font-medium">Time Statistics</CardTitle>
                        </CardHeader>
                        <CardContent className="p-0">
                             <div className="divide-y">
                                {Object.entries(data).map(([key, value]) => (
                                    <div key={key} className="flex justify-between py-3 px-6 hover:bg-muted/50 transition-colors bg-card">
                                        <TooltipProvider>
                                            <Tooltip>
                                                <TooltipTrigger asChild>
                                                    <span className="text-sm font-medium text-foreground cursor-help decoration-dotted underline-offset-4 hover:underline">
                                                        {key}
                                                    </span>
                                                </TooltipTrigger>
                                                <TooltipContent>
                                                    <p className="max-w-xs">{getTooltip(key)}</p>
                                                </TooltipContent>
                                            </Tooltip>
                                        </TooltipProvider>
                                        <span className="text-sm font-medium text-foreground">{value}</span>
                                    </div>
                                ))}
                             </div>
                        </CardContent>
                    </Card>
                 ) : (
                    <div className="text-center text-muted-foreground p-12 bg-muted/10 rounded-lg border border-dashed">
                        No time analysis data available for this backtest.
                    </div>
                 )}
            </div>
        </div>
    )
}

function getTooltip(key: string): string {
    const tooltips: Record<string, string> = {
        "Trading Period": "Total duration of the trading period, spanning from the first trade's open time to the last trade's close time.",
        "Time in the Market": "Total cumulative duration where at least one position was open. Overlapping positions are merged.",
        "Percent in the Market": "Percentage of the total trading period where the strategy had an active position in the market.",
        "Longest flat period": "Longest continuous duration where the strategy had no open positions (was flat).",
        "Max Run-up Date": "The date when the equity curve reached its peak value during the maximum run-up phase.",
        "Max Drawdown Date": "The date when the equity curve reached its lowest point (deepest valley) during the maximum drawdown.",
        "Max Close To Close Drawdown Date": "The close date of the trade that marked the bottom of the maximum drawdown calculated on a close-to-close basis."
    }
    return tooltips[key] || "Time-based performance metric."
}
