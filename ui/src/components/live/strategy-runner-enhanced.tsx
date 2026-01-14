"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Play, Square, Pause, PlayCircle, AlertCircle, Loader2 } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { LiveTradingAPI } from "@/lib/api/live"
import { useLiveWebSocket } from "@/lib/hooks/use-live-websocket"
import type { LiveSession, SessionStatusInfo } from "@/types/live"
import { toast } from "sonner"

interface StrategyRunnerEnhancedProps {
  sessionId?: number
  onSessionChange?: (sessionId: number) => void
  onStatusChange?: (status: string) => void
  refreshTrigger?: number
}

export function StrategyRunnerEnhanced({ sessionId: initialSessionId, onSessionChange, onStatusChange, refreshTrigger }: StrategyRunnerEnhancedProps) {
  const [sessions, setSessions] = useState<LiveSession[]>([])
  const [selectedSessionId, setSelectedSessionId] = useState<number | undefined>(initialSessionId)
  const [currentSession, setCurrentSession] = useState<LiveSession | null>(null)
  const [status, setStatus] = useState<SessionStatusInfo | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isActionPending, setIsActionPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // WebSocket for real-time updates
  const { isConnected, reconnectAttempts } = useLiveWebSocket({
    sessionId: selectedSessionId || 0,
    channels: ["status"],
    onStatusUpdate: (newStatus) => {
      setStatus(newStatus)
      onStatusChange?.(newStatus.status)
      setCurrentSession((prev) =>
        prev ? { ...prev, status: newStatus.status } : prev
      )
    },
    autoConnect: !!selectedSessionId,
  })

  // Fetch sessions on mount and when refreshTrigger changes
  useEffect(() => {
    const fetchSessions = async () => {
      try {
        setIsLoading(true)
        setError(null)
        const data = await LiveTradingAPI.listSessions()
        setSessions(data)

        // Auto-select first session if none selected
        if (!selectedSessionId && data.length > 0) {
          setSelectedSessionId(data[0].session_id)
        }
      } catch (err) {
        console.error("Error fetching sessions:", err)
        setError(err instanceof Error ? err.message : "Failed to load sessions")
      } finally {
        setIsLoading(false)
      }
    }

    fetchSessions()
  }, [refreshTrigger])

  // Fetch current session details when selection changes
  useEffect(() => {
    if (!selectedSessionId) return

    const fetchSessionDetails = async () => {
      try {
        const [sessionData, statusData] = await Promise.all([
          LiveTradingAPI.getSession(selectedSessionId),
          LiveTradingAPI.getSessionStatus(selectedSessionId),
        ])
        setCurrentSession(sessionData)
        setStatus(statusData)
        onSessionChange?.(selectedSessionId)
        onStatusChange?.(statusData.status)
      } catch (err) {
        console.error("Error fetching session details:", err)
        setError(err instanceof Error ? err.message : "Failed to load session")
      }
    }

    fetchSessionDetails()
  }, [selectedSessionId])

  useEffect(() => {
    if (!selectedSessionId) return

    let isMounted = true

    const refreshStatus = async () => {
      try {
        const statusData = await LiveTradingAPI.getSessionStatus(selectedSessionId)
        if (!isMounted) return
        setStatus(statusData)
        onStatusChange?.(statusData.status)
        setCurrentSession((prev) =>
          prev ? { ...prev, status: statusData.status } : prev
        )
      } catch (err) {
        console.error("Error refreshing session status:", err)
      }
    }

    refreshStatus()
    const interval = setInterval(() => {
      if (document.hidden) return
      refreshStatus()
    }, 10000)

    return () => {
      isMounted = false
      clearInterval(interval)
    }
  }, [selectedSessionId, onStatusChange])

  const handleSessionChange = (sessionIdStr: string) => {
    const sessionId = parseInt(sessionIdStr, 10)
    setSelectedSessionId(sessionId)
  }

  const handleStart = async () => {
    if (!selectedSessionId) return

    try {
      setIsActionPending(true)
      const response = await LiveTradingAPI.startSession(selectedSessionId)
      toast.success("Session Started", {
        description: response.message,
      })

      // Refresh session details
      const [sessionData, statusData] = await Promise.all([
        LiveTradingAPI.getSession(selectedSessionId),
        LiveTradingAPI.getSessionStatus(selectedSessionId),
      ])
      setCurrentSession(sessionData)
      setStatus(statusData)
      onStatusChange?.(statusData.status)
    } catch (err) {
      console.error("Error starting session:", err)
      toast.error("Failed to Start", {
        description: err instanceof Error ? err.message : "Unknown error",
      })
    } finally {
      setIsActionPending(false)
    }
  }

  const handleStop = async () => {
    if (!selectedSessionId) return

    try {
      setIsActionPending(true)
      const response = await LiveTradingAPI.stopSession(selectedSessionId)
      toast.success("Session Stopped", {
        description: response.message,
      })

      // Refresh session details
      const [sessionData, statusData] = await Promise.all([
        LiveTradingAPI.getSession(selectedSessionId),
        LiveTradingAPI.getSessionStatus(selectedSessionId),
      ])
      setCurrentSession(sessionData)
      setStatus(statusData)
      onStatusChange?.(statusData.status)
    } catch (err) {
      console.error("Error stopping session:", err)
      toast.error("Failed to Stop", {
        description: err instanceof Error ? err.message : "Unknown error",
      })
    } finally {
      setIsActionPending(false)
    }
  }

  const handlePause = async () => {
    if (!selectedSessionId) return

    try {
      setIsActionPending(true)
      const response = await LiveTradingAPI.pauseSession(selectedSessionId)
      toast.success("Session Paused", {
        description: response.message,
      })

      // Refresh session details
      const [sessionData, statusData] = await Promise.all([
        LiveTradingAPI.getSession(selectedSessionId),
        LiveTradingAPI.getSessionStatus(selectedSessionId),
      ])
      setCurrentSession(sessionData)
      setStatus(statusData)
      onStatusChange?.(statusData.status)
    } catch (err) {
      console.error("Error pausing session:", err)
      toast.error("Failed to Pause", {
        description: err instanceof Error ? err.message : "Unknown error",
      })
    } finally {
      setIsActionPending(false)
    }
  }

  const handleResume = async () => {
    if (!selectedSessionId) return

    try {
      setIsActionPending(true)
      const response = await LiveTradingAPI.resumeSession(selectedSessionId)
      toast.success("Session Resumed", {
        description: response.message,
      })

      // Refresh session details
      const [sessionData, statusData] = await Promise.all([
        LiveTradingAPI.getSession(selectedSessionId),
        LiveTradingAPI.getSessionStatus(selectedSessionId),
      ])
      setCurrentSession(sessionData)
      setStatus(statusData)
      onStatusChange?.(statusData.status)
    } catch (err) {
      console.error("Error resuming session:", err)
      toast.error("Failed to Resume", {
        description: err instanceof Error ? err.message : "Unknown error",
      })
    } finally {
      setIsActionPending(false)
    }
  }

  const getStatusColor = () => {
    if (!status) return "secondary"
    switch (status.status) {
      case "running":
        return "default"
      case "paused":
        return "secondary"
      case "error":
        return "destructive"
      default:
        return "outline"
    }
  }

  const isRunning = status?.status === "running"
  const isPaused = status?.status === "paused"
  const isStopped = status?.status === "stopped"
  const isTransitioning = status?.status === "starting" || status?.status === "stopping"

  if (isLoading) {
    return (
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Strategy Control</CardTitle>
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground">Loading sessions...</div>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Strategy Control</CardTitle>
          <AlertCircle className="h-4 w-4 text-destructive" />
        </CardHeader>
        <CardContent>
          <div className="text-sm text-destructive">{error}</div>
        </CardContent>
      </Card>
    )
  }

  if (sessions.length === 0) {
    return (
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Strategy Control</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground">No sessions available. Create a session to get started.</div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">Strategy Control</CardTitle>
        <div className="flex items-center space-x-2">
          <Badge variant={currentSession?.mode === 'live' ? 'destructive' : 'secondary'}>
            {currentSession?.mode === 'live' ? 'LIVE TRADING' : 'PAPER TRADING'}
          </Badge>
          {status && (
            <Badge variant={getStatusColor() as any}>
              {status.status.toUpperCase()}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="space-y-2">
            <label className="text-xs font-medium text-muted-foreground">Active Session</label>
            <Select
              value={selectedSessionId?.toString()}
              onValueChange={handleSessionChange}
              disabled={isRunning || isTransitioning}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select a session" />
              </SelectTrigger>
              <SelectContent>
                {sessions.map((session) => (
                  <SelectItem key={session.session_id} value={session.session_id.toString()}>
                    {session.session_name} ({session.mode})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {currentSession && (
            <div className="space-y-2">
              <label className="text-xs font-medium text-muted-foreground">Session Details</label>
              <div className="text-xs space-y-1 border rounded-md p-2 bg-muted/50">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Status:</span>
                  <span className="font-medium capitalize">
                    {status?.status || currentSession.status}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Max Positions:</span>
                  <span className="font-medium">{currentSession.max_positions}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Max Risk:</span>
                  <span className="font-medium">{currentSession.max_total_risk_pct}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Max Drawdown:</span>
                  <span className="font-medium">{currentSession.max_drawdown_pct}%</span>
                </div>
              </div>
            </div>
          )}

          {status && (
            <div className="space-y-2">
              <label className="text-xs font-medium text-muted-foreground">Performance</label>
              <div className="text-xs space-y-1 border rounded-md p-2 bg-muted/50">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Signals Detected:</span>
                  <span className="font-medium">{status.signals_detected}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Approved:</span>
                  <span className="font-medium text-emerald-600">{status.signals_approved}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Rejected:</span>
                  <span className="font-medium text-red-600">{status.signals_rejected}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Active Positions:</span>
                  <span className="font-medium">{status.active_positions}</span>
                </div>
              </div>
            </div>
          )}

          <div className="pt-2 flex space-x-2">
            {(isStopped || !status) && (
              <Button
                className="w-full bg-emerald-600 hover:bg-emerald-700"
                onClick={handleStart}
                disabled={isActionPending || !selectedSessionId}
              >
                {isActionPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Play className="mr-2 h-4 w-4" />
                )}
                Start Session
              </Button>
            )}

            {isPaused && (
              <>
                <Button
                  variant="outline"
                  className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white"
                  onClick={handleResume}
                  disabled={isActionPending}
                >
                  {isActionPending ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <PlayCircle className="mr-2 h-4 w-4" />
                  )}
                  Resume
                </Button>
                <Button
                  variant="destructive"
                  className="flex-1"
                  onClick={handleStop}
                  disabled={isActionPending}
                >
                  {isActionPending ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Square className="mr-2 h-4 w-4" />
                  )}
                  Stop
                </Button>
              </>
            )}

            {isRunning && (
              <>
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={handlePause}
                  disabled={isActionPending}
                >
                  {isActionPending ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Pause className="mr-2 h-4 w-4" />
                  )}
                  Pause
                </Button>
                <Button
                  variant="destructive"
                  className="flex-1"
                  onClick={handleStop}
                  disabled={isActionPending}
                >
                  {isActionPending ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Square className="mr-2 h-4 w-4" />
                  )}
                  Stop
                </Button>
              </>
            )}

            {isTransitioning && (
              <Button
                className="w-full"
                disabled
              >
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {status.status === "starting" ? "Starting..." : "Stopping..."}
              </Button>
            )}
          </div>

          <div className="flex items-center justify-between pt-2 border-t">
            <div className="flex items-center space-x-2">
              <div className={`h-2 w-2 rounded-full ${
                isConnected ? 'bg-emerald-500' : reconnectAttempts >= 5 ? 'bg-red-500' : 'bg-amber-500'
              }`} />
              <span className="text-xs text-muted-foreground">
                {isConnected ? 'Connected' : reconnectAttempts >= 5 ? 'Disconnected' : 'Connecting...'}
              </span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
