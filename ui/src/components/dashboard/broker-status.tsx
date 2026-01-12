"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Wallet } from "lucide-react"
import { useEffect, useState } from "react"
import { formatCurrency } from "@/lib/utils"
import { useAuth } from "@/lib/auth-context"

interface BrokerData {
  status: string
  broker_name: string
  equity: number
  balance: number
  margin_level: number
  free_margin: number
}

export function BrokerStatus() {
  const { authenticatedFetch } = useAuth()
  const [data, setData] = useState<BrokerData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    let isMounted = true

    async function fetchBrokerStatus() {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"
        const response = await authenticatedFetch(`${apiUrl}/api/broker/`)

        if (!response.ok) throw new Error("Failed to fetch")

        const result = await response.json()
        if (isMounted) {
            setData(result)
            setError(false)
        }
      } catch (err) {
        console.error("Error fetching broker status:", err)
        if (isMounted) {
            setError(true)
        }
      } finally {
        if (isMounted) {
            setLoading(false)
        }
      }
    }

    fetchBrokerStatus()

    // Optional: Poll every 10 seconds for real-time updates
    const interval = setInterval(() => {
        if (document.hidden) return
        fetchBrokerStatus()
    }, 10000)

    return () => {
        isMounted = false
        clearInterval(interval)
    }
  }, [authenticatedFetch])

  if (loading && !data) {
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
