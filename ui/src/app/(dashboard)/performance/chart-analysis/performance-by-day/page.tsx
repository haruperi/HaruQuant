"use client"

import { CustomChartSemanticSnapshot } from "@/components/ai-chat/CustomChartSemanticSnapshot"
import { useMemo, useState, useEffect } from "react"
import {
  BarChart,
  Bar,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  ReferenceLine,
  Cell
} from "recharts"
import { useSelectedBacktest } from "@/contexts/selected-backtest-context"
import { Card, CardContent } from "@/components/ui/card"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Slider } from "@/components/ui/slider"
import {
  Tooltip as UiTooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { strategyApi } from "@/lib/api/strategies"
import {
    format,
    isValid,
    parseISO,
    compareDesc,
    startOfDay
} from "date-fns"

type DisplayMode = "dollar" | "percent" | "r_multiple"
type DateSetting = "entry" | "exit"

interface Trade {
    open_time: string
    close_time: string
    profit_loss: number
    commission: number
    swap: number
    r_multiple?: number
    profit_percent?: number
    net_profit?: number
    pnl?: number
    [key: string]: any
}

interface DayStats {
    dateStr: string
    timestamp: number
    trades: number
    totalPnL: number
    totalPnLPercent: number
    totalPnLR: number
}


function formatCurrency(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(value)
}

function formatPercent(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "percent",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value / 100)
}

function formatR(value: number) {
    return `${value.toFixed(2)}R`
}

const safelyParseFloat = (value: any): number => {
    if (value === undefined || value === null || value === "") return 0
    const parsed = parseFloat(value)
    return isNaN(parsed) ? 0 : parsed
}

