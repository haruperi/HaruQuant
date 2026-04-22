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
import { Info, Loader2 } from "lucide-react"
import { strategyApi } from "@/lib/api/strategies"

type DisplayMode = "dollar" | "percent" | "r_multiple"
type SortMode = "name" | "value"

interface Trade {
    symbol: string
    profit_loss: number
    commission: number
    swap: number
    r_multiple?: number
    profit_percent?: number
    net_profit?: number
    pnl?: number
    [key: string]: any
}

interface InstrumentStats {
    symbol: string
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

export default function PerformanceByInstrumentPage() {
  const { selectedBacktest } = useSelectedBacktest()
  const [displayMode, setDisplayMode] = useState<DisplayMode>("dollar")
  const [sortMode, setSortMode] = useState<SortMode>("name")
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

    // Group by Symbol
    trades.forEach(trade => {
        const symbol = trade.symbol || "Unknown"
        if (!grouped[symbol]) grouped[symbol] = []
        grouped[symbol].push(trade)
    })

    const items: InstrumentStats[] = Object.keys(grouped).map(symbol => {
        const symbolTrades = grouped[symbol]
        const count = symbolTrades.length

        // Calculate Metrics
        let totalPnL = 0
        let totalPnLR = 0
        let totalPnLPercent = 0
        let wins = 0

        symbolTrades.forEach(t => {
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
            // Assuming per-trade percent or calculating based on initial balance not ideal for aggregate?
            // Usually "Instrument Performance %" is sum of trade % returns?
            // Let's stick to (Total PnL / Initial Balance) * 100 for proper portfolio impact?
            // Or sum of individual trade percents? Implementation Plan said "Return, gain sum (%)"
            if (t.profit_percent !== undefined) totalPnLPercent += safelyParseFloat(t.profit_percent)
            else totalPnLPercent += (pnl / initialBalance) * 100
        })

        const winRate = count > 0 ? (wins / count) * 100 : 0
        const avgPnL = count > 0 ? totalPnL / count : 0

        return {
            symbol,
            trades: count,
            wins,
            winRate,
            totalPnL,
            avgPnL,
            totalPnLR,
            totalPnLPercent
        }
    })

    // Sort
    if (sortMode === 'name') {
        items.sort((a, b) => a.symbol.localeCompare(b.symbol))
    } else {
        // Sort by Value (based on display mode)
        items.sort((a, b) => {
             const valA = displayMode === 'dollar' ? a.totalPnL : displayMode === 'percent' ? a.totalPnLPercent : a.totalPnLR
             const valB = displayMode === 'dollar' ? b.totalPnL : displayMode === 'percent' ? b.totalPnLPercent : b.totalPnLR
             return valB - valA // Descending
        })
    }

    // Chart Data Preparation
    const cData = items.map(item => ({
        name: item.symbol,
        value: displayMode === 'dollar' ? item.totalPnL : displayMode === 'percent' ? item.totalPnLPercent : item.totalPnLR,
        color: (displayMode === 'dollar' ? item.totalPnL : displayMode === 'percent' ? item.totalPnLPercent : item.totalPnLR) >= 0 ? '#22c55e' : '#ef4444'
    }))

    // Summary Stats
    const bestItem = items.reduce((prev, current) => (prev.totalPnL > current.totalPnL) ? prev : current, items[0])
    const worstItem = items.reduce((prev, current) => (prev.totalPnL < current.totalPnL) ? prev : current, items[0])

    // Avg PnL Best/Worst
    const bestAvgItem = items.reduce((prev, current) => (prev.avgPnL > current.avgPnL) ? prev : current, items[0])
    const worstAvgItem = items.reduce((prev, current) => (prev.avgPnL < current.avgPnL) ? prev : current, items[0])


    const stats = {
        bestSum: bestItem.totalPnL,
        worstSum: worstItem.totalPnL,
        bestAvg: bestAvgItem.avgPnL,
        worstAvg: worstAvgItem.avgPnL,
        count: items.length
    }

    return {
        chartData: cData,
        tableData: items,
        summaryStats: stats
    }
  }, [trades, initialBalance, displayMode, sortMode])


  if (!selectedBacktest) {
      return <div className="p-6">No backtest selected.</div>
  }

  if (loading) {
      return <div className="flex items-center justify-center p-12 text-muted-foreground">Loading instrument data...</div>
  }

  return (
    <div className="flex flex-col gap-4 p-4 h-full bg-black overflow-hidden">
      <CustomChartSemanticSnapshot
        id={`performance-by-instrument:${selectedBacktest.backtest_id}:${displayMode}:${sortMode}`}
        title="Performance By Instrument"
        summary="Instrument-level trade performance ranking with total gain, average P&L, and win-rate comparisons."
        keywords={["performance by instrument", "symbol performance", "best instrument", "worst instrument", displayMode, sortMode]}
        metrics={[
          { label: "Display Mode", value: displayMode },
          { label: "Sort Mode", value: sortMode },
          { label: "Instrument Count", value: summaryStats ? String(summaryStats.count) : "0" },
          { label: "Best Instrument Sum", value: summaryStats ? formatCurrency(summaryStats.bestSum) : formatCurrency(0) },
          { label: "Worst Instrument Sum", value: summaryStats ? formatCurrency(summaryStats.worstSum) : formatCurrency(0) },
          { label: "Best Instrument Avg", value: summaryStats ? formatCurrency(summaryStats.bestAvg) : formatCurrency(0) },
          { label: "Worst Instrument Avg", value: summaryStats ? formatCurrency(summaryStats.worstAvg) : formatCurrency(0) },
        ]}
        series={[
          {
            label: displayMode === "dollar" ? "Instrument Return" : displayMode === "percent" ? "Instrument Return Percent" : "Instrument Return R",
            points: chartData.slice(0, 240).map((point) => ({
              x: point.name,
              y: String(point.value),
            })),
          },
          {
            label: "Instrument Trades",
            points: tableData.slice(0, 240).map((item) => ({
              x: item.symbol,
              y: String(item.trades),
            })),
          },
          {
            label: "Instrument Win Rate",
            points: tableData.slice(0, 240).map((item) => ({
              x: item.symbol,
              y: String(item.winRate),
            })),
          },
        ]}
      />
      {/* Header Controls */}
      <div className="flex items-center gap-4 shrink-0">
         <div className="w-[200px]">
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

         <div className="w-[200px]">
            <label className="text-[10px] text-slate-400 ml-1 mb-1 block">Sort By</label>
            <Select
                value={sortMode}
                onValueChange={(v: SortMode) => setSortMode(v)}
            >
              <SelectTrigger className="bg-slate-900 border-slate-700 text-white hover:bg-slate-800">
                <SelectValue placeholder="Sort By" />
              </SelectTrigger>
              <SelectContent className="bg-slate-900 border-slate-800 text-slate-300">
                <SelectItem value="name" className="hover:bg-slate-800 focus:bg-slate-800 cursor-pointer">By Name</SelectItem>
                <SelectItem value="value" className="hover:bg-slate-800 focus:bg-slate-800 cursor-pointer">By Value</SelectItem>
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
            <BarChart data={chartData}>
              <CartesianGrid vertical={false} stroke="#334155" strokeDasharray="3 3" opacity={0.5} />
              <XAxis
                  dataKey="name"
                  tick={{ fill: '#64748b', fontSize: 12 }}
                  axisLine={false}
                  tickLine={false}
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
                  No instrument data available.
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
                                <TableRow key={item.symbol} className="border-slate-800 hover:bg-slate-900/30 transition-colors">
                                    <TableCell className="font-medium text-slate-200 py-1.5 text-xs">{item.symbol}</TableCell>
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
                                title="Best Instrument Sum"
                                value={formatCurrency(summaryStats.bestSum)}
                                color="green"
                                tooltip="Highest Total Gain"
                             />
                             <InstrumentMetricCard
                                title="Worst Instrument Sum"
                                value={formatCurrency(summaryStats.worstSum)}
                                color="red"
                                tooltip="Lowest Total Gain"
                             />
                        </div>
                        <div className="flex gap-3">
                             <InstrumentMetricCard
                                title="Best Instrument Avg"
                                value={formatCurrency(summaryStats.bestAvg)}
                                color="green"
                                tooltip="Highest Average P&L per trade"
                             />
                             <InstrumentMetricCard
                                title="Worst Instrument Avg"
                                value={formatCurrency(summaryStats.worstAvg)}
                                color="red"
                                tooltip="Lowest Average P&L per trade"
                             />
                        </div>
                        <div className="w-1/2">
                             <InstrumentMetricCard
                                title="Number of Instruments"
                                value={summaryStats.count}
                                color="green"
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
