"use client"

import { useEffect, useState, useRef } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { AlertCircle, CheckCircle2, Terminal, X, Timer } from "lucide-react"
import { cn } from "@/lib/utils"
import { backtestApi } from "@/lib/api/backtest"

interface BacktestExecutionViewProps {
    backtestId: number
    strategyId: number
    onCancel: () => void
    onComplete: () => void
}

interface LogEntry {
    id: number
    timestamp: string
    level: "INFO" | "WARNING" | "ERROR" | "SUCCESS"
    message: string
}

export function BacktestExecutionView({ backtestId, strategyId, onCancel, onComplete }: BacktestExecutionViewProps) {
    const [progress, setProgress] = useState(0)
    const [logs, setLogs] = useState<LogEntry[]>([])
    const scrollRef = useRef<HTMLDivElement>(null)
    const [status, setStatus] = useState<"running" | "cancelling" | "completed" | "failed">("running")
    const wsRef = useRef<WebSocket | null>(null)
    const logIdCounter = useRef(0)

    // WebSocket connection for real-time logs
    useEffect(() => {
        if (status !== "running") return

        // Connect to WebSocket - use API URL from environment
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'
        const wsUrl = apiUrl.replace('http://', 'ws://').replace('https://', 'wss://')
        const ws = new WebSocket(`${wsUrl}/api/backtest/ws/${backtestId}/logs`)
        wsRef.current = ws

        ws.onopen = () => {
            console.log('Connected to backtest logs WebSocket')
        }

        ws.onmessage = (event) => {
            try {
                const logData = JSON.parse(event.data)
                // Add log from WebSocket with unique incrementing ID
                setLogs(prev => [...prev, {
                    id: ++logIdCounter.current,
                    timestamp: new Date(logData.timestamp).toLocaleTimeString(),
                    level: logData.level,
                    message: logData.message
                }])
            } catch (error) {
                console.error('Error parsing log message:', error)
            }
        }

        ws.onerror = (error) => {
            console.error('WebSocket error:', error)
            addLog("WebSocket connection error", "ERROR")
        }

        ws.onclose = () => {
            console.log('Disconnected from backtest logs WebSocket')
        }

        return () => {
            if (ws.readyState === WebSocket.OPEN) {
                ws.close()
            }
        }
    }, [backtestId, status])

    // Poll backtest progress from API
    useEffect(() => {
        if (status !== "running") return

        const pollInterval = setInterval(async () => {
            try {
                const backtest = await backtestApi.get(backtestId)

                // Estimate progress based on status (backend doesn't provide progress)
                if (backtest.status === "running") {
                    // Increment progress slowly while running to show activity
                    setProgress(prev => Math.min(prev + 5, 95))
                } else if (backtest.status === "completed") {
                    setProgress(100)
                }

                // Update status
                if (backtest.status === "completed") {
                    setStatus("completed")
                    addLog("Backtest completed. Opening performance report...", "SUCCESS")
                    clearInterval(pollInterval)
                    // Close WebSocket
                    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                        wsRef.current.close()
                    }
                    setTimeout(onComplete, 1000)
                } else if (backtest.status === "failed") {
                    setStatus("failed")
                    addLog("Backtest failed. Review logs for details.", "ERROR")
                    clearInterval(pollInterval)
                    // Close WebSocket
                    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                        wsRef.current.close()
                    }
                }
            } catch (error) {
                console.error("Error polling backtest:", error)
                addLog("Error fetching backtest status", "ERROR")
            }
        }, 2000) // Poll every 2 seconds

        return () => clearInterval(pollInterval)
    }, [status, backtestId, strategyId, onComplete])

    // Auto-scroll logs
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight
        }
    }, [logs])

    const addLog = (message: string, level: LogEntry["level"]) => {
        const now = new Date()
        const timestamp = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`

        setLogs(prev => [...prev, {
            id: ++logIdCounter.current,
            timestamp,
            level,
            message
        }])
    }

    const handleCancel = () => {
        setStatus("cancelling")
        addLog("Aborting backtest...", "ERROR")
        setTimeout(() => {
            onCancel()
        }, 1000)
    }

    return (
        <Card className="w-full">
            <CardHeader>
                <CardTitle className="flex justify-between items-center">
                    <span>
                        {status === "completed"
                            ? "Backtest Completed"
                            : status === "failed"
                                ? "Backtest Failed"
                                : "Running Backtest..."}
                    </span>
                    <Button variant="destructive" size="sm" onClick={handleCancel} disabled={status !== "running"}>
                        <X className="mr-2 h-4 w-4" />
                        Abort
                    </Button>
                </CardTitle>
                <CardDescription>
                    {status === "completed"
                        ? "Batch runs are already persisted as backtests and will open the performance report automatically."
                        : status === "failed"
                            ? "The backtest did not complete successfully."
                            : "Simulating historical processing."}
                </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
                {/* Progress Section */}
                <div className="space-y-2">
                    <div className="flex justify-between text-sm text-muted-foreground">
                        <span>Progress</span>
                        <span>{Math.round(progress)}%</span>
                    </div>
                    <div className="h-2 w-full bg-secondary rounded-full overflow-hidden">
                        <div
                            className="h-full bg-primary transition-all duration-300 ease-in-out"
                            style={{ width: `${progress}%` }}
                        />
                    </div>
                    <div className="flex justify-between text-xs text-muted-foreground pt-1">
                        <span className="flex items-center"><Timer className="mr-1 h-3 w-3" /> ETA: {Math.max(0, Math.ceil((100 - progress) / 10))}s</span>
                        <span>Status: {status.toUpperCase()}</span>
                    </div>
                </div>

                <Separator />

                {/* Logs Section */}
                <div className="space-y-2">
                    <div className="flex items-center text-sm font-medium">
                        <Terminal className="mr-2 h-4 w-4" />
                        Live Logs
                    </div>
                    <div
                        className="h-[300px] w-full rounded-md border bg-slate-950 p-4 font-mono text-xs text-slate-50 overflow-y-auto"
                        ref={scrollRef}
                    >
                        {logs.length === 0 && <span className="text-slate-500">Initializing engine...</span>}
                        {logs.map((log) => (
                            <div key={log.id} className="mb-1 flex">
                                <span className="text-slate-500 mr-2">[{log.timestamp}]</span>
                                <span className={cn(
                                    "mr-2 font-bold",
                                    log.level === "INFO" && "text-blue-400",
                                    log.level === "SUCCESS" && "text-green-400",
                                    log.level === "WARNING" && "text-yellow-400",
                                    log.level === "ERROR" && "text-red-400"
                                )}>
                                    {log.level}
                                </span>
                                <span>{log.message}</span>
                            </div>
                        ))}
                    </div>
                </div>
            </CardContent>
        </Card>
    )
}
