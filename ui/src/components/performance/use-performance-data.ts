"use client"

import { useState, useEffect, useRef } from "react"
import { useSelectedBacktest } from "@/contexts/selected-backtest-context"
import strategyApi from "@/lib/api/strategies"
import type { TradeLike } from "@/lib/api/strategies"

// Define types based on backend response
export interface PerformanceMetrics {
  "Net Profit": number
  "Gross Profit": number
  "Gross Loss": number
  "Sharpe Ratio": number
  "Win Rate": number
  "Total Trades": number
  "Max Strategy Drawdown": number
  "Max Strategy Drawdown (%)": number
  chart_data?: Record<string, unknown>
  // ... add others as needed dynamically
  [key: string]: unknown
}

export interface ThreeWayMetrics {
  all: PerformanceMetrics
  long: PerformanceMetrics
  short: PerformanceMetrics
}

export interface EquityPoint {
  date: string
  equity_close: number
  drawdown_usd: number
  [key: string]: unknown
}

// Simple in-memory cache for performance data
const performanceCache = new Map<number, {
  quickMetrics: ThreeWayMetrics
  fullMetrics: ThreeWayMetrics
  equityCurves: { all: EquityPoint[], long: EquityPoint[], short: EquityPoint[] }
  timestamp: number
}>()

const CACHE_TTL = 5 * 60 * 1000 // 5 minutes

export function usePerformanceData() {
  const { selectedBacktest } = useSelectedBacktest()

  // Two-phase metrics state
  const [quickMetrics, setQuickMetrics] = useState<ThreeWayMetrics | null>(null)
  const [fullMetrics, setFullMetrics] = useState<ThreeWayMetrics | null>(null)

  // Expose combined metrics (prefer full, fallback to quick)
  const metrics = fullMetrics || quickMetrics

  const [equityCurves, setEquityCurves] = useState<{
    all: EquityPoint[]
    long: EquityPoint[]
    short: EquityPoint[]
  } | null>(null)

  // Separate loading states for progressive UI
  const [quickLoading, setQuickLoading] = useState(false)
  const [detailedLoading, setDetailedLoading] = useState(false)
  const loading = quickLoading || detailedLoading

  const [error, setError] = useState<string | null>(null)

  // Track the last fetched backtest ID to prevent duplicate fetches
  const lastFetchedId = useRef<number | null>(null)
  const isFetching = useRef(false)

  // Use backtest_id as dependency, not the whole object
  const backtestId = selectedBacktest?.backtest_id

  useEffect(() => {
    async function fetchData() {
      if (!selectedBacktest || !backtestId) {
        return
      }

      // Prevent duplicate fetches for same backtest
      if (lastFetchedId.current === backtestId && (metrics || quickLoading || detailedLoading)) {
        return
      }

      // Prevent concurrent fetches
      if (isFetching.current) {
        return
      }

      // Check cache first
      const cached = performanceCache.get(backtestId)
      if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
        setQuickMetrics(cached.quickMetrics)
        setFullMetrics(cached.fullMetrics)
        setEquityCurves(cached.equityCurves)
        lastFetchedId.current = backtestId
        return
      }

      isFetching.current = true
      setQuickLoading(true)
      setDetailedLoading(true)
      setError(null)

      // Reset previous data when loading new backtest
      setQuickMetrics(null)
      setFullMetrics(null)
      setEquityCurves(null)

      try {
        let trades: TradeLike[] | undefined = selectedBacktest.trades
        let initialBalance = selectedBacktest.initial_balance || 10000

        // If trades are missing, try to fetch full backtest details using backtest_id directly
        if ((!trades || trades.length === 0) && backtestId) {
            try {
                const fullBacktest = await strategyApi.getBacktestById(backtestId)
                if (fullBacktest.trades) {
                    trades = fullBacktest.trades
                    initialBalance = fullBacktest.initial_balance || initialBalance
                }
            } catch (err) {
                console.error("Failed to fetch full backtest details:", err)
                setError("Failed to load backtest details.")
                setQuickLoading(false)
                setDetailedLoading(false)
                isFetching.current = false
                return
            }
        }

        if (!trades || trades.length === 0) {
             setError("No trade data available.")
             setQuickLoading(false)
             setDetailedLoading(false)
             isFetching.current = false
             return
        }

        // =================================================================
        // PHASE 1: Quick metrics (fast first paint ~2-3 sec)
        // =================================================================
        try {
          const quickData = await strategyApi.getPerformanceSummaryQuick(trades, initialBalance)
          setQuickMetrics(quickData)
          setQuickLoading(false)
        } catch (err) {
          console.error("Error fetching quick metrics:", err)
          // Continue to full metrics even if quick fails
        }

        // =================================================================
        // PHASE 2: Full metrics + equity curves (background)
        // =================================================================

        // Prepare trade subsets for equity curves
        const longTrades = trades.filter((t: TradeLike) => {
            const type = (t.type || t.side || "").toString().toLowerCase()
            return type === "buy" || type === "long"
        })
        const shortTrades = trades.filter((t: TradeLike) => {
            const type = (t.type || t.side || "").toString().toLowerCase()
            return type === "sell" || type === "short"
        })

        // Fetch full metrics and equity curves in parallel
        const fetchCurve = async (t: TradeLike[]) => {
          if (t.length === 0) return []
          return await strategyApi.getEquityCurveDetailed(t, initialBalance)
        }

        const [fullMetricsData, allCurve, longCurve, shortCurve] = await Promise.all([
          strategyApi.getPerformanceSummary(trades, initialBalance),
          fetchCurve(trades),
          fetchCurve(longTrades),
          fetchCurve(shortTrades)
        ])

        const curves = {
          all: allCurve,
          long: longCurve,
          short: shortCurve
        }

        // Update state with full data
        setFullMetrics(fullMetricsData)
        setEquityCurves(curves)
        lastFetchedId.current = backtestId

        // Cache the results
        performanceCache.set(backtestId, {
          quickMetrics: quickMetrics || fullMetricsData, // Use full as quick if quick wasn't set
          fullMetrics: fullMetricsData,
          equityCurves: curves,
          timestamp: Date.now()
        })

      } catch (err: unknown) {
        console.error("Error fetching performance data:", err)
        setError(err instanceof Error ? err.message : "Failed to fetch data")
      } finally {
        setQuickLoading(false)
        setDetailedLoading(false)
        isFetching.current = false
      }
    }

    fetchData()
  // selectedBacktest-driven refetching is intentionally keyed only by backtest_id.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [backtestId])

  return {
    metrics,           // Combined metrics (full if available, else quick)
    quickMetrics,      // Quick metrics only
    fullMetrics,       // Full metrics only
    equityCurves,
    loading,           // True if either phase is loading
    quickLoading,      // True only during quick phase
    detailedLoading,   // True only during detailed phase
    error,
    selectedBacktest,
    hasQuickData: !!quickMetrics,
    hasFullData: !!fullMetrics
  }
}
