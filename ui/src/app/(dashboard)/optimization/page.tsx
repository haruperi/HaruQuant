"use client"

import { useState } from "react"
import { OptimizationConfig } from "@/components/optimization/optimization-config"
import { OptimizationResults } from "@/components/optimization/optimization-results"
import { WalkForwardAnalysis } from "@/components/optimization/walk-forward-analysis"
import { MonteCarloSimulation } from "@/components/optimization/monte-carlo-simulation"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { Settings2, FlaskConical, LineChart, Zap } from "lucide-react"
import { optimizationApi, type OptimizationRequest, type ParameterRange } from "@/lib/api/optimization"
import { useOptimization } from "@/lib/hooks/use-optimization"
import { useToast } from "@/components/ui/use-toast"

export default function OptimizationPage() {
    const [view, setView] = useState<'config' | 'running' | 'results'>('config')
    const [optimizationId, setOptimizationId] = useState<number | null>(null)
    const { toast } = useToast()

    // Use optimization hook for real-time updates
    const {
        run,
        results,
        progress,
        isConnected,
        loading,
        error,
        cancelOptimization,
    } = useOptimization({
        optimizationId,
        autoConnect: true,
        onProgressUpdate: (progressData) => {
            console.log("Progress update:", progressData)
        },
        onComplete: () => {
            toast({
                title: "Optimization Complete",
                description: "Parameter optimization has finished successfully.",
            })
            setView('results')
        },
    })

    const handleStart = async (config: any) => {
        try {
            console.log("=== Starting Optimization ===")
            console.log("Config:", config)

            // Transform frontend config to API request format
            const parameters: ParameterRange[] = config.parameters.map((p: any) => ({
                name: p.name,
                min: p.start,
                max: p.stop,
                step: p.step,
                type: p.type,
            }))

            const request: OptimizationRequest = {
                strategy_id: parseInt(config.strategy) || 1,
                method: config.method,
                objective: config.objective,
                symbol: config.symbol || "EURUSD",
                timeframe: config.timeframe || "H1",
                start_date: config.startDate || "2023-01-01",
                end_date: config.endDate || "2023-12-31",
                initial_capital: config.initialCapital || 10000,
                data_source: config.dataSource || "mt5",
                parameters,
                n_jobs: config.workers,
                engine_type: "vectorised",
                // Method-specific parameters
                n_iter: config.method === "random" ? config.nIter : undefined,
                n_initial_points: config.method === "bayesian" ? config.nInitialPoints : undefined,
                population_size: config.method === "genetic" ? config.populationSize : undefined,
                generations: config.method === "genetic" ? config.generations : undefined,
            }

            console.log("API Request:", request)

            // Start optimization via API
            const response = await optimizationApi.startOptimization(request)

            console.log("API Response:", response)
            console.log("Optimization ID:", response.optimization_id)

            toast({
                title: "Optimization Started",
                description: `Testing ${response.total_combinations} parameter combinations.`,
            })

            // Set optimization ID to trigger WebSocket connection
            console.log("Setting optimization ID to:", response.optimization_id)
            setOptimizationId(response.optimization_id)
            setView('running')

        } catch (err) {
            console.error("=== Failed to start optimization ===")
            console.error("Error:", err)
            toast({
                title: "Error",
                description: err instanceof Error ? err.message : "Failed to start optimization. Please try again.",
                variant: "destructive",
            })
        }
    }

    const handleCancel = async () => {
        if (optimizationId) {
            try {
                await cancelOptimization()
                toast({
                    title: "Optimization Cancelled",
                    description: "The optimization run has been stopped.",
                })
                setView('config')
            } catch (err) {
                console.error("Failed to cancel optimization:", err)
            }
        }
    }

    const resetState = () => {
        setView('config')
        setOptimizationId(null)
    }

    return (
        <div className="flex flex-col gap-6 p-6">
            {/* Header */}
            <div className="flex items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Optimization</h1>
                    <p className="text-muted-foreground">
                        Advanced tools for parameter tuning, validation, and stress testing.
                    </p>
                </div>
                <Button variant="outline" onClick={resetState}>
                    New Optimization
                </Button>
            </div>

            <Tabs defaultValue="optimization" className="space-y-6">
                <TabsList>
                    <TabsTrigger value="optimization" className="flex items-center gap-2">
                        <FlaskConical className="h-4 w-4" />
                        Parameter Optimization
                    </TabsTrigger>
                    <TabsTrigger value="wfa" className="flex items-center gap-2">
                        <LineChart className="h-4 w-4" />
                        Walk-Forward Analysis
                    </TabsTrigger>
                    <TabsTrigger value="monte-carlo" className="flex items-center gap-2">
                        <Zap className="h-4 w-4" />
                        Monte Carlo
                    </TabsTrigger>
                </TabsList>

                {/* Tab: Parameter Optimization */}
                <TabsContent value="optimization" className="space-y-4">
                    {view === 'config' && (
                        <OptimizationConfig onStart={handleStart} />
                    )}

                    {view === 'running' && (
                        <div className="flex flex-col items-center justify-center h-[60vh] space-y-6 border rounded-lg bg-card/20">
                            <Settings2 className="h-16 w-16 animate-spin text-primary" />
                            <div className="text-center space-y-2">
                                <h3 className="text-xl font-semibold">Optimization in Progress...</h3>
                                <p className="text-muted-foreground">
                                    {run?.optimization_method && `Using ${run.optimization_method} method`}
                                </p>
                            </div>

                            {/* Progress Information */}
                            <div className="w-full max-w-md space-y-3">
                                <div className="flex justify-between text-sm">
                                    <span>Progress:</span>
                                    <span className="font-mono">
                                        {progress.completed} / {progress.total} ({progress.percentage.toFixed(1)}%)
                                    </span>
                                </div>
                                <div className="w-full bg-secondary rounded-full h-2">
                                    <div
                                        className="bg-primary h-2 rounded-full transition-all duration-300"
                                        style={{ width: `${progress.percentage}%` }}
                                    />
                                </div>

                                {/* Best Score */}
                                {progress.bestScore > 0 && (
                                    <div className="flex justify-between text-sm pt-2">
                                        <span>Best Score:</span>
                                        <span className="font-mono font-semibold text-primary">
                                            {progress.bestScore.toFixed(4)}
                                        </span>
                                    </div>
                                )}

                                {/* WebSocket Status */}
                                <div className="flex items-center justify-center gap-2 text-xs text-muted-foreground pt-2">
                                    <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-gray-400'}`} />
                                    {isConnected ? 'Real-time updates active' : 'Connecting...'}
                                </div>

                                {/* Cancel Button */}
                                <div className="pt-4 flex justify-center">
                                    <Button variant="outline" onClick={handleCancel}>
                                        Cancel Optimization
                                    </Button>
                                </div>
                            </div>
                        </div>
                    )}

                    {view === 'results' && (
                        <OptimizationResults
                            run={run}
                            results={results}
                            onBack={resetState}
                        />
                    )}
                </TabsContent>

                {/* Tab: Walk-Forward Analysis */}
                <TabsContent value="wfa">
                    <WalkForwardAnalysis />
                </TabsContent>

                {/* Tab: Monte Carlo */}
                <TabsContent value="monte-carlo">
                     <MonteCarloSimulation />
                </TabsContent>
            </Tabs>
        </div>
    )
}
