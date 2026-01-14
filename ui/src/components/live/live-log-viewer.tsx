"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { useEffect, useRef, useState } from "react"
import { LiveTradingAPI } from "@/lib/api/live"
import { useLiveWebSocket } from "@/lib/hooks/use-live-websocket"

interface LogEntry {
  id: number
  timestamp: string
  level: "INFO" | "WARN" | "ERROR" | "TRADE"
  message: string
}

interface LiveLogViewerProps {
  sessionId?: number
}

export function LiveLogViewer({ sessionId }: LiveLogViewerProps) {
  const [logs, setLogs] = useState<LogEntry[]>([])
  const scrollRef = useRef<HTMLDivElement>(null)

  const normalizeLevel = (level?: string, category?: string): LogEntry["level"] => {
    const levelUpper = (level || "INFO").toUpperCase()
    if (category && category.toLowerCase().includes("trade")) return "TRADE"
    if (levelUpper === "WARNING") return "WARN"
    if (levelUpper === "ERROR" || levelUpper === "CRITICAL") return "ERROR"
    return "INFO"
  }

  useEffect(() => {
    // Auto-scroll to bottom
    if (scrollRef.current) {
//      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [logs])

  useEffect(() => {
    if (!sessionId) return

    const fetchLogs = async () => {
      try {
        const response = await LiveTradingAPI.getLogs(sessionId, 200)
        const normalized = response.logs
          .slice()
          .reverse()
          .map((log: any) => ({
            id: log.log_id || Date.now(),
            timestamp: log.log_time
              ? new Date(log.log_time).toLocaleTimeString()
              : new Date().toLocaleTimeString(),
            level: normalizeLevel(log.log_level, log.log_category),
            message: log.message,
          }))
        setLogs(normalized)
      } catch (err) {
        console.error("Error fetching logs:", err)
      }
    }

    fetchLogs()
    const interval = setInterval(fetchLogs, 10000)
    return () => clearInterval(interval)
  }, [sessionId])

  useLiveWebSocket({
    sessionId: sessionId || 0,
    channels: ["logs"],
    onLogMessage: (log) => {
      if (!sessionId) return
      const timestamp = new Date().toLocaleTimeString()
      const level = normalizeLevel(log.level, log.category)
      setLogs((prev) => [
        ...prev.slice(-199),
        {
          id: Date.now(),
          timestamp,
          level,
          message: log.message,
        },
      ])
    },
    autoConnect: !!sessionId,
  })

  const renderEmpty = !sessionId || logs.length === 0

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="py-3">
        <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-medium">System Event Log</CardTitle>
            <div className="flex gap-2">
                <Badge variant="outline" className="text-[10px] font-normal">Info</Badge>
                <Badge variant="outline" className="text-[10px] font-normal text-yellow-500 border-yellow-200">Warn</Badge>
                <Badge variant="outline" className="text-[10px] font-normal text-emerald-500 border-emerald-200">Trade</Badge>
            </div>
        </div>
      </CardHeader>
      <CardContent className="flex-1 p-0">
        <ScrollArea className="h-[200px] w-full p-4">
            <div className="space-y-2">
                {renderEmpty ? (
                  <div className="text-xs text-muted-foreground text-center py-8">
                    {sessionId ? "No logs yet." : "Select a session to view logs."}
                  </div>
                ) : logs.map((log) => (
                    <div key={log.id} className="flex items-start space-x-2 text-xs">
                        <span className="text-muted-foreground font-mono shrink-0">[{log.timestamp}]</span>
                        <Badge
                            variant="secondary"
                            className={`
                                h-5 px-1 font-mono text-[10px] shrink-0
                                ${log.level === 'TRADE' ? 'bg-emerald-500/10 text-emerald-600 hover:bg-emerald-500/20' : ''}
                                ${log.level === 'WARN' ? 'bg-yellow-500/10 text-yellow-600 hover:bg-yellow-500/20' : ''}
                                ${log.level === 'ERROR' ? 'bg-red-500/10 text-red-600 hover:bg-red-500/20' : ''}
                            `}
                        >
                            {log.level}
                        </Badge>
                        <span className="break-all">{log.message}</span>
                    </div>
                ))}
                <div ref={scrollRef} />
            </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}
