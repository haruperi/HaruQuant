"use client"

import * as React from "react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { SemanticSnapshotScript } from "@/components/ai-chat/SemanticSnapshotScript"
import { cn } from "@/lib/utils"

interface DistributionPanel3WayProps {
  title: string
  data: {
    all: number[]
    long: number[]
    short: number[]
  }
  className?: string
  unit?: string
}

// --- Stats Helpers ---

const sum = (arr: number[]) => arr.reduce((a, b) => a + b, 0)
const mean = (arr: number[]) => (arr.length ? sum(arr) / arr.length : 0)

const median = (arr: number[]) => {
  if (!arr.length) return 0
  const sorted = [...arr].sort((a, b) => a - b)
  const mid = Math.floor(sorted.length / 2)
  return sorted.length % 2 !== 0
    ? sorted[mid]
    : (sorted[mid - 1] + sorted[mid]) / 2
}

const stdDev = (arr: number[], m?: number) => {
  if (arr.length < 2) return 0
  const mu = m ?? mean(arr)
  const sqDiff = arr.map((x) => Math.pow(x - mu, 2))
  return Math.sqrt(sum(sqDiff) / (arr.length - 1))
}

const skewness = (arr: number[], m?: number, s?: number) => {
  if (arr.length < 3) return 0
  const mu = m ?? mean(arr)
  const sigma = s ?? stdDev(arr, mu)
  if (sigma === 0) return 0
  const n = arr.length
  const cubed = arr.map((x) => Math.pow((x - mu) / sigma, 3))
  return (n / ((n - 1) * (n - 2))) * sum(cubed)
}

const kurtosis = (arr: number[], m?: number, s?: number) => {
  if (arr.length < 4) return 0
  const mu = m ?? mean(arr)
  const sigma = s ?? stdDev(arr, mu)
  if (sigma === 0) return 0
  const n = arr.length
  const fourth = arr.map((x) => Math.pow((x - mu) / sigma, 4))
  return (
    ((n * (n + 1)) / ((n - 1) * (n - 2) * (n - 3))) * sum(fourth) -
    (3 * Math.pow(n - 1, 2)) / ((n - 2) * (n - 3))
  )
}

// --- Histogram Helper ---

const computeHistogram = (all: number[], bins = 20) => {
  if (!all.length) return { buckets: [], step: 0 }
  const min = Math.min(...all)
  const max = Math.max(...all)
  const range = max - min || 1
  const step = range / bins

  // Create bins
  const buckets = Array.from({ length: bins }, (_, i) => ({
    name: (min + i * step + step / 2).toFixed(2), // mid-point label
    start: min + i * step,
    end: min + (i + 1) * step,
    all: 0,
    long: 0,
    short: 0,
  }))

  return { buckets, step }
}

