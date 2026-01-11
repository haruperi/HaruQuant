"use client"

import { useEffect, useState } from "react"
import { useSelectedBacktest } from "@/contexts/selected-backtest-context"
import { strategyApi } from "@/lib/api/strategies"
import { Card, CardContent } from "@/components/ui/card"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine
} from "recharts"
import { formatCurrency, formatNumber } from "@/lib/utils"
import { ChevronDown } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

export default function ConsecutiveWinnersLosersPage() {
    const { selectedBacktest } = useSelectedBacktest()
    const [data, setData] = useState<any[]>([])
    const [loading, setLoading] = useState(true)
    const [displayMode, setDisplayMode] = useState("Return ($)")

    useEffect(() => {
        async function fetchData() {
            if (!selectedBacktest) {
                setLoading(false)
                return
            }

            try {
                setLoading(true)
                const res: any = await strategyApi.getConsecutiveWinnersLosers(selectedBacktest.backtest_id)
                setData(res.consecutive_counts || [])
            } catch (err) {
                console.error("Failed to fetch consecutive stats", err)
            } finally {
                setLoading(false)
            }
        }
        fetchData()
    }, [selectedBacktest])

    if (!selectedBacktest) {
        return (
            <div className="flex h-full items-center justify-center text-slate-500">
                Please select a backtest to view analysis.
            </div>
        )
    }

    if (loading) {
        return (
            <div className="flex h-full items-center justify-center text-slate-500">
                Loading...
            </div>
        )
    }

    // Prepare chart data based on display mode
    const chartData = data.map(item => {
        let winValue, lossValue, label

        if (displayMode === "Return ($)") {
            winValue = item.avg_win_pl
            lossValue = item.avg_loss_pl
            label = "Avg P&L"
        } else if (displayMode === "Return, gain sum (%)") {
            winValue = item.avg_win_pct
            lossValue = item.avg_loss_pct
            label = "Avg Return %"
        } else { // R Multiple
            winValue = item.avg_win_r
            lossValue = item.avg_loss_r
            label = "Avg R"
        }

        return {
            length: item.length,
            winValue,
            lossValue,
            winPct: item.avg_win_pct,
            lossPct: item.avg_loss_pct,
            winCount: item.count_wins,
            lossCount: item.count_losses
        }
    })

    const formatValue = (val: number) => {
        if (displayMode === "Return ($)") return formatCurrency(val)
        if (displayMode === "Return, gain sum (%)") return `${formatNumber(val, 2)}%`
        return `${formatNumber(val, 2)}R`
    }

    return (
        <div className="flex flex-col gap-4 p-4 h-full bg-black overflow-hidden">
             {/* Header Controls */}
            <div className="flex items-center justify-between shrink-0">
                <div className="flex gap-4">
                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <Button variant="outline" className="bg-slate-900 border-slate-700 text-white hover:bg-slate-800 w-64 justify-between px-3 h-12">
                                <div className="flex flex-col items-start gap-0.5 text-left">
                                    <span className="text-[10px] text-slate-400 font-medium">Average</span>
                                    <span className="truncate w-48 text-base font-semibold">{displayMode}</span>
                                </div>
                                <ChevronDown className="h-4 w-4 text-slate-400 shrink-0" />
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent className="w-64 bg-slate-900 border-slate-700 text-white">
                            <DropdownMenuItem onClick={() => setDisplayMode("Return ($)")} className="focus:bg-slate-800 focus:text-white cursor-pointer py-3 text-base">
                                Return ($)
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => setDisplayMode("Return, gain sum (%)")} className="focus:bg-slate-800 focus:text-white cursor-pointer py-3 text-base">
                                Return, gain sum (%)
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => setDisplayMode("R Multiple (R)")} className="focus:bg-slate-800 focus:text-white cursor-pointer py-3 text-base">
                                R Multiple (R)
                            </DropdownMenuItem>
                        </DropdownMenuContent>
                    </DropdownMenu>
                </div>
            </div>

            <div className="flex-1 w-full bg-slate-950/50 rounded-lg border border-slate-800 p-4 relative min-h-[300px]">
                 <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData} barCategoryGap="20%" margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                        <CartesianGrid vertical={false} stroke="#334155" strokeDasharray="3 3" opacity={0.5} />
                        <XAxis
                            dataKey="length"
                            stroke="#cbd5e1"
                            tick={{fill: '#cbd5e1', fontSize: 12}}
                            tickLine={false}
                            axisLine={false}
                            label={{ value: 'Consecutive winners/losers', position: 'insideBottom', offset: -10, fill: '#cbd5e1', fontSize: 12 }}
                        />
                        <YAxis
                            stroke="#cbd5e1"
                            tick={{fill: '#cbd5e1', fontSize: 12}}
                            tickFormatter={formatValue}
                            tickLine={false}
                            axisLine={false}
                            label={{ value: `Average ${displayMode}`, angle: -90, position: 'insideLeft', fill: '#cbd5e1', style: { textAnchor: 'middle' }, fontSize: 12 }}
                        />
                        <Tooltip
                            cursor={{fill: '#1e293b', opacity: 0.5}}
                            content={({ active, payload, label }) => {
                                if (active && payload && payload.length) {
                                  const data = payload[0].payload;
                                  return (
                                    <div className="bg-white p-3 rounded-lg shadow-xl text-slate-900 text-xs min-w-[200px]">
                                      <div className="font-bold mb-3 text-sm border-b border-slate-100 pb-2">{data.length} trades streak</div>

                                      {/* Winners */}
                                      <div className="flex items-start justify-between mb-3">
                                        <div className="flex items-center gap-2 mt-0.5">
                                           <div className="w-2.5 h-2.5 rounded-full bg-green-500 shrink-0" />
                                           <span className="font-medium text-slate-700">Consecutive winners</span>
                                        </div>
                                        <div className="text-right">
                                           <div className="font-bold text-slate-900">{formatValue(data.winValue)}</div>
                                            {/* Only show pct if distinct from main value */}
                                            {displayMode !== "Return, gain sum (%)" && (
                                                <div className="text-slate-500 font-medium">{formatNumber(data.winPct, 2)}%</div>
                                            )}
                                           <div className="text-slate-500 text-[10px] mt-1">Frequency: {data.winCount}</div>
                                        </div>
                                      </div>

                                      {/* Losers */}
                                      <div className="flex items-start justify-between">
                                        <div className="flex items-center gap-2 mt-0.5">
                                           <div className="w-2.5 h-2.5 rounded-full bg-red-500 shrink-0" />
                                           <span className="font-medium text-slate-700">Consecutive losers</span>
                                        </div>
                                        <div className="text-right">
                                           <div className="font-bold text-slate-900">{formatValue(data.lossValue)}</div>
                                            {displayMode !== "Return, gain sum (%)" && (
                                                <div className="text-slate-500 font-medium">{formatNumber(data.lossPct, 2)}%</div>
                                            )}
                                           <div className="text-slate-500 text-[10px] mt-1">Frequency: {data.lossCount}</div>
                                        </div>
                                      </div>
                                    </div>
                                  );
                                }
                                return null;
                            }}
                        />
                        <ReferenceLine y={0} stroke="#475569" strokeWidth={1} />
                        <Bar dataKey="winValue" fill="#22c55e" radius={[4, 4, 0, 0]} maxBarSize={60} />
                        <Bar dataKey="lossValue" fill="#ef4444" radius={[0, 0, 4, 4]} maxBarSize={60} />
                    </BarChart>
                 </ResponsiveContainer>
            </div>
        </div>
    )
}
