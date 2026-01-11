"use client"

import { useState, useMemo, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { Play, AlertCircle, CalendarIcon, Plus, Trash2, XCircle } from "lucide-react"
import { optimizationApi, type WalkForwardRequest, type ParameterRange } from "@/lib/api/optimization"
import { useWalkForward } from "@/lib/hooks/use-optimization"
import { useToast } from "@/components/ui/use-toast"
import { useStrategies } from "@/lib/use-strategies"
import { strategyApi } from "@/lib/api/strategies"
import { Calendar } from "@/components/ui/calendar"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { format } from "date-fns"
import { cn } from "@/lib/utils"

interface ParameterRangeExt extends ParameterRange {
  id: string
  current: number
}

export function WalkForwardAnalysis() {
    const { toast } = useToast()
    const { strategies, loading: strategiesLoading } = useStrategies()

    const [optimizationId, setOptimizationId] = useState<number | null>(null)
    const [isRunning, setIsRunning] = useState(false)

    // Strategy and configuration (matching optimization-config.tsx)
    const [strategy, setStrategy] = useState<string>("")
    const [symbol, setSymbol] = useState<string>("")
    const [timeframe, setTimeframe] = useState<string>("H1")
    const [dataSource, setDataSource] = useState<string>("mt5")
    const [startDate, setStartDate] = useState<Date | undefined>(new Date(new Date().setFullYear(new Date().getFullYear() - 1)))
    const [endDate, setEndDate] = useState<Date | undefined>(new Date())
    const [initialCapital, setInitialCapital] = useState<number>(10000)

    // Walk-forward specific
    const [trainPeriod, setTrainPeriod] = useState<number>(1000)
    const [testPeriod, setTestPeriod] = useState<number>(500)
    const [objective, setObjective] = useState<string>("sharpe")

    // Parameters
    const [parameters, setParameters] = useState<ParameterRangeExt[]>([])
    const [availableParams, setAvailableParams] = useState<string[]>([])
    const [loadingParams, setLoadingParams] = useState<boolean>(false)

    // Use walk-forward hook
    const { windows, loading, error } = useWalkForward(optimizationId)

    // Fetch strategy parameters when strategy changes
    useEffect(() => {
        const fetchStrategyParameters = async () => {
            if (!strategy) {
                setParameters([])
                setAvailableParams([])
                return
            }

            setLoadingParams(true)

            try {
                const selectedStrategy = strategies.find(s => s.id.toString() === strategy)

                if (!selectedStrategy || !selectedStrategy.active_version_id) {
                    setParameters([])
                    setAvailableParams([])
                    setLoadingParams(false)
                    return
                }

                const versionCode = await strategyApi.getVersionCode(
                    selectedStrategy.id,
                    selectedStrategy.active_version_id
                )

                const strategyParams = versionCode.parameters || {}
                const paramNames = Object.keys(strategyParams)

                setAvailableParams(paramNames)

                // Initialize parameter ranges with sensible defaults
                const initialParams: ParameterRangeExt[] = paramNames.map((name, index) => {
                    const value = strategyParams[name]
                    const isInt = Number.isInteger(value)

                    return {
                        id: `param-${index}`,
                        name,
                        current: value,
                        min: isInt ? Math.floor(value * 0.5) : value * 0.5,
                        max: isInt ? Math.ceil(value * 1.5) : value * 1.5,
                        step: isInt ? 1 : 0.1,
                        type: isInt ? 'int' : 'float'
                    }
                })

                setParameters(initialParams)
            } catch (err) {
                console.error('Failed to fetch strategy parameters:', err)
                toast({
                    title: "Error",
                    description: "Failed to load strategy parameters.",
                    variant: "destructive",
                })
            } finally {
                setLoadingParams(false)
            }
        }

        fetchStrategyParameters()
    }, [strategy, strategies, toast])

    const handleRun = async () => {
        if (!strategy) {
            toast({
                title: "Error",
                description: "Please select a strategy.",
                variant: "destructive",
            })
            return
        }

        if (!symbol) {
            toast({
                title: "Error",
                description: "Please enter a symbol.",
                variant: "destructive",
            })
            return
        }

        if (!startDate || !endDate) {
            toast({
                title: "Error",
                description: "Please select start and end dates.",
                variant: "destructive",
            })
            return
        }

        try {
            setIsRunning(true)

            const request: WalkForwardRequest = {
                strategy_id: parseInt(strategy),
                symbol,
                timeframe,
                start_date: format(startDate, 'yyyy-MM-dd'),
                end_date: format(endDate, 'yyyy-MM-dd'),
                train_period: trainPeriod,
                test_period: testPeriod,
                parameters: parameters.map(p => ({
                    name: p.name,
                    min: p.min,
                    max: p.max,
                    step: p.step,
                    type: p.type
                })),
                objective,
                n_jobs: -1,
                initial_capital: initialCapital,
            }

            const response = await optimizationApi.startWalkForward(request)
            setOptimizationId(response.optimization_id)

            toast({
                title: "Walk-Forward Analysis Started",
                description: "The analysis is running in the background.",
            })
        } catch (err) {
            console.error("Failed to start walk-forward analysis:", err)
            toast({
                title: "Error",
                description: "Failed to start walk-forward analysis.",
                variant: "destructive",
            })
        } finally {
            setIsRunning(false)
        }
    }

    const handleCancel = async () => {
        if (!optimizationId) return

        try {
            await optimizationApi.cancelOptimization(optimizationId)
            setIsRunning(false)
            setOptimizationId(null)
            toast({
                title: "Analysis Cancelled",
                description: "The walk-forward analysis has been cancelled.",
            })
        } catch (err) {
            console.error("Failed to cancel walk-forward analysis:", err)
            toast({
                title: "Error",
                description: "Failed to cancel the analysis.",
                variant: "destructive",
            })
        }
    }

    const addParameter = () => {
        const unusedParams = availableParams.filter(
            param => !parameters.some(p => p.name === param)
        )

        if (unusedParams.length === 0) {
            toast({
                title: "No Available Parameters",
                description: "All strategy parameters have been added.",
                variant: "destructive",
            })
            return
        }

        const newParam: ParameterRangeExt = {
            id: `param-${Date.now()}`,
            name: unusedParams[0],
            current: 10,
            min: 1,
            max: 100,
            step: 1,
            type: 'int'
        }

        setParameters([...parameters, newParam])
    }

    const removeParameter = (id: string) => {
        setParameters(parameters.filter(p => p.id !== id))
    }

    const updateParameter = (id: string, field: keyof ParameterRangeExt, value: any) => {
        setParameters(parameters.map(p =>
            p.id === id ? { ...p, [field]: value } : p
        ))
    }

    // Transform windows data for chart
    const chartData = useMemo(() => {
        if (!windows || windows.length === 0) return []

        return windows.map((w) => ({
            period: `Window ${w.window_number}`,
            inSample: w.train_return,
            outOfSample: w.test_return,
        }))
    }, [windows])

    // Calculate robustness score
    const robustnessScore = useMemo(() => {
        if (!windows || windows.length === 0) return null

        const validWindows = windows.filter(w => w.train_return && w.test_return && w.train_return !== 0)
        if (validWindows.length === 0) return null

        const avgRatio = validWindows.reduce((acc, w) => {
            return acc + (w.test_return / w.train_return)
        }, 0) / validWindows.length

        return (avgRatio * 100).toFixed(1)
    }, [windows])

    return (
        <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Configuration Panel */}
                <Card className="h-fit">
                    <CardHeader>
                        <CardTitle>WFA Configuration</CardTitle>
                        <CardDescription>Configure Walk-Forward Validation</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        {/* Strategy Selection */}
                        <div className="space-y-2">
                            <Label>Strategy</Label>
                            <Select value={strategy} onValueChange={setStrategy} disabled={strategiesLoading}>
                                <SelectTrigger className="h-9">
                                    <SelectValue placeholder={strategiesLoading ? "Loading strategies..." : "Select strategy"} />
                                </SelectTrigger>
                                <SelectContent>
                                    {strategies.map((s) => (
                                        <SelectItem key={s.id} value={s.id.toString()}>
                                            {s.name}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>

                        {/* Symbol and Timeframe */}
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label>Symbol</Label>
                                <Input
                                    placeholder="e.g., EURUSD"
                                    value={symbol}
                                    onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                                    className="h-9 font-mono"
                                />
                            </div>
                            <div className="space-y-2">
                                <Label>Timeframe</Label>
                                <Select value={timeframe} onValueChange={setTimeframe}>
                                    <SelectTrigger className="h-9">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="M1">M1</SelectItem>
                                        <SelectItem value="M5">M5</SelectItem>
                                        <SelectItem value="M15">M15</SelectItem>
                                        <SelectItem value="M30">M30</SelectItem>
                                        <SelectItem value="H1">H1</SelectItem>
                                        <SelectItem value="H4">H4</SelectItem>
                                        <SelectItem value="D1">D1</SelectItem>
                                        <SelectItem value="W1">W1</SelectItem>
                                        <SelectItem value="MN1">MN1</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>

                        {/* Date Range */}
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label>Start Date</Label>
                                <Popover>
                                    <PopoverTrigger asChild>
                                        <Button
                                            variant="outline"
                                            className={cn(
                                                "h-9 w-full justify-start text-left font-normal",
                                                !startDate && "text-muted-foreground"
                                            )}
                                        >
                                            <CalendarIcon className="mr-2 h-4 w-4" />
                                            {startDate ? format(startDate, "PPP") : <span>Pick a date</span>}
                                        </Button>
                                    </PopoverTrigger>
                                    <PopoverContent className="w-auto p-0" align="start">
                                        <Calendar
                                            mode="single"
                                            selected={startDate}
                                            onSelect={setStartDate}
                                            initialFocus
                                        />
                                    </PopoverContent>
                                </Popover>
                            </div>

                            <div className="space-y-2">
                                <Label>End Date</Label>
                                <Popover>
                                    <PopoverTrigger asChild>
                                        <Button
                                            variant="outline"
                                            className={cn(
                                                "h-9 w-full justify-start text-left font-normal",
                                                !endDate && "text-muted-foreground"
                                            )}
                                        >
                                            <CalendarIcon className="mr-2 h-4 w-4" />
                                            {endDate ? format(endDate, "PPP") : <span>Pick a date</span>}
                                        </Button>
                                    </PopoverTrigger>
                                    <PopoverContent className="w-auto p-0" align="start">
                                        <Calendar
                                            mode="single"
                                            selected={endDate}
                                            onSelect={setEndDate}
                                            initialFocus
                                        />
                                    </PopoverContent>
                                </Popover>
                            </div>
                        </div>

                        {/* Walk-Forward Specific Settings */}
                        <div className="space-y-2">
                            <Label>Train Period (bars)</Label>
                            <Input
                                type="number"
                                value={trainPeriod}
                                onChange={(e) => setTrainPeriod(parseInt(e.target.value))}
                                className="h-9 font-mono"
                            />
                        </div>

                        <div className="space-y-2">
                            <Label>Test Period (bars)</Label>
                            <Input
                                type="number"
                                value={testPeriod}
                                onChange={(e) => setTestPeriod(parseInt(e.target.value))}
                                className="h-9 font-mono"
                            />
                        </div>

                        <div className="space-y-2">
                            <Label>Initial Capital</Label>
                            <Input
                                type="number"
                                value={initialCapital}
                                onChange={(e) => setInitialCapital(parseFloat(e.target.value))}
                                className="h-9 font-mono"
                            />
                        </div>

                        <div className="space-y-2">
                            <Label>Objective</Label>
                            <Select value={objective} onValueChange={setObjective}>
                                <SelectTrigger className="h-9">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="sharpe">Sharpe Ratio</SelectItem>
                                    <SelectItem value="sortino">Sortino Ratio</SelectItem>
                                    <SelectItem value="calmar">Calmar Ratio</SelectItem>
                                    <SelectItem value="total_return">Total Return</SelectItem>
                                    <SelectItem value="profit_factor">Profit Factor</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        {/* Parameters Section */}
                        <div className="space-y-2 pt-4 border-t">
                            <div className="flex items-center justify-between">
                                <div className="space-y-1">
                                    <Label>Parameters to Optimize</Label>
                                    <p className="text-xs text-muted-foreground">Optional: Leave empty to test default parameters</p>
                                </div>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={addParameter}
                                    disabled={loadingParams || parameters.length >= availableParams.length}
                                >
                                    <Plus className="h-4 w-4 mr-1" />
                                    Add
                                </Button>
                            </div>

                            <div className="space-y-2 max-h-[300px] overflow-y-auto">
                                {parameters.map((param) => (
                                    <Card key={param.id} className="p-3">
                                        <div className="space-y-2">
                                            <div className="flex items-center justify-between">
                                                <Select
                                                    value={param.name}
                                                    onValueChange={(value) => updateParameter(param.id, 'name', value)}
                                                >
                                                    <SelectTrigger className="h-8 w-[140px]">
                                                        <SelectValue />
                                                    </SelectTrigger>
                                                    <SelectContent>
                                                        {availableParams.map((p) => (
                                                            <SelectItem key={p} value={p}>{p}</SelectItem>
                                                        ))}
                                                    </SelectContent>
                                                </Select>
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() => removeParameter(param.id)}
                                                >
                                                    <Trash2 className="h-4 w-4" />
                                                </Button>
                                            </div>

                                            <div className="grid grid-cols-3 gap-2">
                                                <div>
                                                    <Label className="text-xs">Min</Label>
                                                    <Input
                                                        type="number"
                                                        value={param.min}
                                                        onChange={(e) => updateParameter(param.id, 'min', parseFloat(e.target.value))}
                                                        className="h-8 font-mono text-sm"
                                                        step={param.type === 'int' ? 1 : 0.1}
                                                    />
                                                </div>
                                                <div>
                                                    <Label className="text-xs">Max</Label>
                                                    <Input
                                                        type="number"
                                                        value={param.max}
                                                        onChange={(e) => updateParameter(param.id, 'max', parseFloat(e.target.value))}
                                                        className="h-8 font-mono text-sm"
                                                        step={param.type === 'int' ? 1 : 0.1}
                                                    />
                                                </div>
                                                <div>
                                                    <Label className="text-xs">Step</Label>
                                                    <Input
                                                        type="number"
                                                        value={param.step}
                                                        onChange={(e) => updateParameter(param.id, 'step', parseFloat(e.target.value))}
                                                        className="h-8 font-mono text-sm"
                                                        step={param.type === 'int' ? 1 : 0.1}
                                                    />
                                                </div>
                                            </div>
                                        </div>
                                    </Card>
                                ))}
                            </div>
                        </div>

                        <div className="flex gap-2">
                            {isRunning ? (
                                <Button
                                    className="flex-1"
                                    variant="destructive"
                                    onClick={handleCancel}
                                >
                                    <XCircle className="mr-2 h-4 w-4" />
                                    Cancel Analysis
                                </Button>
                            ) : (
                                <Button
                                    className="flex-1"
                                    onClick={handleRun}
                                    disabled={loading || !strategy || !symbol}
                                >
                                    {loading ? "Running Analysis..." : (
                                        <>
                                            <Play className="mr-2 h-4 w-4" />
                                            Run WFA
                                        </>
                                    )}
                                </Button>
                            )}
                        </div>
                    </CardContent>
                </Card>

                {/* Results Panel */}
                <Card className="md:col-span-2 min-h-[400px]">
                    <CardHeader>
                        <CardTitle>Stability Analysis</CardTitle>
                        <CardDescription>
                            In-Sample (Training) vs Out-of-Sample (Validation) Performance
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        {chartData.length > 0 ? (
                            <div className="space-y-6">
                                <div className="flex items-center gap-4 p-4 border rounded-lg bg-card/50">
                                    <div className="space-y-1">
                                        <div className="text-sm text-muted-foreground">OOS Robustness Score</div>
                                        <div className="text-2xl font-bold flex items-center gap-2">
                                            {robustnessScore}%
                                            {robustnessScore && Number(robustnessScore) > 70 ? (
                                                <Badge className="bg-emerald-500 hover:bg-emerald-600">Pass</Badge>
                                            ) : (
                                                <Badge variant="destructive">Fail</Badge>
                                            )}
                                        </div>
                                    </div>
                                    <div className="border-l pl-4 text-sm text-muted-foreground">
                                        {robustnessScore && Number(robustnessScore) > 70
                                            ? "Strategy shows consistent performance in unseen data."
                                            : "Strategy may be overfit. OOS performance drops significantly."}
                                    </div>
                                </div>

                                <div className="h-[300px] w-full">
                                    <ResponsiveContainer width="100%" height="100%">
                                        <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                                            <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                                            <XAxis dataKey="period" />
                                            <YAxis unit="%" />
                                            <Tooltip
                                                contentStyle={{ backgroundColor: "#1e293b", borderColor: "#334155" }}
                                                itemStyle={{ color: "#f8fafc" }}
                                            />
                                            <Legend />
                                            <Bar name="In-Sample" dataKey="inSample" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                                            <Bar name="Out-of-Sample" dataKey="outOfSample" fill="#10b981" radius={[4, 4, 0, 0]} />
                                        </BarChart>
                                    </ResponsiveContainer>
                                </div>

                                {/* Windows Details */}
                                <div className="text-xs text-muted-foreground">
                                    {windows.length} windows analyzed
                                </div>
                            </div>
                        ) : (
                            <div className="h-full flex flex-col items-center justify-center text-muted-foreground space-y-4 py-20">
                                <div className="p-4 bg-muted/50 rounded-full">
                                    <AlertCircle className="h-8 w-8" />
                                </div>
                                <p>{loading ? "Loading results..." : "Run analysis to view stability report"}</p>
                                {error && <p className="text-destructive text-sm">{error}</p>}
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}
