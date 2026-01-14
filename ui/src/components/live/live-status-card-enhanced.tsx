"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Activity, Wifi, Server, Wallet, AlertCircle } from "lucide-react"
import { LiveTradingAPI } from "@/lib/api/live"
import { useLiveWebSocket } from "@/lib/hooks/use-live-websocket"
import type { SessionStatus, SessionStatusInfo } from "@/types/live"

interface LiveStatusCardProps {
  sessionId: number
  onStatusUpdate?: (status: SessionStatusInfo) => void
}

export function LiveStatusCardEnhanced({ sessionId, onStatusUpdate }: LiveStatusCardProps) {
  const [status, setStatus] = useState<SessionStatusInfo | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [latency, setLatency] = useState<number>(0)
  const [nextUpdateIn, setNextUpdateIn] = useState<number>(0)
  const [currentTime, setCurrentTime] = useState<string>("")

  // WebSocket for real-time updates
  const { isConnected } = useLiveWebSocket({
    sessionId,
    channels: ["status"],
    onStatusUpdate: (newStatus) => {
      setStatus(newStatus)
      onStatusUpdate?.(newStatus)
    },
    autoConnect: true,
  })

  // Countdown timer - updates every second
  useEffect(() => {
    const updateCountdown = () => {
      const now = new Date()
      const secondsIntoMinute = now.getSeconds()
      const secondsUntilNext = 60 - secondsIntoMinute
      setNextUpdateIn(secondsUntilNext)
      setCurrentTime(now.toLocaleTimeString())
    }

    updateCountdown()
    const interval = setInterval(updateCountdown, 1000)
    return () => clearInterval(interval)
  }, [])

  // Fetch initial status and sync with 1-minute candle boundaries
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        setIsLoading(true)
        setError(null)
        const data = await LiveTradingAPI.getSessionStatus(sessionId)
        setStatus(data)
        onStatusUpdate?.(data)
      } catch (err) {
        console.error("Error fetching session status:", err)
        setError(err instanceof Error ? err.message : "Failed to load status")
      } finally {
        setIsLoading(false)
      }
    }

    // Initial fetch
    fetchStatus()

    // Calculate milliseconds until next minute
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

  // Latency simulation (or real if available)
  useEffect(() => {
    setLatency(24)
  }, [])

  if (isLoading) {
    return (
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">System Status</CardTitle>
          <Activity className="h-4 w-4 text-muted-foreground animate-pulse" />
        </CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground">Loading...</div>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">System Status</CardTitle>
          <AlertCircle className="h-4 w-4 text-destructive" />
        </CardHeader>
        <CardContent>
          <div className="text-sm text-destructive">{error}</div>
        </CardContent>
      </Card>
    )
  }

  const getStatusBadge = () => {
    if (!status) return null

    const statusConfig: Record<string, { variant: any; label: string }> = {
      running: { variant: "default", label: "Running" },
      paused: { variant: "secondary", label: "Paused" },
      stopped: { variant: "outline", label: "Stopped" },
      starting: { variant: "secondary", label: "Starting..." },
      stopping: { variant: "secondary", label: "Stopping..." },
      error: { variant: "destructive", label: "Error" },
    }

    const config = statusConfig[status.status] || statusConfig.stopped

    return (
      <Badge
        variant={config.variant}
        className={
          status.status === "running"
            ? "bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/20 border-emerald-500/20"
            : ""
        }
      >
        {config.label}
      </Badge>
    )
  }

  const getSessionExpireLabel = () => {
    if (!status || status.stop_mode !== "auto" || !status.stop_at) {
      return "Manual"
    }
    const parsed = new Date(status.stop_at)
    if (Number.isNaN(parsed.getTime())) {
      return status.stop_at
    }
    return parsed.toLocaleString()
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">Session Details</CardTitle>
        <Activity className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Server className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium">Session Status</span>
            </div>
            {getStatusBadge()}
          </div>


          <div className="rounded-md bg-muted/50 p-2 text-xs space-y-1">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Session Name:</span>
              <span className="font-medium">{status?.session_name || 'N/A'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Account Login:</span>
              <span className="font-medium">{status?.account_login || 'N/A'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Server:</span>
              <span className="font-medium">{status?.account_server || 'N/A'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Time:</span>
              <span className="font-medium">{currentTime || 'N/A'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Session Expire:</span>
              <span className="font-medium">{getSessionExpireLabel()}</span>
            </div>
            <div className="flex justify-between border-t border-muted pt-1 mt-1">
              <span className="text-muted-foreground">Next update in:</span>
              <span className="font-medium text-emerald-500">{nextUpdateIn}s</span>
            </div>
          </div>



          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Wifi className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium">Connection</span>
            </div>
            <Badge
              variant="outline"
              className={
                isConnected
                  ? "bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/20 border-emerald-500/20"
                  : "bg-amber-500/10 text-amber-500 hover:bg-amber-500/20 border-amber-500/20"
              }
            >
              {isConnected ? "Live" : "Connecting..."}
            </Badge>
          </div>

          {status && (
            <>
              <div className="pt-2 border-t">
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <div className="text-muted-foreground text-xs">Signals</div>
                    <div className="font-mono font-bold">{status.signals_detected}</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground text-xs">Positions</div>
                    <div className="font-mono font-bold text-emerald-500">{status.active_positions}</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground text-xs">Approved</div>
                    <div className="font-mono text-xs text-emerald-600">{status.signals_approved}</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground text-xs">Rejected</div>
                    <div className="font-mono text-xs text-red-600">{status.signals_rejected}</div>
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-between pt-2 border-t">
                <div className="flex items-center space-x-2">
                  <Wallet className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm font-medium">Equity</span>
                </div>
                <div className="flex flex-col items-end">
                  <span className="text-lg font-bold text-emerald-500">${(status.current_equity || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                  <span className="text-xs text-muted-foreground">Balance: ${(status.current_balance || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                </div>
              </div>
            </>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
