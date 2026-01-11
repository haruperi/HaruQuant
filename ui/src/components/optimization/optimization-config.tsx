"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Slider } from "@/components/ui/slider"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Plus, Trash2, Play, Settings2, BarChart2, CalendarIcon, Loader2 } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { useStrategies } from "@/lib/use-strategies"
import { strategyApi } from "@/lib/api/strategies"
import { Calendar } from "@/components/ui/calendar"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { format } from "date-fns"
import { cn } from "@/lib/utils"

interface ParameterRange {
  id: string
  name: string
  current: number  // Current/default value from strategy
  start: number
  stop: number
  step: number
  type: 'int' | 'float'
}

interface OptimizationConfigProps {
  onStart: (config: any) => void
}

export function OptimizationConfig({ onStart }: OptimizationConfigProps) {
  // Fetch strategies from database
  const { strategies, loading: strategiesLoading, error: strategiesError } = useStrategies()

  const [strategy, setStrategy] = useState<string>("")
  const [method, setMethod] = useState<string>("grid")
  const [objective, setObjective] = useState<string>("sharpe")
  const [workers, setWorkers] = useState<number>(4)

  // Data configuration (matching backtest page)
  const [symbol, setSymbol] = useState<string>("")
  const [timeframe, setTimeframe] = useState<string>("H1")
  const [dataSource, setDataSource] = useState<string>("mt5")
  const [startDate, setStartDate] = useState<Date | undefined>(new Date(new Date().setFullYear(new Date().getFullYear() - 1)))
  const [endDate, setEndDate] = useState<Date | undefined>(new Date())
  const [initialCapital, setInitialCapital] = useState<number>(10000)

  // Method-specific settings
  const [nIter, setNIter] = useState<number>(100)
  const [nInitialPoints, setNInitialPoints] = useState<number>(10)
  const [populationSize, setPopulationSize] = useState<number>(50)
  const [generations, setGenerations] = useState<number>(30)

  // Parameter state
  const [parameters, setParameters] = useState<ParameterRange[]>([])
  const [availableParams, setAvailableParams] = useState<string[]>([])
  const [loadingParams, setLoadingParams] = useState<boolean>(false)

  // Fetch strategy parameters when strategy changes
  useEffect(() => {
    const fetchStrategyParameters = async () => {
      if (!strategy) {
        // Clear parameters when no strategy is selected
        setParameters([])
        setAvailableParams([])
        return
      }

      setLoadingParams(true)

      try {
        // Find the selected strategy
        const selectedStrategy = strategies.find(s => s.id.toString() === strategy)

        if (!selectedStrategy || !selectedStrategy.active_version_id) {
          setParameters([])
          setAvailableParams([])
          setLoadingParams(false)
          return
        }

        // Fetch strategy version code
        const versionCode = await strategyApi.getVersionCode(
          selectedStrategy.id,
          selectedStrategy.active_version_id
        )

        // Extract parameters from the version parameters field
        const strategyParams = versionCode.parameters || {}
        const paramNames = Object.keys(strategyParams)

        setAvailableParams(paramNames)

        // Initialize parameter ranges with sensible defaults
        const initialParams: ParameterRange[] = paramNames.map((name, index) => {
          const value = strategyParams[name]
          const isInt = Number.isInteger(value)

          // Set default ranges based on parameter value
          let start = 0
          let stop = 100
          let step = isInt ? 5 : 0.1

          if (typeof value === 'number') {
            // If we have a numeric default, create range around it
            if (value > 0) {
              start = Math.max(1, Math.floor(value * 0.5))
              stop = Math.ceil(value * 2)
              step = isInt ? Math.max(1, Math.floor(value * 0.1)) : value * 0.05
            } else if (value < 0) {
              start = Math.floor(value * 2)
              stop = Math.max(0, Math.ceil(value * 0.5))
              step = isInt ? Math.max(1, Math.floor(Math.abs(value) * 0.1)) : Math.abs(value) * 0.05
            }
          }

          return {
            id: (index + 1).toString(),
            name,
            current: typeof value === 'number' ? value : 0,  // Store current value
            start,
            stop,
            step,
            type: isInt ? 'int' : 'float'
          }
        })

        setParameters(initialParams)
      } catch (error) {
        console.error('Failed to fetch strategy parameters:', error)
        setParameters([])
        setAvailableParams([])
      } finally {
        setLoadingParams(false)
      }
    }

    fetchStrategyParameters()
  }, [strategy, strategies])

  const handleRun = () => {
    onStart({
      strategy,
      method,
      objective,
      workers,
      parameters,
      symbol,
      timeframe,
      dataSource,
      startDate: startDate ? format(startDate, "yyyy-MM-dd") : "",
      endDate: endDate ? format(endDate, "yyyy-MM-dd") : "",
      initialCapital,
      nIter,
      nInitialPoints,
      populationSize,
      generations,
    })
  }

  const removeParameter = (id: string) => {
    setParameters(parameters.filter(p => p.id !== id))
  }

  const addParameter = async (paramName: string) => {
    // Check if parameter already exists
    if (parameters.some(p => p.name === paramName)) {
      return
    }

    const newId = (Math.max(0, ...parameters.map(p => parseInt(p.id))) + 1).toString()

    // Try to get the current value from strategy
    try {
      const selectedStrategy = strategies.find(s => s.id.toString() === strategy)
      if (selectedStrategy && selectedStrategy.active_version_id) {
        const versionCode = await strategyApi.getVersionCode(
          selectedStrategy.id,
          selectedStrategy.active_version_id
        )
        const strategyParams = versionCode.parameters || {}
        const currentValue = strategyParams[paramName]
        const isInt = Number.isInteger(currentValue)

        let start = 0
        let stop = 100
        let step = isInt ? 5 : 0.1

        if (typeof currentValue === 'number' && currentValue > 0) {
          start = Math.max(1, Math.floor(currentValue * 0.5))
          stop = Math.ceil(currentValue * 2)
          step = isInt ? Math.max(1, Math.floor(currentValue * 0.1)) : currentValue * 0.05
        }

        setParameters([...parameters, {
          id: newId,
          name: paramName,
          current: typeof currentValue === 'number' ? currentValue : 0,
          start,
          stop,
          step,
          type: isInt ? 'int' : 'float'
        }])
        return
      }
    } catch (error) {
      console.error('Failed to fetch parameter value:', error)
    }

    // Fallback to defaults
    setParameters([...parameters, {
      id: newId,
      name: paramName,
      current: 0,
      start: 0,
      stop: 100,
      step: 10,
      type: 'int'
    }])
  }

  // Get parameters that can be added (exist in strategy but not in parameter list)
  const getAddableParams = () => {
    const currentParamNames = parameters.map(p => p.name)
    return availableParams.filter(name => !currentParamNames.includes(name))
  }

  const updateParameter = (id: string, field: keyof ParameterRange, value: any) => {
    setParameters(parameters.map(p =>
      p.id === id ? { ...p, [field]: value } : p
    ))
  }

  return (
    <div className="grid gap-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Left Column: Basic Settings */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Strategy & Method</CardTitle>
              <CardDescription>Select optimization target</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Strategy</Label>
                <Select value={strategy} onValueChange={setStrategy}>
                  <SelectTrigger>
                    <SelectValue placeholder={strategiesLoading ? "Loading strategies..." : "Select strategy..."} />
                  </SelectTrigger>
                  <SelectContent>
                    {strategiesLoading && (
                      <SelectItem value="_loading" disabled>Loading strategies...</SelectItem>
                    )}
                    {strategiesError && (
                      <SelectItem value="_error" disabled>Error loading strategies</SelectItem>
                    )}
                    {!strategiesLoading && !strategiesError && strategies.length === 0 && (
                      <SelectItem value="_empty" disabled>No strategies available</SelectItem>
                    )}
                    {!strategiesLoading && !strategiesError && strategies.map((s) => (
                      <SelectItem key={s.id} value={s.id.toString()}>
                        {s.name} {s.active_version ? `(v${s.active_version})` : '(No version)'}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Optimization Method</Label>
                <Select value={method} onValueChange={setMethod}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="grid">Grid Search</SelectItem>
                    <SelectItem value="random">Random Search</SelectItem>
                    <SelectItem value="bayesian">Bayesian Optimization</SelectItem>
                    <SelectItem value="genetic">Genetic Algorithm</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  {method === 'grid' && "Exhaustive search over specified parameter grid."}
                  {method === 'random' && "Randomly samples parameters from defined ranges."}
                  {method === 'bayesian' && "Uses probabilistic model to guide search (Efficient)."}
                  {method === 'genetic' && "Evolves population of parameters over generations."}
                </p>
              </div>

              <div className="space-y-2">
                 <Label>Objective Function</Label>
                 <Select value={objective} onValueChange={setObjective}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="sharpe">Sharpe Ratio</SelectItem>
                    <SelectItem value="sortino">Sortino Ratio</SelectItem>
                    <SelectItem value="calmar">Calmar Ratio</SelectItem>
                    <SelectItem value="profit_factor">Profit Factor</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  {objective === 'sharpe' && "Return per unit of total volatility (risk-adjusted)."}
                  {objective === 'sortino' && "Return per unit of downside volatility (better for asymmetric returns)."}
                  {objective === 'calmar' && "Return per unit of maximum drawdown."}
                  {objective === 'profit_factor' && "Ratio of gross profit to gross loss."}
                </p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Data Configuration</CardTitle>
              <CardDescription>Backtest data settings</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="symbol">Symbol</Label>
                  <Input
                    id="symbol"
                    placeholder="e.g. EURUSD, BTCUSD"
                    value={symbol}
                    onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                    className="h-9"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="timeframe">Timeframe</Label>
                  <Select value={timeframe} onValueChange={setTimeframe}>
                    <SelectTrigger id="timeframe" className="h-9">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="M1">M1 (1 minute)</SelectItem>
                      <SelectItem value="M5">M5 (5 minutes)</SelectItem>
                      <SelectItem value="M15">M15 (15 minutes)</SelectItem>
                      <SelectItem value="M30">M30 (30 minutes)</SelectItem>
                      <SelectItem value="H1">H1 (1 hour)</SelectItem>
                      <SelectItem value="H4">H4 (4 hours)</SelectItem>
                      <SelectItem value="D1">D1 (Daily)</SelectItem>
                      <SelectItem value="W1">W1 (Weekly)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="dataSource">Data Source</Label>
                <Select value={dataSource} onValueChange={setDataSource}>
                  <SelectTrigger id="dataSource" className="h-9">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="mt5">MetaTrader 5</SelectItem>
                    <SelectItem value="dukascopy">Dukascopy API</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2 flex flex-col">
                  <Label>Start Date</Label>
                  <Popover>
                    <PopoverTrigger asChild>
                      <Button
                        variant="outline"
                        className={cn(
                          "h-9 justify-start text-left font-normal",
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
                        captionLayout="dropdown"
                        fromYear={2000}
                        toYear={new Date().getFullYear() + 1}
                      />
                    </PopoverContent>
                  </Popover>
                </div>
                <div className="space-y-2 flex flex-col">
                  <Label>End Date</Label>
                  <Popover>
                    <PopoverTrigger asChild>
                      <Button
                        variant="outline"
                        className={cn(
                          "h-9 justify-start text-left font-normal",
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
                        captionLayout="dropdown"
                        fromYear={2000}
                        toYear={new Date().getFullYear() + 1}
                      />
                    </PopoverContent>
                  </Popover>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="initialCapital">Initial Capital</Label>
                <Input
                  id="initialCapital"
                  type="number"
                  value={initialCapital}
                  onChange={(e) => setInitialCapital(parseFloat(e.target.value))}
                  className="h-9 font-mono"
                />
              </div>
            </CardContent>
          </Card>

          {/* Method-specific settings */}
          {method === 'random' && (
            <Card>
              <CardHeader>
                <CardTitle>Random Search Settings</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Number of Iterations</Label>
                  <Input
                    type="number"
                    value={nIter}
                    onChange={(e) => setNIter(parseInt(e.target.value))}
                    className="h-9 font-mono"
                  />
                  <p className="text-xs text-muted-foreground">
                    How many random combinations to test
                  </p>
                </div>
              </CardContent>
            </Card>
          )}

          {method === 'bayesian' && (
            <Card>
              <CardHeader>
                <CardTitle>Bayesian Settings</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Number of Iterations</Label>
                  <Input
                    type="number"
                    value={nIter}
                    onChange={(e) => setNIter(parseInt(e.target.value))}
                    className="h-9 font-mono"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Initial Random Points</Label>
                  <Input
                    type="number"
                    value={nInitialPoints}
                    onChange={(e) => setNInitialPoints(parseInt(e.target.value))}
                    className="h-9 font-mono"
                  />
                  <p className="text-xs text-muted-foreground">
                    Random explorations before optimization starts
                  </p>
                </div>
              </CardContent>
            </Card>
          )}

          {method === 'genetic' && (
            <Card>
              <CardHeader>
                <CardTitle>Genetic Algorithm Settings</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Population Size</Label>
                  <Input
                    type="number"
                    value={populationSize}
                    onChange={(e) => setPopulationSize(parseInt(e.target.value))}
                    className="h-9 font-mono"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Generations</Label>
                  <Input
                    type="number"
                    value={generations}
                    onChange={(e) => setGenerations(parseInt(e.target.value))}
                    className="h-9 font-mono"
                  />
                  <p className="text-xs text-muted-foreground">
                    Number of evolution cycles
                  </p>
                </div>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <CardTitle>Resources</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
               <div className="space-y-2">
                  <div className="flex justify-between">
                    <Label>Concurrent Workers</Label>
                    <span className="text-sm font-mono">{workers}</span>
                  </div>
                  <Slider
                    value={[workers]}
                    min={1}
                    max={16}
                    step={1}
                    onValueChange={(vals: number[]) => setWorkers(vals[0])}
                  />
                  <p className="text-xs text-muted-foreground">
                    Higher counts use more CPU but finish faster.
                  </p>
               </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Parameter Ranges */}
        <div className="md:col-span-2 space-y-6">
          <Card className="h-full">
             <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Parameter Ranges</CardTitle>
                <CardDescription>Define the search space for optimization</CardDescription>
              </div>
              {strategy && getAddableParams().length > 0 && (
                <Select onValueChange={(value) => addParameter(value)}>
                  <SelectTrigger className="w-[200px]">
                    <SelectValue placeholder="Add Parameter" />
                  </SelectTrigger>
                  <SelectContent>
                    {getAddableParams().map((paramName) => (
                      <SelectItem key={paramName} value={paramName}>
                        <div className="flex items-center gap-2">
                          <Plus className="h-4 w-4" />
                          {paramName}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </CardHeader>
            <CardContent>
              {!strategy && (
                <div className="text-center py-12 text-muted-foreground border-dashed border-2 rounded-lg">
                  <Settings2 className="mx-auto h-12 w-12 mb-4 opacity-50" />
                  <p className="text-lg font-medium">No strategy selected</p>
                  <p className="text-sm mt-2">Select a strategy to configure optimization parameters</p>
                </div>
              )}

              {strategy && loadingParams && (
                <div className="text-center py-12 text-muted-foreground">
                  <Loader2 className="mx-auto h-12 w-12 mb-4 animate-spin" />
                  <p className="text-lg font-medium">Loading parameters...</p>
                </div>
              )}

              {strategy && !loadingParams && (
                <div className="space-y-4">
                  {parameters.map((param) => (
                  <div key={param.id} className="grid grid-cols-12 gap-4 items-center p-4 border rounded-lg bg-card/50">
                    <div className="col-span-2 space-y-1">
                      <Label className="text-xs">Name</Label>
                      <Input
                        value={param.name}
                        onChange={(e) => updateParameter(param.id, 'name', e.target.value)}
                        className="h-8 font-mono text-sm"
                      />
                    </div>
                     <div className="col-span-2 space-y-1">
                       <Label className="text-xs">Current</Label>
                       <div className="h-8 flex items-center">
                          <Badge variant="outline" className="font-mono text-sm">
                            {param.current}
                          </Badge>
                       </div>
                    </div>
                     <div className="col-span-2 space-y-1">
                      <Label className="text-xs">Start</Label>
                      <Input
                        type="number"
                        value={param.start}
                        onChange={(e) => updateParameter(param.id, 'start', parseFloat(e.target.value))}
                        className="h-8 font-mono text-sm"
                      />
                    </div>
                     <div className="col-span-2 space-y-1">
                      <Label className="text-xs">Stop</Label>
                      <Input
                        type="number"
                        value={param.stop}
                        onChange={(e) => updateParameter(param.id, 'stop', parseFloat(e.target.value))}
                        className="h-8 font-mono text-sm"
                      />
                    </div>
                     <div className="col-span-1 space-y-1">
                      <Label className="text-xs">Step</Label>
                      <Input
                        type="number"
                        value={param.step}
                        onChange={(e) => updateParameter(param.id, 'step', parseFloat(e.target.value))}
                        className="h-8 font-mono text-sm"
                      />
                    </div>
                     <div className="col-span-2 space-y-1">
                       <Label className="text-xs">Total Steps</Label>
                       <div className="h-8 flex items-center">
                          <Badge variant="secondary" className="font-mono">
                            {Math.floor((param.stop - param.start) / param.step) + 1}
                          </Badge>
                       </div>
                    </div>
                     <div className="col-span-1 flex justify-end pt-5">
                      <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive hover:text-destructive" onClick={() => removeParameter(param.id)}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                  ))}

                  {parameters.length === 0 && (
                    <div className="text-center py-8 text-muted-foreground border-dashed border-2 rounded-lg">
                      <p className="text-sm">No parameters configured for optimization.</p>
                      <p className="text-xs mt-1">All strategy parameters are available above.</p>
                    </div>
                  )}
                </div>
              )}

              {strategy && !loadingParams && (
                <div className="mt-6 flex justify-end items-center gap-4 border-t pt-4">
                   <div className="text-sm text-muted-foreground">
                      Total Combinations: <span className="font-mono font-bold text-foreground">
                         {parameters.reduce((acc, p) => acc * (Math.floor((p.stop - p.start) / p.step) + 1), 1).toLocaleString()}
                      </span>
                   </div>
                   <Button size="lg" onClick={handleRun} disabled={parameters.length === 0 || !symbol || !startDate || !endDate}>
                     <Play className="mr-2 h-4 w-4" />
                     Start Optimization
                   </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
