"use client"

import * as React from "react"
import { CalendarIcon, Play, Loader2 } from "lucide-react"
import { format } from "date-fns"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Calendar } from "@/components/ui/calendar"
import {
    Card,
    CardContent,
    CardDescription,
    CardFooter,
    CardHeader,
    CardTitle,
} from "@/components/ui/card"
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from "@/components/ui/popover"
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { EngineSettings } from "./engine-settings"
import { BacktestMetadata } from "./backtest-metadata"
import { toast } from "sonner"
import { useStrategies } from "@/lib/use-strategies"
import { backtestApi } from "@/lib/api/backtest"
import { useSearchParams } from "next/navigation"

interface BacktestConfigFormProps {
    onSubmit: (backtestId: number, strategyId: number) => void
}

export function BacktestConfigForm({ onSubmit }: BacktestConfigFormProps) {
    const { strategies, loading: loadingStrategies } = useStrategies()
    const searchParams = useSearchParams()
    const initialStrategyId = searchParams.get("strategyId")

    const [date, setDate] = React.useState<Date | undefined>(new Date(new Date().setFullYear(new Date().getFullYear() - 1)))
    const [endDate, setEndDate] = React.useState<Date | undefined>(new Date())
    const [rangeBy, setRangeBy] = React.useState<"dates" | "bars">("dates")
    const [numberOfBars, setNumberOfBars] = React.useState<number>(1000)
    const [warmupBy, setWarmupBy] = React.useState<"date" | "bars">("date")
    const [warmupStartDate, setWarmupStartDate] = React.useState<Date | undefined>(() => {
        const defaultDate = new Date(new Date().setFullYear(new Date().getFullYear() - 1))
        defaultDate.setDate(defaultDate.getDate() - 7)
        return defaultDate
    })
    const [warmupBars, setWarmupBars] = React.useState<number>(100)
    const [submitting, setSubmitting] = React.useState(false)
    const [config, setConfig] = React.useState({
        strategyId: initialStrategyId || "",
        symbol: "",
        timeframe: "H1",
        dataSource: "mt5",
        engineSettings: {
            initialCapital: 10000,
            commission: 7,
            slippageType: "fixed" as "fixed" | "variable",
            slippage: 0,
            slippageMin: 0,
            slippageMax: 10,
            spreadType: "use-broker" as "use-broker" | "fixed" | "variable",
            spread: 20,
            spreadMin: 10,
            spreadMax: 50,
            leverage: 400,
            engineType: "event-driven" as "vectorised" | "event-driven",
            dataResolution: "trading_timeframe" as "trading_timeframe" | "m1_ohlc" | "synthetic_ticks" | "real_ticks",
            // Money Management settings
            positionSizingMethod: "fixed_lot" as "fixed_lot" | "milestone" | "fixed_risk" | "kelly" | "volatility" | "fixed_fractional",
            lotSize: 0.1,           // for fixed_lot
            riskPercent: 1.0,       // for fixed_risk, volatility
            baseLotSize: 0.1,       // for milestone
            milestoneAmount: 3000,  // for milestone
            lotIncrement: 0.2,      // for milestone
            kellyFractionLimit: 0.25, // for kelly
            fraction: 2.0,          // for fixed_fractional
        },
        metadata: {
            alias: "",
            description: ""
        }
    })

    const handleRunBacktest = async () => {
        if (!config.strategyId || !config.symbol) {
             toast.error("Please fill in all required fields (Strategy, Symbol)")
             return
        }

        if (rangeBy === "dates" && (!date || !endDate)) {
             toast.error("Please select both start and end dates")
             return
        }

        if (rangeBy === "bars" && (!numberOfBars || numberOfBars <= 0)) {
             toast.error("Please enter a valid number of bars")
             return
        }

        const selectedStrategy = strategies.find(s => s.id === parseInt(config.strategyId))
        if (!selectedStrategy) {
            toast.error("Invalid strategy selected")
            return
        }

        try {
            setSubmitting(true)

            const backtestRequest: any = {
                symbol: config.symbol,
                timeframe: config.timeframe,
                data_source: config.dataSource,
                range_by: rangeBy,
                initial_capital: config.engineSettings.initialCapital,
                commission: config.engineSettings.commission,
                slippage_type: config.engineSettings.slippageType,
                slippage: config.engineSettings.slippage,
                slippage_min: config.engineSettings.slippageMin,
                slippage_max: config.engineSettings.slippageMax,
                spread_type: config.engineSettings.spreadType,
                spread: config.engineSettings.spread,
                spread_min: config.engineSettings.spreadMin,
                spread_max: config.engineSettings.spreadMax,
                leverage: config.engineSettings.leverage,
                engine_type: config.engineSettings.engineType,
                data_resolution: config.engineSettings.dataResolution,
                // Money Management / Position Sizing
                position_sizing_method: config.engineSettings.positionSizingMethod,
                lot_size: config.engineSettings.lotSize,
                risk_percent: config.engineSettings.riskPercent,
                base_lot_size: config.engineSettings.baseLotSize,
                milestone_amount: config.engineSettings.milestoneAmount,
                lot_increment: config.engineSettings.lotIncrement,
                kelly_fraction_limit: config.engineSettings.kellyFractionLimit,
                fraction: config.engineSettings.fraction,
                alias: config.metadata.alias,
                description: config.metadata.description
            }

            if (rangeBy === "dates") {
                backtestRequest.start_date = format(date!, "yyyy-MM-dd")
                backtestRequest.end_date = format(endDate!, "yyyy-MM-dd")
            } else {
                backtestRequest.number_of_bars = numberOfBars
            }

            // Warmup configuration
            backtestRequest.warmup_by = warmupBy
            if (warmupBy === "date" && warmupStartDate) {
                backtestRequest.warmup_start_date = format(warmupStartDate, "yyyy-MM-dd")
            } else if (warmupBy === "bars") {
                backtestRequest.warmup_bars = warmupBars
            }

            const result = await backtestApi.run(parseInt(config.strategyId), backtestRequest)

            const symbols = config.symbol.split(",").map(s => s.trim()).filter(Boolean)
            const isPortfolio = symbols.length > 1
            toast.success(isPortfolio ? "Portfolio backtest started!" : "Backtest started successfully!", {
                description: `Strategy: ${selectedStrategy.name}, ${isPortfolio ? "Symbols" : "Symbol"}: ${symbols.join(", ")}`
            })

            onSubmit(result.backtest_id, parseInt(config.strategyId))
        } catch (error: any) {
            toast.error("Failed to start backtest", {
                description: error?.message || "An error occurred"
            })
            console.error("Backtest error:", error)
        } finally {
            setSubmitting(false)
        }
    }

    return (
        <div className="grid gap-6">
            <Card>
                <CardHeader>
                    <CardTitle>Strategy & Data</CardTitle>
                    <CardDescription>Select the strategy and historical data parameters.</CardDescription>
                </CardHeader>
                <CardContent className="grid gap-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label htmlFor="strategy">Strategy</Label>
                            <Select
                                value={config.strategyId}
                                onValueChange={(val) => setConfig({...config, strategyId: val})}
                                disabled={loadingStrategies}
                            >
                                <SelectTrigger id="strategy">
                                    <SelectValue placeholder={loadingStrategies ? "Loading strategies..." : "Select Strategy"} />
                                </SelectTrigger>
                                <SelectContent>
                                    {strategies.map(s => (
                                        <SelectItem key={s.id} value={s.id.toString()}>{s.name}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="timeframe">Timeframe</Label>
                            <Select
                                value={config.timeframe}
                                onValueChange={(val) => setConfig({...config, timeframe: val})}
                            >
                                <SelectTrigger id="timeframe">
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

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="space-y-2">
                             <Label htmlFor="symbol">Symbol(s)</Label>
                             <Input
                                id="symbol"
                                placeholder="e.g. EURUSD or EURUSD, GBPUSD, USDJPY"
                                value={config.symbol}
                                onChange={(e) => setConfig({...config, symbol: e.target.value.toUpperCase()})}
                             />
                             {config.symbol.includes(",") && (
                                <p className="text-xs text-muted-foreground">
                                    Portfolio mode: {config.symbol.split(",").map(s => s.trim()).filter(Boolean).length} symbols
                                </p>
                             )}
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="dataSource">Data Source</Label>
                            <Select
                                value={config.dataSource}
                                onValueChange={(val) => setConfig({...config, dataSource: val})}
                            >
                                <SelectTrigger id="dataSource">
                                    <SelectValue placeholder="Select Data Source" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="mt5">MetaTrader 5</SelectItem>
                                    <SelectItem value="dukascopy">Dukascopy API</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="space-y-2">
                            <Label htmlFor="positionSizing">Money Management</Label>
                            <Select
                                value={config.engineSettings.positionSizingMethod}
                                onValueChange={(val) => setConfig(prev => ({
                                    ...prev,
                                    engineSettings: { ...prev.engineSettings, positionSizingMethod: val as any }
                                }))}
                            >
                                <SelectTrigger id="positionSizing">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="fixed_lot">Fixed Lot</SelectItem>
                                    <SelectItem value="fixed_risk">Fixed Risk %</SelectItem>
                                    <SelectItem value="milestone">Milestone</SelectItem>
                                    <SelectItem value="kelly">Kelly Criterion</SelectItem>
                                    <SelectItem value="volatility">Volatility (ATR)</SelectItem>
                                    <SelectItem value="fixed_fractional">Fixed Fractional</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                        {config.engineSettings.positionSizingMethod === "fixed_lot" && (
                            <div className="space-y-2">
                                <Label htmlFor="lotSize">Lot Size</Label>
                                <Input
                                    id="lotSize"
                                    type="number"
                                    step="0.01"
                                    min="0.01"
                                    value={config.engineSettings.lotSize}
                                    onChange={(e) => setConfig(prev => ({
                                        ...prev,
                                        engineSettings: { ...prev.engineSettings, lotSize: parseFloat(e.target.value) || 0.1 }
                                    }))}
                                />
                            </div>
                        )}
                        {(config.engineSettings.positionSizingMethod === "fixed_risk" ||
                          config.engineSettings.positionSizingMethod === "volatility") && (
                            <div className="space-y-2">
                                <Label htmlFor="riskPercent">Risk %</Label>
                                <Input
                                    id="riskPercent"
                                    type="number"
                                    step="0.1"
                                    min="0.1"
                                    max="100"
                                    value={config.engineSettings.riskPercent}
                                    onChange={(e) => setConfig(prev => ({
                                        ...prev,
                                        engineSettings: { ...prev.engineSettings, riskPercent: parseFloat(e.target.value) || 1.0 }
                                    }))}
                                />
                            </div>
                        )}
                        {config.engineSettings.positionSizingMethod === "milestone" && (
                            <>
                                <div className="space-y-2">
                                    <Label htmlFor="baseLotSize">Base Lot Size</Label>
                                    <Input
                                        id="baseLotSize"
                                        type="number"
                                        step="0.01"
                                        min="0.01"
                                        value={config.engineSettings.baseLotSize}
                                        onChange={(e) => setConfig(prev => ({
                                            ...prev,
                                            engineSettings: { ...prev.engineSettings, baseLotSize: parseFloat(e.target.value) || 0.1 }
                                        }))}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="milestoneAmount">Milestone ($)</Label>
                                    <Input
                                        id="milestoneAmount"
                                        type="number"
                                        step="100"
                                        min="100"
                                        value={config.engineSettings.milestoneAmount}
                                        onChange={(e) => setConfig(prev => ({
                                            ...prev,
                                            engineSettings: { ...prev.engineSettings, milestoneAmount: parseFloat(e.target.value) || 3000 }
                                        }))}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="lotIncrement">Lot Increment</Label>
                                    <Input
                                        id="lotIncrement"
                                        type="number"
                                        step="0.01"
                                        min="0.01"
                                        value={config.engineSettings.lotIncrement}
                                        onChange={(e) => setConfig(prev => ({
                                            ...prev,
                                            engineSettings: { ...prev.engineSettings, lotIncrement: parseFloat(e.target.value) || 0.2 }
                                        }))}
                                    />
                                </div>
                            </>
                        )}
                        {config.engineSettings.positionSizingMethod === "kelly" && (
                            <div className="space-y-2">
                                <Label htmlFor="kellyLimit">Kelly Fraction Limit</Label>
                                <Input
                                    id="kellyLimit"
                                    type="number"
                                    step="0.01"
                                    min="0.01"
                                    max="1"
                                    value={config.engineSettings.kellyFractionLimit}
                                    onChange={(e) => setConfig(prev => ({
                                        ...prev,
                                        engineSettings: { ...prev.engineSettings, kellyFractionLimit: parseFloat(e.target.value) || 0.25 }
                                    }))}
                                />
                            </div>
                        )}
                        {config.engineSettings.positionSizingMethod === "fixed_fractional" && (
                            <div className="space-y-2">
                                <Label htmlFor="fraction">Fraction %</Label>
                                <Input
                                    id="fraction"
                                    type="number"
                                    step="0.1"
                                    min="0.1"
                                    max="100"
                                    value={config.engineSettings.fraction}
                                    onChange={(e) => setConfig(prev => ({
                                        ...prev,
                                        engineSettings: { ...prev.engineSettings, fraction: parseFloat(e.target.value) || 2.0 }
                                    }))}
                                />
                            </div>
                        )}
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="space-y-2">
                            <Label htmlFor="rangeBy">Range By</Label>
                            <Select
                                value={rangeBy}
                                onValueChange={(val) => setRangeBy(val as "dates" | "bars")}
                            >
                                <SelectTrigger id="rangeBy">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="dates">Dates</SelectItem>
                                    <SelectItem value="bars">Bars</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                        {rangeBy === "dates" ? (
                            <>
                                <div className="space-y-2 flex flex-col">
                                    <Label>Start Date</Label>
                                    <Popover>
                                        <PopoverTrigger asChild>
                                            <Button
                                                variant={"outline"}
                                                className={cn(
                                                    "w-full justify-start text-left font-normal",
                                                    !date && "text-muted-foreground"
                                                )}
                                            >
                                                <CalendarIcon className="mr-2 h-4 w-4" />
                                                {date ? format(date, "PPP") : <span>Pick a date</span>}
                                            </Button>
                                        </PopoverTrigger>
                                        <PopoverContent className="w-auto p-0" align="start">
                                            <Calendar
                                                mode="single"
                                                selected={date}
                                                onSelect={setDate}
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
                                                variant={"outline"}
                                                className={cn(
                                                    "w-full justify-start text-left font-normal",
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
                            </>
                        ) : (
                            <div className="space-y-2 md:col-span-2">
                                <Label htmlFor="numberOfBars">Number of Bars</Label>
                                <Input
                                    id="numberOfBars"
                                    type="number"
                                    min="1"
                                    placeholder="e.g. 1000"
                                    value={numberOfBars}
                                    onChange={(e) => setNumberOfBars(parseInt(e.target.value) || 0)}
                                />
                            </div>
                        )}
                    </div>

                    {/* Warmup Period Configuration */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 border-t">
                        <div className="space-y-2">
                            <Label htmlFor="warmupBy">Warmup Period</Label>
                            <Select
                                value={warmupBy}
                                onValueChange={(val) => setWarmupBy(val as "date" | "bars")}
                            >
                                <SelectTrigger id="warmupBy">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="date">By Date</SelectItem>
                                    <SelectItem value="bars">By Bars</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                        {warmupBy === "date" ? (
                            <div className="space-y-2 flex flex-col md:col-span-2">
                                <Label>Warmup Start Date</Label>
                                <Popover>
                                    <PopoverTrigger asChild>
                                        <Button
                                            variant={"outline"}
                                            className={cn(
                                                "w-full justify-start text-left font-normal",
                                                !warmupStartDate && "text-muted-foreground"
                                            )}
                                        >
                                            <CalendarIcon className="mr-2 h-4 w-4" />
                                            {warmupStartDate ? format(warmupStartDate, "PPP") : <span>Pick a date</span>}
                                        </Button>
                                    </PopoverTrigger>
                                    <PopoverContent className="w-auto p-0" align="start">
                                        <Calendar
                                            mode="single"
                                            selected={warmupStartDate}
                                            onSelect={setWarmupStartDate}
                                            initialFocus
                                            captionLayout="dropdown"
                                            fromYear={2000}
                                            toYear={new Date().getFullYear() + 1}
                                        />
                                    </PopoverContent>
                                </Popover>
                                <p className="text-xs text-muted-foreground">
                                    Data will be downloaded from this date to calculate indicators, but trading starts at the Start Date
                                </p>
                            </div>
                        ) : (
                            <div className="space-y-2 md:col-span-2">
                                <Label htmlFor="warmupBars">Warmup Bars</Label>
                                <Input
                                    id="warmupBars"
                                    type="number"
                                    min="0"
                                    placeholder="e.g. 100"
                                    value={warmupBars}
                                    onChange={(e) => setWarmupBars(parseInt(e.target.value) || 0)}
                                />
                                <p className="text-xs text-muted-foreground">
                                    Number of bars before the trading period to use for indicator warmup
                                </p>
                            </div>
                        )}
                    </div>
                </CardContent>
            </Card>

            <EngineSettings
                values={config.engineSettings}
                onChange={(key, val) => setConfig(prev => ({
                    ...prev,
                    engineSettings: { ...prev.engineSettings, [key]: val }
                }))}
            />

            <BacktestMetadata
                values={config.metadata}
                onChange={(key, val) => setConfig(prev => ({
                    ...prev,
                    metadata: { ...prev.metadata, [key]: val }
                }))}
            />

            <div className="flex justify-end">
                <Button
                    size="lg"
                    onClick={handleRunBacktest}
                    className="w-full md:w-auto"
                    disabled={submitting || loadingStrategies}
                >
                    {submitting ? (
                        <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Starting Backtest...
                        </>
                    ) : (
                        <>
                            <Play className="mr-2 h-4 w-4" />
                            Run Backtest
                        </>
                    )}
                </Button>
            </div>
        </div>
    )
}
