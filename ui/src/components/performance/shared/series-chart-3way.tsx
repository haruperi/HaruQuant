"use client"

import * as React from "react"
import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  CartesianGrid,
  Legend,
} from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { cn } from "@/lib/utils"

interface DataPoint {
  date: string | number
  all?: number | null
  long?: number | null
  short?: number | null
  [key: string]: any
}

interface SeriesChart3WayProps {
  title: string
  data: DataPoint[]
  valueFormatter?: (value: number) => string
  className?: string
  yAxisLabel?: string
}

type ViewMode = "all" | "long" | "short"

export function SeriesChart3Way({
  title,
  data,
  valueFormatter = (val) => val.toFixed(2),
  className,
}: SeriesChart3WayProps) {
  const [visibleModes, setVisibleModes] = React.useState<ViewMode[]>(["all"])

  const handleToggle = (value: string[]) => {
    if (value.length > 0) {
      setVisibleModes(value as ViewMode[])
    }
  }

  // Pre-calculate min/max for Y-axis domain if needed, or let Recharts handle 'auto'
  // Getting stats for footer
  const getLastValue = (key: ViewMode) => {
    const validPoints = data.filter((d) => d[key] !== undefined && d[key] !== null)
    if (validPoints.length === 0) return "-"
    return valueFormatter(Number(validPoints[validPoints.length - 1][key]))
  }

  return (
    <Card className={cn("w-full flex flex-col", className)}>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-lg font-medium">{title}</CardTitle>
        <ToggleGroup
          type="multiple"
          variant="outline"
          value={visibleModes}
          onValueChange={handleToggle}
          className="scale-90 origin-right"
        >
          <ToggleGroupItem value="all" aria-label="Toggle All">
            All
          </ToggleGroupItem>
          <ToggleGroupItem value="long" aria-label="Toggle Long">
            Long
          </ToggleGroupItem>
          <ToggleGroupItem value="short" aria-label="Toggle Short">
            Short
          </ToggleGroupItem>
        </ToggleGroup>
      </CardHeader>
      <CardContent>
        <div className="h-[350px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 5, right: 10, left: 10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
              <XAxis
                dataKey="date"
                stroke="#888888"
                fontSize={12}
                tickLine={false}
                axisLine={false}
                minTickGap={30}
              />
              <YAxis
                stroke="#888888"
                fontSize={12}
                tickLine={false}
                axisLine={false}
                tickFormatter={(val) => `${val}`}
                domain={['auto', 'auto']}
              />
              <Tooltip
                content={({ active, payload, label }) => {
                  if (active && payload && payload.length) {
                    return (
                      <div className="rounded-lg border bg-background p-2 shadow-sm">
                        <div className="grid grid-cols-2 gap-2">
                          <div className="flex flex-col">
                            <span className="text-[0.70rem] uppercase text-muted-foreground">
                              Date
                            </span>
                            <span className="font-bold text-muted-foreground">
                              {label}
                            </span>
                          </div>
                          {payload.map((p) => (
                            <div key={p.name} className="flex flex-col">
                              <span className="text-[0.70rem] uppercase text-muted-foreground">
                                {p.name}
                              </span>
                              <span className="font-bold" style={{ color: p.color }}>
                                {p.value !== undefined ? valueFormatter(Number(p.value)) : "-"}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )
                  }
                  return null
                }}
              />
              <Legend />
              {visibleModes.includes("all") && (
                <Line
                  type="monotone"
                  dataKey="all"
                  name="All Trades"
                  stroke="var(--foreground)" // Use theme foreground or primary color
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4 }}
                  connectNulls
                />
              )}
              {visibleModes.includes("long") && (
                <Line
                  type="monotone"
                  dataKey="long"
                  name="Long Trades"
                  stroke="#3b82f6" // blue-500
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4 }}
                  connectNulls
                />
              )}
              {visibleModes.includes("short") && (
                <Line
                  type="monotone"
                  dataKey="short"
                  name="Short Trades"
                  stroke="#ef4444" // red-500
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4 }}
                  connectNulls
                />
              )}
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="mt-4 grid grid-cols-3 gap-4 border-t pt-4">
          <div className="flex flex-col">
            <span className="text-[0.70rem] uppercase text-muted-foreground">
              Current (All)
            </span>
            <span className="text-xl font-bold">{getLastValue("all")}</span>
          </div>
          <div className="flex flex-col">
             <span className="text-[0.70rem] uppercase text-muted-foreground">
              Current (Long)
            </span>
            <span className="text-xl font-bold text-blue-500">{getLastValue("long")}</span>
          </div>
          <div className="flex flex-col">
             <span className="text-[0.70rem] uppercase text-muted-foreground">
              Current (Short)
            </span>
            <span className="text-xl font-bold text-red-500">{getLastValue("short")}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
