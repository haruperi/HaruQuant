"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { SpeedControl } from "@/components/simulation/speed-control"
import { SkipControl } from "@/components/simulation/skip-control"
import { SimulationChart, type ChartBarData, type ChartIndicatorData } from "@/components/simulation/simulation-chart"
import { TradingPanel } from "@/components/simulation/trading-panel"
import { TradeDialog } from "@/components/simulation/trade-dialog"
import { PositionsPanel, type PositionRow } from "@/components/simulation/positions-panel"
import { OrdersPanel, type OrderRow } from "@/components/simulation/orders-panel"
import { AccountMetricsBar, type AccountMetrics } from "@/components/simulation/account-metrics"
import simulatorApi, { type SimulationConfig, type Position, type Order } from "@/lib/api/simulator"

interface SimulationTrade {
  time?: string
  symbol?: string
  side?: string
  price?: number
  volume?: number
  pnl?: number
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
  const [currentSpeed, setCurrentSpeed] = useState<number>(
    config?.speed_multiplier || 1
  )
  const [isPaused, setIsPaused] = useState(false)
  const [isCompleted, setIsCompleted] = useState(false)
  const [chartClickEnabled, setChartClickEnabled] = useState(false)
  const [currentPrice, setCurrentPrice] = useState<number | undefined>(undefined)
  const [accountState, setAccountState] = useState<AccountMetrics>({
    balance: config?.initial_balance || 10000,
    equity: config?.initial_balance || 10000,
    margin: 0,
    profit: 0,
    margin_free: config?.initial_balance || 10000,
  })
  const [tradeDialogOpen, setTradeDialogOpen] = useState(false)
  const [tradeDialogPrice, setTradeDialogPrice] = useState<number | undefined>(undefined)
  const [trades, setTrades] = useState<SimulationTrade[]>([])
  const [positions, setPositions] = useState<PositionRow[]>([])
  const [orders, setOrders] = useState<OrderRow[]>([])

