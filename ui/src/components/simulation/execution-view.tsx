"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { useRouter } from "next/navigation"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { IndicatorControl, type IndicatorSelection } from "@/components/simulation/indicator-control"
import { SpeedControl } from "@/components/simulation/speed-control"
import { SkipControl } from "@/components/simulation/skip-control"
import { SimulationChart, type ChartBarData, type ChartIndicatorData } from "@/components/simulation/simulation-chart"
import { TradingPanel } from "@/components/simulation/trading-panel"
import { PositionsPanel, type PositionRow } from "@/components/simulation/positions-panel"
import { OrdersPanel, type OrderRow } from "@/components/simulation/orders-panel"
import { AccountMetricsBar, type AccountMetrics } from "@/components/simulation/account-metrics"
import { getErrorMessage } from "@/lib/api-error"
import simulatorApi, {
  type PositionsResponse,
  type SimulationConfig,
  type SimulationGovernanceReport,
  type SimulationMarketRow,
  type SimulationRecommendationSummary,
  type SimulationRiskSnapshotSummary,
  type SimulationRiskScorecardSummary,
  type SimulationStartResponse,
  type SimulationWhatIfComparison,
} from "@/lib/api/simulator"

interface SimulationTrade {
  time?: string
  symbol?: string
  side?: string
  price?: number
  volume?: number
  pnl?: number
}

function mergeBarsByTime(previous: ChartBarData[], incoming: ChartBarData[]) {
  const merged = new Map<string, ChartBarData>()
  for (const bar of previous) {
    merged.set(bar.time, bar)
  }
  for (const bar of incoming) {
    merged.set(bar.time, bar)
  }
  return Array.from(merged.values()).sort((a, b) => a.time.localeCompare(b.time))
}

function mergeIndicatorsByTime(
  previous: ChartIndicatorData[],
  incoming: ChartIndicatorData[]
) {
  const merged = new Map<string, ChartIndicatorData>()
  for (const item of previous) {
    if (item.time) merged.set(item.time, item)
  }
  for (const item of incoming) {
    if (item.time) merged.set(item.time, item)
  }
  return Array.from(merged.values()).sort((a, b) =>
    String(a.time).localeCompare(String(b.time))
  )
}

function mergeMarketBySymbol(
  previous: Record<string, SimulationMarketRow>,
  incoming?: SimulationMarketRow[]
) {
  const next = { ...previous }
  for (const row of incoming || []) {
    next[row.symbol] = row
  }
  return next
}

function formatMarketTime(value?: string) {
  if (!value) {
    return "--"
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, "0")
  const day = String(date.getDate()).padStart(2, "0")
  const hours = String(date.getHours()).padStart(2, "0")
  const minutes = String(date.getMinutes()).padStart(2, "0")
  return `${year}-${month}-${day} ${hours}:${minutes}`
}

function toAccountMetrics(
  account: Partial<AccountMetrics> | undefined,
  fallback: AccountMetrics
): AccountMetrics {
  return {
    balance: Number(account?.balance ?? fallback.balance),
    equity: Number(account?.equity ?? fallback.equity),
    margin: Number(account?.margin ?? fallback.margin),
    profit: Number(account?.profit ?? fallback.profit),
    margin_free: Number(account?.margin_free ?? fallback.margin_free ?? 0),
    margin_level: Number(account?.margin_level ?? fallback.margin_level ?? 0),
  }
}

function toPositionRows(positions: Array<{
  id: number
  symbol: string
  type: string
  volume: number
  open_price: number
  sl: number
  tp: number
  price: number
  profit: number
  swap?: number
  margin_required?: number
  exposure?: number
  weight?: number
  time?: string | number | null
}>): PositionRow[] {
  return positions.map((p) => ({
    id: p.id,
    ticket: p.id,
    symbol: p.symbol,
    time: p.time,
    type: p.type as "buy" | "sell",
    volume: p.volume,
    openPrice: p.open_price,
    sl: p.sl,
    tp: p.tp,
    currentPrice: p.price,
    swap: p.swap ?? 0,
    pnl: p.profit,
    marginRequired: p.margin_required ?? 0,
    exposure: p.exposure,
    weight: p.weight,
  }))
}

