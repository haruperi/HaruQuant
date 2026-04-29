"use client"

import { useDeferredValue, useEffect, useRef, useState } from "react"
import {
  CandlestickSeries,
  ColorType,
  createChart,
  HistogramSeries,
  LineSeries,
  type IChartApi,
  type Time,
  type LogicalRange,
  type LineWidth,
} from "lightweight-charts"
import { ChevronDown, Plus, Settings2, Trash2 } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useEdgeLabData } from "@/contexts/edge-lab-data-context"
import type { EdgeLabPreparedDataset } from "@/lib/api/edge"
import { cn } from "@/lib/utils"
import { SymbolSelector } from "../dashboard/symbol-selector"

type IndicatorKind = "sma" | "bollinger" | "rsi" | "macd"
type IndicatorSource = "open" | "high" | "low" | "close"
type MovingAverageMode = "sma" | "ema"

interface IndicatorConfig {
  id: string
  kind: IndicatorKind
  label: string
  source: IndicatorSource
  length: number
  color: string
  lineWidth: number
  stdDev: number
  maMode: MovingAverageMode
  fastLength: number
  slowLength: number
  signalLength: number
}

interface CandleRow {
  time: Time
  timestamp: number
  open: number
  high: number
  low: number
  close: number
}

interface EdgeLabIndicatorChartProps {
  symbol: string
  timeframe: string
  rows: Array<Record<string, unknown>>
  schema: EdgeLabPreparedDataset["schema"]
  className?: string
}

const indicatorCatalog: Array<{ kind: IndicatorKind; label: string }> = [
  { kind: "sma", label: "Simple Moving Average" },
  { kind: "bollinger", label: "Bollinger Bands" },
  { kind: "rsi", label: "Relative Strength Index" },
  { kind: "macd", label: "Moving Average Convergence Divergence" },
]

function defaultIndicatorConfig(kind: IndicatorKind): IndicatorConfig {
  if (kind === "bollinger") {
    return {
      id: `${kind}-${crypto.randomUUID()}`,
      kind,
      label: "Bollinger Bands",
      source: "close",
      length: 20,
      color: "#60a5fa",
      lineWidth: 2,
      stdDev: 2,
      maMode: "sma",
      fastLength: 12,
      slowLength: 26,
      signalLength: 9,
    }
  }

  if (kind === "rsi") {
    return {
      id: `${kind}-${crypto.randomUUID()}`,
      kind,
      label: "Relative Strength Index",
      source: "close",
      length: 14,
      color: "#8b5cf6",
      lineWidth: 2,
      stdDev: 2,
      maMode: "sma",
      fastLength: 12,
      slowLength: 26,
      signalLength: 9,
    }
  }

  if (kind === "macd") {
    return {
      id: `${kind}-${crypto.randomUUID()}`,
      kind,
      label: "Moving Average Convergence Divergence",
      source: "close",
      length: 14,
      color: "#38bdf8",
      lineWidth: 2,
      stdDev: 2,
      maMode: "ema",
      fastLength: 12,
      slowLength: 26,
      signalLength: 9,
    }
  }

  return {
    id: `${kind}-${crypto.randomUUID()}`,
    kind,
    label: "Simple Moving Average",
    source: "close",
    length: 20,
    color: "#3b82f6",
    lineWidth: 2,
    stdDev: 2,
    maMode: "sma",
    fastLength: 12,
    slowLength: 26,
    signalLength: 9,
  }
}

function clampInteger(value: number, fallback: number, min = 1) {
  if (!Number.isFinite(value)) return fallback
  return Math.max(min, Math.round(value))
}

function inferDigits(rows: CandleRow[]) {
  let digits = 2
  for (const row of rows.slice(0, 80)) {
    for (const value of [row.open, row.high, row.low, row.close]) {
      const text = String(value)
      const decimals = text.includes(".") ? text.split(".")[1].length : 0
      digits = Math.max(digits, Math.min(decimals, 6))
    }
  }
  return digits
}