export function DistributionPanel3Way({
  title,
  data,
  className,
  unit = "",
}: DistributionPanel3WayProps) {
  const stats = React.useMemo(() => {
    const calc = (arr: number[]) => {
      const m = mean(arr)
      const s = stdDev(arr, m)
      return {
        mean: m,
        median: median(arr),
        stdDev: s,
        skew: skewness(arr, m, s),
        kurt: kurtosis(arr, m, s),
        count: arr.length,
      }
    }
    return {
      all: calc(data.all),
      long: calc(data.long),
      short: calc(data.short),
    }
  }, [data])

  const histogramData = React.useMemo(() => {
    const combined = [...data.all]
    const { buckets, step } = computeHistogram(combined, 15)

    // Fill buckets
    const fill = (arr: number[], key: "all" | "long" | "short") => {
      arr.forEach((val) => {
        // Find bucket
        const bucketIndex = Math.min(
            buckets.length - 1,
            Math.floor((val - buckets[0].start) / step)
        )
        if (bucketIndex >= 0) buckets[bucketIndex][key]++
      })
    }

    fill(data.all, "all")
    fill(data.long, "long")
    fill(data.short, "short")

    return buckets
  }, [data])

  const formatStat = (val: number) => {
      if (Math.abs(val) < 0.01 && val !== 0) return val.toExponential(2)
      return val.toFixed(2)
  }

  return (
    <Card className={cn("w-full", className)}>
      <SemanticSnapshotScript
        block={{
          id: `distribution:${title}`,
          blockType: "chart",
          title,
          summary: "Distribution histogram and summary statistics for all, long, and short trades.",
          keywords: [title, "distribution", "histogram", "mean", "median", "std dev", "skewness", "kurtosis"],
          metrics: [
            { label: "Count (All)", value: String(stats.all.count) },
            { label: "Mean (All)", value: `${formatStat(stats.all.mean)} ${unit}`.trim() },
            { label: "Median (All)", value: `${formatStat(stats.all.median)} ${unit}`.trim() },
            { label: "Std Dev (All)", value: formatStat(stats.all.stdDev) },
            { label: "Skewness (All)", value: formatStat(stats.all.skew) },
            { label: "Kurtosis (All)", value: formatStat(stats.all.kurt) },
          ],
          headers: ["Statistic", "All", "Long", "Short"],
          rows: [
            ["Count", String(stats.all.count), String(stats.long.count), String(stats.short.count)],
            ["Mean", `${formatStat(stats.all.mean)} ${unit}`.trim(), `${formatStat(stats.long.mean)} ${unit}`.trim(), `${formatStat(stats.short.mean)} ${unit}`.trim()],
            ["Median", `${formatStat(stats.all.median)} ${unit}`.trim(), `${formatStat(stats.long.median)} ${unit}`.trim(), `${formatStat(stats.short.median)} ${unit}`.trim()],
            ["Std Dev", formatStat(stats.all.stdDev), formatStat(stats.long.stdDev), formatStat(stats.short.stdDev)],
            ["Skewness", formatStat(stats.all.skew), formatStat(stats.long.skew), formatStat(stats.short.skew)],
            ["Kurtosis", formatStat(stats.all.kurt), formatStat(stats.long.kurt), formatStat(stats.short.kurt)],
          ],
        }}
      />
      <CardHeader className="pb-2">
        <CardTitle className="text-lg font-medium">{title}</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-6">
        {/* Chart */}
        <div className="h-[300px] w-full">
           <ResponsiveContainer width="100%" height="100%">
            <BarChart data={histogramData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="name" fontSize={12} tickLine={false} axisLine={false} />
              <YAxis fontSize={12} tickLine={false} axisLine={false} />
              <Tooltip
                 content={({ active, payload, label }) => {
                    if (active && payload && payload.length) {
                        return (
                            <div className="rounded-lg border bg-background p-2 shadow-sm text-xs">
                                <div className="font-bold mb-1">Bin: {label}</div>
                                {payload.map((p) => (
                                    <div key={p.name} className="flex justify-between gap-2">
                                        <span style={{ color: p.color }}>{p.name}:</span>
                                        <span>{p.value}</span>
                                    </div>
                                ))}
                            </div>
                        )
                    }
                    return null
                 }}
              />
              <Legend />
              <Bar dataKey="long" name="Long" fill="#3b82f6" fillOpacity={0.7} />
              <Bar dataKey="short" name="Short" fill="#ef4444" fillOpacity={0.7} />
              {/* Overlay All as line or transparent bar? Let's just show Long/Short stacked or grouped?
                  Or maybe just show Long/Short side by side.
                  Actually user asked for 3 way. Let's start with Long/Short bars.
                  Showing 'All' bar alongside might be cluttered.
                  Let's stick to Long/Short bars that sum up roughly to All visually,
                  or just show Long and Short distribution.
                  Usually 'All' is implicitly the sum.
                  Let's just show Long and Short for now to avoid clutter,
                  as 'All' would cover them.
               */}
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Stats Table */}
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Statistic</TableHead>
              <TableHead className="text-right">All</TableHead>
              <TableHead className="text-right">Long</TableHead>
              <TableHead className="text-right">Short</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow>
               <TableCell className="font-medium">Count</TableCell>
               <TableCell className="text-right">{stats.all.count}</TableCell>
               <TableCell className="text-right text-blue-500">{stats.long.count}</TableCell>
               <TableCell className="text-right text-red-500">{stats.short.count}</TableCell>
            </TableRow>
            <TableRow>
               <TableCell className="font-medium">Mean</TableCell>
               <TableCell className="text-right">{formatStat(stats.all.mean)} {unit}</TableCell>
               <TableCell className="text-right text-blue-500">{formatStat(stats.long.mean)} {unit}</TableCell>
               <TableCell className="text-right text-red-500">{formatStat(stats.short.mean)} {unit}</TableCell>
            </TableRow>
             <TableRow>
               <TableCell className="font-medium">Median</TableCell>
               <TableCell className="text-right">{formatStat(stats.all.median)} {unit}</TableCell>
               <TableCell className="text-right text-blue-500">{formatStat(stats.long.median)} {unit}</TableCell>
               <TableCell className="text-right text-red-500">{formatStat(stats.short.median)} {unit}</TableCell>
            </TableRow>
             <TableRow>
               <TableCell className="font-medium">Std Dev</TableCell>
               <TableCell className="text-right">{formatStat(stats.all.stdDev)}</TableCell>
               <TableCell className="text-right text-blue-500">{formatStat(stats.long.stdDev)}</TableCell>
               <TableCell className="text-right text-red-500">{formatStat(stats.short.stdDev)}</TableCell>
            </TableRow>
             <TableRow>
               <TableCell className="font-medium">Skewness</TableCell>
               <TableCell className="text-right">{formatStat(stats.all.skew)}</TableCell>
               <TableCell className="text-right text-blue-500">{formatStat(stats.long.skew)}</TableCell>
               <TableCell className="text-right text-red-500">{formatStat(stats.short.skew)}</TableCell>
            </TableRow>
             <TableRow>
               <TableCell className="font-medium">Kurtosis</TableCell>
               <TableCell className="text-right">{formatStat(stats.all.kurt)}</TableCell>
               <TableCell className="text-right text-blue-500">{formatStat(stats.long.kurt)}</TableCell>
               <TableCell className="text-right text-red-500">{formatStat(stats.short.kurt)}</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
