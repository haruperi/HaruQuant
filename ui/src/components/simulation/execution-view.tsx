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
import simulatorApi, { type SimulationConfig } from "@/lib/api/simulator"

interface SimulationTrade {
  time?: string
  symbol?: string
  side?: string
  price?: number
  volume?: number
  pnl?: number
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
  totalBars?: number
  symbolDigits?: number
  onComplete: () => void
  onStop: () => void
  onTradesUpdate?: (trades: SimulationTrade[]) => void
  onFinalAccount?: (account: AccountMetrics) => void
}

const timeframeSeconds: Record<string, number> = {
  M1: 60,
  M5: 300,
  M15: 900,
  M30: 1800,
  H1: 3600,
  H4: 14400,
  D1: 86400,
}

// Fixed update rate: 30 updates per second for smooth animation without overwhelming the system
const UPDATE_RATE_MS = 33 // ~30 fps

export function SimulationExecutionView({
  sessionId,
  config,
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
  const [chartBars, setChartBars] = useState<ChartBarData[]>([])
  const [chartIndicators, setChartIndicators] = useState<ChartIndicatorData[]>([])
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

  const symbol = config?.symbol || "EURUSD"

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
        const newBars: ChartBarData[] = []
        const newIndicators: ChartIndicatorData[] = []
        let lastPrice: number | undefined
        let lastAccount: AccountMetrics | undefined

        for (const item of response.bars) {
          const bar = item.bar
          if (bar && bar.time) {
            newBars.push({
              time: (bar.time as string) || (bar.timestamp as string) || "",
              open: (bar.open as number) || 0,
              high: (bar.high as number) || 0,
              low: (bar.low as number) || 0,
              close: (bar.close as number) || 0,
            })

            if (typeof bar.close === "number") {
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
            newIndicators.push(item.indicators)
          }
        }

        // Batch state updates
        if (newBars.length > 0) {
          setChartBars((prev) => [...prev, ...newBars])
        }
        if (newIndicators.length > 0) {
          setChartIndicators((prev) => [...prev, ...newIndicators])
        }
        if (lastPrice !== undefined) {
          setCurrentPrice(lastPrice)
        }
        if (lastAccount) {
          setAccountState(lastAccount)
        }
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
  }, [sessionId, isPaused, isCompleted, isStopping, calculateBarsToFetch, onComplete, accountState])

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

  const getBarIndexForTime = (isoTime: string) => {
    if (!config?.start_time || !config?.timeframe) return null
    const start = new Date(config.start_time).getTime()
    const target = new Date(isoTime).getTime()
    if (Number.isNaN(start) || Number.isNaN(target)) return null
    const step = timeframeSeconds[config.timeframe] || 0
    if (!step) return null
    const diffSeconds = Math.floor((target - start) / 1000)
    if (diffSeconds < 0) return 0
    return Math.floor(diffSeconds / step)
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="text-sm text-muted-foreground">
          Session {sessionId} - {symbol} {config?.timeframe || "M1"} | Bar: {currentBarIndex}/{totalBars}
          {isCompleted && <span className="ml-2 text-green-500">(Completed)</span>}
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

          <div>
            <TradingPanel
              sessionId={sessionId}
              symbol={symbol}
              currentPrice={currentPrice}
              onTradeExecuted={(newPositions, newOrders) => {
                setPositions(toPositionRows(newPositions))
                setOrders(toOrderRows(newOrders))
              }}
            />
          </div>

          <SimulationChart
            symbol={symbol}
            timeframe={config?.timeframe}
            bars={chartBars}
            indicators={chartIndicators}
            digits={digits}
            indicatorVisibility={indicatorSelection}
          />

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base font-semibold">Trading Terminal</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <AccountMetricsBar metrics={accountState} />
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
                }}
                onClosePosition={async (positionId, volume) => {
                  const response = await simulatorApi.partialClosePosition(
                    sessionId,
                    Number(positionId),
                    volume
                  )
                  setPositions(toPositionRows(response.positions))
                  setOrders(toOrderRows(response.orders))
                }}
              />
              <div className="grid grid-cols-1 gap-4">
                <OrdersPanel
                  orders={orders}
                  digits={digits}
                  currentPrice={currentPrice}
                  onModifyOrder={async (orderId, payload) => {
                    try {
                      const response = await simulatorApi.modifyOrder(
                        sessionId,
                        Number(orderId),
                        payload
                      )
                      setPositions(toPositionRows(response.positions))
                      setOrders(toOrderRows(response.orders))
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
