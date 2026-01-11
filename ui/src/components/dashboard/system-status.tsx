"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Activity, Database, Server } from "lucide-react"
import { useEffect, useState } from "react"

interface SystemData {
  backend: string
  database: string
  message: string
}

export function SystemStatus() {
  const [data, setData] = useState<SystemData>({ backend: "Unknown", database: "Unknown", message: "" })
  const [latency, setLatency] = useState<number>(0)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchSystemStatus() {
      const start = Date.now()
      try {
        const response = await fetch("http://localhost:8000/api/system/status")
        const end = Date.now()
        setLatency(end - start) // Calculate round-trip latency

        if (!response.ok) throw new Error("Failed to fetch")
        const result = await response.json()
        setData(result)
      } catch (err) {
        console.error("System status error:", err)
        setData({ backend: "Down", database: "Unknown", message: "Connection Failed" })
        setLatency(0)
      } finally {
        setLoading(false)
      }
    }

    fetchSystemStatus()

    // Poll every 10 seconds
    const interval = setInterval(() => {
        if (document.hidden) return
        fetchSystemStatus()
    }, 10000)

    return () => clearInterval(interval)
  }, [])

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">System Status</CardTitle>
        <Activity className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent className="grid gap-4 mt-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Server className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm font-medium">Backend</span>
          </div>
          <div className="flex items-center space-x-2">
            <span className={`h-2 w-2 rounded-full ${data.backend === 'Operational' ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'}`} />
            <span className="text-sm text-muted-foreground">{data.backend}</span>
          </div>
        </div>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Database className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm font-medium">Database</span>
          </div>
          <div className="flex items-center space-x-2">
            <span className={`h-2 w-2 rounded-full ${data.database === 'Connected' ? 'bg-emerald-500' : 'bg-rose-500'}`} />
            <span className="text-sm text-muted-foreground">{data.database}</span>
          </div>
        </div>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Activity className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm font-medium">Latency</span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-sm font-mono text-muted-foreground">{latency > 0 ? `${latency}ms` : '--'}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
