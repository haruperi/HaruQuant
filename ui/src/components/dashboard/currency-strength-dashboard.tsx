"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { RefreshCw, Activity, Clock, TrendingUp } from "lucide-react"
import { CurrencyStrengthCard } from "./currency-strength-card"
import { CurrencyPairStrengthTable } from "./currency-pair-strength-table"
import type { CurrencyStrengthData, CurrencyStrength } from "@/types/live"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

interface CurrencyStrengthDashboardProps {
  sessionId?: number
  autoRefresh?: boolean
}

type TradingStyle = "short-term" | "mid-term" | "long-term"

interface TimeframePreset {
  name: string
  tf1: string
  tf2: string
  tf3: string
  refreshInterval: number
  description: string
}

const PRESETS: Record<TradingStyle, TimeframePreset> = {
  "short-term": {
    name: "Short-Term",
    tf1: "M1",
    tf2: "M5",
    tf3: "H1",
    refreshInterval: 60, // 1 minute
    description: "Scalping & Ultra Short-Term (M1, M5, H1)",
  },
  "mid-term": {
    name: "Mid-Term",
    tf1: "M5",
    tf2: "H1",
    tf3: "H4",
    refreshInterval: 300, // 5 minutes
    description: "Day Trading (M5, H1, H4)",
  },
  "long-term": {
    name: "Long-Term",
    tf1: "H1",
    tf2: "H4",
    tf3: "D1",
    refreshInterval: 3600, // 1 hour
    description: "Swing Trading (H1, H4, D1)",
  },
}

