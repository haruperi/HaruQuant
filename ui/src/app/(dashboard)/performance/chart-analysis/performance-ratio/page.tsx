"use client"

import { useEffect, useState, useMemo } from "react"
import { useSelectedBacktest } from "@/contexts/selected-backtest-context"
import { strategyApi } from "@/lib/api/strategies"
import { Card, CardContent } from "@/components/ui/card"
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
} from "recharts"
import { formatNumber } from "@/lib/utils"

const METRICS = [
    "Winrate (%)",
    "Sharpe Ratio",
    "Sortino Ratio",
    "Gain To Pain",
    "Calmar",
    "Profit Factor",
    "SQN"
]

interface MetricCardProps {
    title: string
    value: string | number
    subValue?: string
    color?: string
}

function MetricCard({ title, value, color = "bg-green-500" }: MetricCardProps) {
    return (
        <Card className="bg-slate-900 border-slate-800 flex-1 min-w-[200px]">
            <CardContent className="p-0 flex items-stretch overflow-hidden h-full">
                <div className={`w-1.5 ${color} shrink-0`} />
                <div className="flex flex-col justify-center px-4 py-3">
                    <span className="text-xs text-slate-400 font-medium uppercase tracking-wider mb-1">
                        {title}
                    </span>
                    <span className="text-xl font-bold text-white">
                        {value}
                    </span>
                </div>
            </CardContent>
        </Card>
    )
}

function OverallStatsCard({ metric, value }: { metric: string, value: string }) {
    return (
        <Card className="bg-black border-slate-800 col-span-2">
            <CardContent className="p-4 grid grid-cols-4 gap-4 items-center h-full">
               <div className="col-span-1">
                   <div className="text-xs text-slate-400 uppercase font-bold mb-1">Overall</div>
                   <div className="text-white text-sm font-medium">System Performance</div>
               </div>
               <div className="col-span-1 border-l border-slate-800 pl-4">
                   <div className="text-xs text-slate-400 uppercase font-bold mb-1">{metric}</div>
                   <div className="text-white text-xl font-bold">{value}</div>
               </div>
               <div className="col-span-1 border-l border-slate-800 pl-4">
                   <div className="text-xs text-slate-400 uppercase font-bold mb-1">Rating</div>
                   <div className="text-white text-sm">Standard</div>
               </div>
               <div className="col-span-1 border-l border-slate-800 pl-4">
                   <div className="text-xs text-slate-400 uppercase font-bold mb-1">Summary</div>
                   <div className="text-slate-400 text-xs leading-tight">
                       Performance calculated over all available trades.
                   </div>
               </div>
            </CardContent>
        </Card>
    )
}

