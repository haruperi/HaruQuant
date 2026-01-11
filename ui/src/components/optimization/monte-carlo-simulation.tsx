"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { Zap } from "lucide-react"
import { optimizationApi, type MonteCarloRequest, type MonteCarloResponse, type SimulationType } from "@/lib/api/optimization"
import { strategyApi, type Backtest } from "@/lib/api/strategies"
import { useToast } from "@/components/ui/use-toast"

export function MonteCarloSimulation() {
    const { toast } = useToast()
    const [backtestId, setBacktestId] = useState<string>("")
    const [runs, setRuns] = useState<number>(1000)
    const [method, setMethod] = useState<SimulationType>("bootstrap")
    const [result, setResult] = useState<MonteCarloResponse | null>(null)
    const [isRunning, setIsRunning] = useState(false)
    const [backtests, setBacktests] = useState<Backtest[]>([])
    const [loadingBacktests, setLoadingBacktests] = useState(false)

    // Fetch backtests on mount
    useEffect(() => {
        const fetchBacktests = async () => {
            try {
                setLoadingBacktests(true)
                const allBacktests = await strategyApi.listAllBacktests(1000)
                // Filter to only backtests with an alias
                const backtestsWithAlias = allBacktests.filter(bt => bt.alias && bt.alias.trim() !== '')
                setBacktests(backtestsWithAlias)
            } catch (err) {
                console.error('Failed to fetch backtests:', err)
                toast({
                    title: "Error",
                    description: "Failed to load backtests.",
                    variant: "destructive",
                })
            } finally {
                setLoadingBacktests(false)
            }
        }

        fetchBacktests()
    }, [toast])

    const handleRun = async () => {
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

            toast({
                title: "Monte Carlo Simulation Started",
                description: `Running ${runs} simulations...`,
            })

            // Poll for results (simplified - in production would use WebSocket)
            const simulationId = response.simulation_id
            const pollResults = async () => {
                const mcResults = await optimizationApi.getMonteCarloResults(simulationId)
                setResult(mcResults)
                setIsRunning(false)

                toast({
                    title: "Simulation Complete",
                    description: "Monte Carlo analysis finished successfully.",
                })
            }

            // Wait a moment then fetch results
            setTimeout(pollResults, 3000)

        } catch (err) {
            console.error("Failed to run Monte Carlo simulation:", err)
            toast({
                title: "Error",
                description: "Failed to run Monte Carlo simulation.",
                variant: "destructive",
            })
            setIsRunning(false)
        }
    }

    return (
        <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                 {/* Config */}
                 <Card className="h-fit">
                    <CardHeader>
                        <CardTitle>Simulation Settings</CardTitle>
                        <CardDescription>Stress test via randomization</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="space-y-2">
                            <Label>Backtest</Label>
                            <Select value={backtestId} onValueChange={setBacktestId} disabled={loadingBacktests || backtests.length === 0}>
                                <SelectTrigger className="h-9">
                                    <SelectValue placeholder={
                                        loadingBacktests ? "Loading backtests..." :
                                        backtests.length === 0 ? "No backtests with aliases found" :
                                        "Select a backtest"
                                    } />
                                </SelectTrigger>
                                <SelectContent>
                                    {backtests.map((bt) => (
                                        <SelectItem key={bt.backtest_id} value={bt.backtest_id.toString()}>
                                            {bt.alias}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                            <p className="text-xs text-muted-foreground">
                                {backtests.length === 0 && !loadingBacktests ?
                                    "Run a backtest and add an alias to it first" :
                                    "Select the backtest to simulate"
                                }
                            </p>
                        </div>

                        <div className="space-y-2">
                            <Label>Number of Simulations</Label>
                            <Select value={runs.toString()} onValueChange={(v) => setRuns(parseInt(v))}>
                                <SelectTrigger className="h-9">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="100">100 Runs</SelectItem>
                                    <SelectItem value="500">500 Runs</SelectItem>
                                    <SelectItem value="1000">1,000 Runs</SelectItem>
                                    <SelectItem value="5000">5,000 Runs</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        <div className="space-y-2">
                            <Label>Method</Label>
                            <Select value={method} onValueChange={(v) => setMethod(v as SimulationType)}>
                                <SelectTrigger className="h-9">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="bootstrap">Bootstrap (Resample)</SelectItem>
                                    <SelectItem value="shuffle_trades">Shuffle Trades</SelectItem>
                                    <SelectItem value="resample_returns">Resample Returns</SelectItem>
                                </SelectContent>
                            </Select>
                            <p className="text-xs text-muted-foreground">
                                {method === 'bootstrap' && "Standard resampling with replacement. Preserves trade distribution."}
                                {method === 'shuffle_trades' && "Shuffles trade order to break serial correlation."}
                                {method === 'resample_returns' && "Resamples returns with replacement."}
                            </p>
                        </div>

                        <Button
                            className="w-full"
                            variant="secondary"
                            onClick={handleRun}
                            disabled={isRunning || !backtestId || loadingBacktests || backtests.length === 0}
                        >
                            {isRunning ? "Simulating..." : (
                                <>
                                    <Zap className="mr-2 h-4 w-4" />
                                    Run Simulation
                                </>
                            )}
                        </Button>
                    </CardContent>
                </Card>

                {/* Results */}
                <Card className="md:col-span-2 min-h-[400px]">
                    <CardHeader>
                        <CardTitle>Simulation Results</CardTitle>
                        <CardDescription>
                            {result ? `Based on ${result.num_simulations} simulations` : "Confidence Intervals and Risk Metrics"}
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                         {result ? (
                             <div className="space-y-6">
                                {/* Key Metrics */}
                                <div className="grid grid-cols-3 gap-4 text-center">
                                    <div className="p-4 rounded border bg-card/50">
                                        <div className="text-xs text-muted-foreground">Original Return</div>
                                        <div className="text-xl font-bold font-mono text-emerald-500">
                                            {result.original_return.toFixed(2)}%
                                        </div>
                                    </div>
                                    <div className="p-4 rounded border bg-card/50">
                                        <div className="text-xs text-muted-foreground">Mean Simulated</div>
                                        <div className="text-xl font-bold font-mono">
                                            {result.mean_return.toFixed(2)}%
                                        </div>
                                    </div>
                                    <div className="p-4 rounded border bg-card/50">
                                        <div className="text-xs text-muted-foreground">Probability of Profit</div>
                                        <div className="text-xl font-bold font-mono text-emerald-500">
                                            {result.probability_of_profit.toFixed(1)}%
                                        </div>
                                    </div>
                                </div>

                                {/* Confidence Intervals */}
                                <div className="space-y-3">
                                    <h4 className="text-sm font-semibold">Confidence Intervals</h4>
                                    <div className="grid grid-cols-2 gap-4 text-sm">
                                        <div className="p-3 rounded border bg-card/30">
                                            <div className="text-muted-foreground mb-1">95% CI</div>
                                            <div className="font-mono">
                                                {result.ci_95_lower.toFixed(2)}% to {result.ci_95_upper.toFixed(2)}%
                                            </div>
                                        </div>
                                        <div className="p-3 rounded border bg-card/30">
                                            <div className="text-muted-foreground mb-1">99% CI</div>
                                            <div className="font-mono">
                                                {result.ci_99_lower.toFixed(2)}% to {result.ci_99_upper.toFixed(2)}%
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                {/* Risk Metrics */}
                                <div className="space-y-3">
                                    <h4 className="text-sm font-semibold">Risk Metrics</h4>
                                    <div className="grid grid-cols-3 gap-4 text-sm">
                                        <div className="p-3 rounded border bg-card/30">
                                            <div className="text-muted-foreground mb-1">Std Dev</div>
                                            <div className="font-mono">{result.std_return.toFixed(2)}%</div>
                                        </div>
                                        <div className="p-3 rounded border bg-card/30">
                                            <div className="text-muted-foreground mb-1">Expected Shortfall (95%)</div>
                                            <div className="font-mono text-red-500">{result.expected_shortfall_95.toFixed(2)}%</div>
                                        </div>
                                        <div className="p-3 rounded border bg-card/30">
                                            <div className="text-muted-foreground mb-1">Probability of Ruin</div>
                                            <div className="font-mono text-red-500">{result.probability_of_ruin.toFixed(2)}%</div>
                                        </div>
                                    </div>
                                </div>

                                {/* Percentiles */}
                                <div className="space-y-3">
                                    <h4 className="text-sm font-semibold">Percentile Distribution</h4>
                                    <div className="grid grid-cols-5 gap-2 text-xs text-center">
                                        <div className="p-2 rounded border bg-card/30">
                                            <div className="text-muted-foreground mb-1">5th</div>
                                            <div className="font-mono">{result.percentile_5.toFixed(1)}%</div>
                                        </div>
                                        <div className="p-2 rounded border bg-card/30">
                                            <div className="text-muted-foreground mb-1">25th</div>
                                            <div className="font-mono">{result.percentile_25.toFixed(1)}%</div>
                                        </div>
                                        <div className="p-2 rounded border bg-card/30">
                                            <div className="text-muted-foreground mb-1">50th</div>
                                            <div className="font-mono">{result.percentile_50.toFixed(1)}%</div>
                                        </div>
                                        <div className="p-2 rounded border bg-card/30">
                                            <div className="text-muted-foreground mb-1">75th</div>
                                            <div className="font-mono">{result.percentile_75.toFixed(1)}%</div>
                                        </div>
                                        <div className="p-2 rounded border bg-card/30">
                                            <div className="text-muted-foreground mb-1">95th</div>
                                            <div className="font-mono">{result.percentile_95.toFixed(1)}%</div>
                                        </div>
                                    </div>
                                </div>
                             </div>
                         ) : (
                            <div className="h-full flex flex-col items-center justify-center text-muted-foreground space-y-4 py-20">
                                <div className="p-4 bg-muted/50 rounded-full">
                                    <Zap className="h-8 w-8" />
                                </div>
                                <p>{isRunning ? "Running simulation..." : "Run simulation to view confidence intervals and risk metrics"}</p>
                            </div>
                         )}
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}