export default function PerformanceByDayPage() {
  const { selectedBacktest } = useSelectedBacktest()
  const [displayMode, setDisplayMode] = useState<DisplayMode>("dollar")
  const [dateSetting, setDateSetting] = useState<DateSetting>("exit")
  const [daysShown, setDaysShown] = useState<number>(180)
  const [trades, setTrades] = useState<Trade[]>([])
  const [loading, setLoading] = useState(false)
  const [initialBalance, setInitialBalance] = useState(10000)

  // Fetch trades if missing
  useEffect(() => {
      const fetchTrades = async () => {
          if (!selectedBacktest) return
          if (selectedBacktest.trades && selectedBacktest.trades.length > 0) {
              setTrades(selectedBacktest.trades)
              const bal = safelyParseFloat(selectedBacktest.initial_balance)
              setInitialBalance(bal > 0 ? bal : 10000)
              return
          }
          try {
              setLoading(true)
              const fullBacktest = await strategyApi.getBacktestById(selectedBacktest.backtest_id)
              if (fullBacktest && fullBacktest.trades) {
                  setTrades(fullBacktest.trades)
                  const bal = safelyParseFloat(fullBacktest.initial_balance)
                  setInitialBalance(bal > 0 ? bal : 10000)
              }
          } catch (err) {
              console.error("Failed to fetch backtest details", err)
          } finally {
              setLoading(false)
          }
      }
      fetchTrades()
  }, [selectedBacktest])

  const { chartData, stats } = useMemo(() => {
    if (trades.length === 0) return { chartData: [], stats: null }

    const grouped: Record<string, Trade[]> = {}

    // Group by Day (YYYY-MM-DD)
    trades.forEach(trade => {
        let dateStr = dateSetting === 'entry' ? trade.open_time : trade.close_time
        if (!dateStr) return
        const date = new Date(dateStr)
        if (!isValid(date)) return

        const key = format(date, "yyyy-MM-dd")
        if (!grouped[key]) grouped[key] = []
        grouped[key].push(trade)
    })

    // Create Daily Stats Items
    const allDays = Object.keys(grouped).map(key => {
        const dayTrades = grouped[key]
        const date = parseISO(key)

        let totalPnL = 0
        let totalPnLR = 0
        let totalPnLPercent = 0

        dayTrades.forEach(t => {
            let pnl = 0
            if (t.profit_loss !== undefined) pnl = safelyParseFloat(t.profit_loss)
            else if (t.net_profit !== undefined) pnl = safelyParseFloat(t.net_profit)
            else if (t.pnl !== undefined) pnl = safelyParseFloat(t.pnl)
            totalPnL += pnl

            totalPnLR += safelyParseFloat(t.r_multiple)

            if (t.profit_percent !== undefined) totalPnLPercent += safelyParseFloat(t.profit_percent)
            else totalPnLPercent += (pnl / initialBalance) * 100
        })

        return {
            dateStr: key,
            timestamp: date.getTime(),
            trades: dayTrades.length,
            totalPnL,
            totalPnLPercent,
            totalPnLR
        } as DayStats
    })

    // Sort by date descending to get filter latest
    allDays.sort((a,b) => b.timestamp - a.timestamp)

    // Slice by slider
    const filteredDays = allDays.slice(0, daysShown)

    // Sort back to ascending for chart
    filteredDays.sort((a,b) => a.timestamp - b.timestamp)

    // Chart Data
    const cData = filteredDays.map(item => ({
        name: item.dateStr,
        value: displayMode === 'dollar' ? item.totalPnL : displayMode === 'percent' ? item.totalPnLPercent : item.totalPnLR,
        color: (displayMode === 'dollar' ? item.totalPnL : displayMode === 'percent' ? item.totalPnLPercent : item.totalPnLR) >= 0 ? '#22c55e' : '#ef4444'
    }))

    // Calculate Summary Stats from FILTERED days
    const winningDays = filteredDays.filter(d => d.totalPnL > 0)
    const losingDays = filteredDays.filter(d => d.totalPnL < 0)

    const avgWinningDay = winningDays.length > 0
        ? winningDays.reduce((sum, d) => sum + d.totalPnL, 0) / winningDays.length
        : 0

    const avgLosingDay = losingDays.length > 0
        ? losingDays.reduce((sum, d) => sum + d.totalPnL, 0) / losingDays.length
        : 0

    const bestDay = filteredDays.length > 0
        ? filteredDays.reduce((prev, curr) => prev.totalPnL > curr.totalPnL ? prev : curr, filteredDays[0])
        : { totalPnL: 0, totalPnLPercent: 0 }

    const worstDay = filteredDays.length > 0
        ? filteredDays.reduce((prev, curr) => prev.totalPnL < curr.totalPnL ? prev : curr, filteredDays[0])
        : { totalPnL: 0, totalPnLPercent: 0 }

    const calculatedStats = {
        avgWinningDay,
        avgLosingDay,
        biggestWinningDay: bestDay.totalPnL,
        biggestWinningDayPercent: bestDay.totalPnLPercent,
        biggestLosingDay: worstDay.totalPnL,
        biggestLosingDayPercent: worstDay.totalPnLPercent,
        winningDaysCount: winningDays.length,
        losingDaysCount: losingDays.length
    }

    return {
        chartData: cData,
        stats: calculatedStats
    }

  }, [trades, initialBalance, displayMode, dateSetting, daysShown])


  if (!selectedBacktest) return <div className="p-6">No backtest selected.</div>
  if (loading) return <div className="flex items-center justify-center p-12 text-muted-foreground">Loading day analysis...</div>

  return (
    <div className="flex flex-col gap-4 p-4 h-full bg-black overflow-hidden">
      <CustomChartSemanticSnapshot
        id={`performance-by-day:${selectedBacktest.backtest_id}:${displayMode}:${dateSetting}:${daysShown}`}
        title="Performance By Day"
        summary="Daily return distribution grouped by entry or exit date with best, worst, and average day metrics."
        keywords={["performance by day", "daily pnl", "best day", "worst day", displayMode, dateSetting]}
        metrics={[
          { label: "Display Mode", value: displayMode },
          { label: "Date Setting", value: dateSetting },
          { label: "Days Shown", value: String(daysShown) },
          { label: "Winning Days", value: stats ? String(stats.winningDaysCount) : "0" },
          { label: "Losing Days", value: stats ? String(stats.losingDaysCount) : "0" },
          {
            label: "Average Winning Day",
            value: stats ? formatCurrency(stats.avgWinningDay) : formatCurrency(0),
          },
          {
            label: "Average Losing Day",
            value: stats ? formatCurrency(stats.avgLosingDay) : formatCurrency(0),
          },
          {
            label: "Biggest Winning Day",
            value: stats ? formatCurrency(stats.biggestWinningDay) : formatCurrency(0),
          },
          {
            label: "Biggest Losing Day",
            value: stats ? formatCurrency(stats.biggestLosingDay) : formatCurrency(0),
          },
        ]}
        series={[
          {
            label: displayMode === "dollar" ? "Daily Return" : displayMode === "percent" ? "Daily Return Percent" : "Daily Return R",
            points: chartData.slice(-240).map((point) => ({
              x: point.name,
              y: String(point.value),
            })),
          },
        ]}
      />
      {/* Header Controls */}
      <div className="flex items-center gap-6 shrink-0">
         <div className="w-[180px]">
            <label className="text-[10px] text-slate-400 ml-1 mb-1 block">Display</label>
            <Select
                value={displayMode}
                onValueChange={(v: DisplayMode) => setDisplayMode(v)}
            >
              <SelectTrigger className="bg-slate-900 border-slate-700 text-white hover:bg-slate-800">
                <SelectValue placeholder="Display" />
              </SelectTrigger>
              <SelectContent className="bg-slate-900 border-slate-800 text-slate-300">
                <SelectItem value="dollar" className="hover:bg-slate-800 focus:bg-slate-800 cursor-pointer">Return ($)</SelectItem>
                <SelectItem value="percent" className="hover:bg-slate-800 focus:bg-slate-800 cursor-pointer">Return, gain sum (%)</SelectItem>
                <SelectItem value="r_multiple" className="hover:bg-slate-800 focus:bg-slate-800 cursor-pointer">R Multiple (R)</SelectItem>
              </SelectContent>
            </Select>
         </div>

         <div className="w-[180px]">
            <label className="text-[10px] text-slate-400 ml-1 mb-1 block">Date Settings</label>
            <Select
                value={dateSetting}
                onValueChange={(v: DateSetting) => setDateSetting(v)}
            >
              <SelectTrigger className="bg-slate-900 border-slate-700 text-white hover:bg-slate-800">
                <SelectValue placeholder="Date Setting" />
              </SelectTrigger>
              <SelectContent className="bg-slate-900 border-slate-800 text-slate-300">
                <SelectItem value="entry" className="hover:bg-slate-800 focus:bg-slate-800 cursor-pointer">Entry Date</SelectItem>
                <SelectItem value="exit" className="hover:bg-slate-800 focus:bg-slate-800 cursor-pointer">Exit Date</SelectItem>
              </SelectContent>
            </Select>
         </div>

         <div className="flex-1 max-w-[300px]">
             <div className="flex justify-between items-center mb-1">
                 <label className="text-[10px] text-slate-400 block">Days Shown ({daysShown}):</label>
             </div>
             <Slider
                value={[daysShown]}
                min={7}
                max={180}
                step={1}
                onValueChange={(val) => setDaysShown(val[0])}
                className="py-2"
             />
         </div>
      </div>

       {/* Content Wrapper */}
       <div className="flex flex-col gap-4 flex-1 min-h-0 bg-black">
         {/* Chart - Top (Flexible, takes remaining space) */}
         <div className="flex-1 w-full bg-slate-950/50 rounded-lg border border-slate-800 p-4 relative min-h-[200px]">
            {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} barCategoryGap="2%">
                    <CartesianGrid vertical={false} stroke="#334155" strokeDasharray="3 3" opacity={0.5} />
                    <XAxis
                        dataKey="name"
                        tick={{ fill: '#64748b', fontSize: 10 }}
                        axisLine={false}
                        tickLine={false}
                        interval="preserveStartEnd"
                        angle={-45}
                        textAnchor="end"
                        height={60}
                    />
                    <YAxis
                        tick={{ fill: '#64748b', fontSize: 12 }}
                        axisLine={false}
                        tickLine={false}
                        tickFormatter={(val) => {
                            if (displayMode === 'percent') return `${val}%`
                            if (displayMode === 'dollar') return `$${val}`
                            return `${val}R`
                        }}
                         label={{
                            value: displayMode === 'percent' ? 'Return, gain sum (%)' : displayMode === 'dollar' ? 'Return ($)' : 'Return (R)',
                            angle: -90,
                            position: 'insideLeft',
                            fill: '#64748b',
                            fontSize: 10
                        }}
                    />
                    <Tooltip
                        cursor={{ fill: 'transparent' }}
                         content={({ active, payload }) => {
                            if (active && payload && payload.length) {
                                const data = payload[0].payload;
                                return (
                                    <div className="bg-slate-900 border border-slate-800 p-2 rounded shadow-md text-slate-100 text-xs">
                                        <div>{data.name}</div>
                                        <div>Return: {
                                            displayMode === 'dollar' ? formatCurrency(data.value) :
                                            displayMode === 'percent' ? formatPercent(data.value) :
                                            formatR(data.value)
                                        }</div>
                                    </div>
                                );
                            }
                            return null;
                        }}
                    />
                    <ReferenceLine y={0} stroke="#64748b" />
                    <Bar dataKey="value">
                        {chartData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                    </Bar>
                </BarChart>
            </ResponsiveContainer>
            ) : (
                <div className="flex items-center justify-center h-full text-muted-foreground">
                    No daily data available.
                </div>
            )}
         </div>

         {/* Stats - Bottom (Fixed height ~15%) */}
         <div className="h-32 w-full min-h-0 pb-2">
            {stats && (
                <div className="grid grid-cols-6 gap-4 h-full">
                     <DayStatCard
                         title="Avg. Winning Day"
                         value={displayMode === 'percent'
                             ? formatPercent(stats.avgWinningDay / initialBalance * 100)
                             : displayMode === 'r_multiple' ? formatR(stats.avgWinningDay / (initialBalance/100))
                             : formatCurrency(stats.avgWinningDay)
                         }
                         color="green"
                     />
                     <DayStatCard
                         title="Avg. Losing Day"
                         value={displayMode === 'percent'
                             ? formatPercent(stats.avgLosingDay / initialBalance * 100)
                             : displayMode === 'r_multiple' ? formatR(stats.avgLosingDay / (initialBalance/100))
                             : formatCurrency(stats.avgLosingDay)
                         }
                         color="red"
                     />
                     <DayStatCard
                         title="Biggest Winning Day"
                         value={displayMode === 'percent'
                             ? formatPercent(stats.biggestWinningDayPercent)
                             : displayMode === 'r_multiple' ? formatR(0)
                             : formatCurrency(stats.biggestWinningDay)
                         }
                         color="green"
                         tooltip="Max profit in a single day"
                     />
                     <DayStatCard
                         title="Biggest Losing Day"
                         value={displayMode === 'percent'
                             ? formatPercent(stats.biggestLosingDayPercent)
                             : displayMode === 'r_multiple' ? formatR(0)
                             : formatCurrency(stats.biggestLosingDay)
                         }
                         color="red"
                         tooltip="Max loss in a single day"
                     />
                     <DayStatCard
                         title="Winning Days"
                         value={stats.winningDaysCount}
                         color="green"
                     />
                     <DayStatCard
                         title="Losing Days"
                         value={stats.losingDaysCount}
                         color="green"
                     />
                </div>
            )}
         </div>
       </div>
    </div>
  )
}

function DayStatCard({ title, value, tooltip, color = "green" }: { title: string, value: string | number, tooltip?: string, color?: "green" | "red" }) {
  const barColor = color === 'red' ? 'bg-red-500' : 'bg-green-500';

  return (
    <Card className="bg-slate-900 border-slate-800 flex-1 min-w-[140px]">
      <CardContent className="p-0 flex items-stretch overflow-hidden h-full">
         <div className={`w-1.5 ${barColor} shrink-0`} />
         <div className="flex flex-col justify-center px-4 py-3">
             <div className="flex items-center gap-1">
                <TooltipProvider>
                    <UiTooltip>
                        <TooltipTrigger asChild>
                            <span className="text-[11px] text-slate-400 font-medium cursor-help hover:text-slate-300 transition-colors uppercase tracking-wider text-left block">
                              {title}
                            </span>
                        </TooltipTrigger>
                        {tooltip && <TooltipContent><p>{tooltip}</p></TooltipContent>}
                    </UiTooltip>
                </TooltipProvider>
             </div>
             <span className="text-xl font-bold text-white mt-1 text-left">
                {value}
             </span>
         </div>
      </CardContent>
    </Card>
  )
}
