"use client"

import { useEffect, useMemo, useState } from "react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import {
  EngineSettings,
  type EngineSettingsValues,
} from "@/components/backtest/engine-settings"
import { StrategyParametersCard } from "@/components/historical-run/strategy-parameters-card"
import { RangeModeSelector } from "@/components/historical-run/range-mode-selector"
import { RunSourceSelector } from "@/components/historical-run/run-source-selector"
import { StrategySelector } from "@/components/historical-run/strategy-selector"
import { getErrorMessage } from "@/lib/api-error"
import { strategyApi, type StrategyCodeResponse } from "@/lib/api/strategies"
import { useAllBacktests, useStrategies } from "@/lib/use-strategies"
import simulatorApi, {
  type ReplaySource,
  type SimulationConfig,
  type SimulationDataResolution,
  type SimulationMode,
  type SimulationRiskHorizonUnit,
  type SimulationSession,
  type SimulationStartResponse,
} from "@/lib/api/simulator"

interface SimulationConfigFormProps {
  onStart: (sessionId: number, config: SimulationConfig, response?: SimulationStartResponse) => void
  onResume: (sessionId: number) => void
}

const speedOptions = [
  { label: "X1", value: "1" },
  { label: "X5", value: "5" },
  { label: "X15", value: "15" },
  { label: "X30", value: "30" },
  { label: "X60", value: "60" },
  { label: "X120", value: "120" },
  { label: "X240", value: "240" },
  { label: "X720", value: "720" },
  { label: "X1440", value: "1440" },
]

const riskPresetsByTimeframe: Partial<
  Record<string, { horizonUnit: SimulationRiskHorizonUnit; horizonValue: number; volLookback: number; corrLookback: number }>
> = {
  M5: {
    horizonUnit: "hours",
    horizonValue: 1,
    volLookback: 48,
    corrLookback: 96,
  },
  H1: {
    horizonUnit: "hours",
    horizonValue: 1,
    volLookback: 24,
    corrLookback: 72,
  },
  D1: {
    horizonUnit: "days",
    horizonValue: 1,
    volLookback: 20,
    corrLookback: 60,
  },
}

