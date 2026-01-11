"use client"

import * as React from "react"
import { useSelectedBacktest } from "@/contexts/selected-backtest-context"
import { strategyApi } from "@/lib/api/strategies"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine
} from "recharts"

interface SimulationConfig {
    numSimulations: number
    numTrades: number
    winRate: number
    avgGain: number
    avgLoss: number
    startBalance: number
}

export default function SimulatorPage() {
    const { selectedBacktest } = useSelectedBacktest()

    // Config State
    const [config, setConfig] = React.useState<SimulationConfig>({
        numSimulations: 20,
        numTrades: 500,
        winRate: 50,
        avgGain: 100,
        avgLoss: 100,
        startBalance: 10000
    })

    const [useKPI, setUseKPI] = React.useState(false)
    const [simulations, setSimulations] = React.useState<any[]>([])
    const [chartData, setChartData] = React.useState<any[]>([])
    const [loading, setLoading] = React.useState(false)

    // Load KPIs from backtest
    React.useEffect(() => {
        if (!useKPI || !selectedBacktest) return

        const fetchStats = async () => {
             // We need trade stats. getBacktestById or analyze trades keys?
             // Assuming trades are available or fetchable
             let trades = selectedBacktest.trades || []
             if (trades.length === 0) {
                 try {
                     const full = await strategyApi.getBacktestById(selectedBacktest.backtest_id)
                     trades = full.trades || []
                 } catch(e) { console.error(e) }
             }

             if (trades.length > 0) {
                 // Calculate stats
                 let winners = 0
                 let losers = 0
                 let totalWin = 0
                 let totalLoss = 0

                 trades.forEach((t: any) => {
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
                         } else if (pnl < 0) {
                             losers++
                             totalLoss += Math.abs(pnl)
                         }
                     }
                 })

                 const totalTrades = winners + losers
                 const winRate = totalTrades > 0 ? (winners / totalTrades) * 100 : 0
                 const avgGain = winners > 0 ? totalWin / winners : 0
                 const avgLoss = losers > 0 ? totalLoss / losers : 0

                 setConfig(prev => ({
                     ...prev,
                     winRate: parseFloat(winRate.toFixed(2)),
                     avgGain: parseFloat(avgGain.toFixed(2)),
                     avgLoss: parseFloat(avgLoss.toFixed(2)),
                     startBalance: selectedBacktest.initial_balance || 10000
                 }))
             }
        }
        fetchStats()
    }, [useKPI, selectedBacktest])


    const runSimulation = () => {
        setLoading(true)
        // Defer to allow UI update
        setTimeout(() => {
            const newSimulations: number[][] = []

            // Run N simulations
            for (let i = 0; i < config.numSimulations; i++) {
                const equityCurve = [config.startBalance]
                let currentBalance = config.startBalance

                for (let j = 0; j < config.numTrades; j++) {
                    const isWin = Math.random() * 100 < config.winRate
                    const pnl = isWin ? config.avgGain : -Math.abs(config.avgLoss)
                    currentBalance += pnl
                    equityCurve.push(currentBalance)
                }
                newSimulations.push(equityCurve)
            }

            // Format for Recharts: Array of objects { index: 0, sim0: 10000, sim1: 10000 ... }
            const data = []
            // We have config.numTrades + 1 points (including start)
            for (let i = 0; i <= config.numTrades; i++) {
                const point: any = { index: i === 0 ? 1 : i } // 1-based index for chart? Screenshot shows 1, 51...
                newSimulations.forEach((sim, simIdx) => {
                    point[`sim${simIdx}`] = sim[i]
                })
                data.push(point)
            }

            setSimulations(newSimulations)
            setChartData(data)
            setLoading(false)
        }, 100)
    }

    const avgRMultiple = config.avgLoss > 0 ? (config.avgGain / config.avgLoss).toFixed(2) : "N/A"

    // Colors for lines - consistent set or random?
    const colors = [
        "#3b82f6", "#ef4444", "#10b981", "#f59e0b", "#8b5cf6",
        "#ec4899", "#06b6d4", "#84cc16", "#d946ef", "#f43f5e",
        "#6366f1", "#14b8a6", "#f97316", "#a855f7", "#22c55e"
    ]
    const getLineColor = (index: number) => colors[index % colors.length]

    return (
        <div className="flex h-full w-full bg-slate-950 text-slate-200 overflow-hidden">
            {/* Sidebar */}
            <div className="w-[300px] flex flex-col gap-6 p-6 border-r border-slate-800 bg-black/20 overflow-y-auto">
                <div>
                   <h3 className="font-semibold mb-4 text-white">Edit Data</h3>

                   <div className="space-y-4">
                       <div className="space-y-2">
                           <Label className="text-xs text-slate-400">Number of Simulations</Label>
                           <Input
                               type="number"
                               value={config.numSimulations}
                               onChange={e => setConfig({...config, numSimulations: Number(e.target.value)})}
                               className="bg-slate-900 border-slate-700 text-right"
                           />
                       </div>
                       <div className="space-y-2">
                           <Label className="text-xs text-slate-400">Number of Trades</Label>
                           <Input
                               type="number"
                               value={config.numTrades}
                               onChange={e => setConfig({...config, numTrades: Number(e.target.value)})}
                               className="bg-slate-900 border-slate-700 text-right"
                           />
                       </div>
                   </div>
                </div>

                <div className="space-y-4">
                    <div className="flex items-center justify-between">
                        <Label className="font-semibold text-white">Use KPI From my Trades</Label>
                        <Switch checked={useKPI} onCheckedChange={setUseKPI} />
                    </div>

                    <div className="space-y-3">
                       <div className="space-y-1">
                           <div className="flex justify-between text-xs text-slate-400">
                               <span>Winrate (%)</span>
                           </div>
                           <Input
                               type="number"
                               value={config.winRate}
                               onChange={e => setConfig({...config, winRate: Number(e.target.value)})}
                               disabled={useKPI}
                               className="bg-slate-900 border-slate-700 text-right disabled:opacity-50"
                           />
                       </div>
                       <div className="space-y-1">
                           <div className="flex justify-between text-xs text-slate-400">
                               <span>Avg. Gain ($)</span>
                           </div>
                           <Input
                               type="number"
                               value={config.avgGain}
                               onChange={e => setConfig({...config, avgGain: Number(e.target.value)})}
                               disabled={useKPI}
                               className="bg-slate-900 border-slate-700 text-right disabled:opacity-50"
                           />
                       </div>
                       <div className="space-y-1">
                           <div className="flex justify-between text-xs text-slate-400">
                               <span>Avg. Loss ($)</span>
                           </div>
                           <Input
                               type="number"
                               value={config.avgLoss} // User sees positive number typically
                               onChange={e => setConfig({...config, avgLoss: Number(e.target.value)})}
                               disabled={useKPI}
                               className="bg-slate-900 border-slate-700 text-right disabled:opacity-50"
                           />
                       </div>
                       <div className="space-y-1">
                           <div className="flex justify-between text-xs text-slate-400">
                               <span>Start Balance ($)</span>
                           </div>
                           <Input
                               type="number"
                               value={config.startBalance}
                               onChange={e => setConfig({...config, startBalance: Number(e.target.value)})}
                               className="bg-slate-900 border-slate-700 text-right"
                           />
                       </div>
                    </div>
                </div>

                <div className="flex justify-between text-xs text-slate-500 mt-2">
                    <span>Avg. R - Multiple</span>
                    <span>{avgRMultiple}</span>
                </div>

                <Button
                    className="w-full bg-white text-black hover:bg-slate-200 mt-auto"
                    onClick={runSimulation}
                    disabled={loading}
                >
                    {loading ? "Running..." : "Start Simulation"}
                </Button>
            </div>

            {/* Main Content - Chart */}
            <div className="flex-1 p-6 flex flex-col min-w-0">
                {chartData.length > 0 ? (
                    <div className="flex-1 w-full min-h-0">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={chartData}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                                <XAxis
                                    dataKey="index"
                                    stroke="#475569"
                                    tick={{fontSize: 12}}
                                    interval="preserveStartEnd"
                                    minTickGap={50}
                                />
                                <YAxis
                                    stroke="#475569"
                                    tick={{fontSize: 12}}
                                    domain={['auto', 'auto']}
                                    tickFormatter={(val) => val.toLocaleString()}
                                />
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b' }}
                                    itemStyle={{ fontSize: '12px' }}
                                    labelStyle={{ color: '#94a3b8', marginBottom: '8px' }}
                                    formatter={(value: number) => [value.toLocaleString(), '']}
                                />
                                {Array.from({ length: config.numSimulations }).map((_, i) => (
                                    <Line
                                        key={i}
                                        type="monotone"
                                        dataKey={`sim${i}`}
                                        stroke={getLineColor(i)}
                                        dot={false}
                                        strokeWidth={1.5}
                                        activeDot={{ r: 4 }}
                                        isAnimationActive={false} // Performance
                                    />
                                ))}
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                ) : (
                    <div className="flex-1 flex items-center justify-center text-slate-600">
                        To run simulations, press Start button
                    </div>
                )}
            </div>
        </div>
    )
}
