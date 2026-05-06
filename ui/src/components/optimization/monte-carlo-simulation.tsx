"use client"

import React, { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { AreaChart, Area, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, ComposedChart, Bar, Rectangle, ErrorBar, PieChart, Pie, Cell, Legend } from 'recharts'
import { Zap, RefreshCcw } from "lucide-react"
import { optimizationApi, type MonteCarloRequest, type MonteCarloResponse, type SimulationType, type ParametricMonteCarloRequest, type ParametricSimulationResult, type PositionSizingResult, type ConsecutiveLosingRequest, type ConsecutiveLosingResponse, type ProfitTargetRequest, type ProfitTargetResponse, type ProfitTargetResult, type RandomWinRateRequest, type RandomWinRateResponse, type RandomWinRatePair, type ManualPairInput, type RobustnessRequest, type RobustnessResponse, type RobustnessStats, type MultiEntryRequest, type MultiEntryResponse, type MultiEntryScenarioResult } from "@/lib/api/optimization"
import { backtestApi, type Backtest } from "@/lib/api/backtest"
import { useToast } from "@/components/ui/use-toast"
import { Switch } from "@/components/ui/switch"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

function formatNumber(value: number | null | undefined, digits = 2): string {
    return typeof value === "number" && Number.isFinite(value) ? value.toFixed(digits) : "-"
}

export function MonteCarloSimulation() {
    const { toast } = useToast()
    const [mode, setMode] = useState<"backtest" | "parametric" | "position-sizing">("backtest")

    // Backtest Mode State
    const [backtestId, setBacktestId] = useState<string>("")
    const [runs, setRuns] = useState<number>(1000)
    const [method, setMethod] = useState<SimulationType>("bootstrap")
    const [result, setResult] = useState<MonteCarloResponse | null>(null)
    const [backtests, setBacktests] = useState<Backtest[]>([])
    const [loadingBacktests, setLoadingBacktests] = useState(false)

    // Parametric Mode State
    const [paraWinRate, setParaWinRate] = useState<string>("40")
    const [paraRRR, setParaRRR] = useState<string>("1.5")
    const [paraRisk, setParaRisk] = useState<string>("1")
    const [paraNumTrades, setParaNumTrades] = useState<string>("1000")
    const [paraRuns, setParaRuns] = useState<string>("1000")
    const [paraResult, setParaResult] = useState<ParametricSimulationResult | null>(null)

    // Consecutive Losing Mode State
    const [clWinRates, setClWinRates] = useState<string>("30, 38, 50, 61, 78, 85")
    const [clRrrs, setClRrrs] = useState<string>("3, 2, 1.5, 1, 0.5, 0.25")
    const [clNumTrades, setClNumTrades] = useState<string>("1000")
    const [clSims, setClSims] = useState<string>("200")
    const [clResult, setClResult] = useState<ConsecutiveLosingResponse | null>(null)

    // Profit Target Mode State
    const [ptInitialBalance, setPtInitialBalance] = useState<string>("1000")
    const [ptTargetBalance, setPtTargetBalance] = useState<string>("200000")
    const [ptNumTrades, setPtNumTrades] = useState<string>("750")
    const [ptWinRate, setPtWinRate] = useState<string>("76")
    const [ptResult, setPtResult] = useState<ProfitTargetResponse | null>(null)

    // Random Win Rate Mode State
    const [rwrInitialEquity, setRwrInitialEquity] = useState<string>("1000")
    const [rwrRisk, setRwrRisk] = useState<string>("1")
    const [rwrTrades, setRwrTrades] = useState<string>("100")
    const [rwrSimulations, setRwrSimulations] = useState<string>("200")
    const [rwrIsManual, setRwrIsManual] = useState<boolean>(false)
    const [rwrManualPairs, setRwrManualPairs] = useState<ManualPairInput[]>([
        { win_rate: 0.3, rrr: 3.0 },
        { win_rate: 0.4, rrr: 2.0 },
        { win_rate: 0.5, rrr: 1.5 },
        { win_rate: 0.6, rrr: 1.0 },
        { win_rate: 0.7, rrr: 0.5 }
    ])
    const [rwrResult, setRwrResult] = useState<RandomWinRateResponse | null>(null)

    // Robustness Mode State
    const [robSims, setRobSims] = useState<string>("100")
    const [robType, setRobType] = useState<"shuffle" | "bootstrap">("shuffle")
    const [robSkip, setRobSkip] = useState<string>("0") // Percentage 0-100
    const [robDet, setRobDet] = useState<string>("0") // Percentage 0-100
    const [robResult, setRobResult] = useState<RobustnessResponse | null>(null)

    const [isRunning, setIsRunning] = useState(false)

    // Fetch backtests on mount
    useEffect(() => {
        const fetchBacktests = async () => {
            try {
                setLoadingBacktests(true)
                const allBacktests = await backtestApi.listAll(1000)
                const backtestsWithAlias = allBacktests.filter(bt => bt.alias && bt.alias.trim() !== '')
                setBacktests(backtestsWithAlias)
            } catch (err) {
                console.error('Failed to fetch backtests:', err)
                toast({ title: "Error", description: "Failed to load backtests.", variant: "destructive" })
            } finally {
                setLoadingBacktests(false)
            }
        }
        fetchBacktests()
    }, [toast])

    const handleRunBacktest = async () => {
        try {
            setIsRunning(true)
            const request: MonteCarloRequest = {
                backtest_id: parseInt(backtestId),
                simulation_type: method,
                num_simulations: runs,
                block_size: method === "bootstrap" ? 10 : undefined,
                random_seed: undefined,
            }

            const response = await optimizationApi.startMonteCarlo(request)
            toast({ title: "Simulation Started", description: `Running ${runs} simulations...` })

            const simulationId = response.simulation_id
            const pollResults = async () => {
                const mcResults = await optimizationApi.getMonteCarloResults(simulationId)
                setResult(mcResults)
                setIsRunning(false)
                toast({ title: "Simulation Complete", description: "Analysis finished successfully." })
            }
            setTimeout(pollResults, 3000)
        } catch (err) {
            console.error("Failed to run simulation:", err)
            toast({ title: "Error", description: "Failed to run simulation.", variant: "destructive" })
            setIsRunning(false)
        }
    }

    const handleRunParametric = async () => {
        try {
            setIsRunning(true)
            const request: ParametricMonteCarloRequest = {
                win_rate: parseFloat(paraWinRate) / 100,
                reward_risk_ratio: parseFloat(paraRRR),
                risk_per_trade: parseFloat(paraRisk) / 100,
                num_trades: parseInt(paraNumTrades),
                num_simulations: parseInt(paraRuns),
                initial_balance: 10000, // Fixed for now or add input
            }

            const results = await optimizationApi.runParametricMonteCarlo(request)
            setParaResult(results)
            setIsRunning(false)
            toast({ title: "Simulation Complete", description: "Parametric analysis finished." })
        } catch (err) {
            console.error("Failed to run parametric simulation:", err)
            toast({ title: "Error", description: "Failed to run simulation.", variant: "destructive" })
            setIsRunning(false)
        }
    }

    // Position Sizing Mode State
    const [psWinRate, setPsWinRate] = useState<string>("50")
    const [psRRR, setPsRRR] = useState<string>("1.5")
    const [psRisk, setPsRisk] = useState<string>("1")
    const [psNumTrades, setPsNumTrades] = useState<string>("1000")
    const [psResult, setPsResult] = useState<any | null>(null) // Using any for now or import type

    const handleRunPositionSizing = async () => {
        try {
            setIsRunning(true)
            const request = {
                win_rate: parseFloat(psWinRate) / 100,
                reward_risk_ratio: parseFloat(psRRR),
                risk_per_trade: parseFloat(psRisk) / 100,
                num_trades: parseInt(psNumTrades),
                initial_balance: 10000,
            }

            const results = await optimizationApi.runPositionSizing(request)
            setPsResult(results)
            setIsRunning(false)
            toast({ title: "Simulation Complete", description: "Position sizing comparison finished." })
        } catch (err) {
            console.error("Failed to run position sizing simulation:", err)
            toast({ title: "Error", description: "Failed to run simulation.", variant: "destructive" })
            setIsRunning(false)
        }
    }

    const handleRunConsecutiveLosing = async () => {
        try {
            setIsRunning(true)
            const winRates = clWinRates.split(',').map(s => parseFloat(s.trim()) / 100).filter(n => !isNaN(n))
            const rrrs = clRrrs.split(',').map(s => parseFloat(s.trim())).filter(n => !isNaN(n))

            // Ensure we have valid inputs
            if (winRates.length === 0 || rrrs.length === 0) {
                 toast({ title: "Error", description: "Invalid Win Rates or RRR inputs.", variant: "destructive" })
                 setIsRunning(false)
                 return
            }

            const request: ConsecutiveLosingRequest = {
                win_rates: winRates,
                rrrs: rrrs,
                num_trades: parseInt(clNumTrades),
                num_simulations: parseInt(clSims),
            }

            const response = await optimizationApi.runConsecutiveLosing(request)
            setClResult(response)
            setIsRunning(false)
            toast({ title: "Simulation Complete", description: "Consecutive losing analysis finished." })
        } catch (err) {
            console.error("Failed to run consecutive losing simulation:", err)
            toast({ title: "Error", description: "Failed to run simulation.", variant: "destructive" })
            setIsRunning(false)
        }
    }

    const handleRunProfitTarget = async () => {
        try {
            setIsRunning(true)
            const request: ProfitTargetRequest = {
                initial_balance: parseFloat(ptInitialBalance),
                target_balance: parseFloat(ptTargetBalance),
                num_trades: parseInt(ptNumTrades),
                win_rate: parseFloat(ptWinRate) / 100.0,
                num_simulations: 500, // Fixed for performance/heatmap density
            }

            const response = await optimizationApi.runProfitTarget(request)
            setPtResult(response)
            setIsRunning(false)
            toast({ title: "Simulation Complete", description: "Profit target heatmap generated." })
        } catch (err) {
            console.error("Failed to run profit target simulation:", err)
            toast({ title: "Error", description: "Failed to run simulation.", variant: "destructive" })
            setIsRunning(false)
        }
    }

    const handleRunRandomWinRate = async () => {
        try {
            setIsRunning(true)
            const request: RandomWinRateRequest = {
                initial_equity: parseFloat(rwrInitialEquity),
                risk_per_trade: parseFloat(rwrRisk) / 100.0,
                trades_per_run: parseInt(rwrTrades),
                simulations: parseInt(rwrSimulations),
                manual_pairs: rwrIsManual ? rwrManualPairs : undefined
            }

            const response = await optimizationApi.runRandomWinRate(request)
            setRwrResult(response)
            setIsRunning(false)
            toast({ title: "Simulation Complete", description: "Random Win Rate simulation finished." })
        } catch (err) {
            console.error("Failed to run random win rate simulation:", err)
            toast({ title: "Error", description: "Failed to run simulation.", variant: "destructive" })
            setIsRunning(false)
        }
    }

    const handleRunRobustness = async () => {
        if (!backtestId) {
            toast({ title: "Error", description: "Please select a backtest first.", variant: "destructive" })
            return
        }
        try {
            setIsRunning(true)
            const request: RobustnessRequest = {
                backtest_id: backtestId,
                simulations: parseInt(robSims),
                simulation_type: robType,
                skip_probability: parseFloat(robSkip) / 100.0,
                deterioration_pct: parseFloat(robDet) / 100.0
            }
            const response = await optimizationApi.runRobustness(request)
            setRobResult(response)
            setIsRunning(false)
            toast({ title: "Simulation Complete", description: "Robustness simulation finished." })
        } catch (err) {
             console.error("Failed to run robustness simulation:", err)
             toast({ title: "Error", description: "Failed to run simulation.", variant: "destructive" })
             setIsRunning(false)
        }
    }

    // Multi-Entry Mode State
    const [meWinRate, setMeWinRate] = useState<string>("43")
    const [meRRR, setMeRRR] = useState<string>("1.3")
    const [meStep, setMeStep] = useState<string>("0.2")
    const [meRisk, setMeRisk] = useState<string>("3")
    const [meSims, setMeSims] = useState<string>("100")
    const [meResult, setMeResult] = useState<MultiEntryResponse | null>(null)

    const handleRunMultiEntry = async () => {
        try {
            setIsRunning(true)
            const request: MultiEntryRequest = {
                win_rate: parseFloat(meWinRate) / 100.0,
                initial_rrr: parseFloat(meRRR),
                rrr_step: parseFloat(meStep),
                risk_percent: parseFloat(meRisk) / 100.0,
                simulations: parseInt(meSims),
                initial_balance: 1000
            }
            const response = await optimizationApi.runMultiEntry(request)
            setMeResult(response)
            setIsRunning(false)
            toast({ title: "Simulation Complete", description: "Multi-Entry simulation finished." })
        } catch (err) {
            console.error("Failed to run multi-entry simulation:", err)
            toast({ title: "Error", description: "Failed to run simulation.", variant: "destructive" })
            setIsRunning(false)
        }
    }

    const getPsChartData = () => {
        if (!psResult) return []
        return psResult.linear_curve.map((val: number, i: number) => ({
            i,
            linear_raw: val,
            compounding_raw: psResult.compounding_curve[i],
            // Transform to % return
            linear: ((val - 10000) / 10000 * 100),
            compounding: ((psResult.compounding_curve[i] - 10000) / 10000 * 100)
        }))
    }

    // Prepare data for multi-line chart
    const getMultiLineData = () => {
        if (!paraResult || !paraResult.equity_curves.length) return []

        // Transform and normalize to percentage return
        // where initial balance (10000) is 0%
        const numPoints = paraResult.equity_curves[0].length
        const initialBalance = 10000 // Ensure this matches simulation input
        const data = []
        for (let i = 0; i < numPoints; i++) {
            const point: any = { i }
            paraResult.equity_curves.forEach((curve, idx) => {
                // (Current - Initial) / Initial * 100
                const pctReturn = ((curve[i] - initialBalance) / initialBalance) * 100
                point[`run${idx}`] = pctReturn
            })
            data.push(point)
        }
        return data
    }

    const multiLineData = getMultiLineData()

    // Calculate dynamic ticks for X axis (e.g., 5 intervals)
    const getXTicks = () => {
        if (!paraResult) return [0, 200, 400, 600, 800, 1000]
        const total = paraResult.num_trades
        const steps = 5
        const interval = Math.floor(total / steps)
        const ticks: number[] = []
        for (let i = 1; i <= steps; i++) {
            ticks.push(i * interval)
        }
        return ticks
    }
    const xTicks = getXTicks()

    const getPsXTicks = () => {
        const total = psResult ? psResult.num_trades : parseInt(psNumTrades) || 1000
        const steps = 5
        const interval = Math.floor(total / steps)
        const ticks = [0]
        for (let i = 1; i <= steps; i++) {
            ticks.push(i * interval)
        }
        return ticks
    }

    return (
        <div className="space-y-6">
            <Tabs defaultValue="robustness" onValueChange={(v) => setMode(v as any)} className="w-full">
                <TabsList className="grid w-full grid-cols-2 md:grid-cols-4 lg:grid-cols-7 h-auto">
                    <TabsTrigger value="robustness">Robustness & Stress Test</TabsTrigger>
                    <TabsTrigger value="parametric">Synthetic / Parametric</TabsTrigger>
                    <TabsTrigger value="position-sizing">Position Sizing</TabsTrigger>
                    <TabsTrigger value="consecutive-losing">Consecutive Losing</TabsTrigger>
                    <TabsTrigger value="profit-target">Profit Target</TabsTrigger>
                    <TabsTrigger value="random-win-rate">Random Win Rate</TabsTrigger>
                    {/* Multi-Entry is handled separately or is it? No, it's 7th item. Let's adjust grid */}
                    <TabsTrigger value="multi-entry">Multi-Entry</TabsTrigger>
                </TabsList>

                <TabsContent value="backtest" className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        {/* Config */}
                        <Card className="h-fit">
                            <CardHeader>
                                <CardTitle>Simulation Settings</CardTitle>
                                <CardDescription>Resample historical trades</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="space-y-2">
                                    <Label>Backtest</Label>
                                    <Select value={backtestId} onValueChange={setBacktestId} disabled={loadingBacktests || backtests.length === 0}>
                                        <SelectTrigger>
                                            <SelectValue placeholder={loadingBacktests ? "Loading..." : "Select a backtest"} />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {backtests.map((bt) => (
                                                <SelectItem key={bt.backtest_id} value={bt.backtest_id.toString()}>
                                                    {bt.alias}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="space-y-2">
                                    <Label>Simulations</Label>
                                    <Select value={runs.toString()} onValueChange={(v) => setRuns(parseInt(v))}>
                                        <SelectTrigger><SelectValue /></SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="100">100</SelectItem>
                                            <SelectItem value="500">500</SelectItem>
                                            <SelectItem value="1000">1,000</SelectItem>
                                            <SelectItem value="5000">5,000</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="space-y-2">
                                    <Label>Method</Label>
                                    <Select value={method} onValueChange={(v) => setMethod(v as SimulationType)}>
                                        <SelectTrigger><SelectValue /></SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="bootstrap">Bootstrap</SelectItem>
                                            <SelectItem value="shuffle_trades">Shuffle</SelectItem>
                                            <SelectItem value="resample_returns">Resample</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                                <Button className="w-full" variant="secondary" onClick={handleRunBacktest} disabled={isRunning || !backtestId}>
                                    {isRunning ? "Simulating..." : <><Zap className="mr-2 h-4 w-4" /> Run Simulation</>}
                                </Button>
                            </CardContent>
                        </Card>

                        {/* Backtest Results */}
                        <Card className="md:col-span-2 min-h-[400px]">
                            <CardHeader>
                                <CardTitle>Stress Test Results</CardTitle>
                                <CardDescription>Confidence Intervals and Risk Metrics</CardDescription>
                            </CardHeader>
                            <CardContent>
                                {result ? (
                                    <div className="space-y-6">
                                        <div className="grid grid-cols-3 gap-4 text-center">
                                            <div className="p-4 rounded border bg-card/50">
                                                <div className="text-xs text-muted-foreground">Original Return</div>
                                                <div className="text-xl font-bold font-mono text-emerald-500">{formatNumber(result.original_return, 2)}%</div>
                                            </div>
                                            <div className="p-4 rounded border bg-card/50">
                                                <div className="text-xs text-muted-foreground">Mean Simulated</div>
                                                <div className="text-xl font-bold font-mono">{formatNumber(result.mean_return, 2)}%</div>
                                            </div>
                                            <div className="p-4 rounded border bg-card/50">
                                                <div className="text-xs text-muted-foreground">Prob. Profit</div>
                                                <div className="text-xl font-bold font-mono text-emerald-500">{formatNumber(result.probability_of_profit, 1)}%</div>
                                            </div>
                                        </div>
                                         <div className="grid grid-cols-2 gap-4 text-sm">
                                            <div className="p-3 rounded border bg-card/30">
                                                <div className="text-muted-foreground mb-1">95% CI</div>
                                                <div className="font-mono">{formatNumber(result.ci_95_lower, 2)}% to {formatNumber(result.ci_95_upper, 2)}%</div>
                                            </div>
                                            <div className="p-3 rounded border bg-card/30">
                                                <div className="text-muted-foreground mb-1">Prob. Ruin</div>
                                                <div className="font-mono text-red-500">{formatNumber(result.probability_of_ruin, 2)}%</div>
                                            </div>
                                        </div>
                                    </div>
                                ) : (
                                    <div className="h-full flex items-center justify-center text-muted-foreground">Run a simulation to view results</div>
                                )}
                            </CardContent>
                        </Card>
                    </div>
                </TabsContent>

                <TabsContent value="parametric" className="space-y-6">
                     <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        {/* Config */}
                        <Card className="h-fit">
                            <CardHeader>
                                <CardTitle>Synthetic Parameters</CardTitle>
                                <CardDescription>Model theoretical performance</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-2">
                                        <Label>Win Rate (%)</Label>
                                        <Input type="number" value={paraWinRate} onChange={(e) => setParaWinRate(e.target.value)} />
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Risk:Reward</Label>
                                        <Input type="number" value={paraRRR} onChange={(e) => setParaRRR(e.target.value)} />
                                    </div>
                                </div>
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-2">
                                        <Label>Risk (%)</Label>
                                        <Input type="number" value={paraRisk} onChange={(e) => setParaRisk(e.target.value)} />
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Num Trades</Label>
                                        <Input type="number" value={paraNumTrades} onChange={(e) => setParaNumTrades(e.target.value)} />
                                    </div>
                                </div>
                                <div className="space-y-2">
                                    <Label>Num Simulations</Label>
                                    <Input type="number" value={paraRuns} onChange={(e) => setParaRuns(e.target.value)} />
                                </div>
                                <Button className="w-full" onClick={handleRunParametric} disabled={isRunning}>
                                    {isRunning ? "Simulating..." : <><Zap className="mr-2 h-4 w-4" /> Run Synthetic</>}
                                </Button>
                            </CardContent>
                        </Card>

                         {/* Parametric Chart & Results */}
                         <Card className="md:col-span-2 min-h-[500px]">
                            <CardHeader>
                                <CardTitle>Monte Carlo Output</CardTitle>
                                <CardDescription>
                                    {paraResult ? `Simulation of ${paraResult.num_simulations} runs, ${paraResult.num_trades} trades each` : "Visualizing multiple equity curves"}
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-6">
                                {paraResult ? (
                                    <>
                                        <div className="h-[300px] w-full">
                                            <ResponsiveContainer width="100%" height="100%">
                                                <LineChart data={multiLineData} margin={{ top: 10, right: 30, left: 10, bottom: 20 }}>
                                                    <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                                                    <XAxis
                                                        dataKey="i"
                                                        ticks={xTicks}
                                                        label={{ value: "Number of Trades", position: "insideBottom", offset: -10 }}
                                                    />
                                                    <YAxis
                                                        domain={['auto', 'auto']}
                                                        tickFormatter={(val) => `${val.toFixed(0)}%`}
                                                        label={{ value: "Equity Return (%)", angle: -90, position: "insideLeft", offset: 10, style: { textAnchor: 'middle', fill: 'currentColor' } }}
                                                    />
                                                    <Tooltip
                                                        labelFormatter={(v) => `Trade #${v}`}
                                                        formatter={(val: number) => [`${val.toFixed(2)}%`, "Equity Return"]}
                                                    />
                                                    <ReferenceLine y={0} stroke="#ef4444" strokeDasharray="3 3" strokeWidth={2} />
                                                    {/* Render lines individually. Limited to 50 in backend. */}
                                                    {paraResult.equity_curves.map((_, idx) => (
                                                        <Line
                                                            key={idx}
                                                            type="monotone"
                                                            dataKey={`run${idx}`}
                                                            stroke="#06b6d4" // cyan-500
                                                            strokeOpacity={0.3}
                                                            dot={false}
                                                            strokeWidth={1.5}
                                                            isAnimationActive={false}
                                                        />
                                                    ))}
                                                </LineChart>
                                            </ResponsiveContainer>
                                        </div>

                                        <div className="grid grid-cols-4 gap-4 text-center">
                                            <div className="p-3 rounded border bg-card/50">
                                                <div className="text-xs text-muted-foreground">Mean Return</div>
                                                <div className="font-bold">{formatNumber(paraResult.mean_return, 2)}%</div>
                                            </div>
                                            <div className="p-3 rounded border bg-card/50">
                                                <div className="text-xs text-muted-foreground">Median Return</div>
                                                <div className="font-bold">{formatNumber(paraResult.median_return, 2)}%</div>
                                            </div>
                                            <div className="p-3 rounded border bg-card/50">
                                                <div className="text-xs text-muted-foreground">Std Dev (Return)</div>
                                                <div className="font-bold">{formatNumber(paraResult.std_return, 2)}%</div>
                                            </div>
                                            <div className="p-3 rounded border bg-card/50">
                                                <div className="text-xs text-muted-foreground">Prob. Profit</div>
                                                <div className="font-bold text-emerald-500">{formatNumber(paraResult.probability_of_profit, 1)}%</div>
                                            </div>

                                            <div className="p-3 rounded border bg-card/50">
                                                <div className="text-xs text-muted-foreground">Max DD (Avg)</div>
                                                <div className="font-bold text-red-500">{formatNumber(paraResult.max_drawdown_avg, 2)}%</div>
                                            </div>
                                            <div className="p-3 rounded border bg-card/50">
                                                <div className="text-xs text-muted-foreground">Prob. Ruin (&gt;50%)</div>
                                                <div className="font-bold text-red-500">{formatNumber(paraResult.probability_of_ruin, 2)}%</div>
                                            </div>
                                            <div className="p-3 rounded border bg-card/50 col-span-2">
                                                 <div className="text-xs text-muted-foreground">95% CI</div>
                                                 <div className="text-xs font-mono mt-1">{formatNumber(paraResult.ci_95_lower, 1)}% / {formatNumber(paraResult.ci_95_upper, 1)}%</div>
                                            </div>
                                        </div>
                                    </>
                                ) : (
                                    <div className="h-full flex items-center justify-center text-muted-foreground py-20">
                                        Configure parameters and run simulation to visualize equity curves.
                                    </div>
                                )}
                            </CardContent>
                         </Card>
                     </div>
                </TabsContent>
                <TabsContent value="position-sizing" className="space-y-6">
                     <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        {/* Config */}
                        <Card className="h-fit">
                            <CardHeader>
                                <CardTitle>Position Sizing Comparison</CardTitle>
                                <CardDescription>Linear vs Compounding Growth</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-2">
                                        <Label>Win Rate (%)</Label>
                                        <Input type="number" value={psWinRate} onChange={(e) => setPsWinRate(e.target.value)} />
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Risk:Reward</Label>
                                        <Input type="number" value={psRRR} onChange={(e) => setPsRRR(e.target.value)} />
                                    </div>
                                </div>
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-2">
                                        <Label>Risk (%)</Label>
                                        <Input type="number" value={psRisk} onChange={(e) => setPsRisk(e.target.value)} />
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Num Trades</Label>
                                        <Input type="number" value={psNumTrades} onChange={(e) => setPsNumTrades(e.target.value)} />
                                    </div>
                                </div>
                                <Button className="w-full" onClick={handleRunPositionSizing} disabled={isRunning}>
                                    {isRunning ? "Simulating..." : <><Zap className="mr-2 h-4 w-4" /> Compare Sizing</>}
                                </Button>
                            </CardContent>
                        </Card>

                         {/* Position Sizing Chart & Results */}
                         <Card className="md:col-span-2 min-h-[500px]">
                            <CardHeader>
                                <CardTitle>Equity Comparison</CardTitle>
                                <CardDescription>
                                    Single trade sequence applied to different sizing models (Linear vs Compounding)
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-6">
                                {psResult ? (
                                    <>
                                        <div className="h-[300px] w-full">
                                            <ResponsiveContainer width="100%" height="100%">
                                                <LineChart data={getPsChartData()} margin={{ top: 10, right: 30, left: 40, bottom: 20 }}>
                                                    <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                                                    <XAxis
                                                        dataKey="i"
                                                        ticks={getPsXTicks()}
                                                        label={{ value: "Number of Trades", position: "insideBottom", offset: -10 }}
                                                    />
                                                    <YAxis
                                                        domain={['auto', 'auto']}
                                                        tickFormatter={(val) => `${val.toFixed(0)}%`}
                                                        label={{ value: "Equity Return (%)", angle: -90, position: "insideLeft", offset: -25, style: { textAnchor: 'middle', fill: 'currentColor' } }}
                                                    />
                                                    <Tooltip
                                                        labelFormatter={(v) => `Trade #${v}`}
                                                        formatter={(val: number, name: string) => [`${val.toFixed(2)}%`, name]}
                                                    />
                                                    <ReferenceLine y={0} stroke="#ef4444" strokeDasharray="3 3" strokeWidth={1} />

                                                    <Line
                                                        type="monotone"
                                                        dataKey="compounding"
                                                        name="Compounding (Risk %)"
                                                        stroke="#2563eb" // blue-600
                                                        strokeWidth={2}
                                                        dot={false}
                                                    />
                                                    <Line
                                                        type="monotone"
                                                        dataKey="linear"
                                                        name="Linear (Fixed Risk)"
                                                        stroke="#16a34a" // green-600
                                                        strokeWidth={2}
                                                        dot={false}
                                                    />
                                                </LineChart>
                                            </ResponsiveContainer>
                                        </div>

                                        <div className="grid grid-cols-2 gap-4 text-center">
                                            {/* Linear Stats */}
                                            <div className="p-3 rounded border bg-card/50 space-y-2">
                                                <div className="text-sm font-semibold text-green-600">Linear (Fixed Risk)</div>
                                                <div className="grid grid-cols-3 gap-2 text-xs">
                                                    <div>
                                                        <div className="text-muted-foreground">Return</div>
                                                        <div className="font-mono font-bold">{psResult.linear_return_pct.toFixed(2)}%</div>
                                                    </div>
                                                    <div>
                                                        <div className="text-muted-foreground">Max DD</div>
                                                        <div className="font-mono font-bold text-red-500">{psResult.linear_max_drawdown.toFixed(2)}%</div>
                                                    </div>
                                                    <div>
                                                        <div className="text-muted-foreground">Ret/DD</div>
                                                        <div className="font-mono font-bold">{psResult.linear_ret_dd_ratio.toFixed(2)}</div>
                                                    </div>
                                                </div>
                                                <div className="text-xs font-mono text-muted-foreground border-t pt-2 mt-2">
                                                    Final Balance: ${psResult.linear_final_balance.toFixed(2)}
                                                </div>
                                            </div>

                                            {/* Compounding Stats */}
                                            <div className="p-3 rounded border bg-card/50 space-y-2">
                                                <div className="text-sm font-semibold text-blue-600">Compounding (Risk %)</div>
                                                <div className="grid grid-cols-3 gap-2 text-xs">
                                                    <div>
                                                        <div className="text-muted-foreground">Return</div>
                                                        <div className="font-mono font-bold">{psResult.compounding_return_pct.toFixed(2)}%</div>
                                                    </div>
                                                    <div>
                                                        <div className="text-muted-foreground">Max DD</div>
                                                        <div className="font-mono font-bold text-red-500">{psResult.compounding_max_drawdown.toFixed(2)}%</div>
                                                    </div>
                                                    <div>
                                                        <div className="text-muted-foreground">Ret/DD</div>
                                                        <div className="font-mono font-bold">{psResult.compounding_ret_dd_ratio.toFixed(2)}</div>
                                                    </div>
                                                </div>
                                                <div className="text-xs font-mono text-muted-foreground border-t pt-2 mt-2">
                                                    Final Balance: ${psResult.compounding_final_balance.toFixed(2)}
                                                </div>
                                            </div>
                                        </div>
                                    </>
                                ) : (
                                    <div className="h-full flex items-center justify-center text-muted-foreground py-20">
                                        Run comparison to visualize equity curves.
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </div>
                </TabsContent>

                <TabsContent value="consecutive-losing" className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        {/* inputs */}
                        <Card className="h-fit">
                            <CardHeader>
                                <CardTitle>Stress Parameters</CardTitle>
                                <CardDescription>Test multiple system scenarios</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="space-y-2">
                                    <Label>Win Rates (comma sep %)</Label>
                                    <Input value={clWinRates} onChange={(e) => setClWinRates(e.target.value)} />
                                </div>
                                <div className="space-y-2">
                                    <Label>Risk:Reward Ratios (comma sep)</Label>
                                    <Input value={clRrrs} onChange={(e) => setClRrrs(e.target.value)} />
                                </div>
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-2">
                                        <Label>Num Trades</Label>
                                        <Input value={clNumTrades} onChange={(e) => setClNumTrades(e.target.value)} type="number" />
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Simulations</Label>
                                        <Input value={clSims} onChange={(e) => setClSims(e.target.value)} type="number" />
                                    </div>
                                </div>
                                <Button
                                    className="w-full"
                                    onClick={handleRunConsecutiveLosing}
                                    disabled={isRunning}
                                >
                                    {isRunning ? <RefreshCcw className="mr-2 h-4 w-4 animate-spin" /> : <Zap className="mr-2 h-4 w-4" />}
                                    Run Stress Test
                                </Button>
                            </CardContent>
                        </Card>

                        {/* Chart */}
                        <Card className="col-span-2 h-[500px] flex flex-col">
                            <CardHeader>
                                <CardTitle>Consecutive Losing Streaks Distribution</CardTitle>
                                <CardDescription>Box Plot of Max Consecutive Losses (Min, Q1, Median, Q3, Max)</CardDescription>
                            </CardHeader>
                            <CardContent className="flex-1 min-h-0">
                                {clResult ? (
                                    <ResponsiveContainer width="100%" height="100%">
                                        <ComposedChart data={clResult.scenarios}>
                                            <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                            <XAxis dataKey="scenario_label" />
                                            <YAxis label={{ value: 'Consecutive Losses', angle: -90, position: 'insideLeft' }} />
                                            <Tooltip
                                                content={({ active, payload }) => {
                                                    if (active && payload && payload.length) {
                                                        const d = payload[0].payload as any;
                                                        return (
                                                            <div className="bg-background border rounded p-2 shadow-md text-xs">
                                                                <div className="font-bold mb-1">{d.scenario_label} (WR={d.win_rate*100}%)</div>
                                                                <div>Max Streak Range: {d.min_losses} - {d.max_losses}</div>
                                                                <div>Median: {d.median_losses}</div>
                                                                <div>Q1-Q3: {d.q1_losses} - {d.q3_losses}</div>
                                                                <div>Mean: {d.mean_losses.toFixed(1)}</div>
                                                            </div>
                                                        );
                                                    }
                                                    return null;
                                                }}
                                            />
                                            {/* We use a Bar with Custom Shape to render Box Plot */}
                                            <Bar dataKey="max_losses" shape={<BoxPlotBar />} />
                                        </ComposedChart>
                                    </ResponsiveContainer>
                                ) : (
                                    <div className="h-full flex items-center justify-center text-muted-foreground">
                                        Run simulation to view losing streak analysis.
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </div>
                </TabsContent>

                <TabsContent value="profit-target" className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                         {/* Inputs */}
                        <Card className="h-fit">
                            <CardHeader>
                                <CardTitle>Profit Target Parameters</CardTitle>
                                <CardDescription>Probability of hitting target</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="space-y-2">
                                    <Label>Initial Balance</Label>
                                    <Input value={ptInitialBalance} onChange={(e) => setPtInitialBalance(e.target.value)} type="number" />
                                </div>
                                <div className="space-y-2">
                                    <Label>Target Balance</Label>
                                    <Input value={ptTargetBalance} onChange={(e) => setPtTargetBalance(e.target.value)} type="number" />
                                </div>
                                <div className="space-y-2">
                                    <Label>Number of Trades</Label>
                                    <Input value={ptNumTrades} onChange={(e) => setPtNumTrades(e.target.value)} type="number" />
                                </div>
                                <div className="space-y-2">
                                    <Label>Win Rate (%)</Label>
                                    <Input value={ptWinRate} onChange={(e) => setPtWinRate(e.target.value)} type="number" />
                                </div>
                                <Button
                                    className="w-full"
                                    onClick={handleRunProfitTarget}
                                    disabled={isRunning}
                                >
                                    {isRunning ? <RefreshCcw className="mr-2 h-4 w-4 animate-spin" /> : <Zap className="mr-2 h-4 w-4" />}
                                    Run Simulation
                                </Button>
                            </CardContent>
                        </Card>

                        {/* Chart */}
                        <Card className="col-span-2 h-[600px] flex flex-col">
                            <CardHeader>
                                <CardTitle>Success Rate Heatmap</CardTitle>
                                <CardDescription>
                                    Probability of reaching ${parseInt(ptTargetBalance).toLocaleString()} in {ptNumTrades} trades
                                    (Win Rate = {ptWinRate}%, Initial = ${parseInt(ptInitialBalance).toLocaleString()})
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="flex-1 min-h-0 overflow-auto">
                                {ptResult ? (
                                    <ProfitTargetHeatmap
                                        data={ptResult.results}
                                    />
                                ) : (
                                    <div className="h-full flex items-center justify-center text-muted-foreground">
                                        Run simulation to view heatmap.
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </div>
                </TabsContent>

                <TabsContent value="random-win-rate" className="space-y-6">
                    {/* Inputs */}
                    <Card className="h-fit">
                        <CardHeader className="flex flex-row items-center justify-between">
                            <div>
                                <CardTitle>Variable Conditions Parameters</CardTitle>
                                <CardDescription>Simulate changing market conditions (random or manual pairs)</CardDescription>
                            </div>
                            <div className="flex items-center space-x-2">
                                <Label htmlFor="rwr-mode" className="text-sm">Manual Mode</Label>
                                <Switch
                                    id="rwr-mode"
                                    checked={rwrIsManual}
                                    onCheckedChange={setRwrIsManual}
                                />
                            </div>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                                <div className="space-y-2">
                                    <Label>Initial Equity</Label>
                                    <Input value={rwrInitialEquity} onChange={(e) => setRwrInitialEquity(e.target.value)} type="number" />
                                </div>
                                <div className="space-y-2">
                                    <Label>Risk per Trade (%)</Label>
                                    <Input value={rwrRisk} onChange={(e) => setRwrRisk(e.target.value)} type="number" />
                                </div>
                                <div className="space-y-2">
                                    <Label>Trades per Run</Label>
                                    <Input value={rwrTrades} onChange={(e) => setRwrTrades(e.target.value)} type="number" />
                                </div>
                                <div className="space-y-2">
                                    <Label>Simulations</Label>
                                    <Input value={rwrSimulations} onChange={(e) => setRwrSimulations(e.target.value)} type="number" />
                                </div>
                            </div>

                            {/* Manual Pairs Input Table */}
                            {rwrIsManual && (
                                <div className="border rounded-md p-4 bg-slate-900/50">
                                    <Label className="mb-2 block">Defined Win Rate / RRR Pairs</Label>
                                    <Table>
                                        <TableHeader>
                                            <TableRow>
                                                <TableHead>Win Rate (0.0 - 1.0)</TableHead>
                                                <TableHead>RRR (&gt; 0)</TableHead>
                                            </TableRow>
                                        </TableHeader>
                                        <TableBody>
                                            {rwrManualPairs.map((pair, index) => (
                                                <TableRow key={index}>
                                                    <TableCell>
                                                        <Input
                                                            type="number"
                                                            step="0.01"
                                                            value={pair.win_rate}
                                                            onChange={(e) => {
                                                                const newPairs = [...rwrManualPairs];
                                                                newPairs[index].win_rate = parseFloat(e.target.value);
                                                                setRwrManualPairs(newPairs);
                                                            }}
                                                        />
                                                    </TableCell>
                                                    <TableCell>
                                                        <Input
                                                            type="number"
                                                            step="0.1"
                                                            value={pair.rrr}
                                                            onChange={(e) => {
                                                                const newPairs = [...rwrManualPairs];
                                                                newPairs[index].rrr = parseFloat(e.target.value);
                                                                setRwrManualPairs(newPairs);
                                                            }}
                                                        />
                                                    </TableCell>
                                                </TableRow>
                                            ))}
                                        </TableBody>
                                    </Table>
                                </div>
                            )}

                            <Button
                                className="w-full"
                                onClick={handleRunRandomWinRate}
                                disabled={isRunning}
                            >
                                {isRunning ? <RefreshCcw className="mr-2 h-4 w-4 animate-spin" /> : <Zap className="mr-2 h-4 w-4" />}
                                Run Simulation
                            </Button>
                        </CardContent>
                    </Card>

                    {rwrResult && (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            {/* Pie Chart: Pair Usage */}
                            <Card className="h-[400px] flex flex-col">
                                <CardHeader>
                                    <CardTitle>Usage Frequency of Win Rate / RRR Pairs</CardTitle>
                                </CardHeader>
                                <CardContent className="flex-1 min-h-0">
                                    <ResponsiveContainer width="100%" height="100%">
                                        <PieChart>
                                            <Pie
                                                data={rwrResult.result.pairs as any[]}
                                                dataKey="usage_count"
                                                nameKey="win_rate"
                                                cx="50%"
                                                cy="50%"
                                                outerRadius={100}
                                                label={({ payload }: any) => {
                                                    const { win_rate, rrr } = payload as RandomWinRatePair;
                                                    return `${(win_rate * 100).toFixed(1)}%/${rrr.toFixed(2)}`;
                                                }}
                                            >
                                                {rwrResult.result.pairs.map((entry: any, index: number) => (
                                                    <Cell key={`cell-${index}`} fill={['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8'][index % 5]} />
                                                ))}
                                            </Pie>
                                            <Tooltip formatter={(value: number, name: any, props: any) => [
                                                `${value} trades (${(props.payload.usage_pct * 100).toFixed(1)}%)`,
                                                `WR: ${(props.payload.win_rate*100).toFixed(1)}% | RRR: ${props.payload.rrr.toFixed(2)}`
                                            ]} />
                                            <Legend formatter={(value) => `${(parseFloat(value) * 100).toFixed(2)}%`} />
                                        </PieChart>
                                    </ResponsiveContainer>
                                </CardContent>
                            </Card>

                            {/* Box Plot: Drawdown */}
                            <Card className="h-[400px] flex flex-col">
                                <CardHeader>
                                    <CardTitle>Drawdown % Distribution</CardTitle>
                                </CardHeader>
                                <CardContent className="flex-1 min-h-0">
                                    <ResponsiveContainer width="100%" height="100%">
                                        <ComposedChart
                                            data={[rwrResult.result.drawdown_stats]}
                                            margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                                        >
                                            <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                            <YAxis label={{ value: 'Drawdown %', angle: -90, position: 'insideLeft' }} />
                                            <Tooltip content={<CustomBoxPlotTooltip />} cursor={{ fill: 'transparent' }} />
                                            <Bar dataKey="max_val" fill="#8884d8" shape={<BoxPlotBar />} />
                                        </ComposedChart>
                                    </ResponsiveContainer>
                                </CardContent>
                            </Card>

                            {/* Box Plot: Final Equity */}
                            <Card className="h-[400px] flex flex-col">
                                <CardHeader>
                                    <CardTitle>Final Equity Distribution</CardTitle>
                                </CardHeader>
                                <CardContent className="flex-1 min-h-0">
                                    <ResponsiveContainer width="100%" height="100%">
                                        <ComposedChart
                                            data={[rwrResult.result.equity_stats]}
                                            margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                                        >
                                            <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                            <YAxis label={{ value: 'Final Equity ($)', angle: -90, position: 'insideLeft' }} />
                                            <Tooltip content={<CustomBoxPlotTooltip />} cursor={{ fill: 'transparent' }} />
                                            <Bar dataKey="max_val" fill="#82ca9d" shape={<BoxPlotBar />} />
                                        </ComposedChart>
                                    </ResponsiveContainer>
                                </CardContent>
                            </Card>

                            {/* Box Plot: Return % */}
                            <Card className="h-[400px] flex flex-col">
                                <CardHeader>
                                    <CardTitle>Return % Distribution</CardTitle>
                                </CardHeader>
                                <CardContent className="flex-1 min-h-0">
                                    <ResponsiveContainer width="100%" height="100%">
                                        <ComposedChart
                                            data={[rwrResult.result.return_stats]}
                                            margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                                        >
                                            <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                            <YAxis label={{ value: 'Return %', angle: -90, position: 'insideLeft' }} />
                                            <Tooltip content={<CustomBoxPlotTooltip />} cursor={{ fill: 'transparent' }} />
                                            <Bar dataKey="max_val" fill="#22c55e" shape={<BoxPlotBar />} />
                                        </ComposedChart>
                                    </ResponsiveContainer>
                                </CardContent>
                            </Card>
                        </div>
                    )}
                </TabsContent>

                <TabsContent value="robustness" className="space-y-6">
                    <Card className="h-fit">
                        <CardHeader>
                            <CardTitle>Strategy Robustness & Stress Test</CardTitle>
                            <CardDescription>
                                Unified stress testing: Resample/Shuffle trades and apply stress factors (Skip/Deterioration).
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
                                <div className="space-y-2">
                                    <Label>Backtest</Label>
                                    <Select value={backtestId} onValueChange={setBacktestId} disabled={loadingBacktests || backtests.length === 0}>
                                        <SelectTrigger>
                                            <SelectValue placeholder={loadingBacktests ? "Loading..." : "Select a backtest"} />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {backtests.map((bt) => (
                                                <SelectItem key={bt.backtest_id} value={bt.backtest_id.toString()}>
                                                    {bt.alias}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="space-y-2">
                                    <Label>Simulation Type</Label>
                                    <Select value={robType} onValueChange={(v: any) => setRobType(v)}>
                                        <SelectTrigger>
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="bootstrap">Bootstrap (Resample)</SelectItem>
                                            <SelectItem value="shuffle">Shuffle (Sequence)</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="space-y-2">
                                    <Label>Skip Probability (%)</Label>
                                    <Input value={robSkip} onChange={(e) => setRobSkip(e.target.value)} type="number" step="0.1" />
                                </div>
                                <div className="space-y-2">
                                    <Label>Deterioration (%)</Label>
                                    <Input value={robDet} onChange={(e) => setRobDet(e.target.value)} type="number" step="0.1" />
                                </div>
                                <div className="space-y-2">
                                    <Label>Simulations</Label>
                                    <Input value={robSims} onChange={(e) => setRobSims(e.target.value)} type="number" />
                                </div>
                            </div>
                            <Button
                                className="w-full"
                                onClick={handleRunRobustness}
                                disabled={isRunning || !backtestId}
                            >
                                {isRunning ? <RefreshCcw className="mr-2 h-4 w-4 animate-spin" /> : <Zap className="mr-2 h-4 w-4" />}
                                Run Stress Test
                            </Button>
                        </CardContent>
                    </Card>

                    {robResult && (
                        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                            {/* Stats Card */}
                            <Card className="lg:col-span-1">
                                <CardHeader>
                                    <CardTitle>Robustness Metrics</CardTitle>
                                </CardHeader>
                                <CardContent className="space-y-4">
                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="col-span-2 p-3 bg-card/50 border rounded text-center">
                                            <p className="text-sm font-medium text-muted-foreground">Original Profit</p>
                                            <p className="text-2xl font-bold font-mono text-green-500">${robResult.stats.original_profit.toFixed(2)}</p>
                                        </div>

                                        <div>
                                            <p className="text-sm font-medium text-muted-foreground">Mean Expected</p>
                                            <p className="text-lg font-bold">${robResult.stats.mean_profit.toFixed(2)}</p>
                                        </div>
                                        <div>
                                             <p className="text-sm font-medium text-muted-foreground">95% Conf. Interval</p>
                                             <p className="text-xs font-mono">
                                                ${robResult.stats.ci_95_lower?.toFixed(0)} - ${robResult.stats.ci_95_upper?.toFixed(0)}
                                             </p>
                                        </div>

                                        <div>
                                            <p className="text-sm font-medium text-muted-foreground">Min Profit</p>
                                            <p className="text-lg font-bold text-red-500">${robResult.stats.min_profit.toFixed(2)}</p>
                                        </div>
                                         <div>
                                            <p className="text-sm font-medium text-muted-foreground">Max Profit</p>
                                            <p className="text-lg font-bold text-green-500">${robResult.stats.max_profit.toFixed(2)}</p>
                                        </div>

                                        <div className="col-span-2 border-t pt-4 grid grid-cols-2 gap-4">
                                            <div>
                                                 <p className="text-sm font-medium text-muted-foreground">VaR (95%)</p>
                                                 <p className="text-lg font-bold text-red-500">${robResult.stats.var_95?.toFixed(2)}</p>
                                            </div>
                                            <div>
                                                 <p className="text-sm font-medium text-muted-foreground">CVaR (95%)</p>
                                                 <p className="text-lg font-bold text-red-600">${robResult.stats.cvar_95?.toFixed(2)}</p>
                                            </div>
                                        </div>

                                        <div className="col-span-2 pt-2">
                                             <p className="text-sm font-medium text-muted-foreground">Risk of Ruin</p>
                                             <p className={`text-xl font-bold ${robResult.stats.risk_of_ruin > 1 ? 'text-red-600' : 'text-green-600'}`}>
                                                {robResult.stats.risk_of_ruin.toFixed(2)}%
                                             </p>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>

                            {/* Equity Cone Chart */}
                            <Card className="lg:col-span-2 h-[500px] flex flex-col">
                                <CardHeader>
                                    <CardTitle>Equity Curve Cone</CardTitle>
                                    <CardDescription>Original (Green) vs 50 Simulated Scenarios (Grey)</CardDescription>
                                </CardHeader>
                                <CardContent className="flex-1 min-h-0">
                                    <ResponsiveContainer width="100%" height="100%">
                                        <LineChart
                                            data={robResult.original_equity.map((val: number, i: number) => {
                                                const point: any = { index: i, original: val };
                                                robResult.simulation_equities.forEach((sim: number[], sIdx: number) => {
                                                    point[`sim_${sIdx}`] = sim[i];
                                                });
                                                return point;
                                            })}
                                        >
                                            <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
                                            <XAxis dataKey="index" hide />
                                            <YAxis />
                                            <Tooltip />

                                            {/* Render first 50 simulation lines */}
                                            {robResult.simulation_equities.slice(0, 50).map((_: number[], idx: number) => (
                                                <Line
                                                    key={idx}
                                                    type="monotone"
                                                    dataKey={`sim_${idx}`}
                                                    stroke="#888888"
                                                    strokeWidth={1}
                                                    dot={false}
                                                    opacity={0.15}
                                                />
                                            ))}

                                            {/* Render Original Line on top */}
                                            <Line
                                                type="monotone"
                                                dataKey="original"
                                                stroke="#22c55e"
                                                strokeWidth={2}
                                                dot={false}
                                            />
                                        </LineChart>
                                    </ResponsiveContainer>
                                </CardContent>
                            </Card>
                        </div>
                    )}
                </TabsContent>

                <TabsContent value="multi-entry" className="space-y-6">
                    <Card>
                        <CardHeader>
                            <CardTitle>Multi-Entry RRR Analysis</CardTitle>
                            <CardDescription>
                                Compare single vs multiple trade entries with varying Risk-to-Reward ratios (MQL5 Article 19693).
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                <div className="space-y-2">
                                    <Label>Win Rate (%)</Label>
                                    <Input type="number" value={meWinRate} onChange={(e) => setMeWinRate(e.target.value)} />
                                </div>
                                <div className="space-y-2">
                                    <Label>Initial RRR</Label>
                                    <Input type="number" value={meRRR} onChange={(e) => setMeRRR(e.target.value)} />
                                </div>
                                <div className="space-y-2">
                                    <Label>RRR Step</Label>
                                    <Input type="number" value={meStep} onChange={(e) => setMeStep(e.target.value)} />
                                </div>
                                <div className="space-y-2">
                                    <Label>Total Risk (%)</Label>
                                    <Input type="number" value={meRisk} onChange={(e) => setMeRisk(e.target.value)} />
                                </div>
                                <div className="space-y-2">
                                    <Label>Simulations</Label>
                                    <Input type="number" value={meSims} onChange={(e) => setMeSims(e.target.value)} />
                                </div>
                            </div>
                            <Button onClick={handleRunMultiEntry} disabled={isRunning} className="w-full md:w-auto">
                                {isRunning && <RefreshCcw className="mr-2 h-4 w-4 animate-spin" />}
                                Run Multi-Entry Simulation
                            </Button>
                        </CardContent>
                    </Card>

                    {meResult && (
                        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                            {/* Summary Stats Table */}
                            <Card className="lg:col-span-3">
                                <CardHeader>
                                    <CardTitle>Performance Comparison</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <Table>
                                        <TableHeader>
                                            <TableRow>
                                                <TableHead>Strategy</TableHead>
                                                <TableHead>Mean Equity</TableHead>
                                                <TableHead>Median Equity</TableHead>
                                                <TableHead>Median DD</TableHead>
                                                <TableHead>Profitable %</TableHead>
                                            </TableRow>
                                        </TableHeader>
                                        <TableBody>
                                            {[
                                                { name: "Single Entry", data: meResult.one_trade },
                                                { name: "Double Entry", data: meResult.two_trades },
                                                { name: "Triple Entry", data: meResult.three_trades }
                                            ].map((row) => (
                                                <TableRow key={row.name}>
                                                    <TableCell className="font-medium">{row.name}</TableCell>
                                                    <TableCell className={row.data.mean_equity > 1000 ? "text-green-600" : "text-red-600"}>
                                                        ${row.data.mean_equity.toFixed(2)}
                                                    </TableCell>
                                                    <TableCell>${row.data.median_equity.toFixed(2)}</TableCell>
                                                    <TableCell className="text-red-600">{row.data.median_drawdown.toFixed(2)}%</TableCell>
                                                    <TableCell>{row.data.profitable_pct.toFixed(1)}%</TableCell>
                                                </TableRow>
                                            ))}
                                        </TableBody>
                                    </Table>
                                </CardContent>
                            </Card>

                            {/* Comparison Chart */}
                            <Card className="lg:col-span-3 h-[500px] flex flex-col">
                                <CardHeader>
                                    <CardTitle>Mean Equity Curves (%)</CardTitle>
                                    <CardDescription>Percentage Return relative to Initial Balance</CardDescription>
                                </CardHeader>
                                <CardContent className="flex-1 min-h-0">
                                    <ResponsiveContainer width="100%" height="100%">
                                        <LineChart
                                            data={meResult.one_trade.equity_curve.map((val, i) => ({
                                                i,
                                                one: ((val - 1000) / 1000) * 100,
                                                two: ((meResult.two_trades.equity_curve[i] - 1000) / 1000) * 100,
                                                three: ((meResult.three_trades.equity_curve[i] - 1000) / 1000) * 100
                                            }))}
                                        >
                                            <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
                                            <XAxis
                                                dataKey="i"
                                                label={{ value: 'Executions', position: 'insideBottomRight', offset: -5 }}
                                            />
                                            <YAxis
                                                label={{ value: 'Return (%)', angle: -90, position: 'insideLeft' }}
                                                domain={['auto', 'auto']}
                                            />
                                            <Tooltip formatter={(value: number) => [`${value.toFixed(2)}%`]} />
                                            <Legend verticalAlign="top"/>
                                            <Line type="monotone" dataKey="one" name="Single Entry" stroke="#ef4444" dot={false} strokeWidth={2} />
                                            <Line type="monotone" dataKey="two" name="Double Entry" stroke="#3b82f6" dot={false} strokeWidth={2} />
                                            <Line type="monotone" dataKey="three" name="Triple Entry" stroke="#22c55e" dot={false} strokeWidth={2} />
                                        </LineChart>
                                    </ResponsiveContainer>
                                </CardContent>
                            </Card>
                        </div>
                    )}
                </TabsContent>
            </Tabs>
        </div>
    )
}




function BoxPlotBar(props: any) {
    const { x, y, width, height, payload } = props;

    // Support multiple naming conventions
    // Consecutive Losing: min_losses
    // Random Win Rate: min_val
    const getVal = (key: string) => {
        if (payload[key] !== undefined) return payload[key];
        if (payload[`${key}_losses`] !== undefined) return payload[`${key}_losses`];
        if (payload[`${key}_val`] !== undefined) return payload[`${key}_val`];
        return undefined;
    }

    const minVal = getVal('min');
    const q1Val = getVal('q1');
    const medianVal = getVal('median');
    const q3Val = getVal('q3');
    const maxVal = getVal('max');

    // Safety check
    if (minVal === undefined) return null;

    // Derived scale logic
    // We assume the bar starts at 0?
    // For Consecutive Losses: Yes, 0 is bottom.
    // For Drawdown: 0 is bottom? Or 100? DD% is 0-100.
    // For Equity: 0 is bottom.
    // The chart passed 'y' is the top of the bar (value MAX) and y+height is bottom (value 0)
    // ONLY IF the bar represents value from 0 to MAX.
    // In Recharts, if we use a composed chart with a bar, the bar's "value" is usually the top.

    // Wait, for Drawdown Box Plot, the "Bar" dataKey should be the MAX value to ensure the SVG area covers the range?
    // Actually, Recharts custom shape receives x, y, width, height based on the dataKey value.
    // If dataKey="max_losses", then height corresponds to max_losses.
    // So 0 is at y + height.
    // This logic holds for "positive" values starting from 0.

    // For Equity, it starts from 0? Yes.

    const barMax = maxVal;
    if (barMax === 0) return null; // Avoid division by zero

    const pixelsPerUnit = height / barMax;
    const zeroY = y + height;

    const getPixel = (val: number) => zeroY - (val * pixelsPerUnit);

    const minP = getPixel(minVal);
    const q1P = getPixel(q1Val);
    const medianP = getPixel(medianVal);
    const q3P = getPixel(q3Val);
    const maxP = getPixel(maxVal); // Should equal y IF barMax matches the chart's value for this bar

    const center = x + width / 2;
    // Box width - slightly narrower than the slot
    const boxWidth = width * 0.5;

    const strokeColor = "currentColor"; // Use text color for outline
    // Dynamic fill based on Win Rate if available, else usage dict?
    // For Random Win Rate, we don't have a single win rate per box plot.
    let boxFill = "#8884d8"; // Default

    if (payload.win_rate !== undefined) {
         boxFill = payload.win_rate < 0.4 ? "#ef4444" : // Red-500
                   payload.win_rate < 0.6 ? "#3b82f6" : // Blue-500
                   "#22c55e"; // Green-500
    } else {
        // Just blue/green generic
        boxFill = "#3b82f6";
    }

    return (
        <g>
            {/* Whiskers (Min to Q1) and (Q3 to Max) */}
            <line x1={center} y1={minP} x2={center} y2={q1P} stroke={strokeColor} strokeWidth={2} />
            <line x1={center} y1={q3P} x2={center} y2={maxP} stroke={strokeColor} strokeWidth={2} />

            {/* Caps */}
            <line x1={center - boxWidth/2} y1={minP} x2={center + boxWidth/2} y2={minP} stroke={strokeColor} strokeWidth={2} />
            <line x1={center - boxWidth/2} y1={maxP} x2={center + boxWidth/2} y2={maxP} stroke={strokeColor} strokeWidth={2} />

            {/* Box (Q1 to Q3) */}
            <rect
                x={center - boxWidth/2}
                y={q3P}
                width={boxWidth}
                height={Math.max(1, Math.abs(q1P - q3P))}
                fill={boxFill}
                stroke={strokeColor}
                strokeWidth={2}
                fillOpacity={0.6}
            />

            {/* Median Line */}
            <line x1={center - boxWidth/2} y1={medianP} x2={center + boxWidth/2} y2={medianP} stroke={strokeColor} strokeWidth={3} />
        </g>
    );
}


function CustomBoxPlotTooltip({ active, payload, label }: any) {
    if (active && payload && payload.length) {
        // The payload usually comes from the Bar, so payload[0].payload is the full data object (DistributionStats)
        const data = payload[0].payload;
        return (
            <div className="bg-slate-800 border border-slate-700 p-3 rounded shadow-lg text-slate-100 text-sm">
                <p className="font-bold mb-2 underline whitespace-nowrap">{label || "Statistics"}</p>
                <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                    <span>Max:</span>
                    <span className="font-mono text-right text-emerald-400">{data.max_val?.toFixed(2)}</span>

                    <span>Mean:</span>
                    <span className="font-mono text-right text-blue-400">{data.mean_val?.toFixed(2)}</span>

                    <span>Median:</span>
                    <span className="font-mono text-right text-yellow-400">{data.median_val?.toFixed(2)}</span>

                    <span>Min:</span>
                    <span className="font-mono text-right text-red-400">{data.min_val?.toFixed(2)}</span>
                </div>
            </div>
        );
    }
    return null;
}

function ProfitTargetHeatmap({ data }: { data: ProfitTargetResult[] }) {
    // 1. Extract unique Axes
    const rrrs = Array.from(new Set(data.map(d => d.rrr))).sort((a, b) => a - b)
    const risks = Array.from(new Set(data.map(d => d.risk_pct))).sort((a, b) => a - b) // Sort Ascending?

    // 2. Build Lookup
    const lookup = new Map<string, number>()
    data.forEach(d => {
        lookup.set(`${d.rrr}-${d.risk_pct}`, d.success_rate)
    })

    // Colors
    // 0 -> Light Yellow (#ffffd9)
    // 1 -> Dark Blue (#081d58)

    const getColor = (rate: number) => {
        if (rate < 0.5) {
            // Interp between Yellow and Teal
            // Pale Yellow: rgb(255, 255, 204)
            // Teal: rgb(65, 182, 196)
            const t = rate * 2;
            const r = Math.round(255 + (65 - 255) * t)
            const g = Math.round(255 + (182 - 255) * t)
            const b = Math.round(204 + (196 - 204) * t)
            return `rgb(${r}, ${g}, ${b})`
        } else {
            // Interp between Teal and Dark Blue
            // Teal: rgb(65, 182, 196)
            // Dark Blue: rgb(37, 52, 148)
            const t = (rate - 0.5) * 2;
            const r = Math.round(65 + (37 - 65) * t)
            const g = Math.round(182 + (52 - 182) * t)
            const b = Math.round(196 + (148 - 196) * t)
            return `rgb(${r}, ${g}, ${b})`
        }
    }

    // Text Color
    const getTextColor = (rate: number) => {
        return rate > 0.5 ? '#fff' : '#000'
    }

    return (
        <div className="w-full h-full overflow-auto flex flex-col items-center">

            <div className="grid gap-1" style={{
                gridTemplateColumns: `auto repeat(${rrrs.length}, minmax(40px, 1fr))`,
            }}>
                {/* Header Row: RRR */}
                <div className="font-bold text-xs text-muted-foreground text-right pr-2">R \ RRR</div>
                {rrrs.map(r => (
                    <div key={r} className="font-bold text-xs text-center text-muted-foreground pb-1">
                        {r.toFixed(1)}
                    </div>
                ))}

                {/* Rows: Risk */}
                {risks.map(risk => (
                    <React.Fragment key={`row-${risk}`}>
                        {/* Row Label */}
                        <div className="font-bold text-xs text-muted-foreground text-right pr-2 flex items-center justify-end">
                            {risk.toFixed(1)}%
                        </div>

                        {/* Cells */}
                        {rrrs.map(rrr => {
                            const val = lookup.get(`${rrr}-${risk}`) ?? 0
                            return (
                                <div
                                    key={`${rrr}-${risk}`}
                                    className="h-8 flex items-center justify-center text-[10px] font-medium border border-transparent hover:border-black/20"
                                    style={{
                                        backgroundColor: getColor(val),
                                        color: getTextColor(val)
                                    }}
                                    title={`RRR: ${rrr}, Risk: ${risk}%, Success: ${(val * 100).toFixed(1)}%`}
                                >
                                    {(val * 100).toFixed(1)}%
                                </div>
                            )
                        })}
                    </React.Fragment>
                ))}
            </div>

            {/* Axis Label Bottom */}
            <div className="mt-2 text-sm font-semibold text-muted-foreground">Reward-Risk Ratio</div>
        </div>
    )
}

