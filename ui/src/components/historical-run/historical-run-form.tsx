"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import { useRouter } from "next/navigation"
import { toast } from "sonner"
import {
  backtestApi,
  type BacktestRunPayload,
  type PortfolioBacktestRunPayload,
} from "@/lib/api/backtest"
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
  variant?: "visual_auto" | "batch_auto" | "manual" | "replay"
  initialExecutionMode?: HistoricalOutputMode
  initialSource?: "manual" | "strategy" | "replay"
  initialStrategyId?: string
  initialReplayBacktestId?: string
  initialReplaySource?: ReplaySource
  initialAutoStartReplay?: boolean
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

export function HistoricalRunForm({
  variant,
  initialExecutionMode = "visualized",
  initialSource = "manual",
  initialStrategyId = "",
  initialReplayBacktestId = "",
  initialReplaySource = "backtest",
  initialAutoStartReplay = false,
  onSimulationStart,
  onSimulationResume,
  onBacktestStart,
}: HistoricalRunFormProps) {
  const router = useRouter()
  const { strategies, loading: loadingStrategies } = useStrategies()
  const { backtests, loading: loadingBacktests } = useAllBacktests(200)

  const [executionMode, setExecutionMode] = useState<HistoricalOutputMode>(initialExecutionMode)
  const [mode, setMode] = useState<"manual" | "strategy" | "replay">(initialSource)
  const [runName, setRunName] = useState("")
  const [description, setDescription] = useState("")
  const [symbol, setSymbol] = useState("AUDUSD, EURGBP, NZDCHF")
  const [timeframe, setTimeframe] = useState("H1")
  const [rangeBy, setRangeBy] = useState<"dates" | "bars">("dates")
  const [startDate, setStartDate] = useState("2025-01-01")
  const [endDate, setEndDate] = useState("2025-12-31")
  const [numberOfBars, setNumberOfBars] = useState(500)
  const [warmupStartDate, setWarmupStartDate] = useState("2024-12-01")
  const [warmupBars, setWarmupBars] = useState(100)
  const [dataSource, setDataSource] = useState<"mt5" | "dukascopy">("mt5")
  const [strategyId, setStrategyId] = useState(initialStrategyId)
  const [strategyVersionId, setStrategyVersionId] = useState<number | undefined>(undefined)
  const [strategyParams, setStrategyParams] = useState<Record<string, unknown>>({})
  const [strategyParameterTypes, setStrategyParameterTypes] = useState<Record<string, string>>({})
  const [loadingStrategyParams, setLoadingStrategyParams] = useState(false)
  const [replaySource, setReplaySource] = useState<ReplaySource>(initialReplaySource)
  const [replayBacktestId, setReplayBacktestId] = useState(initialReplayBacktestId)
  const [replayFileName, setReplayFileName] = useState("")
  const [submitting, setSubmitting] = useState(false)
  const autoStartAttemptedRef = useRef(false)
  const handleSubmitRef = useRef<() => void>(() => undefined)
  const [importing, setImporting] = useState(false)
  const [pausedSessions, setPausedSessions] = useState<Array<{
    session_id: number
    session_name?: string | null
    symbol?: string | null
    timeframe?: string | null
    config?: { symbol?: string | null; timeframe?: string | null }
  }>>([])
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
    leverage: 0,
    engineType: "event_driven",
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
    maxCurrencyExposureFrac: 0.2,
    maxSingleRcFrac: 0.1,
    warningUtilizationFrac: 0.9,
    limitsEnforced: false,
  })

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
    if (variant === "visual_auto") {
      setMode("strategy")
      setExecutionMode("visualized")
    } else if (variant === "batch_auto") {
      setMode("strategy")
      setExecutionMode("batch")
    } else if (variant === "manual") {
      setMode("manual")
      setExecutionMode("visualized")
      setStrategyId("")
    } else if (variant === "replay") {
      setMode("replay")
      setExecutionMode("visualized")
      setStrategyId("")
    }
  }, [variant])

  const showSessionControls = executionMode === "visualized"
  const showRisk = executionMode === "visualized"
  const showStrategy = mode === "strategy" && Boolean(strategyId)
  const showReplay = mode === "replay"
  const canUseBatch = showStrategy
  
  const selectedStrategyName =
    strategies.find((item) => item.id === Number(strategyId))?.name || undefined

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
      engineType: engineSettings.engineType,
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
          maxCurrencyExposureFrac: riskSettings.maxCurrencyExposureFrac,
          maxSingleRcFrac: riskSettings.maxSingleRcFrac,
          warningUtilizationFrac: riskSettings.warningUtilizationFrac,
          limitsEnforced: riskSettings.limitsEnforced,
        }
      : undefined,
    strategy: showStrategy
      ? {
          strategyId: strategyId ? Number(strategyId) : undefined,
          strategyName: selectedStrategyName,
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
    if (variant !== "replay") {
      if (!symbol) return toast.error("Symbol is required.")
      if (rangeBy === "dates" && (!startDate || !endDate)) return toast.error("Start and end dates are required.")
    }
    
    if (mode === "strategy" && !strategyId) return toast.error("Strategy is required for strategy runs.")
    if (mode === "replay" && !replayBacktestId) return toast.error("Please select or import a backtest to replay.")
    
    try {
      setSubmitting(true)
      if (executionMode === "visualized") {
        // For replays, if we're not already on the specific backtest page, redirect there first
        // This allows the page to load because of the URL, and then auto-start
        if (mode === "replay" && replayBacktestId && !initialAutoStartReplay) {
          const params = new URLSearchParams()
          if (replaySource === "csv") {
            params.set("replaySource", "csv")
          }
          const query = params.toString()
          const target = `/simulation/replay/backtest/${replayBacktestId}`
          router.push(query ? `${target}?${query}` : target)
          setSubmitting(false)
          return
        }

        const payload = historicalRunConfigToSimulationPayload(config)
        const response = await simulatorApi.startSession(payload)
        
        // If we are already on the replay page or it's not a replay, we can proceed
        if (mode === "replay" && replayBacktestId) {
          // Ensure we are on the right URL, but use replace to not add to history if we're already basically there
          router.replace(`/simulation/replay/backtest/${replayBacktestId}`)
        }
        
        toast.success("Historical run started", { description: `Session ${response.session_id}` })
        onSimulationStart(response.session_id, config, response)
        return
      }
      const plan = historicalRunConfigToBacktestPayload(config)
      const result = plan.isPortfolio
        ? await backtestApi.runPortfolio(plan.strategyId, plan.payload as PortfolioBacktestRunPayload)
        : await backtestApi.run(plan.strategyId, plan.payload as BacktestRunPayload)
      toast.success("Batch backtest started", { description: `Backtest ${result.backtest_id}` })
      onBacktestStart(result.backtest_id, plan.strategyId, config)
    } catch (error) {
      toast.error("Failed to start historical run", { description: getErrorMessage(error) })
    } finally {
      setSubmitting(false)
    }
  }

  useEffect(() => {
    handleSubmitRef.current = () => {
      void handleSubmit()
    }
  })

  useEffect(() => {
    if (
      autoStartAttemptedRef.current ||
      !initialAutoStartReplay ||
      variant !== "replay" ||
      mode !== "replay" ||
      !replayBacktestId ||
      submitting
    ) {
      return
    }
    autoStartAttemptedRef.current = true
    handleSubmitRef.current()
  }, [initialAutoStartReplay, mode, replayBacktestId, submitting, variant])

  return (
    <div className="grid gap-6">
      {showSessionControls && pausedSessions.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Resume Session</CardTitle>
            <CardDescription>Continue a paused visualized run.</CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-1 md:grid-cols-[1fr_auto] gap-4">
            <Select value={selectedPausedId} onValueChange={setSelectedPausedId}>
              <SelectTrigger><SelectValue placeholder="Select paused session" /></SelectTrigger>
              <SelectContent>
                {pausedSessions.map((session) => (
                  <SelectItem key={session.session_id} value={String(session.session_id)}>
                    {`${session.session_name || `Session ${session.session_id}`} (${session.symbol ?? session.config?.symbol ?? "N/A"} ${session.timeframe ?? session.config?.timeframe ?? "N/A"})`}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button onClick={handleResume} disabled={submitting}>Resume</Button>
          </CardContent>
        </Card>
      )}

      {variant !== "replay" && (
        <Card>
          <CardHeader>
            <CardTitle>Data Settings</CardTitle>
            <CardDescription>
              {variant === "manual" ? "Configure symbol and timeframe for manual trading." : "Common inputs for the simulation run."}
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="symbol">Symbol(s)</Label>
                <Input id="symbol" value={symbol} onChange={(e) => setSymbol(e.target.value.toUpperCase())} placeholder="EURUSD or EURUSD, GBPUSD" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="timeframe">Timeframe</Label>
                <Select value={timeframe} onValueChange={setTimeframe}>
                  <SelectTrigger id="timeframe"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="M1">M1</SelectItem>
                    <SelectItem value="M5">M5</SelectItem>
                    <SelectItem value="M15">M15</SelectItem>
                    <SelectItem value="H1">H1</SelectItem>
                    <SelectItem value="H4">H4</SelectItem>
                    <SelectItem value="D1">D1</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            
            {(variant === "visual_auto" || variant === "batch_auto") && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <RangeModeSelector value={rangeBy} onValueChange={setRangeBy} variant="toggle" />
                <div className="grid grid-cols-2 gap-2">
                  <div className="space-y-2">
                    <Label htmlFor="startDate">Start</Label>
                    <Input id="startDate" type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="endDate">End</Label>
                    <Input id="endDate" type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {variant?.includes("auto") && (
        <Card>
          <CardHeader>
            <CardTitle>Strategy</CardTitle>
            <CardDescription>Select the strategy and parameters for automated execution.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-6">
            <div className="space-y-2">
              <Label>Target Strategy</Label>
              <Select
                value={strategyId ? `strategy:${strategyId}` : "__select_strategy__"}
                onValueChange={(val) => setStrategyId(val.replace("strategy:", ""))}
              >
                <SelectTrigger>
                  <SelectValue placeholder={loadingStrategies ? "Loading..." : "Select strategy"} />
                </SelectTrigger>
                <SelectContent>
                  {strategies.map((strategy) => (
                    <SelectItem key={strategy.id} value={`strategy:${strategy.id}`}>
                      {strategy.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {showStrategy && (
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
            )}
          </CardContent>
        </Card>
      )}

      {variant === "replay" && (
        <Card>
          <CardHeader>
            <CardTitle>Replay Source</CardTitle>
            <CardDescription>Select a previously completed backtest to replay tick-by-tick.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-6">
            <div className="space-y-2">
              <Label>Source Type</Label>
              <ToggleGroup type="single" value={replaySource} onValueChange={(value) => value && setReplaySource(value as ReplaySource)}>
                <ToggleGroupItem value="backtest" className="flex-1">Existing Backtest</ToggleGroupItem>
                <ToggleGroupItem value="csv" className="flex-1">CSV Import</ToggleGroupItem>
              </ToggleGroup>
            </div>
            
            {replaySource === "backtest" ? (
              <div className="space-y-2">
                <Label htmlFor="replayBacktestId">Select Backtest</Label>
                <Select value={replayBacktestId} onValueChange={setReplayBacktestId} disabled={loadingBacktests}>
                  <SelectTrigger id="replayBacktestId">
                    <SelectValue placeholder={loadingBacktests ? "Loading..." : "Select a backtest result"} />
                  </SelectTrigger>
                  <SelectContent>
                    {backtests.map((backtest) => (
                      <SelectItem key={backtest.backtest_id} value={backtest.backtest_id.toString()}>
                        {(backtest.alias || backtest.strategy_name || "Backtest") + ` (#${backtest.backtest_id})`}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground pt-1">
                  Replay will automatically use the symbol, timeframe, and dates from the selected backtest.
                </p>
              </div>
            ) : (
              <div className="grid gap-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2"><Label htmlFor="importStrategyName">Strategy Name</Label><Input id="importStrategyName" value={importStrategyName} onChange={(e) => setImportStrategyName(e.target.value)} /></div>
                  <div className="space-y-2"><Label htmlFor="importFile">CSV File</Label><Input id="importFile" type="file" accept=".csv" onChange={(e) => setImportFile(e.target.files?.[0] || null)} /></div>
                </div>
                <Button onClick={handleCsvImport} disabled={importing}>{importing ? "Importing..." : "Import CSV"}</Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {variant !== "replay" && (
        <EngineSettings 
          values={engineSettings} 
          onChange={(key, value) => setEngineSettings((prev) => ({ ...prev, [key]: value }))} 
        />
      )}

      <div className="flex justify-end pt-4">
        <Button
          size="lg"
          onClick={handleSubmit}
          disabled={submitting || importing || loadingStrategies}
          className="px-8"
        >
          {submitting
            ? "Starting..."
            : variant === "visual_auto"
              ? "Start Visualized Auto Run"
              : variant === "batch_auto"
                ? "Run Batch Backtest"
                : variant === "manual"
                  ? "Start Manual Simulation"
                  : variant === "replay"
                    ? "Start Replay"
                    : "Start Simulation"}
        </Button>
      </div>
    </div>
  )
}
