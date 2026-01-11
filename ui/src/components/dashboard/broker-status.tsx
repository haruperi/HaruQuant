"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Wallet } from "lucide-react"
import { useEffect, useState } from "react"
import { formatCurrency } from "@/lib/utils"

interface BrokerData {
  status: string
  broker_name: string
  equity: number
  balance: number
  margin_level: number
  free_margin: number
}

export function BrokerStatus() {
  const [data, setData] = useState<BrokerData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    async function fetchBrokerStatus() {
      try {
        // Assuming API is proxied or CORS is handled.
        // If running locally, this should point to the FastAPI backend.
        // In the user's environment, it seems `npm run dev` and `uvicorn` are separate.
        // We'll trust the existing proxy setup or use the full URL if needed.
        // Given existing code doesn't show absolute URLs, we'll try relative first
        // if there's a proxy, or fall back to localhost:8000.
        // EDIT: Looking at `main.py`, CORS is allowing localhost:3000.
        // Let's try the full URL to be safe since we don't know the Next.js proxy config.
        const response = await fetch("http://localhost:8000/api/broker/")
        if (!response.ok) throw new Error("Failed to fetch")
        const result = await response.json()
        setData(result)
      } catch (err) {
        console.error("Error fetching broker status:", err)
        setError(true)
      } finally {
        setLoading(false)
      }
    }

    fetchBrokerStatus()

    // Optional: Poll every 5-10 seconds for real-time updates
    const interval = setInterval(() => {
        // Stop polling if tab is not visible
        if (document.hidden) return
        fetchBrokerStatus()
    }, 60000)
    return () => clearInterval(interval)
  }, [])

  if (loading) {
     return (
        <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Broker Connection</CardTitle>
                <Wallet className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
                <div className="h-24 flex items-center justify-center text-muted-foreground text-sm">
                    Connecting...
                </div>
            </CardContent>
        </Card>
     )
  }

  // Fallback data or error state
  const displayData = data || {
      status: "Disconnected",
      broker_name: "No Connection",
      equity: 0,
      balance: 0,
      margin_level: 0,
      free_margin: 0
  }

  const isConnected = displayData.status === "Connected"

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">Broker Connection</CardTitle>
        <Wallet className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="mt-2 flex items-center justify-between">
            <div>
                 <div className="text-2xl font-bold">
                    {formatCurrency(displayData.equity)}
                 </div>
                 <p className="text-xs text-muted-foreground">Total Equity</p>
            </div>
             <div className="flex flex-col items-end">
                <div className={`flex items-center space-x-1 text-sm font-medium ${isConnected ? "text-emerald-500" : "text-rose-500"}`}>
                    <span className={`h-2 w-2 rounded-full ${isConnected ? "bg-emerald-500" : "bg-rose-500"}`} />
                    <span>{displayData.status}</span>
                </div>
                <p className="text-xs text-muted-foreground mt-1">{displayData.broker_name}</p>
            </div>
        </div>
        <div className="mt-4 pt-4 border-t flex justify-between items-center">
             <div className="text-xs text-muted-foreground">
                <p>Margin Level: <span className="text-foreground font-medium">{displayData.margin_level.toFixed(0)}%</span></p>
             </div>
              <div className="text-xs text-muted-foreground">
                <p>Free Margin: <span className="text-foreground font-medium">{formatCurrency(displayData.free_margin)}</span></p>
             </div>
        </div>
      </CardContent>
    </Card>
  )
}
