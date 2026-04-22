"use client"

import { CustomChartSemanticSnapshot } from "@/components/ai-chat/CustomChartSemanticSnapshot"
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
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Cell
} from "recharts"
import { formatNumber } from "@/lib/utils"

const METRICS = [
    "Return (%)",
    "R Multiple"
]

interface StatCardProps {
    title: string
    value: string | number
    color?: string
}

function StatCard({ title, value, color = "border-l-4 border-l-blue-500" }: StatCardProps) {
    return (
        <Card className={`bg-slate-950 border-slate-800 ${color}`}>
            <CardContent className="px-3 py-1.5 flex flex-col justify-center h-full">
                <span className="text-[10px] text-slate-400 font-bold uppercase mb-1 leading-none">
                    {title}
                </span>
                <span className="text-base font-bold text-white leading-none">
                    {value}
                </span>
            </CardContent>
        </Card>
    )
}

export default function RiskDistributionPage() {
    const { selectedBacktest } = useSelectedBacktest()
    const [selectedMetric, setSelectedMetric] = useState("Return (%)")
    const [data, setData] = useState<any[]>([])
    const [stats, setStats] = useState<any>(null)
    const [loading, setLoading] = useState(false)

    useEffect(() => {
        async function fetchData() {
            if (!selectedBacktest?.backtest_id) return

            try {
                setLoading(true)
                const response = await strategyApi.getRiskDistribution(
                    selectedBacktest.backtest_id,
                    selectedMetric
                ) as any

                if (response) {
                    setData(response.distribution || [])
                    setStats(response.stats)
                } else {
                    setData([])
                    setStats(null)
                }
            } catch (error) {
                console.error("Failed to fetch risk distribution:", error)
            } finally {
                setLoading(false)
            }
        }

        fetchData()
    }, [selectedBacktest, selectedMetric])

    if (!selectedBacktest) {
        return <div className="p-6 text-slate-400">No backtest selected.</div>
    }

    return (
        <div className="flex flex-col gap-4 p-4 h-full bg-black overflow-hidden">
            <CustomChartSemanticSnapshot
                id={`risk-distribution:${selectedBacktest.backtest_id}:${selectedMetric}`}
                title="Risk Distribution"
                summary="Trade outcome distribution histogram across return or R-multiple buckets with winner and loser averages."
                keywords={["risk distribution", "return distribution", "r multiple distribution", selectedMetric]}
                metrics={[
                    { label: "Selected Metric", value: selectedMetric },
                    { label: "Bucket Count", value: String(data.length) },
                    { label: "Average Return", value: stats ? `${formatNumber(stats.avg_return, 2)}%` : "0.00%" },
                    { label: "Total Return", value: stats ? `${formatNumber(stats.total_return, 2)}%` : "0.00%" },
                    { label: "Average Winner", value: stats ? `${formatNumber(stats.avg_winner, 2)}%` : "0.00%" },
                    { label: "Average Loser", value: stats ? `${formatNumber(stats.avg_loser, 2)}%` : "0.00%" },
                ]}
                series={[
                    {
                        label: selectedMetric,
                        points: data.slice(0, 240).map((point) => ({
                            x: point.range,
                            y: String(point.count),
                        })),
                    },
                ]}
            />
            {/* Header Controls */}
            <div className="flex items-center gap-4 shrink-0">
                <div className="w-64">
                    <label className="text-[10px] text-slate-400 font-bold uppercase block mb-1">Display</label>
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
            </div>

            {/* Chart */}
            <div className="flex-1 w-full bg-slate-950/20 rounded-lg border border-slate-800/50 p-4 relative min-h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data} barGap={0} barCategoryGap={0}>
                        <CartesianGrid vertical={false} stroke="#334155" strokeDasharray="3 3" opacity={0.3} />
                        <XAxis
                            dataKey="range"
                            stroke="#64748b"
                            tick={{fill: '#64748b', fontSize: 10}}
                            tickLine={false}
                            axisLine={false}
                            interval={Math.floor(data.length / 10)} // Show sparse ticks
                            angle={-45}
                            textAnchor="end"
                            height={60}
                            label={{ value: selectedMetric === 'Return (%)' ? 'Return, gain sum (%)' : 'R Multiple', position: 'insideBottom', offset: -5, fill: '#64748b', fontSize: 10 }}
                        />
                        <YAxis
                            stroke="#64748b"
                            tick={{fill: '#64748b', fontSize: 10}}
                            tickLine={false}
                            axisLine={false}
                            label={{ value: 'Number of Trades', angle: -90, position: 'insideLeft', fill: '#64748b', fontSize: 10, style: { textAnchor: 'middle' } }}
                        />
                        <Tooltip
                            contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', color: '#f8fafc', fontSize: '12px' }}
                            itemStyle={{ color: '#fff' }}
                            cursor={{fill: '#334155', opacity: 0.2}}
                        />
                        <Bar dataKey="count">
                            {data.map((entry, index) => (
                                <Cell
                                    key={`cell-${index}`}
                                    fill={entry.min >= 0 ? "#22c55e" : "#ef4444"}
                                />
                            ))}
                        </Bar>
                    </BarChart>
                </ResponsiveContainer>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-4 gap-2 shrink-0">
                <StatCard
                    title="Avg Return (%)"
                    value={stats ? formatNumber(stats.avg_return, 2) + "%" : "0.00%"}
                    color="border-l-2 border-l-green-500"
                />
                <StatCard
                    title="Total Return (%)"
                    value={stats ? formatNumber(stats.total_return, 2) + "%" : "0.00%"}
                    color="border-l-2 border-l-green-500"
                />
                <StatCard
                    title="Avg Return (%) Winner"
                    value={stats ? formatNumber(stats.avg_winner, 2) + "%" : "0.00%"}
                    color="border-l-2 border-l-green-500"
                />
                <StatCard
                    title="Avg Return (%) Loser"
                    value={stats ? formatNumber(stats.avg_loser, 2) + "%" : "0.00%"}
                    color="border-l-2 border-l-red-500"
                />
            </div>
        </div>
    )
}