function parseTimestamp(row: Record<string, unknown>) {
  const directValue =
    row.time ??
    row.timestamp ??
    row.datetime ??
    row.date_time ??
    row.index

  if (typeof directValue === "number") {
    return directValue > 1e12 ? Math.floor(directValue / 1000) : directValue
  }

  if (typeof directValue === "string" && directValue.trim()) {
    const raw = directValue.trim()
    const normalized = /[zZ]|[+-]\d{2}:?\d{2}$/.test(raw) ? raw : `${raw}Z`
    const parsed = Date.parse(normalized)
    if (Number.isFinite(parsed)) {
      return Math.floor(parsed / 1000)
    }
  }

  if (typeof row.date === "string" && typeof row.time === "string") {
    const combined = `${row.date}T${row.time}`
    const parsed = Date.parse(`${combined}Z`)
    if (Number.isFinite(parsed)) {
      return Math.floor(parsed / 1000)
    }
  }

  if (typeof row.date === "string") {
    const parsed = Date.parse(`${row.date}T00:00:00Z`)
    if (Number.isFinite(parsed)) {
      return Math.floor(parsed / 1000)
    }
  }

  return null
}

function buildCandles(
  rows: Array<Record<string, unknown>>,
  schema: EdgeLabPreparedDataset["schema"]
) {
  const candles: CandleRow[] = []

  for (const row of rows) {
    const timestamp = parseTimestamp(row)
    const open = Number(row[schema.open])
    const high = Number(row[schema.high])
    const low = Number(row[schema.low])
    const close = Number(row[schema.close])

    if (
      timestamp === null ||
      !Number.isFinite(open) ||
      !Number.isFinite(high) ||
      !Number.isFinite(low) ||
      !Number.isFinite(close)
    ) {
      continue
    }

    candles.push({
      time: timestamp as Time,
      timestamp,
      open,
      high,
      low,
      close,
    })
  }

  candles.sort((left, right) => left.timestamp - right.timestamp)
  return candles
}

function sourceValue(candle: CandleRow, source: IndicatorSource) {
  return candle[source]
}

function calculateSma(candles: CandleRow[], source: IndicatorSource, length: number) {
  const values: Array<{ time: Time; value: number }> = []
  let sum = 0

  for (let index = 0; index < candles.length; index += 1) {
    sum += sourceValue(candles[index], source)
    if (index >= length) {
      sum -= sourceValue(candles[index - length], source)
    }
    if (index >= length - 1) {
      values.push({
        time: candles[index].time,
        value: sum / length,
      })
    }
  }

  return values
}

function calculateEma(candles: CandleRow[], source: IndicatorSource, length: number) {
  const values: Array<{ time: Time; value: number }> = []
  const multiplier = 2 / (length + 1)
  let ema = 0
  let seed = 0

  for (let index = 0; index < candles.length; index += 1) {
    const value = sourceValue(candles[index], source)

    if (index < length) {
      seed += value
      if (index === length - 1) {
        ema = seed / length
        values.push({ time: candles[index].time, value: ema })
      }
      continue
    }

    ema = value * multiplier + ema * (1 - multiplier)
    values.push({ time: candles[index].time, value: ema })
  }

  return values
}

function calculateBollinger(
  candles: CandleRow[],
  source: IndicatorSource,
  length: number,
  stdDev: number,
  mode: MovingAverageMode
) {
  const middle =
    mode === "ema"
      ? calculateEma(candles, source, length)
      : calculateSma(candles, source, length)

  const upper: Array<{ time: Time; value: number }> = []
  const lower: Array<{ time: Time; value: number }> = []

  for (let index = length - 1; index < candles.length; index += 1) {
    const slice = candles.slice(index - length + 1, index + 1)
    const values = slice.map((candle) => sourceValue(candle, source))
    const average = middle[index - length + 1]?.value
    if (average === undefined) {
      continue
    }

    const variance =
      values.reduce((sum, value) => sum + (value - average) ** 2, 0) / length
    const deviation = Math.sqrt(variance) * stdDev

    upper.push({ time: candles[index].time, value: average + deviation })
    lower.push({ time: candles[index].time, value: average - deviation })
  }

  return { middle, upper, lower }
}

