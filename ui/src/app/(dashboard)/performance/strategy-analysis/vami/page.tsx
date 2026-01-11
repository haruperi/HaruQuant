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
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend
} from "recharts"

interface EquityPoint {
    date: string
    open_time?: string
    equity_close: number
    equity_high: number
    equity_low: number
    drawdown_usd: number
    drawdown_pct: number
    buy_hold_return_usd: number
    vami: number

    trade_number?: number
}

const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(value)
}

const formatPercentage = (value: number) => {
    return new Intl.NumberFormat('en-US', { style: 'percent', minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(value / 100)
}

const formatDate = (dateStr: string) => {
    if (!dateStr) return ""
    try {
        const date = new Date(dateStr)
        return date.toLocaleString()
    } catch (e) {
        return dateStr
    }
}

// Custom Tooltip for dark mode contrast
const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
        const dataPoint = payload[0].payload;
        return (
            <div className="bg-slate-950 border border-slate-800 p-3 rounded-lg shadow-xl text-sm">
                <p className="font-medium text-slate-200">Trade #{label}</p>
                {dataPoint.open_time && (
                    <p className="text-xs text-slate-500 mb-2">{formatDate(dataPoint.open_time)}</p>
                )}
                {!dataPoint.open_time && <div className="mb-2"></div>}

                {payload
                    .filter((entry: any) => entry.name !== 'trade_number' && entry.dataKey !== 'trade_number')
                    .map((entry: any, index: number) => (
                    <div key={index} className="flex items-center justify-between gap-4 py-0.5">
                        <div className="flex items-center gap-2">
                            <div
                                className="w-2 h-2 rounded-full"
                                style={{ backgroundColor: entry.color || entry.fill || entry.stroke }}
                            />
                            <span className="text-slate-400">{entry.name}</span>
                        </div>
                        <span className="font-mono text-slate-200">
                            {entry.name.includes('%')
                                ? formatPercentage(entry.value)
                                : formatCurrency(entry.value)}
                        </span>
                    </div>
                ))}
            </div>
        )
    }
    return null
}

export default function Page() {
    const { selectedBacktest } = useSelectedBacktest()
    const [data, setData] = useState<EquityPoint[] | null>(null)
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
                const result = await strategyApi.getEquityCurveDetailed(
                    trades,
                    initialBalance
                )

                // Add index for 'Trade #'
                const processedData = result.map((point: any, index: number) => ({
                    ...point,
                    trade_number: index
                }))

                setData(processedData)
            } catch (err) {
                console.error(err)
                setError("Failed to generate equity data.")
            } finally {
                setLoading(false)
            }
        }

        fetchData()
    }, [selectedBacktest])

    if (!selectedBacktest) {
        return (
            <div className="flex flex-col h-full w-full">
                <PerformancePageHeader title="Value Added Monthly Index (VAMI)" />
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

    return (
        <div className="flex flex-col h-full w-full overflow-hidden">
            <PerformancePageHeader title="Value Added Monthly Index (VAMI)" />
            <div className="flex-1 overflow-auto p-4 md:p-6 bg-muted/10">
                <Card className="h-full border-t-4 border-t-primary/20 flex flex-col">
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
                        ) : data && data.length > 0 ? (
                            <ResponsiveContainer width="100%" height="100%">
                                <LineChart
                                    data={data}
                                    margin={{ top: 20, right: 30, left: 20, bottom: 40 }}
                                >
                                    <CartesianGrid strokeDasharray="3 3" vertical={true} horizontal={true} stroke="#334155" opacity={0.5} />
                                    <XAxis
                                        dataKey="date"
                                        tickFormatter={(val) => {
                                            if(!val) return ""
                                            const d = new Date(val)
                                            return d.toLocaleDateString()
                                        }}
                                        minTickGap={50}
                                        label={{ value: "Date", position: "insideBottom", offset: 10 }}
                                        height={60}
                                        tick={{ fontSize: 12, fill: '#94a3b8' }}
                                    />
                                    <YAxis
                                        tickFormatter={(val) => val.toLocaleString()}
                                        label={{ value: "VAMI ($)", angle: -90, position: "insideLeft" }}
                                        tick={{ fontSize: 12, fill: '#94a3b8' }}
                                        width={80}
                                        domain={['auto', 'auto']}
                                    />
                                    <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#475569', strokeWidth: 1 }} />
                                    <Legend verticalAlign="bottom" height={36} wrapperStyle={{ paddingTop: '20px' }}/>

                                    <Line
                                        type="monotone"
                                        dataKey="vami"
                                        name="Value Added Monthly Index ($)"
                                        stroke="#e2e8f0" // Light gray
                                        strokeWidth={1}
                                        dot={false}
                                        activeDot={{ r: 4 }}
                                    />
                                </LineChart>
                            </ResponsiveContainer>
                        ) : (
                             !loading && <div className="flex items-center justify-center h-full text-muted-foreground">No data available to display.</div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}