export function CurrencyStrengthDashboard({
  sessionId,
  autoRefresh = true,
}: CurrencyStrengthDashboardProps) {
  const [data, setData] = useState<CurrencyStrengthData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [tradingStyle, setTradingStyle] = useState<TradingStyle>("short-term")
  const [secondsUntilRefresh, setSecondsUntilRefresh] = useState<number>(PRESETS["short-term"].refreshInterval)

  const currentPreset = PRESETS[tradingStyle]
  const refreshInterval = currentPreset.refreshInterval

  // Fetch currency strength data
  const fetchCurrencyStrength = async () => {
    setIsRefreshing(true)
    try {
      // Get auth token from localStorage
      const token = localStorage.getItem("token")

      // Build API URL - use all 28 pairs for comprehensive analysis
      const params = new URLSearchParams()
      params.append('pairs_count', '28')  // Use all major pairs
      params.append('tf1', currentPreset.tf1)  // Lowest timeframe
      params.append('tf2', currentPreset.tf2)  // Middle timeframe
      params.append('tf3', currentPreset.tf3)  // Highest timeframe
      if (sessionId) {
        params.append('session_id', sessionId.toString())
      }
      const url = `/api/dashboard/currency-strength?${params.toString()}`

      // Fetch from API
      const response = await fetch(url, {
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      })

      if (!response.ok) {
        throw new Error(`API error: ${response.status} ${response.statusText}`)
      }

      const result = await response.json()
      setData(result)
      setLastUpdate(new Date())
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch data")
    } finally {
      setLoading(false)
      setIsRefreshing(false)
    }
  }

  // Initial fetch and refetch when trading style changes
  useEffect(() => {
    fetchCurrencyStrength()
    setSecondsUntilRefresh(refreshInterval)
  }, [sessionId, tradingStyle])

  // Auto-refresh with countdown
  useEffect(() => {
    if (!autoRefresh) return

    // Reset countdown when refresh interval changes
    setSecondsUntilRefresh(refreshInterval)

    // Countdown timer (updates every second)
    const countdownInterval = setInterval(() => {
      setSecondsUntilRefresh((prev) => {
        if (prev <= 1) {
          return refreshInterval
        }
        return prev - 1
      })
    }, 1000)

    // Data refresh timer
    const refreshTimer = setInterval(() => {
      if (!document.hidden) {
        fetchCurrencyStrength()
        setSecondsUntilRefresh(refreshInterval)
      }
    }, refreshInterval * 1000)

    return () => {
      clearInterval(countdownInterval)
      clearInterval(refreshTimer)
    }
  }, [autoRefresh, refreshInterval])

  // Manual refresh
  const handleRefresh = () => {
    fetchCurrencyStrength()
    setSecondsUntilRefresh(refreshInterval)
  }

  // Format countdown time
  const formatCountdown = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  if (loading && !data) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="flex items-center space-x-2">
          <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
          <span className="text-muted-foreground">
            Loading currency strength data...
          </span>
        </div>
      </div>
    )
  }

  if (error && !data) {
    return (
      <Card className="border-red-500/50">
        <CardHeader>
          <CardTitle className="text-red-500">Error</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">{error}</p>
          <Button onClick={handleRefresh} className="mt-4" variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            Retry
          </Button>
        </CardContent>
      </Card>
    )
  }

  if (!data) {
    return (
      <Card>
        <CardContent className="py-8">
          <p className="text-center text-muted-foreground">No data available</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Trading Style Selector */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center gap-4">
            <div className="flex-1">
              <label htmlFor="trading-style" className="text-sm font-medium">
                Trading Style
              </label>
              <Select
                value={tradingStyle}
                onValueChange={(value) => setTradingStyle(value as TradingStyle)}
              >
                <SelectTrigger id="trading-style" className="mt-1.5">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="short-term">
                    <div className="flex flex-col items-start">
                      <span className="font-medium">{PRESETS["short-term"].name}</span>
                      <span className="text-xs text-muted-foreground">
                        {PRESETS["short-term"].description}
                      </span>
                    </div>
                  </SelectItem>
                  <SelectItem value="mid-term">
                    <div className="flex flex-col items-start">
                      <span className="font-medium">{PRESETS["mid-term"].name}</span>
                      <span className="text-xs text-muted-foreground">
                        {PRESETS["mid-term"].description}
                      </span>
                    </div>
                  </SelectItem>
                  <SelectItem value="long-term">
                    <div className="flex flex-col items-start">
                      <span className="font-medium">{PRESETS["long-term"].name}</span>
                      <span className="text-xs text-muted-foreground">
                        {PRESETS["long-term"].description}
                      </span>
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex-1">
              <div className="text-sm font-medium mb-1.5">Timeframes</div>
              <div className="flex items-center gap-2">
                <Badge variant="outline">{currentPreset.tf1}</Badge>
                <Badge variant="outline">{currentPreset.tf2}</Badge>
                <Badge variant="outline">{currentPreset.tf3}</Badge>
              </div>
            </div>
            <div className="flex-1">
              <div className="text-sm font-medium mb-1.5">Refresh Interval</div>
              <div className="text-sm text-muted-foreground">
                {refreshInterval >= 3600
                  ? `${refreshInterval / 3600} hour${refreshInterval > 3600 ? "s" : ""}`
                  : refreshInterval >= 60
                  ? `${refreshInterval / 60} minutes`
                  : `${refreshInterval} seconds`}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Header with Stats */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">
            Currency Strength Dashboard
          </h2>
          <p className="text-muted-foreground mt-1">
            {currentPreset.description}
          </p>
        </div>

        <div className="flex items-center space-x-4">
          {lastUpdate && (
            <div className="flex flex-col items-end space-y-1">
              <div className="flex items-center space-x-2 text-sm text-muted-foreground">
                <Clock className="h-4 w-4" />
                <span>
                  Updated {lastUpdate.toLocaleTimeString()}
                </span>
              </div>
              {autoRefresh && (
                <div className="text-xs text-muted-foreground">
                  Next refresh in {formatCountdown(secondsUntilRefresh)}
                </div>
              )}
            </div>
          )}

          <Button
            onClick={handleRefresh}
            disabled={isRefreshing}
            size="sm"
            variant="outline"
          >
            <RefreshCw
              className={`h-4 w-4 mr-2 ${isRefreshing ? "animate-spin" : ""}`}
            />
            Refresh
          </Button>
        </div>
      </div>

      {/* Status Bar */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Strongest Currency
            </CardTitle>
            <Activity className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {data.currencies[0]?.currency || "-"}
            </div>
            <p className="text-xs text-muted-foreground">
              Strength: {data.currencies[0]?.strength.toFixed(2)}%
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Weakest Currency
            </CardTitle>
            <Activity className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {data.currencies[data.currencies.length - 1]?.currency || "-"}
            </div>
            <p className="text-xs text-muted-foreground">
              Strength:{" "}
              {data.currencies[
                data.currencies.length - 1
              ]?.strength.toFixed(2)}
              %
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Trading Opportunities
            </CardTitle>
            <Badge variant="outline">
              {data.strong_pairs.length + data.weak_pairs.length}
            </Badge>
          </CardHeader>
          <CardContent>
            <div className="flex justify-between text-sm">
              <span className="text-emerald-500">
                {data.strong_pairs.length} LONG
              </span>
              <span className="text-red-500">
                {data.weak_pairs.length} SHORT
              </span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Currency Strength Cards - 4x2 Grid */}
      <div>
        <h3 className="text-xl font-semibold mb-4">Currency Rankings</h3>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {data.currencies
            .sort((a, b) => a.rank - b.rank)
            .map((currency) => (
              <CurrencyStrengthCard key={currency.currency} data={currency} />
            ))}
        </div>
      </div>

      {/* Pair Strength Tables */}
      <div className="grid gap-6 lg:grid-cols-2">
        <CurrencyPairStrengthTable
          pairs={data.strong_pairs}
          title="Strong Pairs - LONG Opportunities"
          type="strong"
          maxRows={10}
          tf1Label={data.tf1_label}
          tf2Label={data.tf2_label}
          tf3Label={data.tf3_label}
        />

        <CurrencyPairStrengthTable
          pairs={data.weak_pairs}
          title="Weak Pairs - SHORT Opportunities"
          type="weak"
          maxRows={10}
          tf1Label={data.tf1_label}
          tf2Label={data.tf2_label}
          tf3Label={data.tf3_label}
        />
      </div>
    </div>
  )
}
