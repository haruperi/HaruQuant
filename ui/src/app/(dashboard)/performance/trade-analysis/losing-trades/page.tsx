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
    ScatterChart,
    Scatter,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ReferenceLine,
} from "recharts"

interface TradePoint {
    trade_number: number
    profit_loss: number
    is_outlier: boolean
    type: string | null
}

interface LosingTradesData {
    trades: TradePoint[]
    average: number
}

const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(value)
}

// Custom Tooltip
const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
        const data = payload[0].payload
        return (
            <div className="bg-slate-950 border border-slate-800 p-3 rounded-lg shadow-xl text-sm">
                <p className="font-medium text-slate-200">Trade #{data.trade_number}</p>
                <div className="mt-2 space-y-1">
                    <div className="flex items-center justify-between gap-4">
                        <span className="text-slate-400">Loss:</span>
                        <span className="font-mono text-red-400">
                            {formatCurrency(data.profit_loss)}
                        </span>
                    </div>
                    {data.type && (
                        <div className="flex items-center justify-between gap-4">
                            <span className="text-slate-400">Type:</span>
                            <span className="font-mono text-slate-200 capitalize">{data.type}</span>
                        </div>
                    )}
                    {data.is_outlier && (
                        <div className="text-red-400 text-xs">Losing Outlier</div>
                    )}
                </div>
            </div>
        )
    }
    return null
}

export default function Page() {
    const { selectedBacktest } = useSelectedBacktest()
    const [data, setData] = useState<LosingTradesData | null>(null)
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
                 if(!selectedBacktest.trades) {
                     setError("No trade data available in selected backtest.")
                     setLoading(false)
                     return
                 }
            }

            try {
                setLoading(true)
                setError(null)
                const result = await strategyApi.getLosingTradesAnalysis(
                    trades,
                    initialBalance
                )

                setData(result)
            } catch (err) {
                console.error(err)
                setError("Failed to generate losing trades chart.")
            } finally {
                setLoading(false)
            }
        }

        fetchData()
    }, [selectedBacktest])

    if (!selectedBacktest) {
        return (
            <div className="flex flex-col h-full w-full">
                <PerformancePageHeader title="Losing Trades" />
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

    // Separate trades into regular and outliers
    const regularTrades = data?.trades.filter(t => !t.is_outlier) || []
    const outliers = data?.trades.filter(t => t.is_outlier) || []

    return (
        <div className="flex flex-col h-full w-full overflow-hidden">
            <PerformancePageHeader title="Losing Trades" />
            <div className="flex-1 overflow-auto p-4 md:p-6 bg-muted/10">
                <Card className="h-full border-t-4 border-t-red-500/50 flex flex-col">
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
                        ) : data && data.trades.length > 0 ? (
                            <ResponsiveContainer width="100%" height="100%">
                                <ScatterChart
                                    margin={{ top: 20, right: 30, left: 20, bottom: 60 }}
                                >
                                    <CartesianGrid strokeDasharray="3 3" vertical={true} horizontal={true} stroke="#334155" opacity={0.5} />
                                    <XAxis
                                        type="number"
                                        dataKey="trade_number"
                                        name="Trade Number"
                                        label={{ value: "Trade Number", position: "insideBottom", offset: -10 }}
                                        tick={{ fontSize: 12, fill: '#94a3b8' }}
                                        domain={[0, 'auto']}
                                    />
                                    <YAxis
                                        type="number"
                                        dataKey="profit_loss"
                                        name="Loss"
                                        tickFormatter={(val) => formatCurrency(val)}
                                        label={{ value: "Loss ($)", angle: -90, position: "insideLeft" }}
                                        tick={{ fontSize: 12, fill: '#94a3b8' }}
                                        width={80}
                                        domain={['auto', 0]}
                                    />
                                    <Tooltip content={<CustomTooltip />} cursor={{ strokeDasharray: '3 3' }} />
                                    <Legend
                                        verticalAlign="bottom"
                                        height={36}
                                        wrapperStyle={{ paddingTop: '20px' }}
                                    />

                                    {/* Average line */}
                                    <ReferenceLine
                                        y={data.average}
                                        stroke="#94a3b8"
                                        strokeDasharray="3 3"
                                        label={{ value: 'Average', position: 'right', fill: '#94a3b8', fontSize: 12 }}
                                    />

                                    {/* Zero line */}
                                    <ReferenceLine y={0} stroke="#64748b" strokeWidth={1.5} />

                                    {/* Regular losing trades - light gray dots */}
                                    <Scatter
                                        name="Losing Trades"
                                        data={regularTrades}
                                        fill="#cbd5e1"
                                        shape="circle"
                                    />

                                    {/* Losing outliers - bright red squares */}
                                    {outliers.length > 0 && (
                                        <Scatter
                                            name="Losing Outliers"
                                            data={outliers}
                                            fill="#f87171"
                                            shape="square"
                                        />
                                    )}
                                </ScatterChart>
                            </ResponsiveContainer>
                        ) : (
                             !loading && <div className="flex items-center justify-center h-full text-muted-foreground">No losing trades to display.</div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}
