"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { useEffect, useRef, useState } from "react"

interface LogEntry {
  id: number
  timestamp: string
  level: "INFO" | "WARN" | "ERROR" | "TRADE"
  message: string
}

export function LiveLogViewer() {
  const [logs, setLogs] = useState<LogEntry[]>([
    { id: 1, timestamp: "10:30:05", level: "INFO", message: "System initialized. Connected to Broker A." },
    { id: 2, timestamp: "10:30:06", level: "INFO", message: "Market data stream connected (XAUUSD, EURUSD)." },
    { id: 3, timestamp: "10:32:15", level: "TRADE", message: "Opened BUY 1.0 XAUUSD @ 2040.50" },
  ])
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // Auto-scroll to bottom
    if (scrollRef.current) {
//      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [logs])

  // Simulate incoming logs
  useEffect(() => {
    const interval = setInterval(() => {
        if (Math.random() > 0.7) {
            const now = new Date().toLocaleTimeString()
            const types: ("INFO" | "WARN" | "TRADE")[] = ["INFO", "INFO", "TRADE", "WARN"]
            const type = types[Math.floor(Math.random() * types.length)]
            const msgs = [
                "Latency spike detected (150ms)",
                "Order #12345 modified SL",
                "Tick data received",
                "Strategy 'MACD' signal ignored (Validation)",
                "Connection heartbeat"
            ]
            const msg = msgs[Math.floor(Math.random() * msgs.length)]

            setLogs(prev => [...prev.slice(-49), {
                id: Date.now(),
                timestamp: now,
                level: type,
                message: msg
            }])
        }
    }, 2000)
    return () => clearInterval(interval)
  }, [])

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
                {logs.map((log) => (
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
