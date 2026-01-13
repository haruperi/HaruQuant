"use client"

import { useState, useEffect, useRef } from "react"
import { useSelectedBacktest } from "@/contexts/selected-backtest-context"
import strategyApi from "@/lib/api/strategies"
import apiClient from "@/lib/api-client"

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
  chart_data?: Record<string, any>
  // ... add others as needed dynamically
  [key: string]: any
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
  [key: string]: any
}

// Simple in-memory cache for performance data
const performanceCache = new Map<number, {
  metrics: ThreeWayMetrics
  equityCurves: { all: EquityPoint[], long: EquityPoint[], short: EquityPoint[] }
  timestamp: number
}>()

const CACHE_TTL = 5 * 60 * 1000 // 5 minutes

export function usePerformanceData() {
  const { selectedBacktest } = useSelectedBacktest()
  const [metrics, setMetrics] = useState<ThreeWayMetrics | null>(null)
  const [equityCurves, setEquityCurves] = useState<{
    all: EquityPoint[]
    long: EquityPoint[]
    short: EquityPoint[]
  } | null>(null)
  const [loading, setLoading] = useState(false)
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
      if (lastFetchedId.current === backtestId && (metrics || loading)) {
        return
      }

      // Prevent concurrent fetches
      if (isFetching.current) {
        return
      }

      // Check cache first
      const cached = performanceCache.get(backtestId)
      if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
        setMetrics(cached.metrics)
        setEquityCurves(cached.equityCurves)
        lastFetchedId.current = backtestId
        return
      }

      isFetching.current = true
      setLoading(true)
      setError(null)

      try {
        let trades = selectedBacktest.trades
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
                setLoading(false)
                isFetching.current = false
                return
            }
        }

        if (!trades || trades.length === 0) {
             setError("No trade data available.")
             setLoading(false)
             isFetching.current = false
             return
        }

        // 1. Fetch Metrics (Single call, returns 3-way)
        const metricsData = await strategyApi.getPerformanceSummary(trades, initialBalance)

        // 2. Fetch Equity Curves (3 calls in parallel)
        // Robust filtering: check both 'type' and 'side', handle case insensitivity
        const longTrades = trades.filter((t: any) => {
            const type = (t.type || t.side || "").toString().toLowerCase()
            return type === "buy" || type === "long"
        })
        const shortTrades = trades.filter((t: any) => {
            const type = (t.type || t.side || "").toString().toLowerCase()
            return type === "sell" || type === "short"
        })

        // Helper to fetch curve
        const fetchCurve = async (t: any[]) => {
          if (t.length === 0) return []
          return await strategyApi.getEquityCurveDetailed(t, initialBalance)
        }

        const [allCurve, longCurve, shortCurve] = await Promise.all([
          fetchCurve(trades),
          fetchCurve(longTrades),
          fetchCurve(shortTrades)
        ])

        const curves = {
          all: allCurve,
          long: longCurve,
          short: shortCurve
        }

        // Update state
        setMetrics(metricsData)
        setEquityCurves(curves)
        lastFetchedId.current = backtestId

        // Cache the results
        performanceCache.set(backtestId, {
          metrics: metricsData,
          equityCurves: curves,
          timestamp: Date.now()
        })

      } catch (err: any) {
        console.error("Error fetching performance data:", err)
        setError(err.message || "Failed to fetch data")
      } finally {
        setLoading(false)
        isFetching.current = false
      }
    }

    fetchData()
  }, [backtestId]) // Only depend on backtest ID, not the whole object

  return { metrics, equityCurves, loading, error, selectedBacktest }
}
