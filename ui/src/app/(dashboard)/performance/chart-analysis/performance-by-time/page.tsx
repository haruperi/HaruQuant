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
import {
  Tooltip as UiTooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { strategyApi } from "@/lib/api/strategies"
import {
    format,
    getDay,
    getMonth,
    getHours,
    startOfWeek,
    startOfMonth,
    startOfHour,
    setMinutes,
    startOfMinute,
    isValid,
    parseISO,
    getISOWeek
} from "date-fns"

type DisplayMode = "dollar" | "percent" | "r_multiple"
type DateSetting = "entry" | "exit"
type Period = "weekday" | "month" | "week" | "hour" | "30min" | "15min" | "5min" | "year"

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

interface TimeStats {
    name: string
    sortKey: number | string // For sorting correctly
    trades: number
    wins: number
    winRate: number
    totalPnL: number
    avgPnL: number
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

export default function PerformanceByTimePage() {
  const { selectedBacktest } = useSelectedBacktest()
  const [displayMode, setDisplayMode] = useState<DisplayMode>("dollar")
  const [dateSetting, setDateSetting] = useState<DateSetting>("entry")
  const [period, setPeriod] = useState<Period>("weekday")
  const [trades, setTrades] = useState<Trade[]>([])
  const [loading, setLoading] = useState(false)
  const [initialBalance, setInitialBalance] = useState(10000)

  // Fetch trades if missing
  useEffect(() => {
      const fetchTrades = async () => {
          if (!selectedBacktest) return

          // If context already has trades, use them
          if (selectedBacktest.trades && selectedBacktest.trades.length > 0) {
              setTrades(selectedBacktest.trades)
              const bal = safelyParseFloat(selectedBacktest.initial_balance)
              setInitialBalance(bal > 0 ? bal : 10000)
              return
          }

          // Otherwise fetch details
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

  const { chartData, tableData, summaryStats } = useMemo(() => {
    if (trades.length === 0) return { chartData: [], tableData: [], summaryStats: null }

    const grouped: Record<string, Trade[]> = {}

    // Initialize groups for fixed periods to ensure 0-value entries
    let fixedKeys: { name: string, sortKey: number | string }[] = []

    if (period === 'weekday') {
        const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        days.forEach((d, i) => {
            fixedKeys.push({ name: d, sortKey: i })
            grouped[d] = []
        })
    } else if (period === 'month') {
        const months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        months.forEach((m, i) => {
            fixedKeys.push({ name: m, sortKey: i })
            grouped[m] = []
        })
    } else if (period === 'hour') {
        for (let i = 0; i < 24; i++) {
            const h = i.toString().padStart(2, '0') + ":00"
            fixedKeys.push({ name: h, sortKey: i })
            grouped[h] = []
        }
    } else if (period === 'week') {
        for (let i = 1; i <= 53; i++) {
            const w = `W${i}`
            fixedKeys.push({ name: w, sortKey: i })
            grouped[w] = []
        }
    } else if (period === '30min' || period === '15min' || period === '5min') {
        const interval = period === '30min' ? 30 : period === '15min' ? 15 : 5
        const totalMinutes = 24 * 60
        for (let i = 0; i < totalMinutes; i += interval) {
             const h = Math.floor(i / 60)
             const m = i % 60
             const timeStr = `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}`
             fixedKeys.push({ name: timeStr, sortKey: i })
             grouped[timeStr] = []
        }
    } else if (period === 'year') {
        // Find min and max year from trades to create range
        const years = trades.map(t => new Date(dateSetting === 'entry' ? t.open_time : t.close_time).getFullYear()).filter(y => !isNaN(y))
        if (years.length > 0) {
            const minYear = Math.min(...years)
            const maxYear = Math.max(...years)
            for (let y = minYear; y <= maxYear; y++) {
                fixedKeys.push({ name: y.toString(), sortKey: y })
                grouped[y.toString()] = []
            }
        }
    }

    trades.forEach(trade => {
        let dateStr = dateSetting === 'entry' ? trade.open_time : trade.close_time
        // Handle potential different timestamp formats if needed, assuming ISO string standard
        if (!dateStr) return

        const date = new Date(dateStr)
        if (!isValid(date)) return

        let key = ""

        if (period === 'weekday') {
            const dayIdx = getDay(date) // 0=Sun, 1=Mon...
            const mappedIdx = dayIdx === 0 ? 6 : dayIdx - 1
            const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            key = days[mappedIdx]
        } else if (period === 'month') {
            const monthIdx = getMonth(date) // 0-11
            const months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
            key = months[monthIdx]
        } else if (period === 'hour') {
            const h = getHours(date)
            key = h.toString().padStart(2, '0') + ":00"
        } else if (period === 'week') {
            const weekNum = getISOWeek(date)
            key = `W${weekNum}`
        } else if (period === '30min' || period === '15min' || period === '5min') {
            const interval = period === '30min' ? 30 : period === '15min' ? 15 : 5
            const m = date.getMinutes()
            const roundedM = Math.floor(m / interval) * interval
            const roundedDate = setMinutes(date, roundedM)
            key = format(roundedDate, "HH:mm")
        } else if (period === 'year') {
            const y = date.getFullYear()
            key = y.toString()
        }

        if (grouped[key]) {
            grouped[key].push(trade)
        }
    })

    // Prepare Items
    let items: TimeStats[] = []

    const allKeys = Object.keys(grouped)

    // Optimization: if fixed periods, use fixedKeys order.
    // Since we pre-fill ALL supported periods now (including intervals), we always use this path.
    if (fixedKeys.length > 0) {
        items = fixedKeys.map(fk => {
            const k = fk.name
            const rawTrades = grouped[k] || []
            return calculateStats(k, rawTrades, initialBalance, fk.sortKey)
        })
    } else {
        // Fallback for purely dynamic (not currently used)
        items = allKeys.map(k => {
            const rawTrades = grouped[k]
            return calculateStats(k, rawTrades, initialBalance, 0)
        })
    }

    // Chart Data
    const cData = items.map(item => ({
        name: item.name,
        value: displayMode === 'dollar' ? item.totalPnL : displayMode === 'percent' ? item.totalPnLPercent : item.totalPnLR,
        color: (displayMode === 'dollar' ? item.totalPnL : displayMode === 'percent' ? item.totalPnLPercent : item.totalPnLR) >= 0 ? '#22c55e' : '#ef4444'
    }))

    // Summary Stats
    const bestItem = items.reduce((prev, current) => (prev.totalPnL > current.totalPnL) ? prev : current, items[0] || { totalPnL: 0 })
    const worstItem = items.reduce((prev, current) => (prev.totalPnL < current.totalPnL) ? prev : current, items[0] || { totalPnL: 0 })

    // Avg PnL Best
    const bestAvgItem = items.reduce((prev, current) => (prev.avgPnL > current.avgPnL) ? prev : current, items[0] || { avgPnL: 0 })

    let periodLabel = 'Period'
    if (period === 'weekday') periodLabel = 'Day'
    else if (period === 'month') periodLabel = 'Month'
    else if (period === 'week') periodLabel = 'Week'
    else if (period === 'hour') periodLabel = 'Hour'
    else if (period === '30min') periodLabel = '30Min'
    else if (period === '15min') periodLabel = '15Min'
    else if (period === '5min') periodLabel = '5Min'
    else if (period === 'year') periodLabel = 'Year'

    const stats = {
        bestLabel: `Best ${periodLabel}`,
        bestValue: bestItem.totalPnL,
        bestName: bestItem.name,

        worstLabel: `Worst ${periodLabel}`,
        worstValue: worstItem.totalPnL,
        worstName: worstItem.name,

        tradesLabel: `Trades per ${periodLabel}`,
        avgTrades: items.length > 0 ? trades.length / items.length : 0,

        avgPnLLabel: `Avg ${periodLabel} P&L`,
        avgPeriodPnL: items.length > 0 ? items.reduce((sum, item) => sum + item.totalPnL, 0) / items.length : 0
    }

    return {
        chartData: cData,
        tableData: items,
        summaryStats: stats
    }
  }, [trades, initialBalance, displayMode, dateSetting, period])


  if (!selectedBacktest) {
      return <div className="p-6">No backtest selected.</div>
  }

  if (loading) {
      return <div className="flex items-center justify-center p-12 text-muted-foreground">Loading time analysis...</div>
  }

  return (
    <div className="flex flex-col gap-4 p-4 h-full bg-black overflow-hidden">
      <CustomChartSemanticSnapshot
        id={`performance-by-time:${selectedBacktest.backtest_id}:${displayMode}:${dateSetting}:${period}`}
        title="Performance By Time"
        summary="Time-bucket performance analysis across entry or exit timestamps with period-level returns and win rates."
        keywords={["performance by time", "time analysis", "best hour", "best weekday", displayMode, dateSetting, period]}
        metrics={[
          { label: "Display Mode", value: displayMode },
          { label: "Date Setting", value: dateSetting },
          { label: "Period", value: period },
          { label: summaryStats?.bestLabel ?? "Best Period", value: summaryStats ? `${summaryStats.bestName} (${formatCurrency(summaryStats.bestValue)})` : "N/A" },
          { label: summaryStats?.worstLabel ?? "Worst Period", value: summaryStats ? `${summaryStats.worstName} (${formatCurrency(summaryStats.worstValue)})` : "N/A" },
          { label: summaryStats?.tradesLabel ?? "Trades per Period", value: summaryStats ? summaryStats.avgTrades.toFixed(2) : "0.00" },
          { label: summaryStats?.avgPnLLabel ?? "Average Period P&L", value: summaryStats ? formatCurrency(summaryStats.avgPeriodPnL) : formatCurrency(0) },
        ]}
        series={[
          {
            label: displayMode === "dollar" ? "Time Bucket Return" : displayMode === "percent" ? "Time Bucket Return Percent" : "Time Bucket Return R",
            points: chartData.slice(0, 240).map((point) => ({
              x: point.name,
              y: String(point.value),
            })),
          },
          {
            label: "Period Trades",
            points: tableData.slice(0, 240).map((item) => ({
              x: item.name,
              y: String(item.trades),
            })),
          },
          {
            label: "Period Win Rate",
            points: tableData.slice(0, 240).map((item) => ({
              x: item.name,
              y: String(item.winRate),
            })),
          },
        ]}
      />
      {/* Header Controls */}
      <div className="flex items-center gap-4 shrink-0">
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

         <div className="w-[180px]">
            <label className="text-[10px] text-slate-400 ml-1 mb-1 block">Period</label>
            <Select
                value={period}
                onValueChange={(v: Period) => setPeriod(v)}
            >
              <SelectTrigger className="bg-slate-900 border-slate-700 text-white hover:bg-slate-800">
                <SelectValue placeholder="Period" />
              </SelectTrigger>
              <SelectContent className="bg-slate-900 border-slate-800 text-slate-300">
                <SelectItem value="5min" className="hover:bg-slate-800 focus:bg-slate-800 cursor-pointer">5 minute intervals</SelectItem>
                <SelectItem value="15min" className="hover:bg-slate-800 focus:bg-slate-800 cursor-pointer">15 minute intervals</SelectItem>
                <SelectItem value="30min" className="hover:bg-slate-800 focus:bg-slate-800 cursor-pointer">30 minute intervals</SelectItem>
                <SelectItem value="hour" className="hover:bg-slate-800 focus:bg-slate-800 cursor-pointer">Hourly</SelectItem>
                <SelectItem value="weekday" className="hover:bg-slate-800 focus:bg-slate-800 cursor-pointer">Daily</SelectItem>
                <SelectItem value="week" className="hover:bg-slate-800 focus:bg-slate-800 cursor-pointer">Weekly</SelectItem>
                <SelectItem value="month" className="hover:bg-slate-800 focus:bg-slate-800 cursor-pointer">Monthly</SelectItem>
                <SelectItem value="year" className="hover:bg-slate-800 focus:bg-slate-800 cursor-pointer">Yearly</SelectItem>
              </SelectContent>
            </Select>
         </div>
      </div>

      {/* Content Wrapper */}
      <div className="flex flex-col gap-4 flex-1 min-h-0 bg-black">

        {/* Chart Area - Top 55% */}
        <div className="flex-[0.55] w-full bg-slate-950/50 rounded-lg border border-slate-800 p-4 relative min-h-[200px]">
          {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} barCategoryGap="5%">
              <CartesianGrid vertical={false} stroke="#334155" strokeDasharray="3 3" opacity={0.5} />
              <XAxis
                  dataKey="name"
                  tick={{ fill: '#64748b', fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                  interval="preserveStartEnd" // Let Recharts decide interval for crowding
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
                      value: displayMode === 'percent' ? 'Return (%)' : displayMode === 'dollar' ? 'Return ($)' : 'Return (R)',
                      angle: -90,
                      position: 'insideLeft',
                      fill: '#64748b',
                      fontSize: 12
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
                  No time data available.
              </div>
          )}
        </div>

        {/* Bottom Split - Flex 45% */}
        <div className="flex-[0.45] flex gap-4 min-h-0">

             {/* Left: Table */}
             <div className="flex-1 overflow-hidden bg-black rounded-lg border border-slate-800">
                <div className="h-full overflow-auto">
                    <Table>
                        <TableHeader className="bg-slate-900/50 sticky top-0 backdrop-blur-sm z-10">
                            <TableRow className="border-slate-800 hover:bg-slate-900/50">
                                <TableHead className="text-slate-400 h-8 text-[11px] font-medium"></TableHead>
                                <TableHead className="text-slate-400 h-8 text-[11px] font-medium text-right">Trades</TableHead>
                                <TableHead className="text-slate-400 h-8 text-[11px] font-medium text-right">Winrate (%)</TableHead>
                                <TableHead className="text-slate-400 h-8 text-[11px] font-medium text-right">Avg. P&L ($)</TableHead>
                                <TableHead className="text-slate-400 h-8 text-[11px] font-medium text-right">Total Gain ($)</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {tableData.map((item) => (
                                <TableRow key={item.name} className="border-slate-800 hover:bg-slate-900/30 transition-colors">
                                    <TableCell className="font-medium text-slate-200 py-1.5 text-xs">{item.name}</TableCell>
                                    <TableCell className="text-right text-slate-300 py-1.5 text-xs">{item.trades}</TableCell>
                                    <TableCell className="text-right text-slate-300 py-1.5 text-xs">{item.winRate.toFixed(2)}</TableCell>
                                    <TableCell className="text-right text-slate-300 py-1.5 text-xs">{item.avgPnL.toFixed(2)}</TableCell>
                                    <TableCell className={`text-right font-medium py-1.5 text-xs ${item.totalPnL >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                                        {formatCurrency(item.totalPnL)}
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </div>
             </div>

             {/* Right: Stats Grid */}
             <div className="flex-1 flex flex-col gap-3 overflow-y-auto pr-1">
                 {summaryStats && (
                     <>
                        <div className="flex gap-3">
                             <InstrumentMetricCard
                                title={summaryStats.bestLabel}
                                value={formatCurrency(summaryStats.bestValue)}
                                color="green"
                             />
                             <InstrumentMetricCard
                                title={summaryStats.worstLabel}
                                value={formatCurrency(summaryStats.worstValue)}
                                color="red"
                             />
                        </div>
                        <div className="flex gap-3">
                             <InstrumentMetricCard
                                title={summaryStats.tradesLabel}
                                value={summaryStats.avgTrades.toFixed(2)}
                                color="green"
                                tooltip="Average trades per period"
                             />
                             <InstrumentMetricCard
                                title={summaryStats.avgPnLLabel}
                                value={formatCurrency(summaryStats.avgPeriodPnL)}
                                color={summaryStats.avgPeriodPnL >= 0 ? "green" : "red"}
                             />
                        </div>
                     </>
                 )}
             </div>
        </div>

      </div>
    </div>
  )
}

function calculateStats(name: string, trades: Trade[], initialBalance: number, sortKey: number | string): TimeStats {
    const count = trades.length

    // Calculate Metrics
    let totalPnL = 0
    let totalPnLR = 0
    let totalPnLPercent = 0
    let wins = 0

    trades.forEach(t => {
        let pnl = 0
        if (t.profit_loss !== undefined) pnl = safelyParseFloat(t.profit_loss)
        else if (t.net_profit !== undefined) pnl = safelyParseFloat(t.net_profit)
        else if (t.pnl !== undefined) pnl = safelyParseFloat(t.pnl)

        totalPnL += pnl
        if (pnl > 0) wins++

        // R
        const r = safelyParseFloat(t.r_multiple)
        totalPnLR += r

        // Percent
        if (t.profit_percent !== undefined) totalPnLPercent += safelyParseFloat(t.profit_percent)
        else totalPnLPercent += (pnl / initialBalance) * 100
    })

    const winRate = count > 0 ? (wins / count) * 100 : 0
    const avgPnL = count > 0 ? totalPnL / count : 0

    return {
        name,
        sortKey,
        trades: count,
        wins,
        winRate,
        totalPnL,
        avgPnL,
        totalPnLPercent,
        totalPnLR
    }
}

function InstrumentMetricCard({ title, value, tooltip, color = "green" }: { title: string, value: string | number, tooltip?: string, color?: "green" | "red" }) {
  const barColor = color === 'red' ? 'bg-red-500' : 'bg-green-500';

  return (
    <Card className="bg-slate-900 border-slate-800 flex-1 min-w-fit">
      <CardContent className="p-0 flex items-stretch overflow-hidden h-full">
         <div className={`w-1.5 ${barColor} shrink-0`} />
         <div className="flex flex-col justify-center px-2 py-0.5">
             <div className="flex items-center gap-1">
                <TooltipProvider>
                    <UiTooltip>
                        <TooltipTrigger asChild>
                            <span className="text-[9px] text-slate-400 font-medium cursor-help hover:text-slate-300 transition-colors uppercase tracking-wider text-left leading-tight block">
                              {title}
                            </span>
                        </TooltipTrigger>
                        {tooltip && <TooltipContent><p>{tooltip}</p></TooltipContent>}
                    </UiTooltip>
                </TooltipProvider>
             </div>
             <span className="text-sm font-bold text-white leading-tight mt-0.5 text-left">
                {value}
             </span>
         </div>
      </CardContent>
    </Card>
  )
}
