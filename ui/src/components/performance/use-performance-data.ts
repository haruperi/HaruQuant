"use client"

import { useState, useEffect, useRef } from "react"
import { useSelectedBacktest } from "@/contexts/selected-backtest-context"
import strategyApi, { PerformanceMetrics, ThreeWayMetrics, EquityPoint, BacktestOverviewResponse } from "@/lib/api/strategies"

// Define types based on backend response
export type { PerformanceMetrics, ThreeWayMetrics, EquityPoint }

export interface PerformanceAnalytics {
  metrics: ThreeWayMetrics
  returns: ThreeWayMetrics
  ratios: ThreeWayMetrics
  risks: ThreeWayMetrics
  drawdowns: ThreeWayMetrics
  distributions: ThreeWayMetrics
  efficiency: ThreeWayMetrics
  benchmark: ThreeWayMetrics
  validation: ThreeWayMetrics
  summary: ThreeWayMetrics
  dashboard?: any
  scorecard?: any
}

export interface ChartDataPoint {
  date: string | number
  all?: number | null
  long?: number | null
  short?: number | null
  [key: string]: any
}

// Simple in-memory cache for performance data
const performanceCache = new Map<number, {
  analytics: PerformanceAnalytics
  equityCurves: { all: EquityPoint[], long: EquityPoint[], short: EquityPoint[] }
  charts: { equity_curve: ChartDataPoint[], drawdown_curve: ChartDataPoint[] }
  timestamp: number
}>()

const CACHE_TTL = 5 * 60 * 1000 // 5 minutes

export function usePerformanceData() {
  const { selectedBacktest } = useSelectedBacktest()

  const [analytics, setAnalytics] = useState<PerformanceAnalytics | null>(null)
  const [equityCurves, setEquityCurves] = useState<{
    all: EquityPoint[]
    long: EquityPoint[]
    short: EquityPoint[]
  } | null>(null)
  const [charts, setCharts] = useState<{
    equity_curve: ChartDataPoint[]
    drawdown_curve: ChartDataPoint[]
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
      if (lastFetchedId.current === backtestId && (analytics || quickLoading || detailedLoading)) {
        return
      }

      // Prevent concurrent fetches
      if (isFetching.current) {
        return
      }

      // Check cache first
      const cached = performanceCache.get(backtestId)
      if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
        setAnalytics(cached.analytics)
        setEquityCurves(cached.equityCurves)
        setCharts(cached.charts)
        lastFetchedId.current = backtestId
        return
      }

      isFetching.current = true
      setQuickLoading(true)
      setDetailedLoading(true)
      setError(null)

      // Reset previous data when loading new backtest
      setAnalytics(null)
      setEquityCurves(null)
      setCharts(null)

      try {
        const overview = await strategyApi.getBacktestOverview(backtestId)

        // The backend returns a full analytics dictionary + equity_curves + charts
        // If it's the old structure, it might only have metrics and charts.
        // We normalize it here.
        const analyticsData: PerformanceAnalytics = {
          metrics: overview.metrics || { all: {}, long: {}, short: {} },
          returns: overview.returns || { all: {}, long: {}, short: {} },
          ratios: overview.ratios || { all: {}, long: {}, short: {} },
          risks: overview.risks || { all: {}, long: {}, short: {} },
          drawdowns: overview.drawdowns || { all: {}, long: {}, short: {} },
          distributions: overview.distributions || { all: {}, long: {}, short: {} },
          efficiency: overview.efficiency || { all: {}, long: {}, short: {} },
          benchmark: overview.benchmark || { all: {}, long: {}, short: {} },
          validation: overview.validation || { all: {}, long: {}, short: {} },
          summary: overview.summary || overview.metrics || { all: {}, long: {}, short: {} },
          dashboard: overview.dashboard,
          scorecard: overview.scorecard,
        }

        const curves = overview.equity_curves
        const chartData = overview.charts as { equity_curve: ChartDataPoint[], drawdown_curve: ChartDataPoint[] }

        setAnalytics(analyticsData)
        setEquityCurves(curves)
        setCharts(chartData)
        lastFetchedId.current = backtestId

        // Cache the results
        performanceCache.set(backtestId, {
          analytics: analyticsData,
          equityCurves: curves,
          charts: chartData,
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
    analytics,
    metrics: analytics?.summary, // Keep 'metrics' as alias for 'summary' for compatibility with current page components
    equityCurves,
    charts,
    loading,           // True if either phase is loading
    quickLoading,      // True only during quick phase
    detailedLoading,   // True only during detailed phase
    error,
    selectedBacktest,
    hasQuickData: !!analytics,
    hasFullData: !!analytics
  }
}
