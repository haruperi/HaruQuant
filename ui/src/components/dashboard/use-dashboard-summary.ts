"use client"

import * as React from "react"
import { useAuth } from "@/lib/auth-context"

export interface DashboardDailyPnlPoint {
  day: string
  pnl: number
}

export interface DashboardActiveStrategyItem {
  name: string
  market: string
  status: string
  timeframe: string
  session_name: string
}

export interface DashboardSummary {
  daily_pnl: DashboardDailyPnlPoint[]
  weekly_pnl_total: number
  weekly_best_day: number
  weekly_worst_day: number
  win_rate: number
  closed_trade_count: number
  winning_trade_count: number
  active_strategy_count: number
  active_strategies: DashboardActiveStrategyItem[]
}

const EMPTY_SUMMARY: DashboardSummary = {
  daily_pnl: [],
  weekly_pnl_total: 0,
  weekly_best_day: 0,
  weekly_worst_day: 0,
  win_rate: 0,
  closed_trade_count: 0,
  winning_trade_count: 0,
  active_strategy_count: 0,
  active_strategies: [],
}

export function useDashboardSummary() {
  const { authenticatedFetch } = useAuth()
  const [data, setData] = React.useState<DashboardSummary>(EMPTY_SUMMARY)
  const [loading, setLoading] = React.useState(true)

  React.useEffect(() => {
    let isMounted = true

    async function fetchSummary() {
      try {
        setLoading(true)
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"
        const response = await authenticatedFetch(`${apiUrl}/api/dashboard/summary`)

        if (!response.ok) {
          throw new Error("Failed to fetch dashboard summary")
        }

        const result = (await response.json()) as DashboardSummary
        if (isMounted) {
          setData(result)
        }
      } catch (error) {
        console.error("Failed to load dashboard summary:", error)
        if (isMounted) {
          setData(EMPTY_SUMMARY)
        }
      } finally {
        if (isMounted) {
          setLoading(false)
        }
      }
    }

    fetchSummary()

    return () => {
      isMounted = false
    }
  }, [authenticatedFetch])

  return { data, loading }
}
