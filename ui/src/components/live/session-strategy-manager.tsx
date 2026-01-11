"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Plus, Trash2, Loader2, AlertCircle } from "lucide-react"
import { LiveTradingAPI } from "@/lib/api/live"
import { strategyApi, type Strategy, type StrategyVersion } from "@/lib/api/strategies"
import type { SessionStrategy, StrategyAddRequest } from "@/types/live"
import { toast } from "sonner"
import { Alert, AlertDescription } from "@/components/ui/alert"

interface SessionStrategyManagerProps {
  sessionId: number
  sessionStatus: string
}

export function SessionStrategyManager({ sessionId, sessionStatus }: SessionStrategyManagerProps) {
  const [sessionStrategies, setSessionStrategies] = useState<SessionStrategy[]>([])
  const [availableStrategies, setAvailableStrategies] = useState<Strategy[]>([])
  const [strategyVersions, setStrategyVersions] = useState<StrategyVersion[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false)
  const [isAdding, setIsAdding] = useState(false)

  // Form state
  const [selectedStrategyId, setSelectedStrategyId] = useState<number | null>(null)
  const [selectedVersionId, setSelectedVersionId] = useState<number | null>(null)
  const [symbols, setSymbols] = useState("EURUSD")
  const [timeframes, setTimeframes] = useState("M15")
  const [maxRiskPerTrade, setMaxRiskPerTrade] = useState(1.0)
  const [positionSizeType, setPositionSizeType] = useState<"risk" | "fixed" | "percent">("risk")
  const [positionSizeValue, setPositionSizeValue] = useState(1.0)

  const isStopped = sessionStatus === "stopped"

  // Load session strategies
  useEffect(() => {
    loadSessionStrategies()
  }, [sessionId])

  // Load available strategies
  useEffect(() => {
    loadAvailableStrategies()
  }, [])

  // Load versions when strategy is selected
  useEffect(() => {
    if (selectedStrategyId) {
      loadStrategyVersions(selectedStrategyId)
    }
  }, [selectedStrategyId])

  const loadSessionStrategies = async () => {
    try {
      setIsLoading(true)
      const response = await LiveTradingAPI.getSessionStrategies(sessionId)
      setSessionStrategies(response.strategies || [])
    } catch (err) {
      console.error("Error loading session strategies:", err)
      toast.error("Failed to load strategies")
    } finally {
      setIsLoading(false)
    }
  }

  const loadAvailableStrategies = async () => {
    try {
      const strategies = await strategyApi.list({ status: "active" })
      setAvailableStrategies(strategies)
    } catch (err) {
      console.error("Error loading available strategies:", err)
      toast.error("Failed to load available strategies")
    }
  }

  const loadStrategyVersions = async (strategyId: number) => {
    try {
      const versions = await strategyApi.listVersions(strategyId)
      setStrategyVersions(versions)
      // Auto-select the latest version (last in list)
      if (versions.length > 0) {
        setSelectedVersionId(versions[versions.length - 1].id)
      }
    } catch (err) {
      console.error("Error loading strategy versions:", err)
      toast.error("Failed to load strategy versions")
    }
  }

  const handleAddStrategy = async () => {
    if (!selectedVersionId) {
      toast.error("Please select a strategy version")
      return
    }

    try {
      setIsAdding(true)

      const symbolsArray = symbols.split(",").map(s => s.trim()).filter(Boolean)
      const timeframesArray = timeframes.split(",").map(t => t.trim()).filter(Boolean)

      if (symbolsArray.length === 0) {
        toast.error("Please enter at least one symbol")
        return
      }

      if (timeframesArray.length === 0) {
        toast.error("Please enter at least one timeframe")
        return
      }

      const request: StrategyAddRequest = {
        strategy_version_id: selectedVersionId,
        symbols: symbolsArray,
        timeframes: timeframesArray,
        max_risk_per_trade_pct: maxRiskPerTrade,
        position_size_type: positionSizeType,
        position_size_value: positionSizeValue,
      }

      await LiveTradingAPI.addStrategy(sessionId, request)

      toast.success("Strategy Added", {
        description: "Strategy has been added to the session"
      })

      // Reset form and close dialog
      resetForm()
      setIsAddDialogOpen(false)

      // Reload strategies
      await loadSessionStrategies()
    } catch (err) {
      console.error("Error adding strategy:", err)
      toast.error("Failed to add strategy", {
        description: err instanceof Error ? err.message : "Unknown error"
      })
    } finally {
      setIsAdding(false)
    }
  }

  const handleRemoveStrategy = async (strategyConfigId: number, strategyName: string) => {
    if (!confirm(`Are you sure you want to remove ${strategyName} from this session?`)) {
      return
    }

    try {
      await LiveTradingAPI.removeStrategy(sessionId, strategyConfigId)

      toast.success("Strategy Removed", {
        description: `${strategyName} has been removed from the session`
      })

      // Reload strategies
      await loadSessionStrategies()
    } catch (err) {
      console.error("Error removing strategy:", err)
      toast.error("Failed to remove strategy", {
        description: err instanceof Error ? err.message : "Unknown error"
      })
    }
  }

  const resetForm = () => {
    setSelectedStrategyId(null)
    setSelectedVersionId(null)
    setSymbols("EURUSD")
    setTimeframes("M15")
    setMaxRiskPerTrade(1.0)
    setPositionSizeType("risk")
    setPositionSizeValue(1.0)
    setStrategyVersions([])
  }

  const getStrategyDisplayName = (strategy: SessionStrategy): string => {
    return `${strategy.strategy_name} (v${strategy.version})`
  }

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Session Strategies</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
        <div>
          <CardTitle className="text-sm font-medium">Session Strategies</CardTitle>
          <CardDescription className="text-xs">
            Strategies active in this session
          </CardDescription>
        </div>
        <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
          <DialogTrigger asChild>
            <Button
              size="sm"
              disabled={!isStopped}
              variant="outline"
            >
              <Plus className="mr-2 h-4 w-4" />
              Add Strategy
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[600px]">
            <DialogHeader>
              <DialogTitle>Add Strategy to Session</DialogTitle>
              <DialogDescription>
                Configure a strategy to run in this trading session
              </DialogDescription>
            </DialogHeader>

            <div className="grid gap-4 py-4">
              {/* Strategy Selection */}
              <div className="grid gap-2">
                <Label htmlFor="strategy">Strategy</Label>
                <Select
                  value={selectedStrategyId?.toString()}
                  onValueChange={(value) => setSelectedStrategyId(parseInt(value))}
                >
                  <SelectTrigger id="strategy">
                    <SelectValue placeholder="Select a strategy" />
                  </SelectTrigger>
                  <SelectContent>
                    {availableStrategies.map((strategy) => (
                      <SelectItem key={strategy.id} value={strategy.id.toString()}>
                        {strategy.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Version Selection */}
              {selectedStrategyId && (
                <div className="grid gap-2">
                  <Label htmlFor="version">Version</Label>
                  <Select
                    value={selectedVersionId?.toString()}
                    onValueChange={(value) => setSelectedVersionId(parseInt(value))}
                  >
                    <SelectTrigger id="version">
                      <SelectValue placeholder="Select version" />
                    </SelectTrigger>
                    <SelectContent>
                      {strategyVersions.map((version) => (
                        <SelectItem key={version.id} value={version.id.toString()}>
                          {version.version}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}

              {/* Symbols */}
              <div className="grid gap-2">
                <Label htmlFor="symbols">Symbols</Label>
                <Input
                  id="symbols"
                  placeholder="e.g., EURUSD, GBPUSD"
                  value={symbols}
                  onChange={(e) => setSymbols(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  Comma-separated list of symbols to trade
                </p>
              </div>

              {/* Timeframes */}
              <div className="grid gap-2">
                <Label htmlFor="timeframes">Timeframes</Label>
                <Input
                  id="timeframes"
                  placeholder="e.g., M15, H1"
                  value={timeframes}
                  onChange={(e) => setTimeframes(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  Comma-separated list of timeframes to monitor
                </p>
              </div>

              {/* Risk Settings */}
              <div className="grid grid-cols-2 gap-4">
                <div className="grid gap-2">
                  <Label htmlFor="maxRisk">Max Risk per Trade (%)</Label>
                  <Input
                    id="maxRisk"
                    type="number"
                    step="0.1"
                    min="0.1"
                    max="10"
                    value={maxRiskPerTrade}
                    onChange={(e) => setMaxRiskPerTrade(parseFloat(e.target.value))}
                  />
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="positionSizeType">Position Size Type</Label>
                  <Select
                    value={positionSizeType}
                    onValueChange={(value: any) => setPositionSizeType(value)}
                  >
                    <SelectTrigger id="positionSizeType">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="risk">Risk-based</SelectItem>
                      <SelectItem value="fixed">Fixed Lots</SelectItem>
                      <SelectItem value="percent">Percent of Balance</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="grid gap-2">
                <Label htmlFor="positionSizeValue">Position Size Value</Label>
                <Input
                  id="positionSizeValue"
                  type="number"
                  step="0.1"
                  min="0.1"
                  value={positionSizeValue}
                  onChange={(e) => setPositionSizeValue(parseFloat(e.target.value))}
                />
                <p className="text-xs text-muted-foreground">
                  {positionSizeType === "risk" && "Risk amount per trade (%)"}
                  {positionSizeType === "fixed" && "Fixed lot size"}
                  {positionSizeType === "percent" && "Percent of balance per trade"}
                </p>
              </div>
            </div>

            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => {
                  resetForm()
                  setIsAddDialogOpen(false)
                }}
                disabled={isAdding}
              >
                Cancel
              </Button>
              <Button onClick={handleAddStrategy} disabled={isAdding || !selectedVersionId}>
                {isAdding ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Adding...
                  </>
                ) : (
                  "Add Strategy"
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </CardHeader>
      <CardContent>
        {!isStopped && (
          <Alert className="mb-4">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              Session must be stopped to add or remove strategies
            </AlertDescription>
          </Alert>
        )}

        {sessionStrategies.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <p className="text-sm">No strategies added to this session</p>
            <p className="text-xs mt-1">Add a strategy to start detecting signals</p>
          </div>
        ) : (
          <div className="space-y-3">
            {sessionStrategies.map((strategy) => (
              <div
                key={strategy.id}
                className="flex items-start justify-between p-3 border rounded-lg bg-muted/30"
              >
                <div className="flex-1 space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-sm">
                      {getStrategyDisplayName(strategy)}
                    </span>
                    <Badge variant={strategy.is_active ? "default" : "secondary"} className="text-xs">
                      {strategy.is_active ? "Active" : "Inactive"}
                    </Badge>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-xs text-muted-foreground">
                    <div>
                      <span className="font-medium">Symbols:</span> {strategy.symbols.join(", ")}
                    </div>
                    <div>
                      <span className="font-medium">Timeframes:</span> {strategy.timeframes.join(", ")}
                    </div>
                    <div>
                      <span className="font-medium">Max Risk:</span> {strategy.max_risk_per_trade_pct}%
                    </div>
                    <div>
                      <span className="font-medium">Position Size:</span> {strategy.position_size_type} ({strategy.position_size_value})
                    </div>
                  </div>
                </div>

                <Button
                  variant="ghost"
                  size="sm"
                  className="text-destructive hover:text-destructive hover:bg-destructive/10"
                  onClick={() => handleRemoveStrategy(strategy.id, strategy.strategy_name)}
                  disabled={!isStopped}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
