"use client"

import { useState, useEffect } from "react"
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

  useEffect(() => {
    async function fetchData() {
      if (!selectedBacktest) {
        return
      }

      setLoading(true)
      setError(null)

      try {
        let trades = selectedBacktest.trades
        let initialBalance = selectedBacktest.initial_balance || 10000

        // If trades are missing, try to fetch full backtest details using backtest_id directly
        if ((!trades || trades.length === 0) && selectedBacktest.backtest_id) {
            try {
                const fullBacktest = await strategyApi.getBacktestById(selectedBacktest.backtest_id)
                if (fullBacktest.trades) {
                    trades = fullBacktest.trades
                    initialBalance = fullBacktest.initial_balance || initialBalance
                }
            } catch (err) {
                console.error("Failed to fetch full backtest details:", err)
                setError("Failed to load backtest details.")
                setLoading(false)
                return
            }
        }

        if (!trades || trades.length === 0) {
             setError("No trade data available.")
             setLoading(false)
             return
        }

        // 1. Fetch Metrics (Single call, returns 3-way)
        // strategyApi.getPerformanceSummary calls /strategy-performance-summary
        // We use apiClient directly if the method doesn't exist or we want custom behavior,
        // but strategyApi.getPerformanceSummary exists.
        const metricsData = await strategyApi.getPerformanceSummary(trades, initialBalance)
        setMetrics(metricsData)

        // 2. Fetch Equity Curves (3 calls)
        // We need to filter trades for Long/Short
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
          // Using strategyApi.getEquityCurveDetailed or direct call
          // strategyApi.getEquityCurveDetailed expects (trades, initialBalance)
          return await strategyApi.getEquityCurveDetailed(t, initialBalance)
        }

        const [allCurve, longCurve, shortCurve] = await Promise.all([
          fetchCurve(trades),
          fetchCurve(longTrades),
          fetchCurve(shortTrades)
        ])

        setEquityCurves({
          all: allCurve,
          long: longCurve,
          short: shortCurve
        })

      } catch (err: any) {
        console.error("Error fetching performance data:", err)
        setError(err.message || "Failed to fetch data")
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [selectedBacktest])

  return { metrics, equityCurves, loading, error, selectedBacktest }
}
