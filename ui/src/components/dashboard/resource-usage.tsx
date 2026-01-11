"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Cpu } from "lucide-react"
import { useEffect, useState } from "react"

interface ResourceData {
  cpu_percent: number
  memory_percent: number
  memory_used_gb: number
  memory_total_gb: number
}

export function ResourceUsage() {
  const [data, setData] = useState<ResourceData>({ cpu_percent: 0, memory_percent: 0, memory_used_gb: 0, memory_total_gb: 8 })

  useEffect(() => {
    async function fetchResources() {
      try {
        const response = await fetch("http://localhost:8000/api/system/resources")
        if (!response.ok) throw new Error("Failed to fetch")
        const result = await response.json()
        setData(result)
      } catch (err) {
        console.error("Resource fetch error:", err)
      }
    }

    fetchResources()

    // Poll every 2 seconds for smooth updates
    const interval = setInterval(() => {
        if (document.hidden) return
        fetchResources()
    }, 2000)

    return () => clearInterval(interval)
  }, [])

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">Resource Usage</CardTitle>
        <Cpu className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent className="mt-2 space-y-4">
        <div className="space-y-1">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">CPU Load</span>
            <span className="font-medium">{data.cpu_percent.toFixed(1)}%</span>
          </div>
          <div className="h-2 w-full rounded-full bg-secondary">
             <div
                className="h-full rounded-full bg-blue-500 transition-all duration-500 ease-in-out"
                style={{ width: `${Math.min(data.cpu_percent, 100)}%` }}
             />
          </div>
        </div>
        <div className="space-y-1">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Memory</span>
            <span className="font-medium">{data.memory_used_gb.toFixed(1)}GB / {data.memory_total_gb.toFixed(0)}GB</span>
          </div>
          <div className="h-2 w-full rounded-full bg-secondary">
             <div
                className="h-full rounded-full bg-purple-500 transition-all duration-500 ease-in-out"
                style={{ width: `${Math.min(data.memory_percent, 100)}%` }}
             />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
