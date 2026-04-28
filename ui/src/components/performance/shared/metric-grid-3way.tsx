import React from "react"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import { SemanticSnapshotScript } from "@/components/ai-chat/SemanticSnapshotScript"

import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

export type MetricConfig = {
  label: string
  accessor: string // key in the data object
  type?: "metric" | "group"
  format?: (value: string | number | null | undefined) => string
  unit?: string
  notes?: string
  description?: string
  onlyShowAll?: boolean
}

export type MetricData = {
  all: Record<string, string | number | null | undefined>
  long: Record<string, string | number | null | undefined>
  short: Record<string, string | number | null | undefined>
}

interface MetricGrid3WayProps {
  title?: string
  metrics: MetricConfig[]
  data: MetricData
  className?: string
}

const defaultFormatter = (val: string | number | null | undefined) => {
  if (typeof val === "number") {
    // Check if it's an integer
    if (Number.isInteger(val)) return val.toString()
    return val.toFixed(2)
  }
  if (val === null || val === undefined) return "-"
  return String(val)
}

export function MetricGrid3Way({
  title,
  metrics,
  data,
  className,
}: MetricGrid3WayProps) {
  const resolveMetric = (
    obj: Record<string, string | number | null | undefined | any>,
    accessor: string,
  ) => {
    if (!obj || !accessor) return undefined;
    
    // Support nested accessors (e.g., "returns.mean")
    if (accessor.includes(".")) {
      const parts = accessor.split(".");
      let current: any = obj;
      for (const part of parts) {
        if (current && current[part] !== undefined) {
          current = current[part];
        } else {
          return undefined;
        }
      }
      return current;
    }

    if (obj[accessor] !== undefined) {
      return obj[accessor]
    }
    if (accessor === "Total # of Trades") {
      if (obj["Total Trades"] !== undefined) return obj["Total Trades"]
      if (obj["total_trades"] !== undefined) return obj["total_trades"]
    }
    return obj[accessor]
  }

  return (
    <Card className={cn("w-full", className)}>
      <SemanticSnapshotScript
        block={{
          id: `metric-grid:${title || "metrics"}`,
          blockType: "metric_table",
          title: title || "Performance metrics",
          summary: "Three-way metric comparison table for all, long, and short trades.",
          keywords: metrics.filter(m => m.type !== "group").map((metric) => metric.label).slice(0, 24),
          headers: ["Metric", "All Trades", "Long", "Short"],
          rows: metrics.slice(0, 60).filter(m => m.type !== "group").map((metric) => {
            const formatter = metric.format || defaultFormatter
            const valAll = resolveMetric(data.all, metric.accessor)
            const valLong = metric.onlyShowAll ? undefined : resolveMetric(data.long, metric.accessor)
            const valShort = metric.onlyShowAll ? undefined : resolveMetric(data.short, metric.accessor)
            return [
              metric.label,
              valAll === null || valAll === undefined ? "-" : formatter(valAll),
              valLong === null || valLong === undefined ? "" : formatter(valLong),
              valShort === null || valShort === undefined ? "" : formatter(valShort),
            ]
          }),
        }}
      />
      {title && (
        <CardHeader className="pb-2">
          <CardTitle className="text-xl font-bold">{title}</CardTitle>
        </CardHeader>
      )}
      <CardContent>
        <TooltipProvider>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[40%]">Metric</TableHead>
                <TableHead className="w-[20%] text-right">All Trades</TableHead>
                <TableHead className="w-[20%] text-right">Long</TableHead>
                <TableHead className="w-[20%] text-right">Short</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {metrics.map((metric, idx) => {
                if (metric.type === "group") {
                    return (
                        <TableRow key={`group-${idx}`} className="bg-muted/40 hover:bg-muted/40 border-y">
                            <TableCell colSpan={4} className="py-2 text-xs font-bold uppercase tracking-wider text-muted-foreground/80">
                                {metric.label}
                            </TableCell>
                        </TableRow>
                    )
                }

                const formatter = metric.format || defaultFormatter
                const valAll = resolveMetric(data.all, metric.accessor)
                const valLong = resolveMetric(data.long, metric.accessor)
                const valShort = resolveMetric(data.short, metric.accessor)

                const renderCell = (
                  val: any,
                  defaultColor: string,
                  onlyShowAll?: boolean,
                  isSubset?: boolean
                ) => {
                  if (onlyShowAll && isSubset) {
                    return (
                        <TableCell className={cn("text-right font-mono", defaultColor)}>
                        </TableCell>
                      )
                  }

                  if (val === null || val === undefined) {
                    return (
                      <TableCell className={cn("text-right font-mono", defaultColor)}>
                        -
                      </TableCell>
                    )
                  }
                  
                  // If it's an object and not a React element, we can't render it directly
                  if (typeof val === 'object' && !React.isValidElement(val)) {
                      return (
                        <TableCell className={cn("text-right font-mono text-muted-foreground", defaultColor)}>
                          N/A
                        </TableCell>
                      )
                  }

                  const isNegative = typeof val === "number" && val < 0
                  // Use absolute value for formatting if negative
                  const absVal = isNegative ? Math.abs(val) : val
                  const formatted = formatter(absVal)
                  const display = isNegative ? `(${formatted})` : formatted
                  const color = isNegative ? "text-red-500" : defaultColor

                  return (
                    <TableCell className={cn("text-right font-mono", color)}>
                      {display}
                    </TableCell>
                  )
                }

                return (
                  <TableRow key={metric.accessor}>
                    <TableCell className="font-medium">
                      {metric.description ? (
                        <Tooltip>
                          <TooltipTrigger className="cursor-help text-left hover:text-primary transition-colors">
                            {metric.label}
                          </TooltipTrigger>
                          <TooltipContent>
                            <p className="max-w-xs">{metric.description}</p>
                          </TooltipContent>
                        </Tooltip>
                      ) : (
                        metric.label
                      )}
                    </TableCell>
                    {renderCell(valAll, "text-foreground/90", metric.onlyShowAll, false)}
                    {renderCell(valLong, "text-foreground/90", metric.onlyShowAll, true)}
                    {renderCell(valShort, "text-foreground/90", metric.onlyShowAll, true)}
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </TooltipProvider>
      </CardContent>
    </Card>
  )
}
