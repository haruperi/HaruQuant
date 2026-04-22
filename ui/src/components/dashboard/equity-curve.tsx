"use client"

import * as React from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { SemanticSnapshotScript } from "@/components/ai-chat/SemanticSnapshotScript"
import { useAuth } from "@/lib/auth-context"
import { formatCurrency } from "@/lib/utils"
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid } from "recharts"

interface EquityPointResponse {
  timestamp: string
  equity: number
}

interface EquityCurveResponse {
  points: EquityPointResponse[]
  history_span_seconds: number
  point_count: number
}

interface ChartPoint {
  label: string
  total: number
  timestamp: number
}

function getSpanLabel(historySpanSeconds: number) {
  const days = historySpanSeconds / 86400

  if (days < 1) return "hours"
  if (days <= 31) return "days"
  if (days < 183) return "weeks"
  if (days < 365) return "months"
  return "years"
}

function formatBucketLabel(date: Date, bucket: string) {
  if (bucket === "hours") {
    return new Intl.DateTimeFormat("en-US", { hour: "numeric" }).format(date)
  }
  if (bucket === "days") {
    return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric" }).format(date)
  }
  if (bucket === "weeks") {
    return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric" }).format(date)
  }
  if (bucket === "months") {
    return new Intl.DateTimeFormat("en-US", { month: "short", year: "2-digit" }).format(date)
  }
  return new Intl.DateTimeFormat("en-US", { year: "numeric" }).format(date)
}

function getBucketKey(date: Date, bucket: string) {
  const year = date.getFullYear()
  const month = date.getMonth()
  const day = date.getDate()

  if (bucket === "hours") {
    return `${year}-${month}-${day}-${date.getHours()}`
  }

  if (bucket === "days") {
    return `${year}-${month}-${day}`
  }

  if (bucket === "weeks") {
    const start = new Date(date)
    start.setHours(0, 0, 0, 0)
    start.setDate(start.getDate() - start.getDay())
    return `${start.getFullYear()}-${start.getMonth()}-${start.getDate()}`
  }

  if (bucket === "months") {
    return `${year}-${month}`
  }

  return `${year}`
}

function groupPoints(points: EquityPointResponse[], historySpanSeconds: number): ChartPoint[] {
  const bucket = getSpanLabel(historySpanSeconds)
  const grouped = new Map<string, ChartPoint>()

  for (const point of points) {
    const date = new Date(point.timestamp)
    const key = getBucketKey(date, bucket)
    grouped.set(key, {
      label: formatBucketLabel(date, bucket),
      total: point.equity,
      timestamp: date.getTime(),
    })
  }

  return Array.from(grouped.values()).sort((a, b) => a.timestamp - b.timestamp)
}

export function EquityCurve() {
  const { authenticatedFetch } = useAuth()
  const [data, setData] = React.useState<ChartPoint[]>([])
  const [description, setDescription] = React.useState("Your total account value over trade history")
  const [loading, setLoading] = React.useState(true)

  React.useEffect(() => {
    let isMounted = true

    async function fetchEquityCurve() {
      try {
        setLoading(true)
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"
        const response = await authenticatedFetch(`${apiUrl}/api/dashboard/equity-curve`)

        if (!response.ok) {
          throw new Error("Failed to fetch equity curve")
        }

        const result = (await response.json()) as EquityCurveResponse
        if (!isMounted) return

        const grouped = groupPoints(result.points, result.history_span_seconds)
        setData(grouped)
        setDescription(
          result.point_count > 0
            ? `Your total account value over ${getSpanLabel(result.history_span_seconds)}`
            : "No trade history available"
        )
      } catch (error) {
        console.error("Failed to load equity curve:", error)
        if (isMounted) {
          setData([])
          setDescription("Unable to load trade history")
        }
      } finally {
        if (isMounted) {
          setLoading(false)
        }
      }
    }

    fetchEquityCurve()

    return () => {
      isMounted = false
    }
  }, [authenticatedFetch])

  return (
    <Card className="col-span-4">
      <SemanticSnapshotScript
        block={{
          id: "dashboard-equity-curve",
          blockType: "chart",
          title: "Equity Curve",
          summary: description,
          keywords: ["equity curve", "account value", "trade history", "equity"],
          metrics: [
            { label: "Point Count", value: String(data.length) },
            { label: "Latest Equity", value: data.length > 0 ? formatCurrency(data[data.length - 1].total) : "N/A" },
            { label: "Starting Equity", value: data.length > 0 ? formatCurrency(data[0].total) : "N/A" },
          ],
          series: [
            {
              label: "Equity",
              points: data.slice(-160).map((point) => ({ x: point.label, y: String(point.total) })),
            },
          ],
        }}
      />
      <CardHeader>
        <CardTitle>Equity Curve</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="pl-2 min-w-0">
        {loading ? (
          <div className="flex h-[350px] items-center justify-center text-sm text-muted-foreground">
            Loading equity curve...
          </div>
        ) : (
          <div className="h-[350px] min-w-0">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data}>
                <defs>
                    <linearGradient id="colorTotal" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                    </linearGradient>
                </defs>
                <XAxis
                  dataKey="label"
                  stroke="#888888"
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  stroke="#888888"
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(value) => formatCurrency(value)}
                  domain={['auto', 'auto']}
                />
                 <Tooltip
                    contentStyle={{ backgroundColor: 'hsl(var(--card))', borderColor: 'hsl(var(--border))', borderRadius: 'var(--radius)' }}
                    itemStyle={{ color: 'hsl(var(--foreground))' }}
                    formatter={(value: number) => [formatCurrency(value), "Equity"]}
                />
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
                <Area
                  type="monotone"
                  dataKey="total"
                  stroke="#10b981"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#colorTotal)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
