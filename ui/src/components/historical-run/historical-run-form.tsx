"use client"

import { useEffect, useMemo, useState } from "react"
import { toast } from "sonner"
import { backtestApi } from "@/lib/api/backtest"
import { getErrorMessage } from "@/lib/api-error"
import { strategyApi, type StrategyCodeResponse } from "@/lib/api/strategies"
import simulatorApi, {
  type ReplaySource,
  type SimulationRiskHorizonUnit,
  type SimulationStartResponse,
} from "@/lib/api/simulator"
import {
  type HistoricalRunConfig,
  historicalRunConfigToBacktestPayload,
  historicalRunConfigToSimulationPayload,
} from "@/lib/historical-run"
import { useAllBacktests, useStrategies } from "@/lib/use-strategies"
import { EngineSettings, type EngineSettingsValues } from "@/components/backtest/engine-settings"
import { OutputModeSelector, type HistoricalOutputMode } from "@/components/historical-run/output-mode-selector"
import { RangeModeSelector } from "@/components/historical-run/range-mode-selector"
import { StrategyParametersCard } from "@/components/historical-run/strategy-parameters-card"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"

interface HistoricalRunFormProps {
  initialExecutionMode?: HistoricalOutputMode
  initialSource?: "manual" | "strategy" | "replay"
  initialStrategyId?: string
  onSimulationStart: (
    sessionId: number,
    config: HistoricalRunConfig,
    response?: SimulationStartResponse
  ) => void
  onSimulationResume: (sessionId: number) => void
  onBacktestStart: (backtestId: number, strategyId: number, config: HistoricalRunConfig) => void
}

function formatLocalDate(value: Date): string {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, "0")
  const day = String(value.getDate()).padStart(2, "0")
  return `${year}-${month}-${day}`
}

function shiftDate(value: Date, { years = 0, months = 0 }: { years?: number; months?: number }) {
  const next = new Date(value)
  next.setFullYear(next.getFullYear() + years)
  next.setMonth(next.getMonth() + months)
  return next
}

const riskPresetsByTimeframe: Partial<
  Record<string, { horizonUnit: SimulationRiskHorizonUnit; horizonValue: number; volLookback: number; corrLookback: number }>
> = {
  M5: { horizonUnit: "hours", horizonValue: 1, volLookback: 48, corrLookback: 96 },
  H1: { horizonUnit: "hours", horizonValue: 1, volLookback: 24, corrLookback: 72 },
  D1: { horizonUnit: "days", horizonValue: 1, volLookback: 20, corrLookback: 60 },
}