function calculateRsi(candles: CandleRow[], source: IndicatorSource, length: number) {
  const values: Array<{ time: Time; value: number }> = []
  if (candles.length <= length) return values

  let gains = 0
  let losses = 0

  for (let index = 1; index <= length; index += 1) {
    const delta = sourceValue(candles[index], source) - sourceValue(candles[index - 1], source)
    gains += Math.max(delta, 0)
    losses += Math.max(-delta, 0)
  }

  let averageGain = gains / length
  let averageLoss = losses / length

  const firstRs = averageLoss === 0 ? 100 : averageGain / averageLoss
  values.push({
    time: candles[length].time,
    value: averageLoss === 0 ? 100 : 100 - 100 / (1 + firstRs),
  })

  for (let index = length + 1; index < candles.length; index += 1) {
    const delta = sourceValue(candles[index], source) - sourceValue(candles[index - 1], source)
    const gain = Math.max(delta, 0)
    const loss = Math.max(-delta, 0)

    averageGain = (averageGain * (length - 1) + gain) / length
    averageLoss = (averageLoss * (length - 1) + loss) / length

    if (averageLoss === 0) {
      values.push({ time: candles[index].time, value: 100 })
      continue
    }

    const rs = averageGain / averageLoss
    values.push({
      time: candles[index].time,
      value: 100 - 100 / (1 + rs),
    })
  }

  return values
}

function emaFromPoints(points: number[], length: number) {
  const multiplier = 2 / (length + 1)
  const result: Array<number | null> = Array(points.length).fill(null)
  if (points.length < length) return result

  let seed = 0
  for (let index = 0; index < length; index += 1) {
    seed += points[index]
  }

  let ema = seed / length
  result[length - 1] = ema

  for (let index = length; index < points.length; index += 1) {
    ema = points[index] * multiplier + ema * (1 - multiplier)
    result[index] = ema
  }

  return result
}

function calculateMacd(
  candles: CandleRow[],
  source: IndicatorSource,
  fastLength: number,
  slowLength: number,
  signalLength: number
) {
  const sourceSeries = candles.map((candle) => sourceValue(candle, source))
  const fast = emaFromPoints(sourceSeries, fastLength)
  const slow = emaFromPoints(sourceSeries, slowLength)
  const macdLineValues = sourceSeries.map((_, index) => {
    if (fast[index] === null || slow[index] === null) return null
    return (fast[index] as number) - (slow[index] as number)
  })

  const signalInput = macdLineValues.filter((value): value is number => value !== null)
  const signalSeed = emaFromPoints(signalInput, signalLength)
  const signalLineValues: Array<number | null> = Array(macdLineValues.length).fill(null)

  let signalIndex = 0
  for (let index = 0; index < macdLineValues.length; index += 1) {
    if (macdLineValues[index] === null) {
      continue
    }
    signalLineValues[index] = signalSeed[signalIndex]
    signalIndex += 1
  }

  const macd: Array<{ time: Time; value: number }> = []
  const signal: Array<{ time: Time; value: number }> = []
  const histogram: Array<{ time: Time; value: number; color: string }> = []

  for (let index = 0; index < candles.length; index += 1) {
    const macdValue = macdLineValues[index]
    const signalValue = signalLineValues[index]

    if (macdValue !== null) {
      macd.push({ time: candles[index].time, value: macdValue })
    }
    if (signalValue !== null) {
      signal.push({ time: candles[index].time, value: signalValue })
      histogram.push({
        time: candles[index].time,
        value: macdValue === null ? 0 : macdValue - signalValue,
        color: macdValue !== null && macdValue - signalValue >= 0 ? "#14b8a6" : "#f43f5e",
      })
    }
  }

  return { macd, signal, histogram }
}

function indicatorSummary(config: IndicatorConfig) {
  if (config.kind === "bollinger") {
    return `${config.length} / ${config.stdDev} std`
  }
  if (config.kind === "rsi") {
    return `${config.length}`
  }
  if (config.kind === "macd") {
    return `${config.fastLength}-${config.slowLength}-${config.signalLength}`
  }
  return `${config.length}`
}

function editingTitle(config: IndicatorConfig | null) {
  if (!config) return ""
  return `${config.label} Settings`
}

