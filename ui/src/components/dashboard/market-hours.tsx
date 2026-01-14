"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Globe, Clock } from "lucide-react"
import { useEffect, useState } from "react"

interface MarketStatus {
    name: string
    status: string // "Open" | "Closed"
    message: string
    open: string
    close: string
    local_time: string
}

const DEFAULT_MARKETS: MarketStatus[] = [
    { name: "London", open: "08:00", close: "16:30", status: "Closed", message: "", local_time: "--:--:--" },
    { name: "New York", open: "09:30", close: "16:00", status: "Closed", message: "", local_time: "--:--:--" },
    { name: "Tokyo", open: "09:00", close: "15:00", status: "Closed", message: "", local_time: "--:--:--" },
    { name: "Sydney", open: "10:00", close: "16:00", status: "Closed", message: "", local_time: "--:--:--" },
]

export function MarketHours() {
  const [markets, setMarkets] = useState<MarketStatus[]>(DEFAULT_MARKETS)
  const [localTime, setLocalTime] = useState<string>("")
  const [loading, setLoading] = useState(true)

  // 1. Fetch Market Data (poll every 30 mins)
  useEffect(() => {
    async function fetchMarketHours() {
      try {
        const response = await fetch("http://localhost:8000/api/dashboard/market-hours")
        if (!response.ok) throw new Error("Failed to fetch markets")
        const data = await response.json()
        if (data.markets) {
            setMarkets(data.markets)
        }
      } catch (err) {
        console.error("Error fetching market hours:", err)
      } finally {
        setLoading(false)
      }
    }

    fetchMarketHours()

    // Poll every 30 minutes (1800000 ms)
    const interval = setInterval(() => {
        if (document.hidden) return
        fetchMarketHours()
    }, 1800000)
    return () => clearInterval(interval)
  }, [])

  // 2. Client-side clock (ticks every second)
  useEffect(() => {
    // Set initial time immediately
    setLocalTime(new Date().toLocaleTimeString())

    const interval = setInterval(() => {
      setLocalTime(new Date().toLocaleTimeString())
    }, 1000)

    return () => clearInterval(interval)
  }, [])

  // Helper to format ISO string to local HH:MM
  const formatTime = (isoString: string) => {
    try {
        if (!isoString.includes("T")) return isoString // Fallback if not ISO
        const date = new Date(isoString)
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false })
    } catch (e) {
        return isoString
    }
  }

  return (
     <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">Market Hours</CardTitle>
        <Globe className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent className="mt-2 space-y-3">
        {markets.map((market) => {
            const isOpen = market.status === "Open"
            const statusColor = isOpen ? "text-emerald-500" : "text-muted-foreground"

            return (
                <div key={market.name} className="flex items-center justify-between text-sm">
                    <div className="flex items-center space-x-2">
                        <Clock className={`h-3 w-3 ${statusColor}`} />
                        <span className="font-medium">{market.name}</span>
                    </div>
                     <div className="flex items-center space-x-2 text-xs text-muted-foreground">
                        <span>{formatTime(market.open)} - {formatTime(market.close)}</span>
                        {market.message && (
                            <span className="hidden sm:inline-block text-[10px] text-muted-foreground/80">
                                {market.message}
                            </span>
                        )}
                        <span className={`px-1.5 py-0.5 rounded-full bg-secondary ${isOpen ? 'bg-emerald-500/10 text-emerald-500' : ''}`}>
                            {market.status}
                        </span>
                     </div>
                </div>
            )
        })}
         <div className="pt-2 border-t text-xs text-center text-muted-foreground mt-2">
            Local Time: <span className="font-mono">{localTime || "--:--:--"}</span>
         </div>
      </CardContent>
    </Card>
  )
}
