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
import { SemanticSnapshotScript } from "@/components/ai-chat/SemanticSnapshotScript"
import { format, isValid, parseISO } from "date-fns"

interface DataPoint {
  date: string | number
  all?: number | null
  long?: number | null
  short?: number | null
  [key: string]: string | number | null | undefined
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

  const getLastValue = (key: ViewMode) => {
    const validPoints = data.filter((d) => d[key] !== undefined && d[key] !== null)
    if (validPoints.length === 0) return "-"
    return valueFormatter(Number(validPoints[validPoints.length - 1][key]))
  }

  return (
    <Card className={cn("w-full flex flex-col", className)}>
      <SemanticSnapshotScript
        block={{
          id: `series-chart:${title}`,
          blockType: "chart",
          title,
          summary: "Time-series chart with all, long, and short trade views.",
          keywords: [title, "chart", "series", ...visibleModes].slice(0, 12),
          metrics: [
            { label: "Current (All)", value: getLastValue("all") },
            { label: "Current (Long)", value: getLastValue("long") },
            { label: "Current (Short)", value: getLastValue("short") },
          ],
          series: [
            {
              label: "All Trades",
              points: data
                .filter((point) => point.all !== undefined && point.all !== null)
                .slice(-160)
                .map((point) => ({ x: String(point.date), y: String(point.all) })),
            },
            {
              label: "Long Trades",
              points: data
                .filter((point) => point.long !== undefined && point.long !== null)
                .slice(-160)
                .map((point) => ({ x: String(point.date), y: String(point.long) })),
            },
            {
              label: "Short Trades",
              points: data
                .filter((point) => point.short !== undefined && point.short !== null)
                .slice(-160)
                .map((point) => ({ x: String(point.date), y: String(point.short) })),
            },
          ],
        }}
      />
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-lg font-medium tracking-tight uppercase">{title}</CardTitle>
        <ToggleGroup
          type="multiple"
          variant="outline"
          value={visibleModes}
          onValueChange={handleToggle}
          className="scale-90 origin-right"
        >
          <ToggleGroupItem value="all" aria-label="Toggle All" className="text-[10px] h-7 px-2">
            All
          </ToggleGroupItem>
          <ToggleGroupItem value="long" aria-label="Toggle Long" className="text-[10px] h-7 px-2">
            Long
          </ToggleGroupItem>
          <ToggleGroupItem value="short" aria-label="Toggle Short" className="text-[10px] h-7 px-2">
            Short
          </ToggleGroupItem>
        </ToggleGroup>
      </CardHeader>
      <CardContent>
        <div className="h-[350px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 5, right: 10, left: 10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" opacity={0.4} />
              <XAxis
                dataKey="date"
                stroke="#888888"
                fontSize={10}
                tickLine={false}
                axisLine={false}
                minTickGap={60}
                tickFormatter={(val) => {
                  if (!val) return ""
                  try {
                    const d = parseISO(String(val))
                    return isValid(d) ? format(d, "MMM dd") : String(val)
                  } catch {
                    return String(val)
                  }
                }}
              />
              <YAxis
                stroke="#888888"
                fontSize={10}
                tickLine={false}
                axisLine={false}
                tickFormatter={(val) => `${val}`}
                domain={['auto', 'auto']}
              />
              <Tooltip
                content={({ active, payload, label }) => {
                  if (active && payload && payload.length) {
                    const formattedDate = (() => {
                      try {
                        const d = parseISO(String(label))
                        return isValid(d) ? format(d, "yyyy-MM-dd HH:mm") : label
                      } catch {
                        return label
                      }
                    })()

                    return (
                      <div className="rounded-lg border bg-background p-2 shadow-xl backdrop-blur-sm border-primary/20">
                        <div className="grid grid-cols-1 gap-2">
                          <div className="flex flex-col border-b border-border/50 pb-1 mb-1">
                            <span className="text-[10px] uppercase text-muted-foreground font-bold tracking-wider">
                              Time Period
                            </span>
                            <span className="font-mono text-xs text-primary">
                              {formattedDate}
                            </span>
                          </div>
                          <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                            {payload.map((p) => (
                              <React.Fragment key={p.name}>
                                <span className="text-[10px] uppercase text-muted-foreground">
                                  {p.name}
                                </span>
                                <span className="font-bold text-right text-xs" style={{ color: p.color }}>
                                  {p.value !== undefined ? valueFormatter(Number(p.value)) : "-"}
                                </span>
                              </React.Fragment>
                            ))}
                          </div>
                        </div>
                      </div>
                    )
                  }
                  return null
                }}
              />
              <Legend verticalAlign="top" height={36}/>
              {visibleModes.includes("all") && (
                <Line
                  type="monotone"
                  dataKey="all"
                  name="All Trades"
                  stroke="var(--foreground)"
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
                  stroke="#3b82f6"
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
                  stroke="#ef4444"
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