export function EdgeLabIndicatorChart({
  symbol,
  timeframe,
  rows,
  schema,
  className,
}: EdgeLabIndicatorChartProps) {
  const deferredRows = useDeferredValue(rows)
  const pricePaneRef = useRef<HTMLDivElement>(null)
  const paneRefs = useRef<Record<string, HTMLDivElement | null>>({})
  const { dataset: fullDataset, loadDataset } = useEdgeLabData()
  const [indicators, setIndicators] = useState<IndicatorConfig[]>([
    defaultIndicatorConfig("macd"),
  ])
  const [editingId, setEditingId] = useState<string | null>(null)
  const [selectorOpen, setSelectorOpen] = useState(false)

  const candles = buildCandles(deferredRows, schema)
  const digits = inferDigits(candles)
  const activeOverlays = indicators.filter((indicator) => indicator.kind === "sma" || indicator.kind === "bollinger")
  const activePanes = indicators.filter((indicator) => indicator.kind === "rsi" || indicator.kind === "macd")
  const editingIndicator = indicators.find((indicator) => indicator.id === editingId) ?? null

  useEffect(() => {
    if (!pricePaneRef.current || candles.length === 0) {
      return
    }

    const mainChart = createChart(pricePaneRef.current, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#cbd5e1",
      },
      grid: {
        vertLines: { color: "rgba(148, 163, 184, 0.10)" },
        horzLines: { color: "rgba(148, 163, 184, 0.10)" },
      },
      timeScale: {
        borderColor: "rgba(148, 163, 184, 0.16)",
        rightOffset: 12,
        timeVisible: true,
        secondsVisible: false,
      },
      rightPriceScale: {
        borderColor: "rgba(148, 163, 184, 0.16)",
      },
      crosshair: {
        vertLine: { color: "rgba(226, 232, 240, 0.35)", width: 1, style: 2 },
        horzLine: { color: "rgba(226, 232, 240, 0.24)", width: 1, style: 2 },
      },
    })

    const candleSeries = mainChart.addSeries(CandlestickSeries, {
      upColor: "#14b8a6",
      downColor: "#f87171",
      borderVisible: false,
      wickUpColor: "#14b8a6",
      wickDownColor: "#f87171",
      priceFormat: {
        type: "price",
        precision: digits,
        minMove: 1 / 10 ** digits,
      },
    })

    candleSeries.setData(candles)

    const childCharts: IChartApi[] = []
    const cleanupTasks: Array<() => void> = []

    for (const overlay of activeOverlays) {
      if (overlay.kind === "sma") {
        const series = mainChart.addSeries(LineSeries, {
          color: overlay.color,
          lineWidth: overlay.lineWidth as LineWidth,
          priceLineVisible: false,
          lastValueVisible: false,
        })
        series.setData(calculateSma(candles, overlay.source, overlay.length))
      }

      if (overlay.kind === "bollinger") {
        const result = calculateBollinger(
          candles,
          overlay.source,
          overlay.length,
          overlay.stdDev,
          overlay.maMode
        )

        const upperSeries = mainChart.addSeries(LineSeries, {
          color: "#f43f5e",
          lineWidth: 2,
          priceLineVisible: false,
          lastValueVisible: false,
        })
        const middleSeries = mainChart.addSeries(LineSeries, {
          color: "#3b82f6",
          lineWidth: 2,
          priceLineVisible: false,
          lastValueVisible: false,
        })
        const lowerSeries = mainChart.addSeries(LineSeries, {
          color: "#14b8a6",
          lineWidth: 2,
          priceLineVisible: false,
          lastValueVisible: false,
        })

        upperSeries.setData(result.upper)
        middleSeries.setData(result.middle)
        lowerSeries.setData(result.lower)
      }
    }

    for (const paneIndicator of activePanes) {
      const paneElement = paneRefs.current[paneIndicator.id]
      if (!paneElement) {
        continue
      }

      const paneChart = createChart(paneElement, {
        autoSize: true,
        layout: {
          background: { type: ColorType.Solid, color: "transparent" },
          textColor: "#94a3b8",
        },
        grid: {
          vertLines: { color: "rgba(148, 163, 184, 0.08)" },
          horzLines: { color: "rgba(148, 163, 184, 0.08)" },
        },
        timeScale: {
          borderColor: "rgba(148, 163, 184, 0.16)",
          timeVisible: true,
          secondsVisible: false,
        },
        rightPriceScale: {
          borderColor: "rgba(148, 163, 184, 0.16)",
          scaleMargins: { top: 0.18, bottom: 0.12 },
        },
        crosshair: {
          vertLine: { color: "rgba(226, 232, 240, 0.25)", width: 1, style: 2 },
          horzLine: { color: "rgba(226, 232, 240, 0.18)", width: 1, style: 2 },
        },
      })

      if (paneIndicator.kind === "rsi") {
        const rsiSeries = paneChart.addSeries(LineSeries, {
          color: paneIndicator.color,
          lineWidth: paneIndicator.lineWidth as LineWidth,
          priceLineVisible: false,
        })
        rsiSeries.setData(calculateRsi(candles, paneIndicator.source, paneIndicator.length))
        rsiSeries.createPriceLine({
          price: 70,
          color: "rgba(248, 113, 113, 0.55)",
          lineWidth: 1,
          lineStyle: 2,
          axisLabelVisible: true,
          title: "70",
        })
        rsiSeries.createPriceLine({
          price: 30,
          color: "rgba(45, 212, 191, 0.55)",
          lineWidth: 1,
          lineStyle: 2,
          axisLabelVisible: true,
          title: "30",
        })
      }

      if (paneIndicator.kind === "macd") {
        const histogramSeries = paneChart.addSeries(HistogramSeries, {
          priceLineVisible: false,
          base: 0,
        })
        const macdSeries = paneChart.addSeries(LineSeries, {
          color: "#2563eb",
          lineWidth: 2,
          priceLineVisible: false,
        })
        const signalSeries = paneChart.addSeries(LineSeries, {
          color: "#f43f5e",
          lineWidth: 2,
          priceLineVisible: false,
        })

        const result = calculateMacd(
          candles,
          paneIndicator.source,
          paneIndicator.fastLength,
          paneIndicator.slowLength,
          paneIndicator.signalLength
        )

        histogramSeries.setData(result.histogram)
        macdSeries.setData(result.macd)
        signalSeries.setData(result.signal)
      }

      childCharts.push(paneChart)
    }

    const charts = [mainChart, ...childCharts]
    let syncing = false

    for (const chart of charts) {
      const syncHandler = (range: LogicalRange | null) => {
        if (syncing || range === null) {
          return
        }
        syncing = true
        for (const peer of charts) {
          if (peer !== chart) {
            peer.timeScale().setVisibleLogicalRange(range)
          }
        }
        syncing = false
      }

      chart.timeScale().subscribeVisibleLogicalRangeChange(syncHandler)
      cleanupTasks.push(() => chart.timeScale().unsubscribeVisibleLogicalRangeChange(syncHandler))
    }

    mainChart.timeScale().fitContent()

    return () => {
      for (const cleanup of cleanupTasks) {
        cleanup()
      }
      for (const chart of charts) {
        chart.remove()
      }
    }
  }, [activeOverlays, activePanes, candles, digits])

  const addIndicator = (kind: IndicatorKind) => {
    setIndicators((current) => [...current, defaultIndicatorConfig(kind)])
  }

  const removeIndicator = (id: string) => {
    setIndicators((current) => current.filter((indicator) => indicator.id !== id))
    if (editingId === id) {
      setEditingId(null)
    }
  }

  const updateIndicator = (id: string, patch: Partial<IndicatorConfig>) => {
    setIndicators((current) =>
      current.map((indicator) =>
        indicator.id === id
          ? {
              ...indicator,
              ...patch,
            }
          : indicator
      )
    )
  }

  const handleSymbolSelect = (newSymbol: string) => {
    if (fullDataset) {
      void loadDataset({
        symbol: newSymbol,
        timeframe: fullDataset.request.timeframe,
        data_source: fullDataset.request.data_source,
        range_by: fullDataset.request.range_by,
        start_date: fullDataset.request.start_date ?? undefined,
        end_date: fullDataset.request.end_date ?? undefined,
        number_of_bars: fullDataset.request.number_of_bars ?? undefined,
        session_basis: fullDataset.request.session_basis ?? undefined,
        session_hours: fullDataset.request.session_hours ?? undefined,
      })
    }
  }

  if (candles.length === 0) {
    return (
      <div className="rounded-xl border border-border/60 bg-muted/10 p-6 text-sm text-muted-foreground">
        The prepared dataset does not include usable OHLC rows for chart rendering.
      </div>
    )
  }

  const latest = candles[candles.length - 1]
  const previous = candles[candles.length - 2]
  const change = previous ? latest.close - previous.close : 0
  const changePct = previous && previous.close !== 0 ? (change / previous.close) * 100 : 0
  const indicatorOverlayHeight =
    activePanes.length === 0 ? "h-0" : activePanes.length === 1 ? "h-[28%]" : "h-[42%]"

  return (
    <div
      className={cn(
        "relative h-full min-h-0 overflow-hidden rounded-2xl border border-slate-800/80 bg-[#070b14] text-slate-100 shadow-[0_24px_80px_rgba(0,0,0,0.35)]",
        className
      )}
    >
      <div className="absolute inset-0">
        <div ref={pricePaneRef} className="h-full w-full" />
      </div>

      <div className="pointer-events-none absolute inset-x-4 top-4 z-20 flex items-start justify-between gap-4">
        <div className="pointer-events-auto max-w-[72%] space-y-3">
          <button
            type="button"
            onClick={() => setSelectorOpen(true)}
            className="group w-fit rounded-xl border border-slate-700/80 bg-[rgba(7,11,20,0.5)] px-4 py-3 text-left backdrop-blur-sm transition-all hover:border-slate-600 hover:bg-[rgba(15,23,42,0.6)]"
          >
            <div className="flex flex-wrap items-center gap-2">
              <Badge className="border-slate-600 bg-[rgba(15,23,42,0.5)] text-slate-100 group-hover:border-indigo-500/50 group-hover:text-indigo-400">
                {symbol}
              </Badge>
              <Badge className="border-slate-600 bg-[rgba(15,23,42,0.5)] text-slate-100">
                {timeframe}
              </Badge>
              <span
                className={cn(
                  "text-sm font-medium",
                  change >= 0 ? "text-emerald-400" : "text-rose-400"
                )}
              >
                {change >= 0 ? "+" : ""}
                {change.toFixed(digits)} ({changePct.toFixed(2)}%)
              </span>
            </div>
            <div className="mt-1 text-xs text-slate-300">
              O: {latest.open.toFixed(digits)} | H: {latest.high.toFixed(digits)} | L:{" "}
              {latest.low.toFixed(digits)} | C: {latest.close.toFixed(digits)}
            </div>
          </button>

          {indicators.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {indicators.map((indicator) => (
                <div
                  key={indicator.id}
                  className="pointer-events-auto flex items-center gap-2 rounded-full border border-slate-700/80 bg-[rgba(7,11,20,0.5)] px-3 py-1 text-xs text-slate-100 backdrop-blur-sm"
                >
                  <span>{indicator.label}</span>
                  <span className="rounded-full bg-[rgba(15,23,42,0.5)] px-2 py-0.5 text-[11px] text-slate-300">
                    {indicatorSummary(indicator)}
                  </span>
                  <button
                    type="button"
                    className="text-slate-300 transition hover:text-slate-100"
                    onClick={() => setEditingId(indicator.id)}
                  >
                    <Settings2 className="h-3.5 w-3.5" />
                  </button>
                  <button
                    type="button"
                    className="text-slate-300 transition hover:text-rose-300"
                    onClick={() => removeIndicator(indicator.id)}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="outline"
              className="pointer-events-auto border-slate-700/80 bg-[rgba(7,11,20,0.5)] text-slate-100 backdrop-blur-sm hover:bg-[rgba(15,23,42,0.5)]"
            >
              <Plus className="mr-2 h-4 w-4" />
              Indicator
              <ChevronDown className="ml-2 h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-80 border-slate-700 bg-slate-950/95 text-slate-100 backdrop-blur-sm">
            <DropdownMenuLabel>Add Indicator</DropdownMenuLabel>
            <DropdownMenuSeparator />
            {indicatorCatalog.map((entry) => (
              <DropdownMenuItem
                key={entry.kind}
                className="cursor-pointer focus:bg-slate-900 focus:text-slate-50"
                onClick={() => addIndicator(entry.kind)}
              >
                {entry.label}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {activePanes.length > 0 && (
        <div className={cn("pointer-events-none absolute inset-x-4 bottom-4 z-20", indicatorOverlayHeight)}>
          <div className="flex h-full min-h-0 flex-col gap-3">
            {activePanes.map((indicator) => (
              <div
                key={indicator.id}
                className="pointer-events-auto flex min-h-0 flex-1 flex-col rounded-xl border border-slate-700/80 bg-[rgba(7,11,20,0.5)] p-2 backdrop-blur-sm"
              >
                <div className="mb-2 flex items-center justify-between px-1 text-xs text-slate-300">
                  <span>{indicator.label}</span>
                  <span>{indicatorSummary(indicator)}</span>
                </div>
                <div
                  className="min-h-0 flex-1"
                  ref={(node) => {
                    paneRefs.current[indicator.id] = node
                  }}
                />
              </div>
            ))}
          </div>
        </div>
      )}

      <Dialog open={editingIndicator !== null} onOpenChange={(open) => !open && setEditingId(null)}>
        <DialogContent className="border-slate-800 bg-slate-950 text-slate-100 sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>{editingTitle(editingIndicator)}</DialogTitle>
            <DialogDescription className="text-slate-400">
              Tune the indicator parameters without leaving the dataset view.
            </DialogDescription>
          </DialogHeader>

          {editingIndicator && (
            <div className="grid gap-4 md:grid-cols-2">
              {(editingIndicator.kind === "sma" ||
                editingIndicator.kind === "bollinger" ||
                editingIndicator.kind === "rsi") && (
                <div className="space-y-2">
                  <Label>Length</Label>
                  <Input
                    type="number"
                    value={editingIndicator.length}
                    onChange={(event) =>
                      updateIndicator(editingIndicator.id, {
                        length: clampInteger(Number(event.target.value), editingIndicator.length),
                      })
                    }
                  />
                </div>
              )}

              <div className="space-y-2">
                <Label>Source</Label>
                <Select
                  value={editingIndicator.source}
                  onValueChange={(value) =>
                    updateIndicator(editingIndicator.id, {
                      source: value as IndicatorSource,
                    })
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="open">Open</SelectItem>
                    <SelectItem value="high">High</SelectItem>
                    <SelectItem value="low">Low</SelectItem>
                    <SelectItem value="close">Close</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {editingIndicator.kind === "bollinger" && (
                <>
                  <div className="space-y-2">
                    <Label>Moving Average Mode</Label>
                    <Select
                      value={editingIndicator.maMode}
                      onValueChange={(value) =>
                        updateIndicator(editingIndicator.id, {
                          maMode: value as MovingAverageMode,
                        })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="sma">SMA</SelectItem>
                        <SelectItem value="ema">EMA</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Standard Deviations</Label>
                    <Input
                      type="number"
                      step="0.1"
                      value={editingIndicator.stdDev}
                      onChange={(event) =>
                        updateIndicator(editingIndicator.id, {
                          stdDev: Math.max(0.1, Number(event.target.value) || editingIndicator.stdDev),
                        })
                      }
                    />
                  </div>
                </>
              )}

              {editingIndicator.kind === "macd" && (
                <>
                  <div className="space-y-2">
                    <Label>Fast Length</Label>
                    <Input
                      type="number"
                      value={editingIndicator.fastLength}
                      onChange={(event) =>
                        updateIndicator(editingIndicator.id, {
                          fastLength: clampInteger(Number(event.target.value), editingIndicator.fastLength),
                        })
                      }
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Slow Length</Label>
                    <Input
                      type="number"
                      value={editingIndicator.slowLength}
                      onChange={(event) =>
                        updateIndicator(editingIndicator.id, {
                          slowLength: clampInteger(Number(event.target.value), editingIndicator.slowLength),
                        })
                      }
                    />
                  </div>
                  <div className="space-y-2 md:col-span-2">
                    <Label>Signal Length</Label>
                    <Input
                      type="number"
                      value={editingIndicator.signalLength}
                      onChange={(event) =>
                        updateIndicator(editingIndicator.id, {
                          signalLength: clampInteger(Number(event.target.value), editingIndicator.signalLength),
                        })
                      }
                    />
                  </div>
                </>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
      <SymbolSelector
        open={selectorOpen}
        onOpenChange={setSelectorOpen}
        onSelect={handleSymbolSelect}
        currentSymbol={symbol}
      />
    </div>
  )
}
