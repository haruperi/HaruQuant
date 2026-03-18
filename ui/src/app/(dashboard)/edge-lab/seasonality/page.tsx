"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { edgeLabApi, type EdgeLabSeasonalityResponse } from "@/lib/api/edge"
import {
  EDGE_LAB_DOW_ORDER,
  buildSeasonalityCalendarSeries,
  buildSeasonalityTakeawayModel,
  buildSeasonalityWeeklyBias,
} from "@/lib/edge-lab-dashboard"
import { useEdgeLabData } from "@/contexts/edge-lab-data-context"
import { EdgeLabDatasetSummary } from "@/components/edge-lab/dataset-summary"
import { EdgeLabPrerequisiteState } from "@/components/edge-lab/prerequisite-state"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

const DOW_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
const formatCell = (value: number | null, digits = 2) => {
  if (value === null || Number.isNaN(value)) return "-"
  return value.toFixed(digits)
}

const formatPct = (value: number | null | undefined, digits = 1) => {
  if (value === null || value === undefined || Number.isNaN(value)) return "-"
  return `${(value * 100).toFixed(digits)}%`
}

const DataInputTable = ({
  rows,
  total,
  offset,
  digits,
}: {
  rows: EdgeLabSeasonalityResponse["data_rows"]
  total: number
  offset: number
  digits: number
}) => (
  <div className="space-y-3">
    <div className="flex items-center justify-between text-sm text-muted-foreground">
      <span>
        {total === 0 ? "0 rows" : `Rows ${offset + 1}-${offset + rows.length} of ${total}`}
      </span>
    </div>
    <div className="max-h-[520px] overflow-auto rounded-md border">
      <table className="w-full border-collapse text-xs">
        <thead className="sticky top-0 bg-background">
          <tr>
            <th className="border px-2 py-1 text-left">Date</th>
            <th className="border px-2 py-1 text-left">Time</th>
            <th className="border px-2 py-1 text-right">Open</th>
            <th className="border px-2 py-1 text-right">High</th>
            <th className="border px-2 py-1 text-right">Low</th>
            <th className="border px-2 py-1 text-right">Close</th>
            <th className="border px-2 py-1 text-right">Volume</th>
            <th className="border px-2 py-1 text-right">Spread (Pips)</th>
            <th className="border px-2 py-1 text-left">Decade</th>
            <th className="border px-2 py-1 text-right">Day</th>
            <th className="border px-2 py-1 text-left">Month</th>
            <th className="border px-2 py-1 text-right">Year</th>
            <th className="border px-2 py-1 text-left">DOW</th>
            <th className="border px-2 py-1 text-right">Count</th>
            <th className="border px-2 py-1 text-right">Range H-L (Pips)</th>
            <th className="border px-2 py-1 text-right">C-O Pips</th>
            <th className="border px-2 py-1 text-right">C-O Win/Loss</th>
            <th className="border px-2 py-1 text-right">C-O % of Close</th>
            <th className="border px-2 py-1 text-right">TimeRND</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, idx) => (
            <tr key={`${row.date}-${row.time}-${idx}`}>
              <td className="border px-2 py-1">{row.date}</td>
              <td className="border px-2 py-1">{row.time}</td>
              <td className="border px-2 py-1 text-right">{formatCell(row.open, digits)}</td>
              <td className="border px-2 py-1 text-right">{formatCell(row.high, digits)}</td>
              <td className="border px-2 py-1 text-right">{formatCell(row.low, digits)}</td>
              <td className="border px-2 py-1 text-right">{formatCell(row.close, digits)}</td>
              <td className="border px-2 py-1 text-right">{row.volume ?? "-"}</td>
              <td className="border px-2 py-1 text-right">{formatCell(row.spread_pips, 1)}</td>
              <td className="border px-2 py-1">{row.decade}</td>
              <td className="border px-2 py-1 text-right">{row.day}</td>
              <td className="border px-2 py-1">{row.month}</td>
              <td className="border px-2 py-1 text-right">{row.year}</td>
              <td className="border px-2 py-1">{row.dow}</td>
              <td className="border px-2 py-1 text-right">{row.count}</td>
              <td className="border px-2 py-1 text-right">{formatCell(row.range_hl, 1)}</td>
              <td className="border px-2 py-1 text-right">{formatCell(row.co_points, 1)}</td>
              <td className="border px-2 py-1 text-right">{row.co_win_loss}</td>
              <td className="border px-2 py-1 text-right">{formatCell(row.co_pct, 2)}</td>
              <td className="border px-2 py-1 text-right">{row.time_rnd}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  </div>
)

