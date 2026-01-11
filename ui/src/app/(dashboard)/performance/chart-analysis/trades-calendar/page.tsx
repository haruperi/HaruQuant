"use client"

import * as React from "react"
import {
  format,
  eachDayOfInterval,
  endOfMonth,
  startOfMonth,
  startOfWeek,
  endOfWeek,
  isSameMonth,
  isSameDay
} from "date-fns"
import { useSelectedBacktest } from "@/contexts/selected-backtest-context"
import { strategyApi } from "@/lib/api/strategies"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Button } from "@/components/ui/button"
import { ChevronLeft, ChevronRight } from "lucide-react"

export default function TradesCalendarPage() {
    const { selectedBacktest } = useSelectedBacktest()
    const [year, setYear] = React.useState(new Date().getFullYear())
    const [metric, setMetric] = React.useState("return")
    const [stats, setStats] = React.useState<{ pnl: Record<string, number>, return: Record<string, number> }>({ pnl: {}, return: {} })
    const [loading, setLoading] = React.useState(false)

    // Sync year with backtest
    React.useEffect(() => {
        if (selectedBacktest?.end_date) {
            setYear(new Date(selectedBacktest.end_date).getFullYear())
        }
    }, [selectedBacktest])

    // Fetch and process trades
    React.useEffect(() => {
        const fetchTrades = async () => {
             if (!selectedBacktest) return
             setLoading(true)
             try {
                 let trades = selectedBacktest.trades || []
                 if (trades.length === 0) {
                     const full = await strategyApi.getBacktestById(selectedBacktest.backtest_id)
                     trades = full.trades || []
                 }

                 if (trades.length > 0) {
                     const pnlStats: Record<string, number> = {}
                     const returnStats: Record<string, number> = {}
                     const initialBalance = selectedBacktest.initial_balance || 10000

                     trades.forEach((t: any) => {
                         // Robust date parsing
                         const timeStr = t.close_time || t.exit_time || t.time || t.entry_time
                         if (!timeStr) return

                         // Parse the ISO string to a Date object, then format it to YYYY-MM-DD
                         // This handles potential timezone offsets better if we treat everything as local or consistent
                         const dateObj = new Date(timeStr)
                         if (isNaN(dateObj.getTime())) return
                         const dateStr = format(dateObj, 'yyyy-MM-dd')

                         // Robust PnL parsing
                         let pnl = t.profit_loss
                         if (pnl === undefined) pnl = t.net_profit
                         if (pnl === undefined) pnl = t.pl
                         if (pnl === undefined) pnl = t.pnl
                         if (pnl === undefined) pnl = t.profit

                         if (pnl !== undefined) {
                             if (typeof pnl === 'string') pnl = parseFloat(pnl)
                             if (!isNaN(pnl)) {
                                 pnlStats[dateStr] = (pnlStats[dateStr] || 0) + pnl
                             }
                         }
                     })

                     Object.keys(pnlStats).forEach(date => {
                         returnStats[date] = (pnlStats[date] / initialBalance) * 100
                     })

                     setStats({ pnl: pnlStats, return: returnStats })
                 }
             } catch (e) {
                 console.error("Error calculating calendar stats:", e)
             } finally {
                 setLoading(false)
             }
        }
        fetchTrades()
    }, [selectedBacktest])

    const currentStats = metric === "return" ? stats.return : stats.pnl

    const months = Array.from({ length: 12 }, (_, i) => new Date(year, i, 1))

    return (
        <div className="flex flex-col h-full bg-slate-950 p-1 overflow-hidden">
            <div className="flex items-center justify-between px-2 shrink-0 h-8 mb-1">
                <div className="flex items-center gap-4">
                     <Select value={metric} onValueChange={setMetric}>
                        <SelectTrigger className="w-[120px] h-7 bg-slate-900 border-slate-800 text-xs text-slate-400">
                            <SelectValue placeholder="Display" />
                        </SelectTrigger>
                        <SelectContent className="bg-slate-900 border-slate-800">
                            <SelectItem value="return">Return (%)</SelectItem>
                            <SelectItem value="pnl">PnL ($)</SelectItem>
                        </SelectContent>
                    </Select>
                </div>

                <div className="flex items-center gap-1 bg-slate-900 rounded-md border border-slate-800 p-0.5">
                    <Button variant="ghost" size="icon" onClick={() => setYear(year - 1)} className="h-5 w-5 hover:bg-slate-800">
                        <ChevronLeft className="h-3 w-3 text-slate-400" />
                    </Button>
                    <span className="font-bold min-w-[40px] text-center text-xs text-slate-300">{year}</span>
                    <Button variant="ghost" size="icon" onClick={() => setYear(year + 1)} className="h-5 w-5 hover:bg-slate-800">
                        <ChevronRight className="h-3 w-3 text-slate-400" />
                    </Button>
                </div>

                <div className="w-[120px]"></div>
            </div>

            <div className="grid grid-cols-4 gap-x-1 gap-y-1 h-full min-h-0 content-start">
                {months.map(month => (
                    <MonthGrid
                        key={month.toISOString()}
                        month={month}
                        dailyStats={currentStats}
                    />
                ))}
            </div>
        </div>
    )
}

function MonthGrid({ month, dailyStats }: { month: Date, dailyStats: Record<string, number> }) {
    const start = startOfWeek(startOfMonth(month), { weekStartsOn: 1 })
    const end = endOfWeek(endOfMonth(month), { weekStartsOn: 1 })
    const days = eachDayOfInterval({ start, end })

    return (
        <div className="flex flex-col h-full bg-slate-950/50 rounded-sm">
            <div className="mb-1 text-center shrink-0 py-0.5">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                    {format(month, "MMMM")}
                </span>
            </div>

            <div className="grid grid-cols-7 mb-0.5 shrink-0 px-1">
                {['M','T','W','T','F','S','S'].map((d, i) => (
                    <div key={i} className="text-center text-[8px] text-slate-600 font-bold h-3 flex items-center justify-center">
                        {d}
                    </div>
                ))}
            </div>

            <div className="grid grid-cols-7 gap-0.5 px-1 content-start">
                {days.map(day => {
                   const dateKey = format(day, 'yyyy-MM-dd')
                   const val = dailyStats[dateKey]
                   const inMonth = isSameMonth(day, month)

                   if (!inMonth) return <div key={dateKey} className="aspect-square" />

                   return (
                       <div key={dateKey} className="aspect-square flex items-center justify-center">
                           {val !== undefined ? (
                               <div className={`
                                   w-full h-full rounded-[2px] flex items-center justify-center text-[10px] font-bold text-white transition-all
                                   ${val > 0 ? 'bg-emerald-600 shadow-sm shadow-emerald-900/20' : 'bg-red-600 shadow-sm shadow-red-900/20'}
                               `}>
                                   {format(day, 'd')}
                               </div>
                           ) : (
                               <span className="text-[10px] text-slate-600 font-medium">
                                   {format(day, 'd')}
                               </span>
                           )}
                       </div>
                   )
                })}
            </div>
        </div>
    )
}
