"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { edgeLabApi, type EdgeLabSeasonalityResponse } from "@/lib/api/edge"
import { useEdgeLabData } from "@/contexts/edge-lab-data-context"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

const DOW_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
const DOW_ORDER = [6, 0, 1, 2, 3, 4, 5]

const buildWeeklyBias = (result: EdgeLabSeasonalityResponse | null) => {
  if (!result) return []
  const rows: Array<{
    index: number
    hour: number
    day: number
    dayLabel: string
    value: number
  }> = []
  let cumulative = 0
  let idx = 0
  DOW_ORDER.forEach((dow) => {
    const values = result.intraday_bias.by_dow[String(dow)] ?? []
    let prev = 0
    values.forEach((value, hour) => {
      const delta = (value ?? 0) - prev
      cumulative += delta
      prev = value ?? prev
      rows.push({
        index: idx,
        hour,
        day: dow,
        dayLabel: DOW_LABELS[dow] ?? String(dow),
        value: cumulative,
      })
      idx += 1
    })
  })
  return rows
}

const buildCalendarSeries = (
  result: EdgeLabSeasonalityResponse,
  key: "year" | "month" | "day_of_month" | "dow",
  metric: "count" | "avg_range_points" | "avg_co_points" | "avg_spread_points" | "avg_co_pct"
) => {
  const source = result.calendar[key]
  return source.index.map((value, idx) => ({
    label: key === "dow" ? DOW_LABELS[value] ?? value : value,
    value: source[metric][idx] ?? null,
  }))
}

