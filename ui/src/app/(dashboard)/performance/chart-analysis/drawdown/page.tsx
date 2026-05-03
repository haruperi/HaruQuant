"use client"

import { useMemo, useState, useEffect } from "react"
import { CustomChartSemanticSnapshot } from "@/components/ai-chat/CustomChartSemanticSnapshot"
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  ReferenceLine,
} from "recharts"
import { useSelectedBacktest } from "@/contexts/selected-backtest-context"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
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

interface Trade {
    profit_loss?: number | string | null
    commission?: number | string | null
    swap?: number | string | null
    close_time?: string | null
    net_profit?: number | string | null
    profit?: number | string | null
    pnl?: number | string | null
    r_multiple?: number | string | null
    commissions?: number | string | null
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

const safelyParseFloat = (value: string | number | null | undefined): number => {
    if (value === undefined || value === null || value === "") return 0
    if (typeof value === "number") return Number.isFinite(value) ? value : 0
    const parsed = parseFloat(value)
    return isNaN(parsed) ? 0 : parsed
}

function formatCloseTime(value: string | null | undefined) {
    if (!value) return "unknown_time"
    const parsed = new Date(value)
    if (Number.isNaN(parsed.getTime())) {
        return value
    }
    return parsed.toISOString()
}

export default function DrawdownPage() {
  const { selectedBacktest } = useSelectedBacktest()
  const [displayMode, setDisplayMode] = useState<DisplayMode>("dollar")
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

    let currentEquity = initialBalance
    let maxEquity = currentEquity
    let currentEquityR = 0 // Starting at 0R
    let maxEquityR = 0


    const data = trades.map((trade: Trade, index: number) => {
        // Robust parsing trying all common backend field names
        // Order: profit_loss -> net_profit -> profit -> pnl
        let pnlVal = 0
        if (trade.profit_loss !== undefined) pnlVal = safelyParseFloat(trade.profit_loss)
        else if (trade.net_profit !== undefined) pnlVal = safelyParseFloat(trade.net_profit)
        else if (trade.profit !== undefined) pnlVal = safelyParseFloat(trade.profit)
        else if (trade.pnl !== undefined) pnlVal = safelyParseFloat(trade.pnl)

        const comm = safelyParseFloat(trade.commission || trade.commissions)
        const swap = safelyParseFloat(trade.swap)

        // If pnlVal is "Net Profit", it usually already includes comm/swap.
        // If it's "Gross Profit" or "profit_loss" (sometimes gross), we might need to add them.
        // However, standardizing: usually 'profit_loss' in this app seems to be Net.
        // But if we calculate manually:
        // Let's assume the extracted value is the primary P&L.
        // If we strictly follow TradesCalendar:
        // "let pnl = t.profit_loss ... totalPnL += pnl"
        // It does NOT add commission/swap to 'pnl' for the totalPnL chart line.
        // It calculates 'commissions' separately for stats but seems to use 'pnl' directly for the chart.
        // So we should just use the extracted pnlVal as the Net P/L for the trade.

        const pl = pnlVal

        // Dollar
        currentEquity += pl
        if (currentEquity > maxEquity) maxEquity = currentEquity
        const drawdownDollar = currentEquity - maxEquity

        // Percent
        // Drawdown % is relative to the Peak Equity at that point
        const maxEqSafe = maxEquity > 0 ? maxEquity : 1 // Avoid division by zero
        const drawdownPercent = (drawdownDollar / maxEqSafe) * 100

        // R-Multiple
        const rVal = safelyParseFloat(trade.r_multiple)
        const rValue = rVal

        currentEquityR += rValue
        if (currentEquityR > maxEquityR) maxEquityR = currentEquityR
        const drawdownR = currentEquityR - maxEquityR

        return {
            tradeNumber: index + 1,
            drawdownDollar,
            drawdownPercent,
            drawdownR,
            pl,
            closeTime: trade.close_time
        }
    })

    // Calculate Stats
    const series = data.map(d =>
        displayMode === 'dollar' ? d.drawdownDollar :
        displayMode === 'percent' ? d.drawdownPercent :
        d.drawdownR
    )

    const ddPoints = series.filter(v => v < 0)
    const worstDrawdown = series.length > 0 ? Math.min(...series) : 0
    const averageDrawdown = ddPoints.length > 0 ? ddPoints.reduce((a, b) => a + b, 0) / ddPoints.length : 0
    const currentDrawdown = series.length > 0 ? series[series.length - 1] : 0

    // Durations
    const maxDDIndex = series.indexOf(worstDrawdown)

    let peakIndex = maxDDIndex
    while (peakIndex >= 0 && series[peakIndex] < -0.000001) {
        peakIndex--
    }

    const topToBottom = maxDDIndex - peakIndex

    let recoveryIndex = maxDDIndex
    while (recoveryIndex < series.length && series[recoveryIndex] < -0.000001) {
        recoveryIndex++
    }

    const bottomToTop = (recoveryIndex < series.length) ? (recoveryIndex - maxDDIndex) : (series.length - 1 - maxDDIndex)


    // Return to Drawdown
    const totalProfitDollar = currentEquity - initialBalance
    const totalProfitPercent = ((currentEquity - initialBalance) / initialBalance) * 100
    const totalProfitR = currentEquityR

    let returnToDrawdown = 0
    if (Math.abs(worstDrawdown) > 0.000001) {
         if (displayMode === 'dollar') returnToDrawdown = totalProfitDollar / Math.abs(worstDrawdown)
         else if (displayMode === 'percent') returnToDrawdown = totalProfitPercent / Math.abs(worstDrawdown)
         else returnToDrawdown = totalProfitR / Math.abs(worstDrawdown)
    }

    return {
        chartData: data,
        stats: {
            worstDrawdown,
            averageDrawdown,
            currentDrawdown,
            topToBottom,
            bottomToTop,
            returnToDrawdown,
            worstDrawdownIndex: maxDDIndex >= 0 ? maxDDIndex : null
        }
    }
  }, [trades, initialBalance, displayMode]) // Depends on trades state


  const formattedStats = useMemo(() => {
      if (!stats) return null

      const format = (val: number) => {
          if (displayMode === 'dollar') return formatCurrency(Math.abs(val))
          if (displayMode === 'percent') return formatPercent(Math.abs(val))
          return formatR(Math.abs(val))
      }

      return {
          worst: format(stats.worstDrawdown),
          avg: format(stats.averageDrawdown),
          current: format(stats.currentDrawdown),

          worstDisplay: displayMode === 'dollar' ? formatCurrency(Math.abs(stats.worstDrawdown)) :
                        format(stats.worstDrawdown),

          avgDisplay: format(stats.averageDrawdown),

          currentDisplay: (displayMode === 'dollar' ? formatCurrency(stats.currentDrawdown) :
                           displayMode === 'percent' ? formatPercent(stats.currentDrawdown) :
                           formatR(stats.currentDrawdown)),

          topToBottom: stats.topToBottom,
          bottomToTop: stats.bottomToTop,
          returnToDrawdown: stats.returnToDrawdown.toFixed(2)
      }

  }, [stats, displayMode])

  if (!selectedBacktest) {
      return <div className="p-6">No backtest selected.</div>
  }

  if (loading) {
      return <div className="flex items-center justify-center p-12 text-muted-foreground">Loading drawdown data...</div>
  }

  const worstDrawdownPoint =
    stats && stats.worstDrawdownIndex !== null && stats.worstDrawdownIndex >= 0
      ? chartData[stats.worstDrawdownIndex]
      : null

  return (
    <div className="flex flex-col gap-4 p-4 h-full bg-black overflow-hidden">
      <CustomChartSemanticSnapshot
        id={`drawdown-analysis:${selectedBacktest.backtest_id}:${displayMode}`}
        title="Drawdown Analysis"
        summary="Trade-by-trade drawdown chart with extrema, recovery span, and current drawdown state."
        keywords={[
          "drawdown",
          "highest drawdown",
          "worst drawdown",
          "trade drawdown",
          "max drawdown",
          "recovery",
          displayMode,
        ]}
        metrics={[
          {
            label: "Worst Drawdown",
            value: stats
              ? (
                  displayMode === "dollar"
                    ? formatCurrency(stats.worstDrawdown)
                    : displayMode === "percent"
                      ? formatPercent(stats.worstDrawdown)
                      : formatR(stats.worstDrawdown)
                )
              : "N/A",
          },
          {
            label: "Worst Drawdown Trade",
            value: worstDrawdownPoint ? String(worstDrawdownPoint.tradeNumber) : "N/A",
          },
          {
            label: "Worst Drawdown Time",
            value: worstDrawdownPoint ? formatCloseTime(worstDrawdownPoint.closeTime) : "N/A",
          },
          {
            label: "Current Drawdown",
            value: stats
              ? (
                  displayMode === "dollar"
                    ? formatCurrency(stats.currentDrawdown)
                    : displayMode === "percent"
                      ? formatPercent(stats.currentDrawdown)
                      : formatR(stats.currentDrawdown)
                )
              : "N/A",
          },
          { label: "Top to Bottom", value: stats ? String(stats.topToBottom) : "N/A" },
          { label: "Bottom to Top", value: stats ? String(stats.bottomToTop) : "N/A" },
        ]}
        series={[
          {
            label: "Drawdown",
            points: chartData.slice(-240).map((point) => ({
              x: `Trade ${point.tradeNumber} @ ${formatCloseTime(point.closeTime)}`,
              y: String(
                displayMode === "dollar"
                  ? point.drawdownDollar
                  : displayMode === "percent"
                    ? point.drawdownPercent
                    : point.drawdownR,
              ),
            })),
          },
          {
            label: "Trade PnL",
            points: chartData
              .filter((point) => typeof point.pl === "number")
              .slice(-240)
              .map((point) => ({
                x: `Trade ${point.tradeNumber} @ ${formatCloseTime(point.closeTime)}`,
                y: String(point.pl),
              })),
          },
        ]}
      />
      {/* Header Controls */}
      <div className="flex items-center justify-between shrink-0">
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
      </div>

      {/* Content Wrapper (Matches Equity Page snapshot container) */}
      <div className="flex flex-col gap-4 flex-1 min-h-0 bg-black">

        {/* Chart Area - Flex 1 to take remaining space */}
        <div className="flex-1 w-full bg-slate-950/50 rounded-lg border border-slate-800 p-4 relative min-h-[200px]">
          {trades.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="colorDrawdown" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.5}/>
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid vertical={false} stroke="#334155" strokeDasharray="3 3" opacity={0.5} />
              <XAxis
                  dataKey="tradeNumber"
                  tick={{ fill: '#64748b', fontSize: 12 }}
                  axisLine={false}
                  tickLine={false}
                  minTickGap={30}
                  label={{ value: 'Trades', position: 'insideBottom', offset: -5, fill: '#64748b', fontSize: 12 }}
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
                      value: displayMode === 'percent' ? 'Drawdown (%)' : displayMode === 'dollar' ? 'Drawdown ($)' : 'Drawdown (R)',
                      angle: -90,
                      position: 'insideLeft',
                      fill: '#64748b',
                      fontSize: 12
                  }}
              />
              <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', color: '#f8fafc' }}
                  itemStyle={{ color: '#f8fafc' }}
                  formatter={(value: number) => [
                      displayMode === 'dollar' ? formatCurrency(value) :
                      displayMode === 'percent' ? formatPercent(value) :
                      formatR(value),
                      "Drawdown"
                  ]}
                  labelFormatter={(label) => `Trade #${label}`}
              />
              <ReferenceLine y={0} stroke="#64748b" />
              <Area
                  type="monotone"
                  dataKey={displayMode === 'dollar' ? "drawdownDollar" : displayMode === 'percent' ? "drawdownPercent" : "drawdownR" }
                  stroke="#ef4444"
                  fillOpacity={1}
                  fill="url(#colorDrawdown)"
                  strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
          ) : (
              <div className="flex items-center justify-center h-full text-muted-foreground">
                  No trade data available for drawdown analysis.
              </div>
          )}
        </div>

        {/* Metrics Grid */}
        <div className="flex flex-wrap gap-2 items-start w-full">
            {formattedStats && (
            <>
                 <DrawdownMetricCard
                    title="Worst Drawdown"
                    value={formattedStats.worstDisplay}
                    color="green"
                 />
                 <DrawdownMetricCard
                    title="Average Drawdown"
                    value={formattedStats.avgDisplay}
                    color="green"
                 />
                 <DrawdownMetricCard
                    title="Current Drawdown"
                    value={formattedStats.currentDisplay}
                    color="red"
                 />
                 <DrawdownMetricCard
                    title="Top to Bottom"
                    value={formattedStats.topToBottom}
                    color="green"
                    tooltip="Measure the distance in trades between 0 (a peak) and the lowest drawdown"
                 />
                 <DrawdownMetricCard
                    title="Bottom to Top"
                    value={formattedStats.bottomToTop}
                    color="green"
                    tooltip="Measure the distance in trades between the lowest drawdown and back to the peak"
                 />
                 <DrawdownMetricCard
                    title="Return to Drawdown"
                    value={formattedStats.returnToDrawdown}
                    color="green"
                 />
            </>
            )}
        </div>
      </div>
    </div>
  )
}

function DrawdownMetricCard({ title, value, tooltip, color = "green" }: { title: string, value: string | number, tooltip?: string, color?: "green" | "red" | "amber" | "orange" }) {
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
                            <span className="text-[10px] text-slate-400 font-medium cursor-help hover:text-slate-300 transition-colors uppercase tracking-wider whitespace-nowrap text-left">
                              {title}
                            </span>
                        </TooltipTrigger>
                        {tooltip && <TooltipContent><p>{tooltip}</p></TooltipContent>}
                    </UiTooltip>
                </TooltipProvider>
             </div>
             <span className="text-lg font-bold text-white leading-tight mt-0.5 text-left">
                {value}
             </span>
         </div>
      </CardContent>
    </Card>
  )
}
