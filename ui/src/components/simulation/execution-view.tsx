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
import { SessionOverviewCards } from "@/components/simulation/session-overview-cards"
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

function formatPercent(value?: number | null) {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "--"
  }
  return `${(value * 100).toFixed(1)}%`
}

function formatNumber(value?: number | null) {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "--"
  }
  return value.toFixed(2)
}

function formatScore(value?: number | null) {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "--"
  }
  return `${value.toFixed(1)}%`
}

function formatBars(value?: number | null) {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "--"
  }
  return `${Math.round(value)}`
}

function toScoreProgress(value?: number | null) {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return 0
  }
  return Math.max(0, Math.min(value, 100))
}

function formatScoreTooltip(
  explanation?: string | null,
  context?: Record<string, unknown>
) {
  const lines: string[] = []
  if (explanation) {
    lines.push(String(explanation))
  }
  const entries = Object.entries(context || {}).filter(([, value]) => {
    if (value === null || value === undefined || value === "") {
      return false
    }
    if (Array.isArray(value)) {
      return value.length > 0
    }
    return true
  })
  if (entries.length > 0) {
    if (lines.length > 0) {
      lines.push("")
    }
    for (const [key, value] of entries) {
      if (typeof value === "number" && Number.isFinite(value)) {
        lines.push(`${key}: ${value.toFixed(4)}`)
      } else if (Array.isArray(value)) {
        lines.push(`${key}: ${value.join(", ")}`)
      } else {
        lines.push(`${key}: ${String(value)}`)
      }
    }
  }
  return lines.join("\n")
}

function toRiskFraction(value?: number | null, equity?: number | null) {
  if (
    typeof value !== "number" ||
    !Number.isFinite(value) ||
    typeof equity !== "number" ||
    !Number.isFinite(equity) ||
    equity <= 0
  ) {
    return null
  }
  return value / equity
}