function toOrderRows(orders: Array<{
  id: number
  symbol: string
  type: string
  volume: number
  open_price: number
  sl: number
  tp: number
  time?: string | number | null
}>): OrderRow[] {
  return orders.map((o) => ({
    id: o.id,
    ticket: o.id,
    symbol: o.symbol,
    time: o.time,
    type: o.type,
    volume: o.volume,
    price: o.open_price,
    sl: o.sl,
    tp: o.tp,
  }))
}

interface SimulationExecutionViewProps {
  sessionId: number
  config?: SimulationConfig | null
  sessionResponse?: SimulationStartResponse | null
  totalBars?: number
  symbolDigits?: number
  onComplete: () => void
  onStop: () => void
  onTradesUpdate?: (trades: SimulationTrade[]) => void
  onFinalAccount?: (account: AccountMetrics) => void
}

// Fixed update rate: 30 updates per second for smooth animation without overwhelming the system
const UPDATE_RATE_MS = 33 // ~30 fps

export function SimulationExecutionView({
  sessionId,
  config,
  sessionResponse,
  totalBars = 0,
  symbolDigits = 5,
  onComplete,
  onStop,
  onTradesUpdate,
  onFinalAccount,
}: SimulationExecutionViewProps) {
  const router = useRouter()
  const [currentSpeed, setCurrentSpeed] = useState<number>(
    config?.speed_multiplier || 1
  )
  const [isPaused, setIsPaused] = useState(false)
  const [isCompleted, setIsCompleted] = useState(false)
  const [currentPrice, setCurrentPrice] = useState<number | undefined>(undefined)
  const symbols = (config?.symbol || "EURUSD")
    .split(",")
    .map((item) => item.trim().toUpperCase())
    .filter(Boolean)
  const [accountState, setAccountState] = useState<AccountMetrics>({
    balance: config?.initial_balance || 10000,
    equity: config?.initial_balance || 10000,
    margin: 0,
    profit: 0,
    margin_free: config?.initial_balance || 10000,
    margin_level: 0,
  })
  const [trades] = useState<SimulationTrade[]>([])
  const [positions, setPositions] = useState<PositionRow[]>([])
  const [orders, setOrders] = useState<OrderRow[]>([])

  // Chart data
  const [chartBarsBySymbol, setChartBarsBySymbol] = useState<Record<string, ChartBarData[]>>({})
  const [chartIndicatorsBySymbol, setChartIndicatorsBySymbol] = useState<Record<string, ChartIndicatorData[]>>({})
  const [marketBySymbol, setMarketBySymbol] = useState<Record<string, SimulationMarketRow>>({})
  const [riskSnapshot, setRiskSnapshot] = useState<SimulationRiskSnapshotSummary>({})
  const [riskScorecard, setRiskScorecard] = useState<SimulationRiskScorecardSummary>({})
  const [recommendations, setRecommendations] = useState<SimulationRecommendationSummary>({ items: [] })
  const [latestGovernanceReport, setLatestGovernanceReport] = useState<SimulationGovernanceReport | null>(null)
  const [whatIfComparison, setWhatIfComparison] = useState<SimulationWhatIfComparison | null>(null)
  const [whatIfLoading, setWhatIfLoading] = useState(false)
  const [currentBarIndex, setCurrentBarIndex] = useState(0)
  const [digits, setDigits] = useState(symbolDigits)
  const [indicatorSelection, setIndicatorSelection] = useState<IndicatorSelection>({
    sma: Boolean(config?.indicator_sma_enabled),
    ema: Boolean(config?.indicator_ema_enabled),
    rsi: Boolean(config?.indicator_rsi_enabled),
  })
  const [stopDialogOpen, setStopDialogOpen] = useState(false)
  const [stopActionLoading, setStopActionLoading] = useState<"save" | "quit" | null>(null)
  const isStopping = stopActionLoading !== null

  const intervalRef = useRef<NodeJS.Timeout | null>(null)
  const isFetchingRef = useRef(false)
  const accumulatorRef = useRef(0) // Accumulates fractional bars over time
  const lastUpdateTimeRef = useRef(Date.now())

  const symbol = symbols[0] || "EURUSD"
  const sessionDetails = [
    { label: "Login", value: sessionResponse?.account_login ?? "--" },
    { label: "Server", value: sessionResponse?.account_server || "--" },
    { label: "Company", value: sessionResponse?.account_company || "--" },
    { label: "Initial balance", value: config?.initial_balance ?? "--" },
    { label: "Leverage", value: sessionResponse?.account_leverage ?? config?.leverage ?? "--" },
    { label: "Commission", value: config?.commission ?? "--" },
    { label: "Slippage Type", value: config?.slippage_type || "--" },
    { label: "Spread type", value: config?.spread_type || "--" },
    { label: "Data Resolution", value: config?.data_resolution || "--" },
  ]

  // Calculate how many bars to fetch based on speed and elapsed time
  const calculateBarsToFetch = useCallback(() => {
    const now = Date.now()
    const elapsed = now - lastUpdateTimeRef.current
    lastUpdateTimeRef.current = now

    // Calculate bars per millisecond at current speed
    // Speed X1 = 1 bar per 1000ms = 0.001 bars/ms
    // Speed X60 = 60 bars per 1000ms = 0.06 bars/ms
    // Speed X1440 = 1440 bars per 1000ms = 1.44 bars/ms
    const barsPerMs = currentSpeed / 1000

    // Accumulate fractional bars
    accumulatorRef.current += barsPerMs * elapsed

    // Get integer number of bars to fetch
    const barsToFetch = Math.floor(accumulatorRef.current)
    accumulatorRef.current -= barsToFetch

    // Cap at reasonable batch size to prevent overwhelming the backend
    return Math.min(barsToFetch, 100)
  }, [currentSpeed])

  // Fetch bars in batch
  const fetchBars = useCallback(async () => {
    if (isFetchingRef.current || isPaused || isCompleted || isStopping) return

    const barsToFetch = calculateBarsToFetch()
    if (barsToFetch <= 0) return

    isFetchingRef.current = true

    try {
      const response = await simulatorApi.advanceBars(sessionId, barsToFetch)

      if (response.digits) {
        setDigits(response.digits)
      }

      if (response.bars.length > 0) {
        // Batch update chart bars
        const barsBySymbol: Record<string, ChartBarData[]> = {}
        const indicatorsBySymbol: Record<string, ChartIndicatorData[]> = {}
        let lastPrice: number | undefined
        let lastAccount: AccountMetrics | undefined

        for (const item of response.bars) {
          const bar = item.bar
          const barSymbol = String(bar?.symbol || symbol)
          if (bar && bar.time) {
            const nextBar = {
              time: (bar.time as string) || (bar.timestamp as string) || "",
              open: (bar.open as number) || 0,
              high: (bar.high as number) || 0,
              low: (bar.low as number) || 0,
              close: (bar.close as number) || 0,
            }
            barsBySymbol[barSymbol] = [...(barsBySymbol[barSymbol] || []), nextBar]

            if (typeof bar.close === "number" && barSymbol === symbol) {
              lastPrice = bar.close
            }
          }

          if (item.account) {
            lastAccount = {
              balance: Number(item.account.balance ?? accountState.balance),
              equity: Number(item.account.equity ?? accountState.equity),
              margin: Number(item.account.margin ?? accountState.margin),
              profit: Number(item.account.profit ?? accountState.profit),
              margin_free: Number(item.account.margin_free ?? accountState.margin_free ?? 0),
              margin_level: Number(item.account.margin_level ?? accountState.margin_level ?? 0),
            }
          }

          if (item.indicators && Object.keys(item.indicators).length > 0) {
            indicatorsBySymbol[barSymbol] = [
              ...(indicatorsBySymbol[barSymbol] || []),
              item.indicators,
            ]
          }
        }

        const barSymbols = Object.keys(barsBySymbol)
        if (barSymbols.length > 0) {
          setChartBarsBySymbol((prev) => {
            const next = { ...prev }
            for (const symbolKey of barSymbols) {
              next[symbolKey] = mergeBarsByTime(prev[symbolKey] || [], barsBySymbol[symbolKey])
            }
            return next
          })
        }
        const indicatorSymbols = Object.keys(indicatorsBySymbol)
        if (indicatorSymbols.length > 0) {
          setChartIndicatorsBySymbol((prev) => {
            const next = { ...prev }
            for (const symbolKey of indicatorSymbols) {
              next[symbolKey] = mergeIndicatorsByTime(
                prev[symbolKey] || [],
                indicatorsBySymbol[symbolKey]
              )
            }
            return next
          })
        }
        if (lastPrice !== undefined) {
          setCurrentPrice(lastPrice)
        }
        if (lastAccount) {
          setAccountState(lastAccount)
        }
      }

      if (response.market) {
        setMarketBySymbol((prev) => mergeMarketBySymbol(prev, response.market))
        const primaryMarket = response.market.find((item) => item.symbol === symbol)
        if (primaryMarket) {
          setCurrentPrice(primaryMarket.close)
        }
      }
      if (response.risk_snapshot) {
        setRiskSnapshot(response.risk_snapshot)
      }
      if (response.risk_scorecard) {
        setRiskScorecard(response.risk_scorecard)
      }
      if (response.recommendations) {
        setRecommendations(response.recommendations)
      }
      if (response.governance) {
        setLatestGovernanceReport(response.governance)
      }

      if (response.positions) {
        setPositions(toPositionRows(response.positions))
      }

      if (response.orders) {
        setOrders(toOrderRows(response.orders))
      }

      setCurrentBarIndex(response.current_index)

      if (response.completed) {
        setIsCompleted(true)
        onComplete()
      }
    } catch (error) {
      if (isStopping && getErrorMessage(error) === "Session not found") {
        return
      }
      console.error("Failed to fetch bars:", error)
    } finally {
      isFetchingRef.current = false
    }
  }, [sessionId, isPaused, isCompleted, isStopping, calculateBarsToFetch, onComplete, accountState, symbol])

  // Start/stop interval with fixed update rate
  useEffect(() => {
    if (isPaused || isCompleted) {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
      return
    }

    // Reset timing when starting
    lastUpdateTimeRef.current = Date.now()
    accumulatorRef.current = 0

    // Use fixed update rate regardless of speed
    intervalRef.current = setInterval(fetchBars, UPDATE_RATE_MS)

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
  }, [isPaused, isCompleted, fetchBars])

  // Reset accumulator when speed changes
  useEffect(() => {
    accumulatorRef.current = 0
    lastUpdateTimeRef.current = Date.now()
  }, [currentSpeed])

  useEffect(() => {
    onFinalAccount?.(accountState)
  }, [accountState, onFinalAccount])

  useEffect(() => {
    onTradesUpdate?.(trades)
  }, [onTradesUpdate, trades])

  useEffect(() => {
    setWhatIfComparison(null)
  }, [currentBarIndex, positions, orders, accountState.equity, accountState.margin])

  const handlePauseToggle = async () => {
    try {
      await simulatorApi.updateSession(sessionId, { paused: !isPaused })
      setIsPaused(!isPaused)
      // Reset timing when resuming
      if (isPaused) {
        lastUpdateTimeRef.current = Date.now()
        accumulatorRef.current = 0
      }
    } catch {
      toast.error("Failed to toggle pause")
    }
  }

  const handleStopSimulation = async () => {
    setStopDialogOpen(true)
  }

  const handleQuitSimulation = async () => {
    try {
      setStopActionLoading("quit")
      setIsPaused(true)
      await simulatorApi.deleteSession(sessionId)
      toast.success("Simulation stopped")
      setStopDialogOpen(false)
      onStop()
    } catch (error) {
      toast.error("Failed to stop simulation", {
        description: getErrorMessage(error),
      })
    } finally {
      setStopActionLoading(null)
    }
  }

  const handleSaveAndStopSimulation = async () => {
    try {
      setStopActionLoading("save")
      setIsPaused(true)
      const response = await simulatorApi.stopAndSaveSession(sessionId)
      toast.success("Simulation saved to backtest results")
      setStopDialogOpen(false)
      router.push(`/performance?selected=${response.backtest_id}`)
    } catch (error) {
      toast.error("Failed to save simulation", {
        description: getErrorMessage(error),
      })
    } finally {
      setStopActionLoading(null)
    }
  }

  const handleSpeedChange = (newSpeed: number) => {
    setCurrentSpeed(newSpeed)
  }

  const handleSeek = useCallback(
    async (barIndex: number) => {
      try {
        const response: PositionsResponse = await simulatorApi.getPositions(sessionId)
        setPositions(toPositionRows(response.positions))
        setOrders(toOrderRows(response.orders))
        if (response.market) {
          setMarketBySymbol((prev) => mergeMarketBySymbol(prev, response.market))
          const primaryMarket = response.market.find((item) => item.symbol === symbol)
          if (primaryMarket) {
            setCurrentPrice(primaryMarket.close)
          }
        }
        if (response.risk_snapshot) {
          setRiskSnapshot(response.risk_snapshot)
        }
        if (response.risk_scorecard) {
          setRiskScorecard(response.risk_scorecard)
        }
        if (response.recommendations) {
          setRecommendations(response.recommendations)
        }
        if (response.governance) {
          setLatestGovernanceReport(response.governance)
        }
        if (response.account) {
          setAccountState((prev) => toAccountMetrics(response.account, prev))
        }
        setCurrentBarIndex(barIndex)
      } catch (error) {
        toast.error("Failed to refresh simulation state", {
          description: getErrorMessage(error),
        })
      }
    },
    [sessionId, symbol]
  )

  const getBarIndexForTime = (isoTime: string) => {
    const target = new Date(isoTime).getTime()
    if (Number.isNaN(target)) return null

    const primaryBars = chartBarsBySymbol[symbol] || []
    if (primaryBars.length === 0) {
      return null
    }

    let closestIndex = 0
    let closestDistance = Number.POSITIVE_INFINITY

    for (let index = 0; index < primaryBars.length; index += 1) {
      const barTime = new Date(primaryBars[index].time).getTime()
      if (Number.isNaN(barTime)) {
        continue
      }
      const distance = Math.abs(barTime - target)
      if (distance < closestDistance) {
        closestDistance = distance
        closestIndex = index
      }
      if (barTime >= target) {
        return index
      }
    }

    return closestIndex
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="space-y-2">
          <div className="text-sm text-muted-foreground">
            Session {sessionId} - {symbol} {config?.timeframe || "M1"} | Step: {currentBarIndex}/{totalBars}
            {isCompleted && <span className="ml-2 text-green-500">(Completed)</span>}
          </div>
          <div className="text-xs text-muted-foreground">
            Regime: <span className="text-foreground">{riskSnapshot.regime_name || "--"}</span>
            {" | "}Confidence: <span className="text-foreground">
              {typeof riskSnapshot.regime_confidence === "number"
                ? `${(riskSnapshot.regime_confidence * 100).toFixed(0)}%`
                : "--"}
            </span>
            {" | "}Market: <span className="text-foreground">{riskSnapshot.market_regime || "--"}</span>
            {" | "}Volatility: <span className="text-foreground">{riskSnapshot.volatility_regime || "--"}</span>
            {" | "}Liquidity: <span className="text-foreground">{riskSnapshot.liquidity_regime || "--"}</span>
          </div>
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
            {sessionDetails.map((item) => (
              <span key={item.label}>
                {item.label}: <span className="text-foreground">{String(item.value)}</span>
              </span>
            ))}
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            variant={isPaused ? "default" : "outline"}
            onClick={handlePauseToggle}
            disabled={isCompleted}
          >
            {isPaused ? "Resume" : "Pause"}
          </Button>
          <Button variant="destructive" onClick={handleStopSimulation}>
            Stop Simulation
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="space-y-4 lg:col-span-3">
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
            <SkipControl
              sessionId={sessionId}
              getBarIndexForTime={getBarIndexForTime}
              onSeek={handleSeek}
            />
            <SpeedControl
              sessionId={sessionId}
              initialSpeed={currentSpeed}
              onSpeedChange={handleSpeedChange}
            />
            <IndicatorControl
              sessionId={sessionId}
              value={indicatorSelection}
              onChange={setIndicatorSelection}
            />
          </div>

          {symbols.length <= 4 ? (
            <div
              className={
                symbols.length === 1
                  ? "grid grid-cols-1 gap-4"
                  : "grid grid-cols-1 gap-4 lg:grid-cols-2"
              }
            >
              {symbols.map((symbolKey) => (
                <SimulationChart
                  key={symbolKey}
                  symbol={symbolKey}
                  timeframe={config?.timeframe}
                  bars={chartBarsBySymbol[symbolKey] || []}
                  indicators={chartIndicatorsBySymbol[symbolKey] || []}
                  digits={digits}
                  indicatorVisibility={indicatorSelection}
                />
              ))}
            </div>
          ) : (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base font-semibold">Market Snapshot</CardTitle>
              </CardHeader>
              <CardContent className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="border-b text-left">
                      <th className="p-2">Symbol</th>
                      <th className="p-2">Time</th>
                      <th className="p-2">Open</th>
                      <th className="p-2">High</th>
                      <th className="p-2">Low</th>
                      <th className="p-2">Close</th>
                      <th className="p-2">Bid</th>
                      <th className="p-2">Ask</th>
                      <th className="p-2">Spread</th>
                    </tr>
                  </thead>
                  <tbody>
                    {symbols.map((symbolKey) => {
                      const market = marketBySymbol[symbolKey]
                      return (
                        <tr key={symbolKey} className="border-b">
                          <td className="p-2">{symbolKey}</td>
                          <td className="p-2">{formatMarketTime(market?.time)}</td>
                          <td className="p-2">{market ? market.open.toFixed(digits) : "--"}</td>
                          <td className="p-2">{market ? market.high.toFixed(digits) : "--"}</td>
                          <td className="p-2">{market ? market.low.toFixed(digits) : "--"}</td>
                          <td className="p-2">{market ? market.close.toFixed(digits) : "--"}</td>
                          <td className="p-2">{market ? market.bid.toFixed(digits) : "--"}</td>
                          <td className="p-2">{market ? market.ask.toFixed(digits) : "--"}</td>
                          <td className="p-2">{market ? market.spread.toFixed(0) : "--"}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base font-semibold">Trading Terminal</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <AccountMetricsBar
                metrics={accountState}
                riskSnapshot={riskSnapshot}
                riskScorecard={riskScorecard}
                recommendations={recommendations}
                governanceReport={latestGovernanceReport}
                whatIfComparison={whatIfComparison}
                whatIfLoading={whatIfLoading}
                positions={positions.map((position) => ({
                  id: Number(position.id),
                  symbol: position.symbol,
                  type: position.type,
                  volume: Number(position.volume),
                }))}
                symbols={symbols}
                currentLeverage={
                  typeof sessionResponse?.account_leverage === "number"
                    ? sessionResponse.account_leverage
                    : typeof config?.leverage === "number"
                      ? config.leverage
                      : null
                }
                onEvaluateWhatIf={async (payload) => {
                  try {
                    setWhatIfLoading(true)
                    const response = await simulatorApi.evaluateWhatIf(sessionId, payload)
                    setWhatIfComparison(response)
                  } catch (error) {
                    toast.error("Failed to evaluate what-if", {
                      description: getErrorMessage(error),
                    })
                  } finally {
                    setWhatIfLoading(false)
                  }
                }}
              />
              <TradingPanel
                sessionId={sessionId}
                symbol={symbol}
                symbols={symbols}
                currentPrice={currentPrice}
                currentPricesBySymbol={Object.fromEntries(
                  Object.entries(marketBySymbol).map(([key, value]) => [key, value.close])
                )}
                accountEquity={accountState.equity}
                onTradeExecuted={(newPositions, newOrders) => {
                  setPositions(toPositionRows(newPositions))
                  setOrders(toOrderRows(newOrders))
                }}
                onGovernanceEvaluated={setLatestGovernanceReport}
                onRiskSnapshotUpdate={setRiskSnapshot}
                onRiskScorecardUpdate={setRiskScorecard}
                onRecommendationsUpdate={setRecommendations}
              />
              <PositionsPanel
                positions={positions}
                digits={digits}
                onModifyPositionField={async (positionId, field, newValue) => {
                  const payload: { sl?: number; tp?: number } = {}
                  payload[field] = newValue ?? 0
                  const response = await simulatorApi.modifyPosition(
                    sessionId,
                    Number(positionId),
                    payload
                  )
                  setPositions(toPositionRows(response.positions))
                  setOrders(toOrderRows(response.orders))
                  setMarketBySymbol((prev) => mergeMarketBySymbol(prev, response.market))
                  if (response.risk_snapshot) {
                    setRiskSnapshot(response.risk_snapshot)
                  }
                  if (response.risk_scorecard) {
                    setRiskScorecard(response.risk_scorecard)
                  }
                  if (response.recommendations) {
                    setRecommendations(response.recommendations)
                  }
                  if (response.governance) {
                    setLatestGovernanceReport(response.governance)
                  }
                }}
                onClosePosition={async (positionId, volume) => {
                  const response = await simulatorApi.partialClosePosition(
                    sessionId,
                    Number(positionId),
                    volume
                  )
                  setPositions(toPositionRows(response.positions))
                  setOrders(toOrderRows(response.orders))
                  setMarketBySymbol((prev) => mergeMarketBySymbol(prev, response.market))
                  if (response.risk_snapshot) {
                    setRiskSnapshot(response.risk_snapshot)
                  }
                  if (response.risk_scorecard) {
                    setRiskScorecard(response.risk_scorecard)
                  }
                  if (response.recommendations) {
                    setRecommendations(response.recommendations)
                  }
                  if (response.governance) {
                    setLatestGovernanceReport(response.governance)
                  }
                }}
              />
              <div className="grid grid-cols-1 gap-4">
                <OrdersPanel
                  orders={orders}
                  digits={digits}
                  currentPrice={currentPrice}
                  currentPricesBySymbol={Object.fromEntries(
                    Object.entries(marketBySymbol).map(([key, value]) => [key, value.close])
                  )}
                  onModifyOrder={async (orderId, payload) => {
                    try {
                      const response = await simulatorApi.modifyOrder(
                        sessionId,
                        Number(orderId),
                        payload
                      )
                      setPositions(toPositionRows(response.positions))
                      setOrders(toOrderRows(response.orders))
                      setMarketBySymbol((prev) => mergeMarketBySymbol(prev, response.market))
                      if (response.risk_snapshot) {
                        setRiskSnapshot(response.risk_snapshot)
                      }
                      if (response.risk_scorecard) {
                        setRiskScorecard(response.risk_scorecard)
                      }
                      if (response.recommendations) {
                        setRecommendations(response.recommendations)
                      }
                      if (response.governance) {
                        setLatestGovernanceReport(response.governance)
                      }
                    } catch (error) {
                      toast.error("Failed to modify order", {
                        description: getErrorMessage(error),
                      })
                      throw error
                    }
                  }}
                  onDeleteOrder={async (orderId) => {
                    try {
                      const response = await simulatorApi.cancelOrder(
                        sessionId,
                        Number(orderId)
                      )
                      setPositions(toPositionRows(response.positions))
                      setOrders(toOrderRows(response.orders))
                      setMarketBySymbol((prev) => mergeMarketBySymbol(prev, response.market))
                      if (response.risk_snapshot) {
                        setRiskSnapshot(response.risk_snapshot)
                      }
                      if (response.risk_scorecard) {
                        setRiskScorecard(response.risk_scorecard)
                      }
                      if (response.recommendations) {
                        setRecommendations(response.recommendations)
                      }
                      if (response.governance) {
                        setLatestGovernanceReport(response.governance)
                      }
                    } catch (error) {
                      toast.error("Failed to delete order", {
                        description: getErrorMessage(error),
                      })
                      throw error
                    }
                  }}
                />
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      <Dialog
        open={stopDialogOpen}
        onOpenChange={(open) => {
          if (!stopActionLoading) {
            setStopDialogOpen(open)
          }
        }}
      >
        <DialogContent className="sm:max-w-[420px]">
          <DialogHeader>
            <DialogTitle>Stop Simulation</DialogTitle>
            <DialogDescription>
              Do you want to save this simulation as a completed backtest, or quit without saving?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 sm:justify-between">
            <Button
              variant="outline"
              onClick={() => setStopDialogOpen(false)}
              disabled={stopActionLoading !== null}
            >
              Cancel
            </Button>
            <div className="flex gap-2">
              <Button
                variant="secondary"
                onClick={handleSaveAndStopSimulation}
                disabled={stopActionLoading !== null}
              >
                {stopActionLoading === "save" ? "Saving..." : "Save"}
              </Button>
              <Button
                variant="destructive"
                onClick={handleQuitSimulation}
                disabled={stopActionLoading !== null}
              >
                {stopActionLoading === "quit" ? "Quitting..." : "Quit"}
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
