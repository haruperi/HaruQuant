"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "../ui/progress"
import { ShieldAlert } from "lucide-react"
import { LiveTradingAPI } from "@/lib/api/live"
import type { SessionStatusInfo } from "@/types/live"

interface RiskMonitorProps {
  sessionId?: number
}

export function RiskMonitor({ sessionId }: RiskMonitorProps) {
  const [status, setStatus] = useState<SessionStatusInfo | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    if (!sessionId) {
      setStatus(null)
      return
    }

    const fetchStatus = async () => {
      try {
        setIsLoading(true)
        const data = await LiveTradingAPI.getSessionStatus(sessionId)
        setStatus(data)
      } catch (error) {
        console.error("Error fetching session status for risk monitor:", error)
      } finally {
        setIsLoading(false)
      }
    }

    // Initial fetch
    fetchStatus()

    // Schedule fetches to align with 1-minute candle boundaries
    const scheduleNextFetch = () => {
      const now = new Date()
      const msUntilNextMinute = (60 - now.getSeconds()) * 1000 - now.getMilliseconds()

      setTimeout(() => {
        fetchStatus()
        scheduleNextFetch() // Schedule the next one
      }, msUntilNextMinute)
    }

    scheduleNextFetch()
  }, [sessionId])

  // Calculate progress percentages
  const dailyPnlProgress = status?.daily_pnl_limit && status.daily_pnl_limit > 0
    ? Math.min(Math.abs((status.daily_pnl || 0) / status.daily_pnl_limit) * 100, 100)
    : 0

  const drawdownProgress = status?.max_drawdown_pct && status.max_drawdown_pct > 0
    ? Math.min((status.current_drawdown_pct || 0) / status.max_drawdown_pct * 100, 100)
    : 0

  // Determine colors based on risk levels
  const getPnlColor = () => {
    const pnl = status?.daily_pnl || 0
    if (pnl >= 0) return "text-emerald-500"
    if (dailyPnlProgress < 50) return "text-yellow-500"
    if (dailyPnlProgress < 80) return "text-orange-500"
    return "text-red-500"
  }

  const getDrawdownColor = () => {
    if (drawdownProgress < 50) return "text-emerald-500"
    if (drawdownProgress < 80) return "text-yellow-500"
    return "text-red-500"
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value)
  }

  const formatPercent = (value: number) => {
    return `${value.toFixed(1)}%`
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">Risk Monitor</CardTitle>
        <ShieldAlert className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        {!sessionId ? (
          <div className="text-sm text-muted-foreground">Select a session to monitor risk</div>
        ) : isLoading && !status ? (
          <div className="text-sm text-muted-foreground">Loading...</div>
        ) : (
          <div className="space-y-4">

            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Daily P&L</span>
                <span className={`font-medium ${getPnlColor()}`}>
                  {formatCurrency(status?.daily_pnl || 0)} / {formatCurrency(status?.daily_pnl_limit || 0)}
                </span>
              </div>
              <Progress
                value={dailyPnlProgress}
                className={`h-2 ${
                  drawdownProgress >= 80 ? '[&>div]:bg-red-500' :
                  drawdownProgress >= 50 ? '[&>div]:bg-yellow-500' :
                  '[&>div]:bg-emerald-500'
                }`}
              />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>Current P&L</span>
                <span>Max Loss</span>
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Drawdown</span>
                <span className={`font-medium ${getDrawdownColor()}`}>
                  {formatPercent(status?.current_drawdown_pct || 0)} / {formatPercent(status?.max_drawdown_pct || 10)}
                </span>
              </div>
              <Progress
                value={drawdownProgress}
                className={`h-2 ${
                  drawdownProgress >= 80 ? '[&>div]:bg-red-500' :
                  drawdownProgress >= 50 ? '[&>div]:bg-yellow-500' :
                  '[&>div]:bg-emerald-500'
                }`}
              />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>Current DD</span>
                <span>Limit</span>
              </div>
            </div>

          </div>
        )}
      </CardContent>
    </Card>
  )
}