function toCapProgress(currentFraction?: number | null, limit?: number | null) {
  if (
    typeof currentFraction !== "number" ||
    !Number.isFinite(currentFraction) ||
    typeof limit !== "number" ||
    !Number.isFinite(limit) ||
    limit <= 0
  ) {
    return 0
  }
  return Math.max(0, Math.min((currentFraction / limit) * 100, 100))
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
  const [acceptedTradeCount, setAcceptedTradeCount] = useState(0)
  const [rejectedTradeCount, setRejectedTradeCount] = useState(0)
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
  const sessionDetails = {
    sessionNumber: String(sessionId),
    sessionName: config?.session_name || `Session ${sessionId}`,
    step: `${currentBarIndex}/${totalBars}`,
    login: String(sessionResponse?.account_login ?? "--"),
    server: sessionResponse?.account_server || "--",
    leverage: String(sessionResponse?.account_leverage ?? config?.leverage ?? "--"),
    commission: String(config?.commission ?? "--"),
    slippageType: config?.slippage_type || "--",
    spreadType: config?.spread_type || "--",
    dataResolution: config?.data_resolution || "--",
  }
  const strategyControl = {
    strategyLabel:
      config?.mode === "manual"
        ? "Manual"
        : config?.mode === "replay"
          ? "Replay"
          : config?.strategy_name || "Strategy",
    symbols: symbols.join(", "),
    timeframe: config?.timeframe || "--",
    approvedCount: String(acceptedTradeCount),
    rejectedCount: String(rejectedTradeCount),
  }
  const currentEquity = accountState.equity
  const portfolioVarFrac = toRiskFraction(riskSnapshot.portfolio_var, currentEquity)
  const portfolioEsFrac = toRiskFraction(riskSnapshot.portfolio_es, currentEquity)
  const riskMonitor = {
    varCap: {
      current: formatPercent(portfolioVarFrac),
      limit: formatPercent(config?.risk_var_cap_frac),
      progress: toCapProgress(portfolioVarFrac, config?.risk_var_cap_frac),
    },
    cvarCap: {
      current: formatPercent(portfolioEsFrac),
      limit: formatPercent(config?.risk_es_cap_frac),
      progress: toCapProgress(portfolioEsFrac, config?.risk_es_cap_frac),
    },
    currentDrawdown: formatPercent(riskSnapshot.current_drawdown),
    maxDrawdown: formatPercent(riskSnapshot.max_drawdown),
    drawdownVelocity: formatBars(riskSnapshot.drawdown_velocity),
    timeUnderWater: formatBars(riskSnapshot.time_under_water),
    scores: [
      {
        key: "portfolio_health_score",
        label: "Portfolio Health",
        value: formatScore(riskScorecard.portfolio_health_score),
        max: "100.0%",
        progress: toScoreProgress(riskScorecard.portfolio_health_score),
        tooltip: formatScoreTooltip(
          riskScorecard.details?.portfolio_health_score?.explanation,
          riskScorecard.details?.portfolio_health_score?.context
        ),
      },
      {
        key: "concentration_score",
        label: "Concentration",
        value: formatScore(riskScorecard.concentration_score),
        max: "100.0%",
        progress: toScoreProgress(riskScorecard.concentration_score),
        tooltip: formatScoreTooltip(
          riskScorecard.details?.concentration_score?.explanation,
          riskScorecard.details?.concentration_score?.context
        ),
      },
      {
        key: "stress_resilience_score",
        label: "Stress Resilience",
        value: formatScore(riskScorecard.stress_resilience_score),
        max: "100.0%",
        progress: toScoreProgress(riskScorecard.stress_resilience_score),
        tooltip: formatScoreTooltip(
          riskScorecard.details?.stress_resilience_score?.explanation,
          riskScorecard.details?.stress_resilience_score?.context
        ),
      },
      {
        key: "leverage_safety_score",
        label: "Leverage Safety",
        value: formatScore(riskScorecard.leverage_safety_score),
        max: "100.0%",
        progress: toScoreProgress(riskScorecard.leverage_safety_score),
        tooltip: formatScoreTooltip(
          riskScorecard.details?.leverage_safety_score?.explanation,
          riskScorecard.details?.leverage_safety_score?.context
        ),
      },
      {
        key: "margin_safety_score",
        label: "Margin Safety",
        value: formatScore(riskScorecard.margin_safety_score),
        max: "100.0%",
        progress: toScoreProgress(riskScorecard.margin_safety_score),
        tooltip: formatScoreTooltip(
          riskScorecard.details?.margin_safety_score?.explanation,
          riskScorecard.details?.margin_safety_score?.context
        ),
      },
      {
        key: "diversification_score",
        label: "Diversification",
        value: formatScore(riskScorecard.diversification_score),
        max: "100.0%",
        progress: toScoreProgress(riskScorecard.diversification_score),
        tooltip: formatScoreTooltip(
          riskScorecard.details?.diversification_score?.explanation,
          riskScorecard.details?.diversification_score?.context
        ),
      },
      {
        key: "regime_alignment_score",
        label: "Regime Alignment",
        value: formatScore(riskScorecard.regime_alignment_score),
        max: "100.0%",
        progress: toScoreProgress(riskScorecard.regime_alignment_score),
        tooltip: formatScoreTooltip(
          riskScorecard.details?.regime_alignment_score?.explanation,
          riskScorecard.details?.regime_alignment_score?.context
        ),
      },
      {
        key: "governance_compliance_score",
        label: "Governance Compliance",
        value: formatScore(riskScorecard.governance_compliance_score),
        max: "100.0%",
        progress: toScoreProgress(riskScorecard.governance_compliance_score),
        tooltip: formatScoreTooltip(
          riskScorecard.details?.governance_compliance_score?.explanation,
          riskScorecard.details?.governance_compliance_score?.context
        ),
      },
      {
        key: "overall_risk_quality_score",
        label: "Overall Risk Quality",
        value: formatScore(riskScorecard.overall_risk_quality_score),
        max: "100.0%",
        progress: toScoreProgress(riskScorecard.overall_risk_quality_score),
        tooltip: formatScoreTooltip(
          riskScorecard.details?.overall_risk_quality_score?.explanation,
          riskScorecard.details?.overall_risk_quality_score?.context
        ),
      },
    ],
  }
  const marginUsed =
    typeof riskSnapshot.margin_used === "number" && Number.isFinite(riskSnapshot.margin_used)
      ? riskSnapshot.margin_used
      : accountState.margin
  const marginUsedPct =
    typeof riskSnapshot.margin_used_frac === "number" && Number.isFinite(riskSnapshot.margin_used_frac)
      ? riskSnapshot.margin_used_frac
      : currentEquity > 0
        ? marginUsed / currentEquity
        : null
  const accountMargin = {
    balance: formatNumber(accountState.balance),
    equity: formatNumber(accountState.equity),
    profit: formatNumber(accountState.profit),
    profitTone: accountState.profit >= 0 ? "text-emerald-500" : "text-red-500",
    freeMargin: formatNumber(accountState.margin_free),
    marginUsed: formatNumber(marginUsed),
    marginUsedPct: formatPercent(marginUsedPct),
    marginLevel:
      typeof accountState.margin_level === "number" && Number.isFinite(accountState.margin_level)
        ? `${accountState.margin_level.toFixed(2)}%`
        : "--",
  }
  const exposureHeat = {
    grossExposure: formatNumber(riskSnapshot.gross_exposure),
    netExposure: formatNumber(riskSnapshot.net_exposure),
    maxSingleExposurePct: formatPercent(riskSnapshot.max_single_exposure_frac),
    currencyExposure: (riskSnapshot.currency_exposure || []).slice(0, 8).map((item) => ({
      label: item.currency,
      value: formatNumber(item.value),
    })),
    currencyWeights: (riskSnapshot.currency_weights || []).slice(0, 8).map((item) => ({
      label: item.currency,
      value:
        typeof item.value === "number" && Number.isFinite(item.value)
          ? `${(item.value * 100).toFixed(2)}%`
          : "--",
    })),
    avgCorrelation: formatNumber(riskSnapshot.average_pair_correlation),
    maxCorrelation: formatNumber(riskSnapshot.max_pair_correlation),
    hiddenOverlap: formatNumber(riskSnapshot.hidden_overlap_score),
    redundancyScore: formatNumber(riskSnapshot.redundancy_score),
    effectiveIndependentBets: formatNumber(riskSnapshot.effective_independent_bets),
    diversificationRatio: formatNumber(riskSnapshot.diversification_ratio),
  }
  const regime = {
    aggregate: riskSnapshot.regime_name || "--",
    confidence: formatPercent(riskSnapshot.regime_confidence),
    transitionChanged: riskSnapshot.regime_transition_changed ? "Yes" : "No",
    market: riskSnapshot.market_regime || "--",
    volatility: riskSnapshot.volatility_regime || "--",
    liquidity: riskSnapshot.liquidity_regime || "--",
    crisis: riskSnapshot.crisis_regime || "--",
    warnings: riskSnapshot.regime_warnings || [],
    signals: riskSnapshot.regime_signals_triggered || [],
  }
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
    let cancelled = false

    const loadInitialState = async () => {
      try {
        const response: PositionsResponse = await simulatorApi.getPositions(sessionId)
        if (cancelled) {
          return
        }
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
      } catch (error) {
        console.error("Failed to load simulation state:", error)
      }
    }

    loadInitialState()

    return () => {
      cancelled = true
    }
  }, [sessionId, symbol])

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

  const pauseForManualReview = useCallback(async () => {
    if (isPaused) {
      return
    }
    await simulatorApi.updateSession(sessionId, { paused: true })
    setIsPaused(true)
    lastUpdateTimeRef.current = Date.now()
    accumulatorRef.current = 0
  }, [isPaused, sessionId])

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
          {isCompleted && (
            <div className="text-sm text-green-500">(Completed)</div>
          )}
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

          <SessionOverviewCards
            sessionDetails={sessionDetails}
            strategyControl={strategyControl}
            riskMonitor={riskMonitor}
            accountMargin={accountMargin}
            exposureHeat={exposureHeat}
            regime={regime}
          />

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
                    await pauseForManualReview()
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
                mode={config?.mode}
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
                onTradeAttemptResult={({ accepted }) => {
                  if (accepted) {
                    setAcceptedTradeCount((prev) => prev + 1)
                    return
                  }
                  setRejectedTradeCount((prev) => prev + 1)
                }}
                onGovernanceEvaluated={setLatestGovernanceReport}
                onRiskSnapshotUpdate={setRiskSnapshot}
                onRiskScorecardUpdate={setRiskScorecard}
                onRecommendationsUpdate={setRecommendations}
                onPauseForManualReview={pauseForManualReview}
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