const HeatmapChart = ({
  title,
  table,
  digits = 2,
  percent = false,
}: {
  title: string
  table: EdgeLabSeasonalityResponse["heatmaps"][string]
  digits?: number
  percent?: boolean
}) => {
  const values = table.values.flat().filter((val) => val !== null) as number[]
  const min = values.length ? Math.min(...values) : 0
  const max = values.length ? Math.max(...values) : 1
  const scale = (value: number | null) => {
    if (value === null || Number.isNaN(value)) return "rgba(30, 41, 59, 0.25)"
    const norm = max === min ? 0.5 : (value - min) / (max - min)
    const alpha = 0.2 + norm * 0.75
    return `rgba(59, 130, 246, ${alpha})`
  }

  return (
    <div className="rounded-md border p-3">
      <div className="text-sm font-medium">{title}</div>
      <div className="mt-3 grid grid-cols-[44px_repeat(7,minmax(0,1fr))] gap-1 text-[10px]">
        <div />
        {table.columns.map((col) => (
          <div key={`head-${title}-${col}`} className="text-center text-muted-foreground">
            {DOW_LABELS[col] ?? col}
          </div>
        ))}
        {table.index.map((hour, rowIdx) => (
          <div key={`row-${title}-${hour}`} className="contents">
            <div
              className="flex items-center justify-end pr-1 font-mono text-muted-foreground"
            >
              {hour}
            </div>
            {table.values[rowIdx].map((value, colIdx) => (
              <div
                key={`${title}-${hour}-${colIdx}`}
                className="flex h-7 items-center justify-center rounded text-[10px] font-medium text-white"
                style={{ backgroundColor: scale(value) }}
                title={`${DOW_LABELS[table.columns[colIdx] ?? colIdx] ?? colIdx} ${hour}:00 = ${
                  percent ? `${Math.round((value ?? 0) * 100)}%` : formatCell(value, digits)
                }`}
              >
                {percent ? `${Math.round((value ?? 0) * 100)}` : formatCell(value, digits)}
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}

export default function SeasonalityPage() {
  const { dataset, coreMetricProfile, seasonalityResult, setSeasonalityResult } = useEdgeLabData()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [dataOffset, setDataOffset] = useState(0)
  const dataLimit = 20
  const [calendarMetric, setCalendarMetric] = useState<
    "count" | "avg_range_points" | "avg_co_points" | "avg_spread_points" | "avg_co_pct"
  >("avg_co_points")

  const runSeasonality = async (overrideOffset?: number) => {
    if (!dataset) {
      setError("Load a dataset in the Data tab first.")
      return
    }
    setLoading(true)
    setError(null)
    try {
      const effectiveOffset = overrideOffset ?? dataOffset
      const payload = {
        symbol: dataset.request.symbol,
        timeframe: dataset.request.timeframe,
        data_source: dataset.request.data_source,
        range_by: dataset.request.range_by,
        start_date: dataset.request.start_date ?? undefined,
        end_date: dataset.request.end_date ?? undefined,
        number_of_bars: dataset.request.number_of_bars ?? undefined,
        prepared_dataset: dataset,
        data_offset: effectiveOffset,
        data_limit: dataLimit,
      }
      const response = await edgeLabApi.getSeasonality(payload)
      setSeasonalityResult(response)
      setDataOffset(effectiveOffset)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run seasonality.")
      setSeasonalityResult(null)
    } finally {
      setLoading(false)
    }
  }

  const intradayRows = buildSeasonalityWeeklyBias(seasonalityResult)
  const takeaway = buildSeasonalityTakeawayModel(seasonalityResult)
  const sessionOpportunityRows = seasonalityResult?.session_summary.map((row) => ({
    session: row.session,
    opportunity: row.opportunity_score,
    avgRange: row.avg_range_pips,
    avgSpread: row.avg_spread_pips,
  })) ?? []
  const sessionHighLowRows = seasonalityResult?.session_high_low.rows.map((row) => ({
    session: row.session,
    highRate: (row.high_rate ?? 0) * 100,
    lowRate: (row.low_rate ?? 0) * 100,
  })) ?? []
  const opportunityHourRows = [
    ...(seasonalityResult?.opportunity_windows.best_hours.map((row) => ({
      label: `${row.hour}:00`,
      score: row.opportunity_score,
      group: "Best",
    })) ?? []),
    ...(seasonalityResult?.opportunity_windows.dead_hours.map((row) => ({
      label: `${row.hour}:00`,
      score: row.opportunity_score,
      group: "Low",
    })) ?? []),
  ]

  if (!coreMetricProfile) {
    return (
      <div className="flex flex-col gap-6 p-6">
        <EdgeLabPrerequisiteState
          title="Seasonality Requires Core Metric"
          description="Run Core Metric first so Seasonality becomes the next progressive step in the Edge Lab flow."
          actionHref="/edge-lab/core-metric"
          actionLabel="Go To Core Metric"
        />
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <Card>
        <CardHeader>
          <CardTitle>Run Seasonality</CardTitle>
          <CardDescription>Generate intraday bias, heatmaps, and calendar stats from the session dataset.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <EdgeLabDatasetSummary
            dataset={dataset}
            emptyMessage="Load a dataset in the Data tab before running Seasonality."
          />

          <div className="flex items-center gap-3">
            <Button
              onClick={() => {
                runSeasonality(0)
              }}
              disabled={loading || !dataset}
            >
              {loading ? "Running..." : "Run Seasonality"}
            </Button>
            {error && <p className="text-sm text-destructive">{error}</p>}
          </div>
          {dataset?.meta.session_basis && (
            <div className="text-xs text-muted-foreground">
              Session classification uses {dataset.meta.session_basis} hours.
            </div>
          )}
        </CardContent>
      </Card>

      {seasonalityResult && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>Intraday Bias</CardTitle>
              <CardDescription>
                {seasonalityResult.meta.filtered_rows} of {seasonalityResult.meta.total_rows} bars in scope.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[360px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={intradayRows}
                    margin={{ top: 10, right: 16, left: 0, bottom: 24 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="index"
                      tickFormatter={(value) => String(intradayRows[value]?.hour ?? "")}
                      interval={5}
                      tickMargin={8}
                    />
                    <YAxis
                      width={70}
                      tickFormatter={(value) =>
                        Number.isFinite(value) ? `${value.toFixed(1)}p` : ""
                      }
                    />
                    <Tooltip
                      formatter={(value: number | string) =>
                        typeof value === "number" ? `${value.toFixed(2)} pips` : "-"
                      }
                      labelFormatter={(label) => {
                        const row = intradayRows[label]
                        if (!row) return ""
                        return `${row.dayLabel} ${row.hour}:00`
                      }}
                    />
                    {EDGE_LAB_DOW_ORDER.map((dow, idx) => (
                      <ReferenceLine
                        key={`day-${dow}`}
                        x={idx * 24}
                        stroke="#f97316"
                        strokeWidth={1}
                        label={{
                          position: "insideTop",
                          value: DOW_LABELS[dow] ?? dow,
                          fill: "#f97316",
                          fontSize: 12,
                          dy: -6,
                        }}
                      />
                    ))}
                    <Line
                      type="monotone"
                      dataKey="value"
                      name="Bias"
                      stroke="#3b82f6"
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Hour x Day Heatmaps</CardTitle>
              <CardDescription>Average metrics per hour and day-of-week.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid gap-4 xl:grid-cols-2">
                <HeatmapChart title="Avg Range (Pips)" table={seasonalityResult.heatmaps.avg_range_pips} />
                <HeatmapChart title="Avg Volume" table={seasonalityResult.heatmaps.avg_volume} digits={0} />
                <HeatmapChart title="Win Rate (%)" table={seasonalityResult.heatmaps.win_rate} percent />
                <HeatmapChart title="Avg Spread (Pips)" table={seasonalityResult.heatmaps.avg_spread_pips} />
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-md border p-3 text-sm">
                  <div className="font-medium">Range (Pips)</div>
                  <div className="flex items-center justify-between">
                    <span>Min</span>
                    <span className="font-mono">
                      {formatCell(seasonalityResult.extremes.range_pips.min.value, 1)} @ {seasonalityResult.extremes.range_pips.min.timestamp}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Max</span>
                    <span className="font-mono">
                      {formatCell(seasonalityResult.extremes.range_pips.max.value, 1)} @ {seasonalityResult.extremes.range_pips.max.timestamp}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Average</span>
                    <span className="font-mono">{formatCell(seasonalityResult.extremes.range_pips.avg, 1)}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>95% percentile</span>
                    <span className="font-mono">{formatCell(seasonalityResult.extremes.range_pips.p95, 1)}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>99% percentile</span>
                    <span className="font-mono">{formatCell(seasonalityResult.extremes.range_pips.p99, 1)}</span>
                  </div>
                </div>
                <div className="rounded-md border p-3 text-sm">
                  <div className="font-medium">C-O (Pips)</div>
                  <div className="flex items-center justify-between">
                    <span>Min</span>
                    <span className="font-mono">
                      {formatCell(seasonalityResult.extremes.co_pips.min.value, 1)} @ {seasonalityResult.extremes.co_pips.min.timestamp}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Max</span>
                    <span className="font-mono">
                      {formatCell(seasonalityResult.extremes.co_pips.max.value, 1)} @ {seasonalityResult.extremes.co_pips.max.timestamp}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Average</span>
                    <span className="font-mono">{formatCell(seasonalityResult.extremes.co_pips.avg, 1)}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>95% percentile</span>
                    <span className="font-mono">{formatCell(seasonalityResult.extremes.co_pips.p95, 1)}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>99% percentile</span>
                    <span className="font-mono">{formatCell(seasonalityResult.extremes.co_pips.p99, 1)}</span>
                  </div>
                </div>
                <div className="rounded-md border p-3 text-sm">
                  <div className="font-medium">Volume</div>
                  <div className="flex items-center justify-between">
                    <span>Min</span>
                    <span className="font-mono">
                      {formatCell(seasonalityResult.extremes.volume.min.value, 0)} @ {seasonalityResult.extremes.volume.min.timestamp}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Max</span>
                    <span className="font-mono">
                      {formatCell(seasonalityResult.extremes.volume.max.value, 0)} @ {seasonalityResult.extremes.volume.max.timestamp}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Average</span>
                    <span className="font-mono">{formatCell(seasonalityResult.extremes.volume.avg, 0)}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>95% percentile</span>
                    <span className="font-mono">{formatCell(seasonalityResult.extremes.volume.p95, 0)}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>99% percentile</span>
                    <span className="font-mono">{formatCell(seasonalityResult.extremes.volume.p99, 0)}</span>
                  </div>
                </div>
                <div className="rounded-md border p-3 text-sm">
                  <div className="font-medium">Spread (Pips)</div>
                  <div className="flex items-center justify-between">
                    <span>Min</span>
                    <span className="font-mono">
                      {formatCell(seasonalityResult.extremes.spread_pips.min.value, 1)} @ {seasonalityResult.extremes.spread_pips.min.timestamp}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Max</span>
                    <span className="font-mono">
                      {formatCell(seasonalityResult.extremes.spread_pips.max.value, 1)} @ {seasonalityResult.extremes.spread_pips.max.timestamp}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Average</span>
                    <span className="font-mono">{formatCell(seasonalityResult.extremes.spread_pips.avg, 1)}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>95% percentile</span>
                    <span className="font-mono">{formatCell(seasonalityResult.extremes.spread_pips.p95, 1)}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>99% percentile</span>
                    <span className="font-mono">{formatCell(seasonalityResult.extremes.spread_pips.p99, 1)}</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Calendar Seasonality</CardTitle>
              <CardDescription>Grouped by year, month, day-of-month, and DOW.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-2">
                <Label>Metric</Label>
                <Select
                  value={calendarMetric}
                  onValueChange={(val) =>
                    setCalendarMetric(
                      val as
                        | "count"
                        | "avg_range_points"
                        | "avg_co_points"
                        | "avg_spread_points"
                        | "avg_co_pct"
                    )
                  }
                >
                  <SelectTrigger className="w-56">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="avg_co_points">Avg C-O Points</SelectItem>
                    <SelectItem value="avg_range_points">Avg Range Points</SelectItem>
                    <SelectItem value="avg_spread_points">Avg Spread Points</SelectItem>
                    <SelectItem value="avg_co_pct">Avg C-O %</SelectItem>
                    <SelectItem value="count">Count</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                {(["year", "month", "day_of_month", "dow"] as const).map((key) => (
                  <div key={key} className="h-[220px] w-full rounded-md border p-3">
                    <div className="text-xs font-medium uppercase text-muted-foreground">
                      {key.replace("_", " ")}
                    </div>
                    <div className="h-[180px] w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={buildSeasonalityCalendarSeries(seasonalityResult, key, calendarMetric)}>
                          <CartesianGrid strokeDasharray="3 3" vertical={false} />
                          <XAxis dataKey="label" interval={0} angle={-20} textAnchor="end" height={50} />
                          <YAxis />
                          <Tooltip />
                          <Bar dataKey="value" fill="#38bdf8" />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Session Summary</CardTitle>
              <CardDescription>
                Quantifies movement, spread efficiency, and daily high/low ownership by session.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid gap-4 xl:grid-cols-2">
                <div className="h-[280px] rounded-md border p-3">
                  <div className="text-sm font-medium">Session Opportunity Chart</div>
                  <div className="mt-2 h-[220px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={sessionOpportunityRows}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                        <XAxis dataKey="session" />
                        <YAxis />
                        <Tooltip />
                        <Legend />
                        <Bar dataKey="opportunity" name="Opportunity Score" fill="#3b82f6" />
                        <Bar dataKey="avgRange" name="Avg Range (Pips)" fill="#10b981" />
                        <Bar dataKey="avgSpread" name="Avg Spread (Pips)" fill="#f97316" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
                <div className="h-[280px] rounded-md border p-3">
                  <div className="text-sm font-medium">Daily High/Low Formation Chart</div>
                  <div className="mt-2 h-[220px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={sessionHighLowRows}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                        <XAxis dataKey="session" />
                        <YAxis unit="%" />
                        <Tooltip formatter={(value: number | string) => `${Number(value).toFixed(1)}%`} />
                        <Legend />
                        <Bar dataKey="highRate" name="High Rate" fill="#8b5cf6" />
                        <Bar dataKey="lowRate" name="Low Rate" fill="#f43f5e" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
              <div className="overflow-x-auto rounded-md border">
                <table className="w-full border-collapse text-xs">
                  <thead>
                    <tr>
                      <th className="border px-2 py-1 text-left">Session</th>
                      <th className="border px-2 py-1 text-right">Bars</th>
                      <th className="border px-2 py-1 text-right">Avg Range (Pips)</th>
                      <th className="border px-2 py-1 text-right">Avg Spread (Pips)</th>
                      <th className="border px-2 py-1 text-right">Avg |C-O| (Pips)</th>
                      <th className="border px-2 py-1 text-right">Win Rate</th>
                      <th className="border px-2 py-1 text-right">Daily High Rate</th>
                      <th className="border px-2 py-1 text-right">Daily Low Rate</th>
                      <th className="border px-2 py-1 text-right">Opportunity Score</th>
                      <th className="border px-2 py-1 text-left">Label</th>
                    </tr>
                  </thead>
                  <tbody>
                    {seasonalityResult.session_summary.map((row) => (
                      <tr key={row.session}>
                        <td className="border px-2 py-1 capitalize">{row.session}</td>
                        <td className="border px-2 py-1 text-right">{row.bars}</td>
                        <td className="border px-2 py-1 text-right">{formatCell(row.avg_range_pips, 1)}</td>
                        <td className="border px-2 py-1 text-right">{formatCell(row.avg_spread_pips, 1)}</td>
                        <td className="border px-2 py-1 text-right">{formatCell(row.avg_abs_co_pips, 1)}</td>
                        <td className="border px-2 py-1 text-right">{formatPct(row.win_rate, 1)}</td>
                        <td className="border px-2 py-1 text-right">{formatPct(row.high_rate, 1)}</td>
                        <td className="border px-2 py-1 text-right">{formatPct(row.low_rate, 1)}</td>
                        <td className="border px-2 py-1 text-right font-mono">{formatCell(row.opportunity_score, 1)}</td>
                        <td className="border px-2 py-1 capitalize">{row.label}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-md border p-3 text-sm">
                  <div className="font-medium">Daily High/Low Formation</div>
                  <div className="mt-1 text-xs text-muted-foreground">
                    Based on {seasonalityResult.session_high_low.total_days} daily sessions.
                  </div>
                  <div className="mt-3 space-y-2">
                    {seasonalityResult.session_high_low.rows.map((row) => (
                      <div key={row.session} className="flex items-center justify-between">
                        <span className="capitalize">{row.session}</span>
                        <span className="font-mono">
                          High {formatPct(row.high_rate, 1)} / Low {formatPct(row.low_rate, 1)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="rounded-md border p-3 text-sm">
                  <div className="font-medium">Session Takeaway</div>
                  <div className="mt-3 space-y-2">
                    <div className="flex items-center justify-between">
                      <span>Best session</span>
                      <span className="font-mono capitalize">
                        {takeaway?.bestSession.label ?? "-"} ({formatCell(takeaway?.bestSession.score ?? null, 1)})
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Dead session</span>
                      <span className="font-mono capitalize">
                        {takeaway?.lowOpportunitySession.label ?? "-"} ({formatCell(takeaway?.lowOpportunitySession.score ?? null, 1)})
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Best hour</span>
                      <span className="font-mono">
                        {takeaway?.bestHour.label ?? "-"} ({formatCell(takeaway?.bestHour.score ?? null, 1)})
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Dead hour</span>
                      <span className="font-mono">
                        {takeaway?.lowOpportunityHour.label ?? "-"} ({formatCell(takeaway?.lowOpportunityHour.score ?? null, 1)})
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Opportunity Windows</CardTitle>
              <CardDescription>
                Ranked best and low-opportunity sessions/hours from movement, spread, and efficiency.
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2">
              <div className="h-[280px] rounded-md border p-3 md:col-span-2">
                <div className="text-sm font-medium">Opportunity Hours Chart</div>
                <div className="mt-1 text-xs text-muted-foreground">
                  Compares the strongest and weakest hours identified in this dataset.
                </div>
                <div className="mt-2 h-[210px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={opportunityHourRows}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="label" />
                      <YAxis domain={[0, 100]} />
                      <Tooltip formatter={(value: number | string) => `${Number(value).toFixed(1)} / 100`} />
                      <Legend />
                      <Bar dataKey="score" name="Opportunity Score" fill="#38bdf8" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
              <div className="rounded-md border p-3 text-sm">
                <div className="font-medium">Best Sessions</div>
                <div className="mt-1 text-xs text-muted-foreground">
                  Opportunity Score is a 0-100 composite. Higher means stronger movement with better spread efficiency.
                </div>
                <div className="mt-3 space-y-2">
                  {seasonalityResult.opportunity_windows.best_sessions.map((row) => (
                    <div key={`best-session-${row.session}`} className="flex items-center justify-between">
                      <span className="capitalize">{row.session}</span>
                      <span className="font-mono">{formatCell(row.opportunity_score, 1)} / 100</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="rounded-md border p-3 text-sm">
                <div className="font-medium">Low-Opportunity Sessions</div>
                <div className="mt-1 text-xs text-muted-foreground">
                  Lower scores mean weaker movement and/or worse spread burden relative to the move.
                </div>
                <div className="mt-3 space-y-2">
                  {seasonalityResult.opportunity_windows.dead_sessions.map((row) => (
                    <div key={`dead-session-${row.session}`} className="flex items-center justify-between">
                      <span className="capitalize">{row.session}</span>
                      <span className="font-mono">{formatCell(row.opportunity_score, 1)} / 100</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="rounded-md border p-3 text-sm">
                <div className="font-medium">Best Hours</div>
                <div className="mt-1 text-xs text-muted-foreground">
                  Read as relative opportunity quality inside this dataset, not an absolute edge guarantee.
                </div>
                <div className="mt-3 space-y-2">
                  {seasonalityResult.opportunity_windows.best_hours.map((row) => (
                    <div key={`best-hour-${row.hour}`} className="flex items-center justify-between">
                      <span>{row.hour}:00</span>
                      <span className="font-mono">{formatCell(row.opportunity_score, 1)} / 100</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="rounded-md border p-3 text-sm">
                <div className="font-medium">Low-Opportunity Hours</div>
                <div className="mt-1 text-xs text-muted-foreground">
                  Typically lower range, lower movement, or poorer spread efficiency than stronger windows.
                </div>
                <div className="mt-3 space-y-2">
                  {seasonalityResult.opportunity_windows.dead_hours.map((row) => (
                    <div key={`dead-hour-${row.hour}`} className="flex items-center justify-between">
                      <span>{row.hour}:00</span>
                      <span className="font-mono">{formatCell(row.opportunity_score, 1)} / 100</span>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Data Input</CardTitle>
              <CardDescription>Rows used to build the seasonality stats.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between pb-3">
                <div className="text-xs text-muted-foreground">Page size: {dataLimit} rows</div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      runSeasonality(0)
                    }}
                    disabled={dataOffset === 0 || loading}
                  >
                    Beginning
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      const next = Math.max(0, dataOffset - dataLimit)
                      runSeasonality(next)
                    }}
                    disabled={dataOffset === 0 || loading}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      const next = dataOffset + dataLimit
                      if (seasonalityResult.data_rows_count && next < seasonalityResult.data_rows_count) {
                        runSeasonality(next)
                      }
                    }}
                    disabled={
                      loading ||
                      !seasonalityResult.data_rows_count ||
                      dataOffset + dataLimit >= seasonalityResult.data_rows_count
                    }
                  >
                    Next
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      if (!seasonalityResult.data_rows_count) return
                      const lastOffset = Math.max(0, seasonalityResult.data_rows_count - dataLimit)
                      runSeasonality(lastOffset)
                    }}
                    disabled={
                      loading ||
                      !seasonalityResult.data_rows_count ||
                      dataOffset + dataLimit >= seasonalityResult.data_rows_count
                    }
                  >
                    End
                  </Button>
                </div>
              </div>
              {seasonalityResult.meta.digits === undefined || seasonalityResult.meta.digits === null ? (
                <div className="text-sm text-destructive">
                  Missing MT5 symbol digits for formatting.
                </div>
              ) : (
                <DataInputTable
                  rows={seasonalityResult.data_rows}
                  total={seasonalityResult.data_rows_count}
                  offset={seasonalityResult.data_rows_offset}
                  digits={seasonalityResult.meta.digits}
                />
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