export default function PerformanceRatioPage() {
    const { selectedBacktest } = useSelectedBacktest()
    const [selectedMetric, setSelectedMetric] = useState("Winrate (%)")
    const [data, setData] = useState<any[]>([])
    const [stats, setStats] = useState<any>(null)
    const [loading, setLoading] = useState(false)

    useEffect(() => {
        async function fetchData() {
            if (!selectedBacktest?.backtest_id) return

            try {
                setLoading(true)
                const [chartResponse, statsResponse]: [any, any] = await Promise.all([
                    strategyApi.getPerformanceRatioChart(
                        selectedBacktest.backtest_id,
                        selectedMetric
                    ),
                    strategyApi.getEquityPerformance(selectedBacktest.backtest_id)
                ])

                if (Array.isArray(chartResponse)) {
                    setData(chartResponse)
                } else {
                    setData([])
                }

                if (statsResponse && statsResponse.metrics) {
                    setStats(statsResponse.metrics)
                }
            } catch (error) {
                console.error("Failed to fetch performance data:", error)
            } finally {
                setLoading(false)
            }
        }

        fetchData()
    }, [selectedBacktest, selectedMetric])

    const lastValue = useMemo(() => {
        if (data.length > 0) {
            return data[data.length - 1].value
        }
        return 0
    }, [data])

    // Calculate generic stats for the bottom cards from trades directly if possible,
    // or just display the current metric status.
    // Screenshot shows: Combined Winrate, Winners, Losers, Break Evens.
    // These are static for "Winrate (%)".
    // Does the bottom panel change based on metric?
    // Screenshot shows "Combined Winrate" when "Ratio: Winrate (%)" is selected.
    // This implies the bottom panel is context-aware.

    // For now, let's derive stats from the trades for the "Winrate" case,
    // and for others show generic Current Value info.

    const tradeStats = useMemo(() => {
       if (!stats) return { winners: 0, losers: 0, breakeven: 0 }
       return {
           winners: stats.winning_trades,
           losers: stats.losing_trades,
           breakeven: stats.total_trades - (stats.winning_trades + stats.losing_trades)
       }
    }, [stats])

    if (!selectedBacktest) {
        return <div className="p-6 text-slate-400">No backtest selected.</div>
    }

    return (
        <div className="flex flex-col gap-4 p-4 h-full bg-black overflow-hidden">
            {/* Header Controls */}
            <div className="flex items-center gap-4 shrink-0">
                <div className="w-64">
                    <label className="text-[10px] text-slate-400 font-bold uppercase block mb-1">Ratio</label>
                    <Select value={selectedMetric} onValueChange={setSelectedMetric}>
                        <SelectTrigger className="bg-slate-950 border-slate-800 text-white h-10">
                            <SelectValue placeholder="Select Metric" />
                        </SelectTrigger>
                        <SelectContent className="bg-slate-900 border-slate-800 text-white">
                            {METRICS.map(m => (
                                <SelectItem key={m} value={m} className="cursor-pointer hover:bg-slate-800 focus:bg-slate-800">
                                    {m}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>
                 <div className="w-48 opacity-50 pointer-events-none">
                    <label className="text-[10px] text-slate-400 font-bold uppercase block mb-1">Filter</label>
                    <Select defaultValue="Setups">
                        <SelectTrigger className="bg-slate-950 border-slate-800 text-white h-10">
                            <SelectValue placeholder="Setups" />
                        </SelectTrigger>
                    </Select>
                </div>
                <div className="ml-auto flex items-center gap-2 text-xs text-blue-500">
                    <span className="w-2 h-2 rounded-full bg-blue-500"></span>
                    Overall
                </div>
            </div>

            {/* Chart */}
            <div className="flex-1 w-full bg-slate-950/20 rounded-lg border border-slate-800/50 p-4 relative min-h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={data}>
                        <CartesianGrid vertical={false} stroke="#334155" strokeDasharray="3 3" opacity={0.3} />
                        <XAxis
                            dataKey="index"
                            stroke="#64748b"
                            tick={{fill: '#64748b', fontSize: 10}}
                            tickLine={false}
                            axisLine={false}
                            label={{ value: 'Trades', position: 'insideBottom', offset: -5, fill: '#64748b', fontSize: 10 }}
                        />
                        <YAxis
                            domain={['auto', 'auto']}
                            stroke="#64748b"
                            tick={{fill: '#64748b', fontSize: 10}}
                            tickFormatter={(val) => formatNumber(val, 2)}
                            tickLine={false}
                            axisLine={false}
                            label={{ value: selectedMetric, angle: -90, position: 'insideLeft', fill: '#64748b', fontSize: 10, style: { textAnchor: 'middle' } }}
                        />
                        <Tooltip
                            contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', color: '#f8fafc' }}
                            itemStyle={{ color: '#3b82f6' }}
                            formatter={(value: number) => [formatNumber(value, 2), selectedMetric]}
                            labelFormatter={(label) => `Trade ${label}`}
                        />
                        <Line
                            type="monotone"
                            dataKey="value"
                            stroke="#3b82f6"
                            strokeWidth={2}
                            dot={false}
                        />
                    </LineChart>
                </ResponsiveContainer>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-6 gap-4 shrink-0 h-32">
                <OverallStatsCard metric={selectedMetric} value={formatNumber(lastValue, 2)} />

                {/* Context Aware Cards - If Winrate, show W/L counts. Else show other stats? */}
                {selectedMetric === "Winrate (%)" ? (
                    <>
                        <MetricCard title="Combined Winrate" value={formatNumber(lastValue, 2) + "%"} color="bg-green-500" />
                        <MetricCard title="Winners" value={tradeStats.winners} color="bg-green-500" />
                        <MetricCard title="Losers" value={tradeStats.losers} color="bg-red-500" />
                        <MetricCard title="Break Evens" value={tradeStats.breakeven} color="bg-green-500" />
                    </>
                ) : (
                    <>
                        {/* Generic Cards for other metrics */}
                        <MetricCard title="Current Value" value={formatNumber(lastValue, 2)} color="bg-blue-500" />
                        <MetricCard title="Total Trades" value={data.length} color="bg-slate-500" />
                         <MetricCard title="Max Value" value={formatNumber(Math.max(...data.map(d => d.value) || [0]), 2)} color="bg-green-500" />
                        <MetricCard title="Min Value" value={formatNumber(Math.min(...data.map(d => d.value) || [0]), 2)} color="bg-red-500" />
                    </>
                )}
            </div>
        </div>
    )
}
