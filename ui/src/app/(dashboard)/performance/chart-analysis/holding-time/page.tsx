"use client"

import { CustomChartSemanticSnapshot } from "@/components/ai-chat/CustomChartSemanticSnapshot"
import { useMemo, useState, useEffect } from "react"
import {
  ScatterChart,
  Scatter,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
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
import { Info, Loader2 } from "lucide-react"
import { strategyApi } from "@/lib/api/strategies"

type DisplayMode = "dollar" | "percent" | "r_multiple"
type TimeUnit = "minutes" | "hours" | "days"

interface Trade {
    profit_loss?: number | string | null
    commission?: number | string | null
    swap?: number | string | null
    open_time?: string | null
    close_time?: string | null
    entry_time?: string | null
    exit_time?: string | null
    net_profit?: number | string | null
    pnl?: number | string | null
    profit_percent?: number | string | null
    r_multiple?: number | string | null
    [key: string]: unknown
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

function formatDuration(value: number, unit: TimeUnit) {
    return `${value.toFixed(2)}`
}

const safelyParseFloat = (value: string | number | null | undefined): number => {
    if (value === undefined || value === null || value === "") return 0
    if (typeof value === "number") return Number.isFinite(value) ? value : 0
    const parsed = parseFloat(value)
    return isNaN(parsed) ? 0 : parsed
}

const safeTimestamp = (value: string | null | undefined): number => {
    if (!value) return 0
    const parsed = new Date(value).getTime()
    return Number.isFinite(parsed) ? parsed : 0
}

export default function HoldingTimePage() {
  const { selectedBacktest } = useSelectedBacktest()
  const [displayMode, setDisplayMode] = useState<DisplayMode>("dollar")
  const [timeUnit, setTimeUnit] = useState<TimeUnit>("minutes")
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

  const { chartData, stats } = useMemo(() => {
    if (trades.length === 0) return { chartData: [], stats: null }

    const data = trades.map((trade: Trade, index: number) => {
        // Return Value
        let retVal = 0

        let pnlVal = 0
        if (trade.profit_loss !== undefined) pnlVal = safelyParseFloat(trade.profit_loss)
        else if (trade.net_profit !== undefined) pnlVal = safelyParseFloat(trade.net_profit)
        else if (trade.pnl !== undefined) pnlVal = safelyParseFloat(trade.pnl)

        if (displayMode === 'dollar') {
            retVal = pnlVal
        } else if (displayMode === 'percent') {
            // Percent of initial balance? Or percent return on trade?
            // Usually "Return, gain sum (%)" implies return on account or return on margin.
            // Following Drawdown page logic: return on initial balance for simplicity unless trade.profit_percent exists
            if (trade.profit_percent !== undefined) retVal = safelyParseFloat(trade.profit_percent)
            else retVal = (pnlVal / initialBalance) * 100
        } else {
            // R Multiple
             retVal = safelyParseFloat(trade.r_multiple)
        }

        // Duration
        const open = safeTimestamp(trade.open_time ?? trade.entry_time)
        const close = safeTimestamp(trade.close_time ?? trade.exit_time)
        let durationMs = close - open
        if (durationMs < 0) durationMs = 0 // Should not happen but safety first

        let duration = 0
        if (timeUnit === 'minutes') duration = durationMs / (1000 * 60)
        else if (timeUnit === 'hours') duration = durationMs / (1000 * 60 * 60)
        else duration = durationMs / (1000 * 60 * 60 * 24) // Days

        // Determine if winner or loser (based on P&L, not display value to be consistent)
        const isWin = pnlVal > 0

        return {
            tradeNumber: index + 1,
            x: duration,
            y: retVal,
            isWin,
            pnl: pnlVal,
            rawDurationMinutes: durationMs / (1000 * 60)
        }
    })

    // Stats Calculation
    const winners = data.filter(d => d.isWin)
    const losers = data.filter(d => !d.isWin)

    // Use d.x which is already converted to the selected timeUnit
    const winnersDurationSum = winners.reduce((sum, d) => sum + d.x, 0)
    const losersDurationSum = losers.reduce((sum, d) => sum + d.x, 0)

    const winnersDurationAvg = winners.length > 0 ? winnersDurationSum / winners.length : 0
    const losersDurationAvg = losers.length > 0 ? losersDurationSum / losers.length : 0

    // Biggest Winner (Max Profit)
    let biggestWinnerDuration = 0
    if (winners.length > 0) {
        const maxWin = winners.reduce((max, d) => d.pnl > max.pnl ? d : max, winners[0])
        biggestWinnerDuration = maxWin.x
    }

    // Biggest Loser (Max Loss - lowest negative number)
    let biggestLoserDuration = 0
    if (losers.length > 0) {
        const maxLoss = losers.reduce((min, d) => d.pnl < min.pnl ? d : min, losers[0])
        biggestLoserDuration = maxLoss.x
    }

    return {
        chartData: data,
        stats: {
            winnersAvg: winnersDurationAvg,
            losersAvg: losersDurationAvg,
            winnersSum: winnersDurationSum,
            losersSum: losersDurationSum,
            biggestWinner: biggestWinnerDuration,
            biggestLoser: biggestLoserDuration
        }
    }
  }, [trades, initialBalance, displayMode, timeUnit])


  const formattedStats = useMemo(() => {
      if (!stats) return null

      const unitLabel = timeUnit.charAt(0).toUpperCase() + timeUnit.slice(1)

      return {
          unitLabel,
          winnersAvg: stats.winnersAvg.toFixed(2),
          losersAvg: stats.losersAvg.toFixed(2),
          winnersSum: stats.winnersSum.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
          losersSum: stats.losersSum.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
          biggestWinner: stats.biggestWinner.toFixed(2),
          biggestLoser: stats.biggestLoser.toFixed(2)
      }

  }, [stats, timeUnit])

  if (!selectedBacktest) {
      return <div className="p-6">No backtest selected.</div>
  }

  if (loading) {
      return <div className="flex items-center justify-center p-12 text-muted-foreground">Loading holding time data...</div>
  }

  return (
    <div className="flex flex-col gap-4 p-4 h-full bg-black overflow-hidden">
      <CustomChartSemanticSnapshot
        id={`holding-time:${selectedBacktest.backtest_id}:${displayMode}:${timeUnit}`}
        title="Holding Time Analysis"
        summary="Trade holding-time scatterplot relating duration to outcome, with average and extreme hold-time statistics."
        keywords={["holding time", "trade duration", "winners", "losers", displayMode, timeUnit]}
        metrics={[
          { label: "Display Mode", value: displayMode },
          { label: "Time Unit", value: timeUnit },
          { label: "Trade Count", value: String(chartData.length) },
          { label: "Winners Average Holding Time", value: formattedStats?.winnersAvg ?? "0.00" },
          { label: "Losers Average Holding Time", value: formattedStats?.losersAvg ?? "0.00" },
          { label: "Winners Holding Time Sum", value: formattedStats?.winnersSum ?? "0.00" },
          { label: "Losers Holding Time Sum", value: formattedStats?.losersSum ?? "0.00" },
          { label: "Biggest Winner Holding Time", value: formattedStats?.biggestWinner ?? "0.00" },
          { label: "Biggest Loser Holding Time", value: formattedStats?.biggestLoser ?? "0.00" },
        ]}
        series={[
          {
            label: "Trade Holding Time vs Return",
            points: chartData.slice(-240).map((point) => ({
              x: `Trade ${point.tradeNumber} (${point.x.toFixed(2)} ${timeUnit})`,
              y: String(point.y),
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
            <label className="text-[10px] text-slate-400 ml-1 mb-1 block">Time Settings</label>
            <Select
                value={timeUnit}
                onValueChange={(v: TimeUnit) => setTimeUnit(v)}
            >
              <SelectTrigger className="bg-slate-900 border-slate-700 text-white hover:bg-slate-800">
                <SelectValue placeholder="Time Unit" />
              </SelectTrigger>
              <SelectContent className="bg-slate-900 border-slate-800 text-slate-300">
                <SelectItem value="minutes" className="hover:bg-slate-800 focus:bg-slate-800 cursor-pointer">Minutes</SelectItem>
                <SelectItem value="hours" className="hover:bg-slate-800 focus:bg-slate-800 cursor-pointer">Hours</SelectItem>
                <SelectItem value="days" className="hover:bg-slate-800 focus:bg-slate-800 cursor-pointer">Days</SelectItem>
              </SelectContent>
            </Select>
         </div>
      </div>

      {/* Content Wrapper */}
      <div className="flex flex-col gap-4 flex-1 min-h-0 bg-black">

        {/* Chart Area */}
        <div className="flex-1 w-full bg-slate-950/50 rounded-lg border border-slate-800 p-4 relative min-h-[200px]">
          {trades.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart>
              <CartesianGrid vertical={false} stroke="#334155" strokeDasharray="3 3" opacity={0.5} />
              <XAxis
                  type="number"
                  dataKey="x"
                  name="Time"
                  unit=""
                  tick={{ fill: '#64748b', fontSize: 12 }}
                  axisLine={false}
                  tickLine={false}
                  label={{
                      value: timeUnit.charAt(0).toUpperCase() + timeUnit.slice(1),
                      position: 'insideBottom',
                      offset: -5,
                      fill: '#64748b',
                      fontSize: 12
                  }}
              />
              <YAxis
                  type="number"
                  dataKey="y"
                  name="Return"
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
              <ZAxis type="number" range={[50, 50]} />
              <Tooltip
                  cursor={{ strokeDasharray: '3 3' }}
                  content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                          const data = payload[0].payload;
                          return (
                              <div className="bg-slate-900 border border-slate-800 p-2 rounded shadow-md text-slate-100 text-xs">
                                  <div>Trade #{data.tradeNumber}</div>
                                  <div>Time: {formatDuration(data.x, timeUnit)} {timeUnit}</div>
                                  <div>Return: {
                                      displayMode === 'dollar' ? formatCurrency(data.y) :
                                      displayMode === 'percent' ? formatPercent(data.y) :
                                      formatR(data.y)
                                  }</div>
                              </div>
                          );
                      }
                      return null;
                  }}
              />
              <ReferenceLine y={0} stroke="#64748b" />
              <Scatter name="Trades" data={chartData} fill="#8884d8">
                  {chartData.map((entry, index: number) => (
                      <Cell key={`cell-${index}`} fill={entry.y > 0 ? '#22c55e' : '#ef4444'} />
                  ))}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
          ) : (
              <div className="flex items-center justify-center h-full text-muted-foreground">
                  No trade data available for holding time analysis.
              </div>
          )}
        </div>

        {/* Metrics Grid */}
        <div className="flex flex-wrap gap-2 items-start w-full">
            {formattedStats && (
            <>
                 <HoldingTimeMetricCard
                    title={`Winners Holding Time Avg (${formattedStats.unitLabel})`}
                    value={formattedStats.winnersAvg}
                    color="green"
                    lineBreakTitle
                 />
                 <HoldingTimeMetricCard
                    title={`Losers Holding Time Avg (${formattedStats.unitLabel})`}
                    value={formattedStats.losersAvg}
                    color="green"
                    lineBreakTitle
                 />
                 <HoldingTimeMetricCard
                    title={`Winners Holding Time Sum (${formattedStats.unitLabel})`}
                    value={formattedStats.winnersSum}
                    color="green"
                    lineBreakTitle
                 />
                 <HoldingTimeMetricCard
                    title={`Losers Holding Time Sum (${formattedStats.unitLabel})`}
                    value={formattedStats.losersSum}
                    color="green"
                    lineBreakTitle
                 />
                 <HoldingTimeMetricCard
                    title={`Biggest Winner (${formattedStats.unitLabel})`}
                    value={formattedStats.biggestWinner}
                    tooltip="Holding time of the trade with the largest profit"
                    color="green"
                    lineBreakTitle
                 />
                 <HoldingTimeMetricCard
                    title={`Biggest Loser (${formattedStats.unitLabel})`}
                    value={formattedStats.biggestLoser}
                    tooltip="Holding time of the trade with the largest loss"
                    color="green"
                    lineBreakTitle
                 />
            </>
            )}
        </div>
      </div>
    </div>
  )
}

function HoldingTimeMetricCard({ title, value, tooltip, color = "green", lineBreakTitle = false }: { title: string, value: string | number, tooltip?: string, color?: "green" | "red" | "amber" | "orange", lineBreakTitle?: boolean }) {
  const barColor = color === 'red' ? 'bg-red-500' : color === 'amber' ? 'bg-amber-500' : color === 'orange' ? 'bg-orange-500' : 'bg-green-500';

  return (
    <Card className="bg-slate-900 border-slate-800 flex-1 min-w-fit">
      <CardContent className="p-0 flex items-stretch overflow-hidden h-full">
         <div className={`w-1.5 ${barColor} shrink-0`} />
         <div className="flex flex-col justify-center px-3 py-2">
             <div className="flex items-center gap-1">
                <TooltipProvider>
                    <UiTooltip>
                        <TooltipTrigger asChild>
                            <span className="text-[10px] text-slate-400 font-medium cursor-help hover:text-slate-300 transition-colors uppercase tracking-wider text-left leading-tight block max-w-[150px]">
                              {title}
                            </span>
                        </TooltipTrigger>
                        {tooltip && <TooltipContent><p>{tooltip}</p></TooltipContent>}
                    </UiTooltip>
                </TooltipProvider>
             </div>
             <span className="text-lg font-bold text-white leading-tight mt-1 text-left">
                {value}
             </span>
         </div>
      </CardContent>
    </Card>
  )
}