export function SimulationConfigForm({ onStart, onResume }: SimulationConfigFormProps) {
  const { strategies, loading: loadingStrategies } = useStrategies()
  const { backtests, loading: loadingBacktests } = useAllBacktests(200)

  const [sessionName, setSessionName] = useState("")
  const [symbol, setSymbol] = useState("EURUSD")
  const [timeframe, setTimeframe] = useState("H1")
  const [speed, setSpeed] = useState("1")
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
    varCapFrac: 0.10,
    esCapFrac: 0.15,
    deltaVarCapFrac: 0.02,
    deltaEsCapFrac: 0.03,
    maxMarginUsedFrac: 0.50,
    maxSingleRcFrac: 0.10,
    warningUtilizationFrac: 0.90,
    limitsEnforced: true,
  })

  const [rangeBy, setRangeBy] = useState<"dates" | "bars">("bars")
  const [startDate, setStartDate] = useState("")
  const [endDate, setEndDate] = useState("")
  const [numberOfBars, setNumberOfBars] = useState(500)

  const [mode, setMode] = useState<SimulationMode>("manual")
  const [strategyId, setStrategyId] = useState("")
  const [strategyVersionId, setStrategyVersionId] = useState<number | undefined>(undefined)
  const [strategyParams, setStrategyParams] = useState<Record<string, unknown>>({})
  const [strategyParameterTypes, setStrategyParameterTypes] = useState<Record<string, string>>({})
  const [loadingStrategyParams, setLoadingStrategyParams] = useState(false)
  const [replaySource, setReplaySource] = useState<ReplaySource>("backtest")
  const [replayBacktestId, setReplayBacktestId] = useState("")
  const [replayFileName, setReplayFileName] = useState("")

  const [submitting, setSubmitting] = useState(false)

  const [pausedSessions, setPausedSessions] = useState<SimulationSession[]>([])
  const [selectedPausedId, setSelectedPausedId] = useState("")

  const [importFile, setImportFile] = useState<File | null>(null)
  const [importStrategyName, setImportStrategyName] = useState("")
  const [importAlias, setImportAlias] = useState("")
  const [importDescription, setImportDescription] = useState("")
  const [importing, setImporting] = useState(false)

  useEffect(() => {
    const loadPausedSessions = async () => {
      try {
        const data = await simulatorApi.getPausedSessions()
        setPausedSessions(data)
        if (data.length > 0) {
          setSelectedPausedId(String(data[0].session_id))
        }
      } catch (error) {
        toast.error("Failed to load paused sessions", {
          description: getErrorMessage(error),
        })
      }
    }

    loadPausedSessions()
  }, [])

  useEffect(() => {
    const preset = riskPresetsByTimeframe[timeframe]
    if (!preset) {
      return
    }
    setRiskSettings((prev) => ({
      ...prev,
      horizonUnit: preset.horizonUnit,
      horizonValue: preset.horizonValue,
      volLookback: preset.volLookback,
      corrLookback: preset.corrLookback,
    }))
  }, [timeframe])

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

  const pausedOptions = useMemo(() => {
    return pausedSessions.map((session) => {
      const name = session.session_name || `Session ${session.session_id}`
      const meta = `${session.symbol} ${session.timeframe}`
      return {
        label: `${name} (${meta})`,
        value: String(session.session_id),
      }
    })
  }, [pausedSessions])
  const symbolCount = symbol.split(",").map((item) => item.trim()).filter(Boolean).length

  const handleStart = async () => {
    if (!symbol) {
      toast.error("Symbol is required.")
      return
    }

    if (rangeBy === "dates" && (!startDate || !endDate)) {
      toast.error("Start and end dates are required.")
      return
    }

    if (rangeBy === "bars" && (!numberOfBars || numberOfBars <= 0)) {
      toast.error("Please enter a valid number of bars.")
      return
    }

    if (mode === "strategy" && !strategyId) {
      toast.error("Strategy is required for strategy mode.")
      return
    }

    if (mode === "replay" && !replayBacktestId) {
      toast.error("Please select or import a backtest to replay.")
      return
    }

    const config: SimulationConfig = {
      session_name: sessionName || undefined,
      symbol,
      timeframe,
      initial_balance: engineSettings.initialCapital,
      speed_multiplier: Number(speed),
      commission: engineSettings.commission,
      leverage: engineSettings.leverage,
      slippage_type: engineSettings.slippageType,
      slippage: engineSettings.slippage,
      slippage_min: engineSettings.slippageMin,
      slippage_max: engineSettings.slippageMax,
      spread_type: engineSettings.spreadType,
      spread: engineSettings.spread,
      spread_min: engineSettings.spreadMin,
      spread_max: engineSettings.spreadMax,
      data_resolution: engineSettings.dataResolution as SimulationDataResolution,
      risk_confidence_level: riskSettings.confidenceLevel,
      risk_horizon_unit: riskSettings.horizonUnit,
      risk_horizon_value: riskSettings.horizonValue,
      risk_vol_lookback: riskSettings.volLookback,
      risk_corr_lookback: riskSettings.corrLookback,
      risk_var_cap_frac: riskSettings.varCapFrac,
      risk_es_cap_frac: riskSettings.esCapFrac,
      risk_delta_var_cap_frac: riskSettings.deltaVarCapFrac,
      risk_delta_es_cap_frac: riskSettings.deltaEsCapFrac,
      risk_max_margin_used_frac: riskSettings.maxMarginUsedFrac,
      risk_max_single_rc_frac: riskSettings.maxSingleRcFrac,
      risk_warning_utilization_frac: riskSettings.warningUtilizationFrac,
      risk_limits_enforced: riskSettings.limitsEnforced,
      mode,
    }

    if (rangeBy === "dates") {
      config.start_time = startDate
      config.end_time = endDate
    } else {
      config.number_of_bars = numberOfBars
    }

    if (mode === "strategy") {
      config.strategy_id = Number(strategyId)
      config.strategy_version_id = strategyVersionId
      config.strategy_params = strategyParams
    }

    if (mode === "replay") {
      config.replay_source = replaySource
      config.replay_backtest_id = Number(replayBacktestId)
      if (replayFileName) {
        config.replay_file_name = replayFileName
      }
    }

    try {
      setSubmitting(true)
      const response = await simulatorApi.startSession(config)
      toast.success("Simulation started", {
        description: `Session ${response.session_id}`,
      })
      onStart(response.session_id, config, response)
    } catch (error) {
      toast.error("Failed to start simulation", {
        description: getErrorMessage(error),
      })
    } finally {
      setSubmitting(false)
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
      toast.success("Session resumed", {
        description: `Session ${response.session_id}`,
      })
      onResume(response.session_id)
    } catch (error) {
      toast.error("Failed to resume session", {
        description: getErrorMessage(error),
      })
    } finally {
      setSubmitting(false)
    }
  }

  const handleCsvImport = async () => {
    if (!importFile) {
      toast.error("Please choose a CSV file to import.")
      return
    }

    if (!importStrategyName) {
      toast.error("Strategy name is required for CSV import.")
      return
    }

    if (!symbol) {
      toast.error("Symbol is required for CSV import.")
      return
    }

    if (!timeframe) {
      toast.error("Timeframe is required for CSV import.")
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
      const headers: HeadersInit = {}
      if (token) {
        headers["Authorization"] = `Bearer ${token}`
      }

      const response = await fetch(`${baseUrl}/api/import/sqx`, {
        method: "POST",
        body: formData,
        headers,
      })

      if (!response.ok) {
        const text = await response.text()
        let detail = text
        try {
          const data = JSON.parse(text)
          detail = data?.detail || data?.message || text
        } catch {
          // keep raw text
        }
        throw new Error(detail)
      }

      const data = await response.json()
      const importedId = Number(data.backtest_id)
      setReplayBacktestId(String(importedId))
      setReplaySource("csv")
      setReplayFileName(importFile.name)
      toast.success("CSV imported", {
        description: `Backtest ${importedId} ready to replay.`,
      })
    } catch (error) {
      toast.error("Failed to import CSV", {
        description: getErrorMessage(error),
      })
    } finally {
      setImporting(false)
    }
  }

  return (
    <div className="grid gap-6">
      {pausedOptions.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Resume Session</CardTitle>
            <CardDescription>Continue a paused simulator session.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4">
            <div className="grid grid-cols-1 md:grid-cols-[1fr_auto] gap-4">
              <Select
                value={selectedPausedId}
                onValueChange={(val) => setSelectedPausedId(val)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select paused session" />
                </SelectTrigger>
                <SelectContent>
                  {pausedOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button onClick={handleResume} disabled={submitting}>
                Resume
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Simulation Configuration</CardTitle>
          <CardDescription>Set up your simulator session.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="sessionName">Session Name (optional)</Label>
              <Input
                id="sessionName"
                value={sessionName}
                onChange={(e) => setSessionName(e.target.value)}
                placeholder="e.g. London Session Replay"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="speed">Speed</Label>
              <Select value={speed} onValueChange={setSpeed}>
                <SelectTrigger id="speed">
                  <SelectValue placeholder="Select speed" />
                </SelectTrigger>
                <SelectContent>
                  {speedOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="symbol">Symbol</Label>
              <Input
                id="symbol"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                placeholder="EURUSD or EURUSD, GBPUSD"
              />
              {symbolCount > 1 && symbolCount <= 4 && (
                <p className="text-xs text-muted-foreground">
                  Visualized simulation will render {symbolCount} charts, one per symbol.
                </p>
              )}
              {symbolCount > 4 && (
                <p className="text-xs text-muted-foreground">
                  Visualized simulation will switch to table view when more than 4 symbols are entered.
                </p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="timeframe">Timeframe</Label>
              <Select value={timeframe} onValueChange={setTimeframe}>
                <SelectTrigger id="timeframe">
                  <SelectValue />
                </SelectTrigger>
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

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <RunSourceSelector value={mode} onValueChange={setMode} />
            <RangeModeSelector
              value={rangeBy}
              onValueChange={setRangeBy}
              variant="toggle"
            />
          </div>

          {rangeBy === "dates" ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="startDate">Start Date</Label>
                <Input
                  id="startDate"
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="endDate">End Date</Label>
                <Input
                  id="endDate"
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                />
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              <Label htmlFor="numberOfBars">Number of Bars</Label>
              <Input
                id="numberOfBars"
                type="number"
                min="1"
                value={numberOfBars}
                onChange={(e) => setNumberOfBars(Number(e.target.value))}
              />
            </div>
          )}
        </CardContent>
      </Card>

      {mode === "strategy" && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>Strategy Selection</CardTitle>
              <CardDescription>Select a strategy to execute.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4">
              <StrategySelector
                id="strategyId"
                value={strategyId}
                onValueChange={setStrategyId}
                strategies={strategies}
                loading={loadingStrategies}
              />
            </CardContent>
          </Card>
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

      {mode === "replay" && (
        <Card>
          <CardHeader>
            <CardTitle>Replay Source</CardTitle>
            <CardDescription>Choose a stored backtest or import CSV.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-6">
            <div className="space-y-2">
              <Label>Source</Label>
              <ToggleGroup
                type="single"
                value={replaySource}
                onValueChange={(val) => val && setReplaySource(val as ReplaySource)}
              >
                <ToggleGroupItem value="backtest">Backtest</ToggleGroupItem>
                <ToggleGroupItem value="csv">CSV Import</ToggleGroupItem>
              </ToggleGroup>
            </div>

            {replaySource === "backtest" ? (
              <div className="space-y-2">
                <Label htmlFor="replayBacktestId">Backtest</Label>
                <Select
                  value={replayBacktestId}
                  onValueChange={setReplayBacktestId}
                  disabled={loadingBacktests}
                >
                  <SelectTrigger id="replayBacktestId">
                    <SelectValue placeholder={loadingBacktests ? "Loading..." : "Select backtest"} />
                  </SelectTrigger>
                  <SelectContent>
                    {backtests.map((backtest) => (
                      <SelectItem
                        key={backtest.backtest_id}
                        value={backtest.backtest_id.toString()}
                      >
                        {(backtest.alias || backtest.strategy_name || "Backtest") +
                          ` (#${backtest.backtest_id})`}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            ) : (
              <div className="grid gap-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="importStrategyName">Strategy Name</Label>
                    <Input
                      id="importStrategyName"
                      value={importStrategyName}
                      onChange={(e) => setImportStrategyName(e.target.value)}
                      placeholder="e.g. SQX_Import_01"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="importFile">CSV File</Label>
                    <Input
                      id="importFile"
                      type="file"
                      accept=".csv"
                      onChange={(e) => {
                        const file = e.target.files?.[0] || null
                        setImportFile(file)
                      }}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="importAlias">Alias (optional)</Label>
                    <Input
                      id="importAlias"
                      value={importAlias}
                      onChange={(e) => setImportAlias(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="importDescription">Description (optional)</Label>
                    <Input
                      id="importDescription"
                      value={importDescription}
                      onChange={(e) => setImportDescription(e.target.value)}
                    />
                  </div>
                </div>

                <Button onClick={handleCsvImport} disabled={importing}>
                  {importing ? "Importing..." : "Import CSV"}
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      <EngineSettings
        values={engineSettings}
        onChange={(key, value) =>
          setEngineSettings((prev) => ({
            ...prev,
            [key]: value,
          }))
        }
      />

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Risk Settings</CardTitle>
          <CardDescription>Configure the VaR, CVaR, and limit inputs for this simulation session.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4">
          <div className="space-y-2">
            <Label>Risk Limit Mode</Label>
            <ToggleGroup
              type="single"
              value={riskSettings.limitsEnforced ? "blocking" : "descriptive"}
              onValueChange={(value) => {
                if (!value) return
                setRiskSettings((prev) => ({
                  ...prev,
                  limitsEnforced: value === "blocking",
                }))
              }}
            >
              <ToggleGroupItem value="blocking">Blocking</ToggleGroupItem>
              <ToggleGroupItem value="descriptive">Descriptive Only</ToggleGroupItem>
            </ToggleGroup>
            <div className="text-xs text-muted-foreground">
              Blocking rejects trades and pending orders on governance breaches. Descriptive Only still computes and shows governance warnings without enforcing them.
            </div>
          </div>
          <div className="space-y-1">
            <div className="text-sm font-medium">VaR And CVaR</div>
            <div className="text-xs text-muted-foreground">
              Controls the descriptive portfolio risk snapshot calculations.
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="space-y-2">
              <Label htmlFor="riskConfidenceLevel">Confidence Level</Label>
              <Input
                id="riskConfidenceLevel"
                type="number"
                min="0.5"
                max="0.999"
                step="0.01"
                value={riskSettings.confidenceLevel}
                onChange={(e) =>
                  setRiskSettings((prev) => ({
                    ...prev,
                    confidenceLevel: Number(e.target.value) || 0.95,
                  }))
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="riskHorizonUnit">Risk Horizon Unit</Label>
              <Select
                value={riskSettings.horizonUnit}
                onValueChange={(value) =>
                  setRiskSettings((prev) => ({
                    ...prev,
                    horizonUnit: value as SimulationRiskHorizonUnit,
                  }))
                }
              >
                <SelectTrigger id="riskHorizonUnit">
                  <SelectValue placeholder="Select horizon unit" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="bars">Bars</SelectItem>
                  <SelectItem value="hours">Hours</SelectItem>
                  <SelectItem value="days">Days</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="riskHorizonValue">Risk Horizon Value</Label>
              <Input
                id="riskHorizonValue"
                type="number"
                min="1"
                step="1"
                value={riskSettings.horizonValue}
                onChange={(e) =>
                  setRiskSettings((prev) => ({
                    ...prev,
                    horizonValue: Number.parseInt(e.target.value, 10) || 1,
                  }))
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="riskVolLookback">Volatility Lookback</Label>
              <Input
                id="riskVolLookback"
                type="number"
                min="2"
                step="1"
                value={riskSettings.volLookback}
                onChange={(e) =>
                  setRiskSettings((prev) => ({
                    ...prev,
                    volLookback: Number.parseInt(e.target.value, 10) || 20,
                  }))
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="riskCorrLookback">Correlation Lookback</Label>
              <Input
                id="riskCorrLookback"
                type="number"
                min="2"
                step="1"
                value={riskSettings.corrLookback}
                onChange={(e) =>
                  setRiskSettings((prev) => ({
                    ...prev,
                    corrLookback: Number.parseInt(e.target.value, 10) || 60,
                  }))
                }
              />
            </div>
          </div>
          <div className="space-y-1 pt-2">
            <div className="text-sm font-medium">Limits</div>
            <div className="text-xs text-muted-foreground">
              These values feed the current compliance and warning status.
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="riskVarCapFrac">VaR Cap %</Label>
              <Input
                id="riskVarCapFrac"
                type="number"
                min="0"
                step="0.01"
                value={riskSettings.varCapFrac}
                onChange={(e) =>
                  setRiskSettings((prev) => ({
                    ...prev,
                    varCapFrac: Number(e.target.value) || 0,
                  }))
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="riskEsCapFrac">CVaR Cap %</Label>
              <Input
                id="riskEsCapFrac"
                type="number"
                min="0"
                step="0.01"
                value={riskSettings.esCapFrac}
                onChange={(e) =>
                  setRiskSettings((prev) => ({
                    ...prev,
                    esCapFrac: Number(e.target.value) || 0,
                  }))
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="riskDeltaVarCapFrac">Delta VaR Cap %</Label>
              <Input
                id="riskDeltaVarCapFrac"
                type="number"
                min="0"
                step="0.01"
                value={riskSettings.deltaVarCapFrac}
                onChange={(e) =>
                  setRiskSettings((prev) => ({
                    ...prev,
                    deltaVarCapFrac: Number(e.target.value) || 0,
                  }))
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="riskDeltaEsCapFrac">Delta CVaR Cap %</Label>
              <Input
                id="riskDeltaEsCapFrac"
                type="number"
                min="0"
                step="0.01"
                value={riskSettings.deltaEsCapFrac}
                onChange={(e) =>
                  setRiskSettings((prev) => ({
                    ...prev,
                    deltaEsCapFrac: Number(e.target.value) || 0,
                  }))
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="riskMaxMarginUsedFrac">Max Margin Used %</Label>
              <Input
                id="riskMaxMarginUsedFrac"
                type="number"
                min="0"
                step="0.01"
                value={riskSettings.maxMarginUsedFrac}
                onChange={(e) =>
                  setRiskSettings((prev) => ({
                    ...prev,
                    maxMarginUsedFrac: Number(e.target.value) || 0,
                  }))
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="riskMaxSingleRcFrac">Max Single Risk Contribution Buffer %</Label>
              <Input
                id="riskMaxSingleRcFrac"
                type="number"
                min="0"
                step="0.01"
                value={riskSettings.maxSingleRcFrac}
                onChange={(e) =>
                  setRiskSettings((prev) => ({
                    ...prev,
                    maxSingleRcFrac: Number(e.target.value) || 0,
                  }))
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="riskWarningUtilizationFrac">Warning Utilization %</Label>
              <Input
                id="riskWarningUtilizationFrac"
                type="number"
                min="0"
                step="0.01"
                value={riskSettings.warningUtilizationFrac}
                onChange={(e) =>
                  setRiskSettings((prev) => ({
                    ...prev,
                    warningUtilizationFrac: Number(e.target.value) || 0,
                  }))
                }
              />
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-end">
        <Button
          size="lg"
          onClick={handleStart}
          disabled={submitting || importing || loadingStrategies}
        >
          {submitting ? "Starting..." : "Start Simulation"}
        </Button>
      </div>
    </div>
  )
}
