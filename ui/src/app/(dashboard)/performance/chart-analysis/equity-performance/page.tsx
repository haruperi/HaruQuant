"use client"

import { useEffect, useState, useRef, useMemo } from "react"
import { CustomChartSemanticSnapshot } from "@/components/ai-chat/CustomChartSemanticSnapshot"
import { useSelectedBacktest } from "@/contexts/selected-backtest-context"
import { strategyApi } from "@/lib/api/strategies"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { toPng } from "html-to-image"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Area,
  AreaChart,
  ReferenceArea,
  ComposedChart
} from "recharts"
import { formatCurrency, formatNumber } from "@/lib/utils"
import { Camera, ChevronDown } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Tooltip as UiTooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

interface MetricCardProps {
  title: string
  value: string | number
  subValue?: string
  tooltip?: string
  color?: string
}

interface EquityPerformanceTrade {
  profit_loss?: number | string
  net_profit?: number | string
  pl?: number | string
  pnl?: number | string
  profit?: number | string
  side?: string
  direction?: string
  close_time?: string
  exit_time?: string
  time?: string
}

function tradeTimestamp(trade: EquityPerformanceTrade): number {
  const value = trade.close_time || trade.exit_time || trade.time
  if (!value) return 0
  const timestamp = new Date(value).getTime()
  return Number.isFinite(timestamp) ? timestamp : 0
}

function MetricCard({ title, value, tooltip, color }: MetricCardProps) {
  // Determine color based on value: Red if negative, Green otherwise
  const isNegative = typeof value === 'number'
    ? value < 0
    : value.toString().includes('-');

  const barColor = isNegative ? 'bg-red-500' : 'bg-green-500';

  return (
    <Card className="bg-slate-900 border-slate-800 flex-1 min-w-fit">
      <CardContent className="p-0 flex items-stretch overflow-hidden h-full">
         <div className={`w-1.5 ${barColor} shrink-0`} />
         <div className="flex flex-col justify-center px-3 py-2">
             <TooltipProvider>
                <UiTooltip>
                  <TooltipTrigger asChild>
                    <span className="text-[10px] text-slate-400 font-medium cursor-help hover:text-slate-300 transition-colors uppercase tracking-wider whitespace-nowrap text-left">
                      {title}
                    </span>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>{tooltip}</p>
                  </TooltipContent>
                </UiTooltip>
              </TooltipProvider>
              <span className="text-lg font-bold text-white leading-tight mt-0.5 text-left">
                {value}
              </span>
         </div>
      </CardContent>
    </Card>
  )
}