  // Chart data
  const [chartBars, setChartBars] = useState<ChartBarData[]>([])
  const [chartIndicators, setChartIndicators] = useState<ChartIndicatorData[]>([])
  const [currentBarIndex, setCurrentBarIndex] = useState(0)
  const [digits, setDigits] = useState(symbolDigits)

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
    if (isFetchingRef.current || isPaused || isCompleted) return

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
              time: bar.time || bar.timestamp || "",
              open: bar.open || 0,
              high: bar.high || 0,
              low: bar.low || 0,
              close: bar.close || 0,
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
        const positionRows: PositionRow[] = response.positions.map((p) => ({
          id: p.id,
          symbol: p.symbol,
          type: p.type as "buy" | "sell",
          volume: p.volume,
          openPrice: p.open_price,
          currentPrice: p.price,
          pnl: p.profit,
        }))
        setPositions(positionRows)
      }

      if (response.orders) {
        const orderRows: OrderRow[] = response.orders.map((o) => ({
          id: o.id,
          symbol: o.symbol,
          type: o.type,
          volume: o.volume,
          price: o.open_price,
          sl: o.sl,
          tp: o.tp,
        }))
        setOrders(orderRows)
      }

      setCurrentBarIndex(response.current_index)

      if (response.completed) {
        setIsCompleted(true)
        onComplete()
      }
    } catch (error) {
      console.error("Failed to fetch bars:", error)
    } finally {
      isFetchingRef.current = false
    }
  }, [sessionId, isPaused, isCompleted, calculateBarsToFetch, onComplete, accountState])

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

  const handleChartClick = useCallback(
    (payload: { time: string; price: number }) => {
      if (!chartClickEnabled) return
      setTradeDialogPrice(payload.price)
      setTradeDialogOpen(true)
    },
    [chartClickEnabled]
  )

  const handlePauseToggle = async () => {
    try {
      await simulatorApi.updateSession(sessionId, { paused: !isPaused })
      setIsPaused(!isPaused)
      // Reset timing when resuming
      if (isPaused) {
        lastUpdateTimeRef.current = Date.now()
        accumulatorRef.current = 0
      }
    } catch (error) {
      toast.error("Failed to toggle pause")
    }
  }

  const handleStopSimulation = async () => {
    try {
      await simulatorApi.deleteSession(sessionId)
      toast.success("Simulation stopped")
      onStop()
    } catch (error) {
      toast.error("Failed to stop simulation")
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
        <div className="lg:col-span-2 space-y-4">
          <SpeedControl
            sessionId={sessionId}
            initialSpeed={currentSpeed}
            onSpeedChange={handleSpeedChange}
          />
          <SkipControl
            sessionId={sessionId}
            getBarIndexForTime={getBarIndexForTime}
          />
          <SimulationChart
            sessionId={sessionId}
            symbol={symbol}
            timeframe={config?.timeframe}
            bars={chartBars}
            indicators={chartIndicators}
            digits={digits}
            onChartClick={handleChartClick}
          />
        </div>

        <div className="space-y-4">
          <AccountMetricsBar metrics={accountState} />
          <TradingPanel
            sessionId={sessionId}
            symbol={symbol}
            currentPrice={currentPrice}
            chartClickEnabled={chartClickEnabled}
            onToggleChartClick={setChartClickEnabled}
            onTradeExecuted={(newPositions, newOrders) => {
              // Convert API positions to PositionRow format
              const positionRows: PositionRow[] = newPositions.map((p) => ({
                id: p.id,
                symbol: p.symbol,
                type: p.type as "buy" | "sell",
                volume: p.volume,
                openPrice: p.open_price,
                currentPrice: p.price,
                pnl: p.profit,
              }))
              setPositions(positionRows)

              // Convert API orders to OrderRow format
              const orderRows: OrderRow[] = newOrders.map((o) => ({
                id: o.id,
                symbol: o.symbol,
                type: o.type,
                volume: o.volume,
                price: o.open_price,
                sl: o.sl,
                tp: o.tp,
              }))
              setOrders(orderRows)
            }}
          />
          <PositionsPanel
            positions={positions}
            onModifyPosition={async (positionId) => {
              const slInput = window.prompt("New Stop Loss (leave blank to keep)")
              const tpInput = window.prompt("New Take Profit (leave blank to keep)")
              const payload: { sl?: number; tp?: number } = {}
              if (slInput) payload.sl = Number(slInput)
              if (tpInput) payload.tp = Number(tpInput)
              const response = await simulatorApi.modifyPosition(
                sessionId,
                Number(positionId),
                payload
              )
              const positionRows: PositionRow[] = response.positions.map((p) => ({
                id: p.id,
                symbol: p.symbol,
                type: p.type as "buy" | "sell",
                volume: p.volume,
                openPrice: p.open_price,
                currentPrice: p.price,
                pnl: p.profit,
              }))
              setPositions(positionRows)
              const orderRows: OrderRow[] = response.orders.map((o) => ({
                id: o.id,
                symbol: o.symbol,
                type: o.type,
                volume: o.volume,
                price: o.open_price,
                sl: o.sl,
                tp: o.tp,
              }))
              setOrders(orderRows)
            }}
            onClosePosition={async (positionId) => {
              const response = await simulatorApi.closePosition(
                sessionId,
                Number(positionId)
              )
              const positionRows: PositionRow[] = response.positions.map((p) => ({
                id: p.id,
                symbol: p.symbol,
                type: p.type as "buy" | "sell",
                volume: p.volume,
                openPrice: p.open_price,
                currentPrice: p.price,
                pnl: p.profit,
              }))
              setPositions(positionRows)
              const orderRows: OrderRow[] = response.orders.map((o) => ({
                id: o.id,
                symbol: o.symbol,
                type: o.type,
                volume: o.volume,
                price: o.open_price,
                sl: o.sl,
                tp: o.tp,
              }))
              setOrders(orderRows)
            }}
          />
          <OrdersPanel
            orders={orders}
            onModifyOrder={async (orderId) => {
              const priceInput = window.prompt("New Price (leave blank to keep)")
              const slInput = window.prompt("New Stop Loss (leave blank to keep)")
              const tpInput = window.prompt("New Take Profit (leave blank to keep)")
              const payload: { price?: number; sl?: number; tp?: number } = {}
              if (priceInput) payload.price = Number(priceInput)
              if (slInput) payload.sl = Number(slInput)
              if (tpInput) payload.tp = Number(tpInput)
              const response = await simulatorApi.modifyOrder(
                sessionId,
                Number(orderId),
                payload
              )
              const positionRows: PositionRow[] = response.positions.map((p) => ({
                id: p.id,
                symbol: p.symbol,
                type: p.type as "buy" | "sell",
                volume: p.volume,
                openPrice: p.open_price,
                currentPrice: p.price,
                pnl: p.profit,
              }))
              setPositions(positionRows)
              const orderRows: OrderRow[] = response.orders.map((o) => ({
                id: o.id,
                symbol: o.symbol,
                type: o.type,
                volume: o.volume,
                price: o.open_price,
                sl: o.sl,
                tp: o.tp,
              }))
              setOrders(orderRows)
            }}
            onCancelOrder={async (orderId) => {
              const response = await simulatorApi.cancelOrder(
                sessionId,
                Number(orderId)
              )
              const positionRows: PositionRow[] = response.positions.map((p) => ({
                id: p.id,
                symbol: p.symbol,
                type: p.type as "buy" | "sell",
                volume: p.volume,
                openPrice: p.open_price,
                currentPrice: p.price,
                pnl: p.profit,
              }))
              setPositions(positionRows)
              const orderRows: OrderRow[] = response.orders.map((o) => ({
                id: o.id,
                symbol: o.symbol,
                type: o.type,
                volume: o.volume,
                price: o.open_price,
                sl: o.sl,
                tp: o.tp,
              }))
              setOrders(orderRows)
            }}
          />
        </div>
      </div>

      <TradeDialog
        open={tradeDialogOpen}
        sessionId={sessionId}
        symbol={symbol}
        price={tradeDialogPrice}
        onOpenChange={setTradeDialogOpen}
      />
    </div>
  )
}
