"use client"

import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { ArrowLeft, Download, Share2, Loader2 } from "lucide-react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { EquityChart } from "./charts/equity-chart"
import { PriceChart } from "./charts/price-chart"
import { TradeList } from "./tables/trade-list"
import { toast } from "sonner"
import { strategyApi, type Backtest } from "@/lib/api/strategies"

interface BacktestResultsViewProps {
    backtestId: number
    strategyId: number
    onBack: () => void
}

export function BacktestResultsView({ backtestId, strategyId, onBack }: BacktestResultsViewProps) {
    const [backtest, setBacktest] = useState<Backtest | null>(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        const fetchBacktestResults = async () => {
            try {
                setLoading(true)
                const result = await strategyApi.getBacktest(strategyId, backtestId)
                setBacktest(result)
            } catch (error) {
                console.error("Error fetching backtest results:", error)
                toast.error("Failed to load backtest results")
            } finally {
                setLoading(false)
            }
        }

        fetchBacktestResults()
    }, [backtestId, strategyId])
    const handleExport = () => {
        if (!backtest || !backtest.trades) {
            toast.error("No trade data available to export")
            return
        }

        const headers = ["ID", "Time", "Type", "Symbol", "Price", "Volume", "Profit"]
        const csvContent = [
            headers.join(","),
            ...backtest.trades.map((t: any, idx: number) =>
                `${idx + 1},${t.time || "N/A"},${t.type || "N/A"},${backtest.symbol || "N/A"},${t.price || 0},${t.volume || 0},${t.profit || 0}`
            )
        ].join("\n")

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
        const url = URL.createObjectURL(blob)
        const link = document.createElement("a")
        link.setAttribute("href", url)
        link.setAttribute("download", `backtest_${backtestId}_report.csv`)
        link.style.visibility = 'hidden'
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)

        toast.success("Report downloaded successfully")
    }

    if (loading) {
        return (
            <div className="flex items-center justify-center h-[400px]">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        )
    }

    if (!backtest) {
        return (
            <div className="text-center py-12">
                <p className="text-muted-foreground">No backtest results available.</p>
                <Button variant="outline" onClick={onBack} className="mt-4">
                    <ArrowLeft className="mr-2 h-4 w-4" />
                    Back to Config
                </Button>
            </div>
        )
    }

    return (
        <div className="space-y-6">
            {/* Header / Actions */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <Button variant="ghost" onClick={onBack} className="pl-0 hover:pl-2 transition-all">
                    <ArrowLeft className="mr-2 h-4 w-4" />
                    Back to Config
                </Button>
                <div className="flex gap-2">
                    <Button variant="outline" size="sm">
                        <Share2 className="mr-2 h-4 w-4" />
                        Share
                    </Button>
                     <Button variant="outline" size="sm" onClick={handleExport}>
                        <Download className="mr-2 h-4 w-4" />
                        Export Report
                    </Button>
                </div>
            </div>

            {/* Key Metrics Summary */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <Card>
                    <CardHeader className="p-4 pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground">Total Return</CardTitle>
                    </CardHeader>
                    <CardContent className="p-4 pt-0">
                        <div className={`text-2xl font-bold ${(backtest.total_return || 0) >= 0 ? 'text-emerald-500' : 'text-red-500'}`}>
                            {(backtest.total_return || 0) >= 0 ? '+' : ''}{(backtest.total_return || 0).toFixed(2)}%
                        </div>
                        <p className="text-xs text-muted-foreground">Symbol: {backtest.symbol || 'N/A'}</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="p-4 pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground">Sharpe Ratio</CardTitle>
                    </CardHeader>
                    <CardContent className="p-4 pt-0">
                        <div className="text-2xl font-bold">{(backtest.sharpe_ratio || 0).toFixed(2)}</div>
                        <p className="text-xs text-muted-foreground">Timeframe: {backtest.timeframe || 'N/A'}</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="p-4 pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground">Max Drawdown</CardTitle>
                    </CardHeader>
                    <CardContent className="p-4 pt-0">
                        <div className="text-2xl font-bold text-red-500">{(backtest.max_drawdown || 0).toFixed(2)}%</div>
                        <p className="text-xs text-muted-foreground">Total Trades: {backtest.total_trades || 0}</p>
                    </CardContent>
                </Card>
                <Card>
                     <CardHeader className="p-4 pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground">Win Rate</CardTitle>
                    </CardHeader>
                    <CardContent className="p-4 pt-0">
                        <div className="text-2xl font-bold">{(backtest.win_rate || 0).toFixed(1)}%</div>
                        <p className="text-xs text-muted-foreground">PF: {(backtest.profit_factor || 0).toFixed(2)}</p>
                    </CardContent>
                </Card>
            </div>

            {/* Detailed Views */}
            <Tabs defaultValue="overview" className="space-y-4">
                <TabsList>
                    <TabsTrigger value="overview">Overview</TabsTrigger>
                    <TabsTrigger value="analysis">Price Chart (Markers)</TabsTrigger>
                    <TabsTrigger value="trades">Trades</TabsTrigger>
                    <TabsTrigger value="metrics">Detailed Metrics</TabsTrigger>
                </TabsList>

                <TabsContent value="overview" className="space-y-4">
                     <EquityChart equityCurve={backtest.equity_curve} />
                </TabsContent>

                <TabsContent value="analysis">
                    <PriceChart />
                </TabsContent>

                <TabsContent value="trades">
                    <TradeList trades={backtest.trades || []} />
                </TabsContent>

                <TabsContent value="metrics">
                    <Card>
                        <CardContent className="p-6">
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                                <div className="space-y-4">
                                    <h3 className="font-semibold text-lg border-b pb-2">Trading Activity</h3>
                                    <div className="grid grid-cols-2 gap-2 text-sm">
                                        <span className="text-muted-foreground">Total Trades</span>
                                        <span className="font-mono text-right">142</span>
                                        <span className="text-muted-foreground">Longs</span>
                                        <span className="font-mono text-right">80 (56%)</span>
                                        <span className="text-muted-foreground">Shorts</span>
                                        <span className="font-mono text-right">62 (44%)</span>
                                    </div>
                                </div>
                                <div className="space-y-4">
                                     <h3 className="font-semibold text-lg border-b pb-2">Averages</h3>
                                     <div className="grid grid-cols-2 gap-2 text-sm">
                                        <span className="text-muted-foreground">Avg Profit</span>
                                        <span className="font-mono text-right text-emerald-500">$45.20</span>
                                        <span className="text-muted-foreground">Avg Loss</span>
                                        <span className="font-mono text-right text-red-500">-$28.50</span>
                                        <span className="text-muted-foreground">Avg Holding</span>
                                        <span className="font-mono text-right">4h 12m</span>
                                     </div>
                                </div>
                                <div className="space-y-4">
                                    <h3 className="font-semibold text-lg border-b pb-2">Streaks</h3>
                                     <div className="grid grid-cols-2 gap-2 text-sm">
                                        <span className="text-muted-foreground">Max Consec. Wins</span>
                                        <span className="font-mono text-right">8</span>
                                        <span className="text-muted-foreground">Max Consec. Losses</span>
                                        <span className="font-mono text-right">4</span>
                                     </div>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    )
}