const formatCell = (value: number | null, digits = 2) => {
  if (value === null || Number.isNaN(value)) return "-"
  return value.toFixed(digits)
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

const HeatmapTable = ({
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
    if (value === null || Number.isNaN(value)) return "transparent"
    const norm = max === min ? 0.5 : (value - min) / (max - min)
    const alpha = 0.15 + norm * 0.75
    return `rgba(59, 130, 246, ${alpha})`
  }

  return (
    <div className="space-y-2">
      <div className="text-sm font-medium">{title}</div>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-xs">
          <thead>
            <tr>
              <th className="border px-2 py-1 text-left">Hour</th>
              {table.columns.map((col) => (
                <th key={col} className="border px-2 py-1">
                  {DOW_LABELS[col] ?? col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {table.index.map((hour, rowIdx) => (
              <tr key={hour}>
                <td className="border px-2 py-1 font-mono">{hour}</td>
                {table.values[rowIdx].map((value, colIdx) => (
                  <td
                    key={`${hour}-${colIdx}`}
                    className="border px-2 py-1 text-center text-slate-100"
                    style={{ backgroundColor: scale(value) }}
                  >
                    {percent ? `${Math.round((value ?? 0) * 100)}` : formatCell(value, digits)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default function SeasonalityPage() {
  const { dataset } = useEdgeLabData()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<EdgeLabSeasonalityResponse | null>(null)
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
      setResult(response)
      setDataOffset(effectiveOffset)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run seasonality.")
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  const intradayRows = buildWeeklyBias(result)

  return (
    <div className="flex flex-col gap-6 p-6">
      <Card>
        <CardHeader>
          <CardTitle>Run Seasonality</CardTitle>
          <CardDescription>Generate intraday bias, heatmaps, and calendar stats from the session dataset.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {!dataset ? (
            <div className="text-sm text-muted-foreground">Load a dataset in the Data tab before running Seasonality.</div>
          ) : (
            <div className="grid gap-4 md:grid-cols-4 text-sm">
              <div><div className="text-muted-foreground">Symbol</div><div>{dataset.request.symbol}</div></div>
              <div><div className="text-muted-foreground">Timeframe</div><div>{dataset.request.timeframe}</div></div>
              <div><div className="text-muted-foreground">Rows</div><div>{dataset.meta.n_rows}</div></div>
              <div><div className="text-muted-foreground">Warnings</div><div>{dataset.report.warnings.length}</div></div>
            </div>
          )}

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
        </CardContent>
      </Card>

      {result && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>Intraday Bias</CardTitle>
              <CardDescription>
                {result.meta.filtered_rows} of {result.meta.total_rows} bars in scope.
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
                    {DOW_ORDER.map((dow, idx) => (
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
              <HeatmapTable title="Avg Range (Pips)" table={result.heatmaps.avg_range_pips} />
              <HeatmapTable title="Avg Volume" table={result.heatmaps.avg_volume} digits={0} />
              <HeatmapTable title="Win Rate (%)" table={result.heatmaps.win_rate} percent />
              <HeatmapTable title="Avg Spread (Pips)" table={result.heatmaps.avg_spread_pips} />
              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-md border p-3 text-sm">
                  <div className="font-medium">Range (Pips)</div>
                  <div className="flex items-center justify-between">
                    <span>Min</span>
                    <span className="font-mono">
                      {formatCell(result.extremes.range_pips.min.value, 1)} @ {result.extremes.range_pips.min.timestamp}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Max</span>
                    <span className="font-mono">
                      {formatCell(result.extremes.range_pips.max.value, 1)} @ {result.extremes.range_pips.max.timestamp}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Average</span>
                    <span className="font-mono">{formatCell(result.extremes.range_pips.avg, 1)}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>95% percentile</span>
                    <span className="font-mono">{formatCell(result.extremes.range_pips.p95, 1)}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>99% percentile</span>
                    <span className="font-mono">{formatCell(result.extremes.range_pips.p99, 1)}</span>
                  </div>
                </div>
                <div className="rounded-md border p-3 text-sm">
                  <div className="font-medium">C-O (Pips)</div>
                  <div className="flex items-center justify-between">
                    <span>Min</span>
                    <span className="font-mono">
                      {formatCell(result.extremes.co_pips.min.value, 1)} @ {result.extremes.co_pips.min.timestamp}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Max</span>
                    <span className="font-mono">
                      {formatCell(result.extremes.co_pips.max.value, 1)} @ {result.extremes.co_pips.max.timestamp}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Average</span>
                    <span className="font-mono">{formatCell(result.extremes.co_pips.avg, 1)}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>95% percentile</span>
                    <span className="font-mono">{formatCell(result.extremes.co_pips.p95, 1)}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>99% percentile</span>
                    <span className="font-mono">{formatCell(result.extremes.co_pips.p99, 1)}</span>
                  </div>
                </div>
                <div className="rounded-md border p-3 text-sm">
                  <div className="font-medium">Volume</div>
                  <div className="flex items-center justify-between">
                    <span>Min</span>
                    <span className="font-mono">
                      {formatCell(result.extremes.volume.min.value, 0)} @ {result.extremes.volume.min.timestamp}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Max</span>
                    <span className="font-mono">
                      {formatCell(result.extremes.volume.max.value, 0)} @ {result.extremes.volume.max.timestamp}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Average</span>
                    <span className="font-mono">{formatCell(result.extremes.volume.avg, 0)}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>95% percentile</span>
                    <span className="font-mono">{formatCell(result.extremes.volume.p95, 0)}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>99% percentile</span>
                    <span className="font-mono">{formatCell(result.extremes.volume.p99, 0)}</span>
                  </div>
                </div>
                <div className="rounded-md border p-3 text-sm">
                  <div className="font-medium">Spread (Pips)</div>
                  <div className="flex items-center justify-between">
                    <span>Min</span>
                    <span className="font-mono">
                      {formatCell(result.extremes.spread_pips.min.value, 1)} @ {result.extremes.spread_pips.min.timestamp}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Max</span>
                    <span className="font-mono">
                      {formatCell(result.extremes.spread_pips.max.value, 1)} @ {result.extremes.spread_pips.max.timestamp}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Average</span>
                    <span className="font-mono">{formatCell(result.extremes.spread_pips.avg, 1)}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>95% percentile</span>
                    <span className="font-mono">{formatCell(result.extremes.spread_pips.p95, 1)}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>99% percentile</span>
                    <span className="font-mono">{formatCell(result.extremes.spread_pips.p99, 1)}</span>
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
                        <BarChart data={buildCalendarSeries(result, key, calendarMetric)}>
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
                      if (result.data_rows_count && next < result.data_rows_count) {
                        runSeasonality(next)
                      }
                    }}
                    disabled={
                      loading ||
                      !result.data_rows_count ||
                      dataOffset + dataLimit >= result.data_rows_count
                    }
                  >
                    Next
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      if (!result.data_rows_count) return
                      const lastOffset = Math.max(0, result.data_rows_count - dataLimit)
                      runSeasonality(lastOffset)
                    }}
                    disabled={
                      loading ||
                      !result.data_rows_count ||
                      dataOffset + dataLimit >= result.data_rows_count
                    }
                  >
                    End
                  </Button>
                </div>
              </div>
              {result.meta.digits === undefined || result.meta.digits === null ? (
                <div className="text-sm text-destructive">
                  Missing MT5 symbol digits for formatting.
                </div>
              ) : (
                <DataInputTable
                  rows={result.data_rows}
                  total={result.data_rows_count}
                  offset={result.data_rows_offset}
                  digits={result.meta.digits}
                />
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