export function HistoricalRunForm({
  initialExecutionMode = "visualized",
  initialSource = "manual",
  initialStrategyId = "",
  onSimulationStart,
  onSimulationResume,
  onBacktestStart,
}: HistoricalRunFormProps) {
  const today = useMemo(() => new Date(), [])
  const defaultEndDate = useMemo(() => formatLocalDate(today), [today])
  const defaultStartDate = useMemo(() => formatLocalDate(shiftDate(today, { years: -1 })), [today])
  const defaultWarmupStartDate = useMemo(
    () => formatLocalDate(shiftDate(shiftDate(today, { years: -1 }), { months: -1 })),
    [today]
  )
  const { strategies, loading: loadingStrategies } = useStrategies()
  const { backtests, loading: loadingBacktests } = useAllBacktests(200)

  const [executionMode, setExecutionMode] = useState<HistoricalOutputMode>(initialExecutionMode)
  const [mode, setMode] = useState<"manual" | "strategy" | "replay">(initialSource)
  const [runName, setRunName] = useState("")
  const [description, setDescription] = useState("")
  const [symbol, setSymbol] = useState("EURUSD")
  const [timeframe, setTimeframe] = useState("H1")
  const [rangeBy, setRangeBy] = useState<"dates" | "bars">("bars")
  const [startDate, setStartDate] = useState(defaultStartDate)
  const [endDate, setEndDate] = useState(defaultEndDate)
  const [numberOfBars, setNumberOfBars] = useState(500)
  const [warmupStartDate, setWarmupStartDate] = useState(defaultWarmupStartDate)
  const [warmupBars, setWarmupBars] = useState(100)
  const [dataSource, setDataSource] = useState<"mt5" | "dukascopy">("mt5")
  const [strategyId, setStrategyId] = useState(initialStrategyId)
  const [strategyVersionId, setStrategyVersionId] = useState<number | undefined>(undefined)
  const [strategyParams, setStrategyParams] = useState<Record<string, unknown>>({})
  const [strategyParameterTypes, setStrategyParameterTypes] = useState<Record<string, string>>({})
  const [loadingStrategyParams, setLoadingStrategyParams] = useState(false)
  const [replaySource, setReplaySource] = useState<ReplaySource>("backtest")
  const [replayBacktestId, setReplayBacktestId] = useState("")
  const [replayFileName, setReplayFileName] = useState("")
  const [submitting, setSubmitting] = useState(false)
  const [importing, setImporting] = useState(false)
  const [pausedSessions, setPausedSessions] = useState<Array<{ session_id: number; session_name?: string | null; symbol: string; timeframe: string }>>([])
  const [selectedPausedId, setSelectedPausedId] = useState("")
  const [importFile, setImportFile] = useState<File | null>(null)
  const [importStrategyName, setImportStrategyName] = useState("")
  const [importAlias, setImportAlias] = useState("")
  const [importDescription, setImportDescription] = useState("")

  const [engineSettings, setEngineSettings] = useState<EngineSettingsValues>({
    initialCapital: 10000,
    commission: 7,
    slippageType: "fixed",
    slippage: 0,
    slippageMin: 0,
    slippageMax: 10,
    spreadType: "use-broker",
    spread: 20,
    spreadMin: 10,
    spreadMax: 50,
    leverage: 400,
    dataResolution: "trading_timeframe",
  })
  const [riskSettings, setRiskSettings] = useState({
    confidenceLevel: 0.95,
    horizonUnit: "days" as SimulationRiskHorizonUnit,
    horizonValue: 1,
    volLookback: 20,
    corrLookback: 60,
    varCapFrac: 0.1,
    esCapFrac: 0.15,
    deltaVarCapFrac: 0.02,
    deltaEsCapFrac: 0.03,
    maxMarginUsedFrac: 0.5,
    maxSingleRcFrac: 0.1,
    warningUtilizationFrac: 0.9,
    limitsEnforced: false,
  })

  useEffect(() => {
    const preset = riskPresetsByTimeframe[timeframe]
    if (!preset) return
    setRiskSettings((prev) => ({
      ...prev,
      horizonUnit: preset.horizonUnit,
      horizonValue: preset.horizonValue,
      volLookback: preset.volLookback,
      corrLookback: preset.corrLookback,
    }))
  }, [timeframe])

  useEffect(() => {
    const loadPausedSessions = async () => {
      try {
        const data = await simulatorApi.getPausedSessions()
        setPausedSessions(data)
        if (data.length > 0) setSelectedPausedId(String(data[0].session_id))
      } catch (error) {
        toast.error("Failed to load paused sessions", { description: getErrorMessage(error) })
      }
    }
    loadPausedSessions()
  }, [])

  useEffect(() => {
    if (mode !== "strategy" && executionMode === "batch") {
      setExecutionMode("visualized")
    }
  }, [mode, executionMode])

  useEffect(() => {
    setExecutionMode(initialExecutionMode)
  }, [initialExecutionMode])

  useEffect(() => {
    setMode(initialSource)
  }, [initialSource])

  useEffect(() => {
    setStrategyId(initialStrategyId)
  }, [initialStrategyId])

  useEffect(() => {
    if (rangeBy === "dates") {
      setStartDate((prev) => prev || defaultStartDate)
      setEndDate((prev) => prev || defaultEndDate)
      setWarmupStartDate((prev) => prev || defaultWarmupStartDate)
      return
    }
    setNumberOfBars((prev) => (prev > 0 ? prev : 500))
    setWarmupBars((prev) => (prev >= 0 ? prev : 100))
  }, [defaultEndDate, defaultStartDate, defaultWarmupStartDate, rangeBy])

  useEffect(() => {
    if (rangeBy !== "dates" || !startDate) {
      return
    }
    const start = new Date(startDate)
    if (Number.isNaN(start.getTime())) {
      return
    }
    setWarmupStartDate(formatLocalDate(shiftDate(start, { months: -1 })))
  }, [rangeBy, startDate])

  useEffect(() => {
    const selectedStrategy = strategies.find((item) => item.id === Number(strategyId))
    if (!selectedStrategy?.active_version_id) {
      setStrategyVersionId(undefined)
      setStrategyParams({})
      setStrategyParameterTypes({})
      return
    }

    const loadStrategyParameters = async () => {
      try {
        setLoadingStrategyParams(true)
        const versionCode: StrategyCodeResponse = await strategyApi.getVersionCode(
          selectedStrategy.id,
          selectedStrategy.active_version_id as number
        )
        setStrategyVersionId(versionCode.version_id)
        setStrategyParams({ ...(versionCode.parameters || {}) })
        setStrategyParameterTypes({ ...(versionCode.parameterTypes || {}) })
      } catch (error) {
        setStrategyVersionId(selectedStrategy.active_version_id ?? undefined)
        setStrategyParams({})
        setStrategyParameterTypes({})
        toast.error("Failed to load strategy parameters", {
          description: getErrorMessage(error),
        })
      } finally {
        setLoadingStrategyParams(false)
      }
    }

    void loadStrategyParameters()
  }, [strategyId, strategies])

  const pausedOptions = useMemo(
    () =>
      pausedSessions.map((session) => ({
        value: String(session.session_id),
        label: `${session.session_name || `Session ${session.session_id}`} (${session.symbol} ${session.timeframe})`,
      })),
    [pausedSessions]
  )

  const strategySelectionValue =
    mode === "manual"
      ? "manual"
      : mode === "replay"
        ? "replay"
        : strategyId
          ? `strategy:${strategyId}`
          : "__select_strategy__"
  const showSessionControls = executionMode === "visualized"
  const showRisk = executionMode === "visualized"
  const showStrategy = mode === "strategy" && Boolean(strategyId)
  const showReplay = mode === "replay"
  const canUseBatch = showStrategy
  const symbolCount = symbol.split(",").map((item) => item.trim()).filter(Boolean).length

  const config: HistoricalRunConfig = {
    source: mode,
    executionMode,
    visualize: executionMode === "visualized",
    symbol,
    timeframe,
    range: {
      rangeBy,
      startDate: rangeBy === "dates" ? startDate : undefined,
      endDate: rangeBy === "dates" ? endDate : undefined,
      numberOfBars: rangeBy === "bars" ? numberOfBars : undefined,
    },
    warmup: {
      warmupBy: rangeBy === "dates" ? "date" : "bars",
      warmupStartDate: rangeBy === "dates" ? warmupStartDate : undefined,
      warmupBars: rangeBy === "bars" ? warmupBars : undefined,
    },
    engine: {
      initialCapital: engineSettings.initialCapital,
      commission: engineSettings.commission,
      leverage: engineSettings.leverage,
      slippageType: engineSettings.slippageType,
      slippage: engineSettings.slippage,
      slippageMin: engineSettings.slippageMin,
      slippageMax: engineSettings.slippageMax,
      spreadType: engineSettings.spreadType,
      spread: engineSettings.spread,
      spreadMin: engineSettings.spreadMin,
      spreadMax: engineSettings.spreadMax,
      dataSource,
      dataResolution: engineSettings.dataResolution,
    },
    risk: showRisk
      ? {
          confidenceLevel: riskSettings.confidenceLevel,
          horizonUnit: riskSettings.horizonUnit,
          horizonValue: riskSettings.horizonValue,
          volLookback: riskSettings.volLookback,
          corrLookback: riskSettings.corrLookback,
          varCapFrac: riskSettings.varCapFrac,
          esCapFrac: riskSettings.esCapFrac,
          deltaVarCapFrac: riskSettings.deltaVarCapFrac,
          deltaEsCapFrac: riskSettings.deltaEsCapFrac,
          maxMarginUsedFrac: riskSettings.maxMarginUsedFrac,
          maxSingleRcFrac: riskSettings.maxSingleRcFrac,
          warningUtilizationFrac: riskSettings.warningUtilizationFrac,
          limitsEnforced: riskSettings.limitsEnforced,
        }
      : undefined,
    strategy: showStrategy
      ? {
          strategyId: strategyId ? Number(strategyId) : undefined,
          strategyVersionId,
          strategyParams,
        }
      : undefined,
    replay: showReplay
      ? {
          replaySource,
          replayBacktestId: replayBacktestId ? Number(replayBacktestId) : undefined,
          replayFileName: replayFileName || undefined,
        }
      : undefined,
    metadata: {
      sessionName: runName || undefined,
      alias: runName || undefined,
      description: description || undefined,
    },
  }

  const handleStrategySelectionChange = (value: string) => {
    if (value === "manual") {
      setMode("manual")
      setExecutionMode("visualized")
      setStrategyId("")
      return
    }
    if (value === "replay") {
      setMode("replay")
      setExecutionMode("visualized")
      setStrategyId("")
      return
    }
    if (value === "__select_strategy__") {
      setMode("strategy")
      setStrategyId("")
      return
    }
    if (value.startsWith("strategy:")) {
      setMode("strategy")
      setStrategyId(value.replace("strategy:", ""))
    }
  }

  const handleResume = async () => {
    if (!selectedPausedId) {
      toast.error("Select a paused session to resume.")
      return
    }
    try {
      setSubmitting(true)
      const response = await simulatorApi.resumeSession(Number(selectedPausedId))
      toast.success("Session resumed", { description: `Session ${response.session_id}` })
      onSimulationResume(response.session_id)
    } catch (error) {
      toast.error("Failed to resume session", { description: getErrorMessage(error) })
    } finally {
      setSubmitting(false)
    }
  }

  const handleCsvImport = async () => {
    if (!importFile || !importStrategyName || !symbol || !timeframe) {
      toast.error("CSV import requires file, strategy name, symbol, and timeframe.")
      return
    }
    const formData = new FormData()
    formData.append("file", importFile)
    formData.append("strategy_name", importStrategyName)
    formData.append("symbol", symbol)
    formData.append("timeframe", timeframe)
    formData.append("initial_balance", engineSettings.initialCapital.toString())
    if (importAlias) formData.append("alias", importAlias)
    if (importDescription) formData.append("description", importDescription)

    try {
      setImporting(true)
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"
      const token = localStorage.getItem("hq_auth_token")
      const headers: HeadersInit = token ? { Authorization: `Bearer ${token}` } : {}
      const response = await fetch(`${baseUrl}/api/import/sqx`, { method: "POST", body: formData, headers })
      if (!response.ok) throw new Error(await response.text())
      const data = await response.json()
      const importedId = Number(data.backtest_id)
      setReplayBacktestId(String(importedId))
      setReplaySource("csv")
      setReplayFileName(importFile.name)
      toast.success("CSV imported", { description: `Backtest ${importedId} ready to replay.` })
    } catch (error) {
      toast.error("Failed to import CSV", { description: getErrorMessage(error) })
    } finally {
      setImporting(false)
    }
  }

  const handleSubmit = async () => {
    if (!symbol) return toast.error("Symbol is required.")
    if (rangeBy === "dates" && (!startDate || !endDate)) return toast.error("Start and end dates are required.")
    if (rangeBy === "bars" && (!numberOfBars || numberOfBars <= 0)) return toast.error("Please enter a valid number of bars.")
    if (mode === "strategy" && !strategyId) return toast.error("Strategy is required for strategy runs.")
    if (mode === "replay" && !replayBacktestId) return toast.error("Please select or import a backtest to replay.")
    if (mode === "manual" && executionMode === "batch") return toast.error("Manual runs are visualized only in phase 1.")
    if (mode === "replay" && executionMode === "batch") return toast.error("Batch replay is not supported yet.")
    try {
      setSubmitting(true)
      if (executionMode === "visualized") {
        const payload = historicalRunConfigToSimulationPayload(config)
        const response = await simulatorApi.startSession(payload)
        toast.success("Historical run started", { description: `Session ${response.session_id}` })
        onSimulationStart(response.session_id, config, response)
        return
      }
      const plan = historicalRunConfigToBacktestPayload(config)
      const result = plan.isPortfolio
        ? await backtestApi.runPortfolio(plan.strategyId, plan.payload)
        : await backtestApi.run(plan.strategyId, plan.payload)
      toast.success("Batch backtest started", { description: `Backtest ${result.backtest_id}` })
      onBacktestStart(result.backtest_id, plan.strategyId, config)
    } catch (error) {
      toast.error("Failed to start historical run", { description: getErrorMessage(error) })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="grid gap-6">
      {showSessionControls && pausedOptions.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Resume Session</CardTitle>
            <CardDescription>Continue a paused visualized run.</CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-1 md:grid-cols-[1fr_auto] gap-4">
            <Select value={selectedPausedId} onValueChange={setSelectedPausedId}>
              <SelectTrigger><SelectValue placeholder="Select paused session" /></SelectTrigger>
              <SelectContent>
                {pausedOptions.map((option) => (
                  <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button onClick={handleResume} disabled={submitting}>Resume</Button>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Data</CardTitle>
          <CardDescription>Shared run inputs used across all simulation modes.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="runName">Run Name</Label>
              <Input id="runName" value={runName} onChange={(e) => setRunName(e.target.value)} placeholder="e.g. London Session Replay" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="runDescription">Description</Label>
              <Input id="runDescription" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Describe the run setup or hypothesis" />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="symbol">Symbol(s)</Label>
              <Input id="symbol" value={symbol} onChange={(e) => setSymbol(e.target.value.toUpperCase())} placeholder="EURUSD or EURUSD, GBPUSD, USDJPY" />
              {symbolCount > 1 && executionMode === "batch" && (
                <p className="text-xs text-muted-foreground">
                  Multi-symbol input is allowed for batch strategy runs.
                </p>
              )}
              {symbolCount > 1 && executionMode === "visualized" && symbolCount <= 4 && (
                <p className="text-xs text-muted-foreground">
                  Visualized mode will render {symbolCount} charts, one per symbol.
                </p>
              )}
              {symbolCount > 4 && executionMode === "visualized" && (
                <p className="text-xs text-muted-foreground">
                  Visualized mode will switch to table view when more than 4 symbols are entered.
                </p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="timeframe">Timeframe</Label>
              <Select value={timeframe} onValueChange={setTimeframe}>
                <SelectTrigger id="timeframe"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="M1">M1</SelectItem><SelectItem value="M5">M5</SelectItem><SelectItem value="M15">M15</SelectItem>
                  <SelectItem value="H1">H1</SelectItem><SelectItem value="H4">H4</SelectItem><SelectItem value="D1">D1</SelectItem><SelectItem value="W1">W1</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <RangeModeSelector value={rangeBy} onValueChange={setRangeBy} variant="toggle" />
            <div />
          </div>
          {rangeBy === "dates" ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-2"><Label htmlFor="startDate">Start Date</Label><Input id="startDate" type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} /></div>
              <div className="space-y-2"><Label htmlFor="endDate">End Date</Label><Input id="endDate" type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} /></div>
              <div className="space-y-2"><Label htmlFor="warmupStartDate">Warmup Start Date</Label><Input id="warmupStartDate" type="date" value={warmupStartDate} onChange={(e) => setWarmupStartDate(e.target.value)} /></div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2"><Label htmlFor="numberOfBars">Number of Bars</Label><Input id="numberOfBars" type="number" min="1" value={numberOfBars} onChange={(e) => setNumberOfBars(Number(e.target.value))} /></div>
              <div className="space-y-2"><Label htmlFor="warmupBars">Warmup Bars</Label><Input id="warmupBars" type="number" min="0" value={warmupBars} onChange={(e) => setWarmupBars(Number(e.target.value))} /></div>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Strategy</CardTitle>
          <CardDescription>Select `Manual`, `Replay`, or a strategy-driven run.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-6">
          <div className="space-y-2">
            <Label htmlFor="strategyMode">Strategy</Label>
            <Select value={strategySelectionValue} onValueChange={handleStrategySelectionChange}>
              <SelectTrigger id="strategyMode">
                <SelectValue placeholder={loadingStrategies ? "Loading..." : "Select mode or strategy"} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="manual">Manual</SelectItem>
                <SelectItem value="replay">Replay</SelectItem>
                <SelectItem value="__select_strategy__" disabled>
                  Strategies
                </SelectItem>
                {strategies.map((strategy) => (
                  <SelectItem key={strategy.id} value={`strategy:${strategy.id}`}>
                    {strategy.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {showStrategy && (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <OutputModeSelector
                  value={executionMode}
                  onValueChange={(value) =>
                    value === "batch" && !canUseBatch ? undefined : setExecutionMode(value)
                  }
                />
                <div className="space-y-2">
                  <Label htmlFor="dataSource">Data Source</Label>
                  <Select
                    value={dataSource}
                    onValueChange={(value) => setDataSource(value as "mt5" | "dukascopy")}
                  >
                    <SelectTrigger id="dataSource"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="mt5">MetaTrader 5</SelectItem>
                      <SelectItem value="dukascopy">Dukascopy API</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <StrategyParametersCard
                values={strategyParams}
                parameterTypes={strategyParameterTypes}
                loading={loadingStrategyParams}
                onChange={(key, value) =>
                  setStrategyParams((prev) => ({
                    ...prev,
                    [key]: value,
                  }))
                }
              />
            </>
          )}
        </CardContent>
      </Card>

      {showReplay && (
        <Card>
          <CardHeader><CardTitle>Replay Source</CardTitle><CardDescription>Replay existing trades in the visualized simulator flow.</CardDescription></CardHeader>
          <CardContent className="grid gap-6">
            <div className="space-y-2">
              <Label>Source</Label>
              <ToggleGroup type="single" value={replaySource} onValueChange={(value) => value && setReplaySource(value as ReplaySource)}>
                <ToggleGroupItem value="backtest">Backtest</ToggleGroupItem>
                <ToggleGroupItem value="csv">CSV Import</ToggleGroupItem>
              </ToggleGroup>
            </div>
            {replaySource === "backtest" ? (
              <div className="space-y-2">
                <Label htmlFor="replayBacktestId">Backtest</Label>
                <Select value={replayBacktestId} onValueChange={setReplayBacktestId} disabled={loadingBacktests}>
                  <SelectTrigger id="replayBacktestId"><SelectValue placeholder={loadingBacktests ? "Loading..." : "Select backtest"} /></SelectTrigger>
                  <SelectContent>
                    {backtests.map((backtest) => (
                      <SelectItem key={backtest.backtest_id} value={backtest.backtest_id.toString()}>
                        {(backtest.alias || backtest.strategy_name || "Backtest") + ` (#${backtest.backtest_id})`}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            ) : (
              <div className="grid gap-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2"><Label htmlFor="importStrategyName">Strategy Name</Label><Input id="importStrategyName" value={importStrategyName} onChange={(e) => setImportStrategyName(e.target.value)} /></div>
                  <div className="space-y-2"><Label htmlFor="importFile">CSV File</Label><Input id="importFile" type="file" accept=".csv" onChange={(e) => setImportFile(e.target.files?.[0] || null)} /></div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2"><Label htmlFor="importAlias">Alias</Label><Input id="importAlias" value={importAlias} onChange={(e) => setImportAlias(e.target.value)} /></div>
                  <div className="space-y-2"><Label htmlFor="importDescription">Description</Label><Input id="importDescription" value={importDescription} onChange={(e) => setImportDescription(e.target.value)} /></div>
                </div>
                <Button onClick={handleCsvImport} disabled={importing}>{importing ? "Importing..." : "Import CSV"}</Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      <EngineSettings values={engineSettings} onChange={(key, value) => setEngineSettings((prev) => ({ ...prev, [key]: value }))} />

      {showRisk && (
        <Card>
          <CardHeader><CardTitle className="text-lg">Risk Settings</CardTitle><CardDescription>Configure the VaR, CVaR, and limit inputs for this simulation session.</CardDescription></CardHeader>
          <CardContent className="grid gap-4">
            <div className="space-y-2">
              <Label>Risk Limit Mode</Label>
              <ToggleGroup type="single" value={riskSettings.limitsEnforced ? "blocking" : "descriptive"} onValueChange={(value) => value && setRiskSettings((prev) => ({ ...prev, limitsEnforced: value === "blocking" }))}>
                <ToggleGroupItem value="blocking">Blocking</ToggleGroupItem>
                <ToggleGroupItem value="descriptive">Descriptive Only</ToggleGroupItem>
              </ToggleGroup>
            </div>
            <div className="space-y-1">
              <div className="text-sm font-medium">VaR And CVaR</div>
              <div className="text-xs text-muted-foreground">
                Controls the descriptive portfolio risk snapshot calculations.
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="space-y-2"><Label htmlFor="riskConfidenceLevel">Confidence Level</Label><Input id="riskConfidenceLevel" type="number" step="0.01" value={riskSettings.confidenceLevel} onChange={(e) => setRiskSettings((prev) => ({ ...prev, confidenceLevel: Number(e.target.value) || 0.95 }))} /></div>
              <div className="space-y-2"><Label htmlFor="riskHorizonUnit">Risk Horizon Unit</Label><Select value={riskSettings.horizonUnit} onValueChange={(value) => setRiskSettings((prev) => ({ ...prev, horizonUnit: value as SimulationRiskHorizonUnit }))}><SelectTrigger id="riskHorizonUnit"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="bars">Bars</SelectItem><SelectItem value="hours">Hours</SelectItem><SelectItem value="days">Days</SelectItem></SelectContent></Select></div>
              <div className="space-y-2"><Label htmlFor="riskHorizonValue">Risk Horizon Value</Label><Input id="riskHorizonValue" type="number" min="1" value={riskSettings.horizonValue} onChange={(e) => setRiskSettings((prev) => ({ ...prev, horizonValue: Number(e.target.value) || 1 }))} /></div>
              <div className="space-y-2"><Label htmlFor="riskVolLookback">Volatility Lookback</Label><Input id="riskVolLookback" type="number" min="2" value={riskSettings.volLookback} onChange={(e) => setRiskSettings((prev) => ({ ...prev, volLookback: Number(e.target.value) || 20 }))} /></div>
              <div className="space-y-2"><Label htmlFor="riskCorrLookback">Correlation Lookback</Label><Input id="riskCorrLookback" type="number" min="2" value={riskSettings.corrLookback} onChange={(e) => setRiskSettings((prev) => ({ ...prev, corrLookback: Number(e.target.value) || 60 }))} /></div>
            </div>
            <div className="space-y-1 pt-2">
              <div className="text-sm font-medium">Limits</div>
              <div className="text-xs text-muted-foreground">
                These values feed the current compliance and warning status.
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <div className="space-y-2"><Label htmlFor="riskVarCapFrac">VaR Cap %</Label><Input id="riskVarCapFrac" type="number" min="0" step="0.01" value={riskSettings.varCapFrac} onChange={(e) => setRiskSettings((prev) => ({ ...prev, varCapFrac: Number(e.target.value) || 0 }))} /></div>
              <div className="space-y-2"><Label htmlFor="riskEsCapFrac">CVaR Cap %</Label><Input id="riskEsCapFrac" type="number" min="0" step="0.01" value={riskSettings.esCapFrac} onChange={(e) => setRiskSettings((prev) => ({ ...prev, esCapFrac: Number(e.target.value) || 0 }))} /></div>
              <div className="space-y-2"><Label htmlFor="riskDeltaVarCapFrac">Delta VaR Cap %</Label><Input id="riskDeltaVarCapFrac" type="number" min="0" step="0.01" value={riskSettings.deltaVarCapFrac} onChange={(e) => setRiskSettings((prev) => ({ ...prev, deltaVarCapFrac: Number(e.target.value) || 0 }))} /></div>
              <div className="space-y-2"><Label htmlFor="riskDeltaEsCapFrac">Delta CVaR Cap %</Label><Input id="riskDeltaEsCapFrac" type="number" min="0" step="0.01" value={riskSettings.deltaEsCapFrac} onChange={(e) => setRiskSettings((prev) => ({ ...prev, deltaEsCapFrac: Number(e.target.value) || 0 }))} /></div>
              <div className="space-y-2"><Label htmlFor="riskMaxMarginUsedFrac">Max Margin Used %</Label><Input id="riskMaxMarginUsedFrac" type="number" min="0" step="0.01" value={riskSettings.maxMarginUsedFrac} onChange={(e) => setRiskSettings((prev) => ({ ...prev, maxMarginUsedFrac: Number(e.target.value) || 0 }))} /></div>
              <div className="space-y-2"><Label htmlFor="riskMaxSingleRcFrac">Max Single Risk Contribution Buffer %</Label><Input id="riskMaxSingleRcFrac" type="number" min="0" step="0.01" value={riskSettings.maxSingleRcFrac} onChange={(e) => setRiskSettings((prev) => ({ ...prev, maxSingleRcFrac: Number(e.target.value) || 0 }))} /></div>
              <div className="space-y-2"><Label htmlFor="riskWarningUtilizationFrac">Warning Utilization %</Label><Input id="riskWarningUtilizationFrac" type="number" step="0.01" value={riskSettings.warningUtilizationFrac} onChange={(e) => setRiskSettings((prev) => ({ ...prev, warningUtilizationFrac: Number(e.target.value) || 0.9 }))} /></div>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="flex justify-end">
        <Button
          size="lg"
          onClick={handleSubmit}
          disabled={
            submitting ||
            importing ||
            loadingStrategies
          }
        >
          {submitting ? (executionMode === "visualized" ? "Starting..." : "Starting Backtest...") : executionMode === "visualized" ? "Start Visualized Run" : "Run Batch Backtest"}
        </Button>
      </div>
    </div>
  )
}