export default function EquityPerformancePage() {
    const { selectedBacktest } = useSelectedBacktest()
    const [trades, setTrades] = useState<EquityPerformanceTrade[]>([])
    const [loading, setLoading] = useState(true)
    const [displayMode, setDisplayMode] = useState("Return ($)")
    const [snapshotUrl, setSnapshotUrl] = useState<string | null>(null)
    const [isSnapshotOpen, setIsSnapshotOpen] = useState(false)
    const [filter, setFilter] = useState<'all' | 'long' | 'short'>('all')
    const [drawdownMode, setDrawdownMode] = useState<'none' | 'amount' | 'percent'>('none')
    const chartRef = useRef<HTMLDivElement>(null)

    useEffect(() => {
        async function fetchTrades() {
            if (!selectedBacktest) {
                setLoading(false)
                return
            }
            try {
                setLoading(true)
                let tradeData = selectedBacktest.trades || []
                if (tradeData.length === 0) {
                     const full = await strategyApi.getBacktestById(selectedBacktest.backtest_id)
                     tradeData = full.trades || []
                }
                setTrades(tradeData)
            } catch (error) {
                console.error("Failed to fetch trades:", error)
            } finally {
                setLoading(false)
            }
        }
        fetchTrades()
    }, [selectedBacktest])

    // Calculate Data based on filters
    const processedData = useMemo(() => {
        if (!selectedBacktest || trades.length === 0) return null

        // 1. Filter Trades
        const initialBalance = selectedBacktest.initial_balance || 10000
        const filteredTrades = trades.filter(t => {
            if (filter === 'all') return true
            // Support 'side' (long/short) or 'type' (buy/sell -> implies direction?)
            // Assuming t.side is 'LONG' or 'SHORT' or t.type
            // Or infer from PnL? No.
            // Let's assume standardized 'side' exists or 'direction'.
            // If not, check entry/exit.
            // Standardize format usually has 'side'.
            const side = (t.side || t.direction || '').toUpperCase()
            if (filter === 'long') return side === 'LONG' || side === 'BUY' // careful if BUY is just entry
            if (filter === 'short') return side === 'SHORT' || side === 'SELL'
            return true
        })

        if (filteredTrades.length === 0 && trades.length > 0 && filter !== 'all') {
             // Fallback if filtering failed (e.g. no side info), return empty or warn?
             // For now return empty with valid structure
        }

        // 2. Calculate Equity Curve & Drawdown
        let currentEquity = initialBalance
        let maxEquity = initialBalance
        const equityCurve = []
        const chartData = []

        // Start point
        chartData.push({
            index: 0,
            equity: initialBalance,
            drawdown: 0,
            drawdownPct: 0,
            value: 0 // For displayMode adjustment
        })

        // Sort trades by time just in case
        const sortedTrades = [...filteredTrades].sort((a, b) =>
            tradeTimestamp(a) - tradeTimestamp(b)
        )

        for (let i = 0; i < sortedTrades.length; i++) {
            const t = sortedTrades[i]
            let pnl = t.profit_loss
            if (pnl === undefined) pnl = t.net_profit
            if (pnl === undefined) pnl = t.pl
            if (pnl === undefined) pnl = t.pnl
            if (pnl === undefined) pnl = t.profit

            if (pnl !== undefined) {
                 if (typeof pnl === 'string') pnl = parseFloat(pnl)
                 if (isNaN(pnl)) pnl = 0
            } else {
                pnl = 0
            }

            currentEquity += pnl
            maxEquity = Math.max(maxEquity, currentEquity)
            const dd = currentEquity - maxEquity
            const ddPct = maxEquity > 0 ? (dd / maxEquity) * 100 : 0

            let displayValue = currentEquity
            let maxEquityDisplay = maxEquity
            let drawdownRangeDisplay = [currentEquity, maxEquity]

            switch (displayMode) {
                case "Return ($)":
                    displayValue = currentEquity - initialBalance;
                    maxEquityDisplay = maxEquity - initialBalance;
                    drawdownRangeDisplay = [displayValue, maxEquityDisplay];
                    break;
                case "Account Balance ($)":
                    displayValue = currentEquity;
                    maxEquityDisplay = maxEquity;
                    drawdownRangeDisplay = [displayValue, maxEquityDisplay];
                    break;
                case "Return, gain sum (%)":
                    displayValue = ((currentEquity - initialBalance) / initialBalance) * 100;
                    maxEquityDisplay = ((maxEquity - initialBalance) / initialBalance) * 100;
                    drawdownRangeDisplay = [displayValue, maxEquityDisplay];
                    break;
                case "R Multiple (R)":
                    // Default to Return ($) logic for now
                    displayValue = currentEquity - initialBalance;
                    maxEquityDisplay = maxEquity - initialBalance;
                    drawdownRangeDisplay = [displayValue, maxEquityDisplay];
                    break;
                default:
                    displayValue = currentEquity - initialBalance;
                    maxEquityDisplay = maxEquity - initialBalance;
                    drawdownRangeDisplay = [displayValue, maxEquityDisplay];
            }

            chartData.push({
                index: i + 1,
                equity: currentEquity,
                maxEquity: maxEquity,
                drawdownRange: [currentEquity, currentEquity === maxEquity ? currentEquity : maxEquity],
                drawdown: dd,
                drawdownPct: ddPct,
                value: displayValue,
                maxEquityDisplay: maxEquityDisplay,
                drawdownRangeDisplay: drawdownRangeDisplay
            })
        }

        // 3. Calculate Metrics
        let winners = 0
        let losers = 0
        let totalWin = 0
        let totalLoss = 0
        let maxDD = 0
        let biggestWin = -Infinity
        let biggestLoss = Infinity // PnL is negative, so closer to 0 is bigger? No, most negative.

        sortedTrades.forEach(t => {
            let pnl = t.profit_loss
            if (pnl === undefined) pnl = t.net_profit
            if (pnl === undefined) pnl = t.pl
            if (pnl === undefined) pnl = t.pnl
            if (pnl === undefined) pnl = t.profit

            if (pnl !== undefined) {
                 if (typeof pnl === 'string') pnl = parseFloat(pnl)
                 if (isNaN(pnl)) return

                if (pnl > 0) {
                    winners++
                    totalWin += pnl
                    if (pnl > biggestWin) biggestWin = pnl
                } else if (pnl < 0) {
                    losers++
                    totalLoss += Math.abs(pnl) // totalLoss is positive sum
                    if (pnl < biggestLoss) biggestLoss = pnl // most negative
                }
            }
        })

        // Find Max DD from chart data
        chartData.forEach(d => {
            if (d.drawdown < maxDD) maxDD = d.drawdown // d.drawdown is <= 0
        })

        const totalTrades = winners + losers
        const totalNetProfit = totalWin - totalLoss
        const avgTrade = totalTrades > 0 ? totalNetProfit / totalTrades : 0
        const profitFactor = totalLoss > 0 ? totalWin / totalLoss : totalWin > 0 ? Infinity : 0
        const winRate = totalTrades > 0 ? (winners / totalTrades) * 100 : 0

        return {
            chartData,
            metrics: {
                total_trades: totalTrades,
                winning_trades: winners,
                losing_trades: losers,
                win_rate: winRate,
                avg_trade: avgTrade,
                profit_factor: profitFactor,
                total_net_profit: totalNetProfit,
                max_drawdown: maxDD,
                biggest_winner: biggestWin === -Infinity ? 0 : biggestWin,
                biggest_loser: biggestLoss === Infinity ? 0 : biggestLoss
            }
        }

    }, [trades, filter, displayMode, selectedBacktest])


    if (!selectedBacktest) return null // Handled by parent or context usually
    if (loading && trades.length === 0) return <div className="p-12 text-center text-slate-500">Loading...</div>
    if (!processedData) return <div className="p-12 text-center text-slate-500">No data available</div>

    const { chartData, metrics } = processedData
    const off = 0.5 // Simplified gradient offset or calc if needed
    // Re-calc offset for displayValue
    const dataMax = Math.max(...chartData.map(i => i.value))
    const dataMin = Math.min(...chartData.map(i => i.value))
    const gradientOffset = () => {
        if (dataMax <= 0) return 0
        if (dataMin >= 0) return 1
        return dataMax / (dataMax - dataMin) // simple zero crossing logic
    }
    const offSet = gradientOffset()


    const formatDynamicMetric = (value: number) => {
        if (displayMode.includes("(%)")) return formatNumber((value / (selectedBacktest.initial_balance || 10000)) * 100, 2) + "%"
        return formatCurrency(value)
    }

    const formatChartValue = (val: number) => {
        if (displayMode.includes("(%)")) return formatNumber(val, 2) + "%"
        return formatCurrency(val)
    }

    // Chart helpers
    const handleSnapshot = async () => {
        if (!chartRef.current) return
        try {
            const url = await toPng(chartRef.current, {
                backgroundColor: '#020617',
                pixelRatio: 2
            })
            setSnapshotUrl(url)
            setIsSnapshotOpen(true)
        } catch (err) {
            console.error("Snapshot failed", err)
        }
    }

    const handleDownload = () => {
        if (!snapshotUrl) return
        const link = document.createElement('a')
        link.href = snapshotUrl
        link.download = `equity-performance-${selectedBacktest?.backtest_id || 'chart'}.png`
        link.click()
        setIsSnapshotOpen(false)
    }

    const handleCopy = async () => {
        if (!snapshotUrl) return
        try {
            const res = await fetch(snapshotUrl)
            const blob = await res.blob()
            await navigator.clipboard.write([
                new ClipboardItem({ [blob.type]: blob })
            ])
            setIsSnapshotOpen(false)
        } catch (err) {
            console.error("Failed to copy", err)
        }
    }

    // Dropdown Logic
    const toggleDrawdown = (mode: 'none' | 'amount' | 'percent') => {
        setDrawdownMode(mode)
    }

    return (
        <div className="flex flex-col gap-4 p-4 h-full bg-black overflow-hidden">
            <CustomChartSemanticSnapshot
                id={`equity-performance:${selectedBacktest.backtest_id}:${displayMode}:${filter}:${drawdownMode}`}
                title="Equity Performance"
                summary="Custom performance chart showing equity progression, drawdown overlay, and aggregate trade metrics."
                keywords={[
                    "equity performance",
                    "equity curve",
                    "drawdown",
                    "backtest",
                    "return",
                    filter,
                    drawdownMode,
                ]}
                metrics={[
                    { label: "Trades", value: String(metrics.total_trades) },
                    { label: "Winning Trades", value: String(metrics.winning_trades) },
                    { label: "Losing Trades", value: String(metrics.losing_trades) },
                    { label: "Win Rate", value: formatNumber(metrics.win_rate, 2) },
                    { label: "Return", value: formatDynamicMetric(metrics.total_net_profit) },
                    { label: "Max Drawdown", value: formatDynamicMetric(metrics.max_drawdown) },
                ]}
                series={[
                    {
                        label: "Equity",
                        points: chartData.slice(-240).map((point) => ({
                            x: `Trade ${point.index}`,
                            y: String(point.value),
                        })),
                    },
                    {
                        label: "Drawdown",
                        points: chartData.slice(-240).map((point) => ({
                            x: `Trade ${point.index}`,
                            y: String(drawdownMode === 'percent' ? point.drawdownPct : point.drawdown),
                        })),
                    },
                ]}
            />
            {/* Header Controls */}
            <div className="flex items-center justify-between shrink-0">
                <div className="flex gap-4">
                    {/* Display Dropdown */}
                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <Button variant="outline" className="bg-slate-900 border-slate-700 text-white hover:bg-slate-800 w-56 justify-between px-3">
                                <div className="flex flex-col items-start gap-0.5 text-left">
                                    <span className="text-[10px] text-slate-400">Display</span>
                                    <span className="truncate w-40">{displayMode}</span>
                                </div>
                                <ChevronDown className="h-4 w-4 text-slate-400 shrink-0" />
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent className="w-56 bg-slate-900 border-slate-800 text-slate-300">
                             {["Return ($)", "Account Balance ($)", "Return, gain sum (%)", "R Multiple (R)"].map(m => (
                                 <DropdownMenuItem key={m} onClick={() => setDisplayMode(m)} className="hover:bg-slate-800 cursor-pointer">{m}</DropdownMenuItem>
                             ))}
                        </DropdownMenuContent>
                    </DropdownMenu>

                    {/* Options Dropdown */}
                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <Button variant="outline" className="bg-slate-900 border-slate-700 text-white hover:bg-slate-800 w-56 justify-between px-3">
                                <div className="flex flex-col items-start gap-0.5 text-left">
                                    <span className="text-[10px] text-slate-400">Options</span>
                                    <span className="truncate w-40">
                                        {filter === 'all' ? 'All' : filter === 'long' ? 'Long only' : 'Short only'}
                                        {drawdownMode !== 'none' && ` + DD ${drawdownMode === 'amount' ? '$' : '%'}`}
                                    </span>
                                </div>
                                <ChevronDown className="h-4 w-4 text-slate-400 shrink-0" />
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent className="w-56 bg-slate-900 border-slate-800 text-slate-300">
                            <div className="px-2 py-1.5 text-xs font-semibold text-slate-500">Filter</div>
                            <DropdownMenuItem onClick={() => setFilter('all')} className="hover:bg-slate-800 cursor-pointer flex justify-between">
                                All {filter === 'all' && "✓"}
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => setFilter('long')} className="hover:bg-slate-800 cursor-pointer flex justify-between">
                                Long only {filter === 'long' && "✓"}
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => setFilter('short')} className="hover:bg-slate-800 cursor-pointer flex justify-between">
                                Short only {filter === 'short' && "✓"}
                            </DropdownMenuItem>

                            <div className="h-px bg-slate-800 my-1" />
                            <div className="px-2 py-1.5 text-xs font-semibold text-slate-500">Drawdown</div>
                            <DropdownMenuItem onClick={() => toggleDrawdown(drawdownMode === 'amount' ? 'none' : 'amount')} className="hover:bg-slate-800 cursor-pointer flex justify-between">
                                Add Drawdown {drawdownMode === 'amount' && "✓"}
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => toggleDrawdown(drawdownMode === 'percent' ? 'none' : 'percent')} className="hover:bg-slate-800 cursor-pointer flex justify-between">
                                Add Drawdown % {drawdownMode === 'percent' && "✓"}
                            </DropdownMenuItem>
                        </DropdownMenuContent>
                    </DropdownMenu>
                </div>
                 <div className="flex items-center gap-4 text-slate-400">
                    <Camera onClick={handleSnapshot} className="h-5 w-5 cursor-pointer hover:text-white" />
                </div>
            </div>

            {/* Snapshot Container */}
            <div ref={chartRef} className="flex flex-col gap-4 flex-1 min-h-0 bg-black">
                {/* Chart Area */}
                <div className="flex-1 w-full bg-slate-950/50 rounded-lg border border-slate-800 p-4 relative min-h-[300px]">
                    <ResponsiveContainer width="100%" height="100%">
                        <ComposedChart data={chartData}>
                            <defs>
                                <linearGradient id="splitColor" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset={offSet} stopColor="#22c55e" stopOpacity={1} />
                                    <stop offset={offSet} stopColor="#ea580c" stopOpacity={1} />
                                </linearGradient>
                                <linearGradient id="fillSplitColor" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="0" stopColor="#22c55e" stopOpacity={0.5} />
                                    <stop offset={offSet} stopColor="#22c55e" stopOpacity={0} />
                                    <stop offset={offSet} stopColor="#ea580c" stopOpacity={0} />
                                    <stop offset="1" stopColor="#ea580c" stopOpacity={0.8} />
                                </linearGradient>
                                <linearGradient id="drawdownGradient" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.1}/>
                                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0.4}/>
                                </linearGradient>
                            </defs>
                            <CartesianGrid vertical={false} stroke="#334155" strokeDasharray="3 3" opacity={0.5} />
                            <XAxis
                                dataKey="index"
                                stroke="#64748b"
                                tick={{fill: '#64748b', fontSize: 12}}
                                tickLine={false}
                                axisLine={false}
                                label={{ value: 'Trades', position: 'insideBottom', offset: -10, fill: '#64748b' }}
                            />
                            <YAxis
                                yAxisId="left"
                                width={80}
                                domain={['auto', 'auto']}
                                stroke="#64748b"
                                tick={{fill: '#64748b', fontSize: 12}}
                                tickFormatter={(val) => formatChartValue(val)}
                                tickLine={false}
                                axisLine={false}
                            />
                            {drawdownMode === 'percent' && (
                                <YAxis
                                    yAxisId="right"
                                    orientation="right"
                                    width={60}
                                    stroke="#ef4444"
                                    tick={{fill: '#ef4444', fontSize: 12}}
                                    tickFormatter={(val) => formatNumber(val, 1) + '%'}
                                    tickLine={false}
                                    axisLine={false}
                                />
                            )}
                            <Tooltip
                                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', color: '#f8fafc' }}
                                itemStyle={{ color: '#f8fafc' }}
                                formatter={(value: number, name: string) => {
                                    if (name === 'Drawdown %') return [formatNumber(value, 2) + '%', name]
                                    if (name === 'High Water Mark') return [formatChartValue(value as number), name]
                                    if (name === 'Underwater') return ['', ''] // Don't show range value in tooltip, slightly clearer
                                    return [formatChartValue(value), displayMode]
                                }}
                                labelFormatter={(label) => `Trade ${label}`}
                            />

                            {/* Main Equity Curve */}
                            <Area
                                yAxisId="left"
                                type="monotone"
                                dataKey="value"
                                stroke="url(#splitColor)"
                                strokeWidth={2}
                                fillOpacity={1}
                                fill="url(#fillSplitColor)"
                            />

                            {/* Underwater Drawdown (Amount Mode) */}
                            {drawdownMode === 'amount' && (
                                <>
                                    <Area
                                        yAxisId="left"
                                        type="step"
                                        dataKey="drawdownRangeDisplay"
                                        stroke="none"
                                        fill="#ef4444"
                                        fillOpacity={0.2}
                                        name="Underwater"
                                    />
                                    {/* High Water Mark Line */}
                                    <Line
                                        yAxisId="left"
                                        type="step"
                                        dataKey="maxEquityDisplay"
                                        stroke="#3b82f6"
                                        strokeDasharray="4 4"
                                        strokeWidth={1}
                                        dot={false}
                                        name="High Water Mark"
                                    />
                                </>
                            )}

                            {/* Standard Drawdown Percent (Percent Mode) */}
                            {drawdownMode === 'percent' && (
                                <Area
                                    yAxisId="right"
                                    type="monotone"
                                    dataKey="drawdownPct"
                                    name="Drawdown %"
                                    stroke="#ef4444"
                                    fill="url(#drawdownGradient)"
                                    opacity={0.5}
                                />
                            )}

                            <ReferenceLine yAxisId="left" y={chartData[0]?.value} stroke="#ef4444" strokeDasharray="3 3" />
                        </ComposedChart>
                    </ResponsiveContainer>
                </div>

                {/* Metrics Grid */}
                <div className="flex flex-wrap gap-2 items-start w-full">
                    <MetricCard
                        title="Trades"
                        value={metrics.total_trades}
                        tooltip="Total number of trades executed"
                        color="emerald"
                    />
                    <MetricCard
                        title="Winners"
                        value={metrics.winning_trades}
                        tooltip="Number of winning trades"
                        color="emerald"
                    />
                    <MetricCard
                        title="Losers"
                        value={metrics.losing_trades}
                        tooltip="Number of losing trades"
                        color="emerald"
                    />
                    <MetricCard
                        title="Winrate (%)"
                        value={formatNumber(metrics.win_rate, 2)}
                        tooltip="Percentage of winning trades"
                        color="emerald"
                    />
                    <MetricCard
                        title="Avg. P&L"
                        value={formatDynamicMetric(metrics.avg_trade)}
                        tooltip="Average profit or loss per trade"
                        color="amber"
                    />
                    <MetricCard
                        title="Profit Factor"
                        value={formatNumber(metrics.profit_factor, 2)}
                        tooltip="Ratio of gross profit to gross loss"
                        color="emerald"
                    />
                    <MetricCard
                        title="Return"
                        value={formatDynamicMetric(metrics.total_net_profit)}
                        tooltip="Total return"
                        color="emerald"
                    />
                    <MetricCard
                        title="Max DD"
                        value={formatDynamicMetric(metrics.max_drawdown)}
                        tooltip="Maximum Strategy Drawdown"
                        color="red"
                    />
                    <MetricCard
                        title="Biggest Winner"
                        value={formatDynamicMetric(metrics.biggest_winner)}
                        tooltip="Largest single winning trade"
                        color="emerald"
                    />
                    <MetricCard
                        title="Biggest Loser"
                        value={formatDynamicMetric(metrics.biggest_loser)}
                        tooltip="Largest single losing trade"
                        color="red"
                    />
                    <MetricCard
                        title="Profit/Loss"
                        value={formatDynamicMetric(metrics.total_net_profit)}
                        tooltip="Total Net Profit"
                        color="orange"
                    />
                </div>
            </div>

            <Dialog open={isSnapshotOpen} onOpenChange={setIsSnapshotOpen}>
                <DialogContent className="bg-slate-900 border-slate-800 text-white max-w-3xl">
                    <DialogHeader>
                        <DialogTitle>Chart Snapshot</DialogTitle>
                    </DialogHeader>
                    <div className="flex items-center justify-center p-4 bg-slate-950 rounded-lg overflow-auto max-h-[60vh]">
                        {snapshotUrl && (
                            <img src={snapshotUrl} alt="Chart Snapshot" className="max-w-full h-auto" />
                        )}
                    </div>
                    <DialogFooter className="gap-2 sm:gap-0">
                        <Button variant="outline" onClick={() => setIsSnapshotOpen(false)} className="border-slate-700 hover:bg-slate-800 text-white">
                            Cancel
                        </Button>
                        <Button variant="outline" onClick={handleCopy} className="border-slate-700 hover:bg-slate-800 text-white">
                            Copy to Clipboard
                        </Button>
                        <Button onClick={handleDownload} className="bg-emerald-600 hover:bg-emerald-700 text-white">
                            Download
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    )
}
