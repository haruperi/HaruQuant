"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import {
  CandlestickSeries,
  ColorType,
  IChartApi,
  ISeriesApi,
  LineSeries,
  Time,
  createChart,
} from "lightweight-charts"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import simulatorApi from "@/lib/api/simulator"

type IndicatorKey = "sma" | "ema" | "rsi"

// Bar data for the chart
export interface ChartBarData {
  time: string
  open: number
  high: number
  low: number
  close: number
}

// Indicator data for the chart
export interface ChartIndicatorData {
  time?: string
  sma?: number
  ema?: number
  rsi?: number
}

interface SimulationChartProps {
  sessionId?: number
  symbol?: string
  timeframe?: string
  height?: number
  bars: ChartBarData[]
  indicators?: ChartIndicatorData[]
  digits?: number
  onChartClick?: (payload: { time: string; price: number }) => void
}

interface TradeMarker {
  id: number
  time: Time
  price: number
  side: "buy" | "sell"
}

const indicatorColors: Record<IndicatorKey, string> = {
  sma: "#3b82f6",
  ema: "#f97316",
  rsi: "#8b5cf6",
}

const parseDate = (value: unknown): Date | null => {
  if (value === null || value === undefined) return null
  if (typeof value === "number") {
    const ms = value > 1e12 ? value : value * 1000
    return new Date(ms)
  }
  if (typeof value === "string") {
    const raw = value.trim()
    const normalized = /[zZ]|[+-]\d{2}:?\d{2}$/.test(raw) ? raw : `${raw}Z`
    const date = new Date(normalized)
    if (!Number.isNaN(date.getTime())) {
      return date
    }
  }
  return null
}

const toIsoString = (time: number) => new Date(time * 1000).toISOString()

const isDailyOrHigher = (timeframe?: string) => {
  if (!timeframe) return false
  const tf = timeframe.toUpperCase()
  return tf === "D1" || tf === "W1" || tf === "MN1"
}

const resolveChartTime = (value: unknown, timeframe?: string): Time | null => {
  const date = parseDate(value)
  if (!date) return null

  if (isDailyOrHigher(timeframe)) {
    const y = date.getUTCFullYear()
    const m = String(date.getUTCMonth() + 1).padStart(2, "0")
    const d = String(date.getUTCDate()).padStart(2, "0")
    return `${y}-${m}-${d}` as Time
  }

  return Math.floor(date.getTime() / 1000) as Time
}

export function SimulationChart({
  sessionId,
  symbol = "EURUSD",
  timeframe,
  height = 520,
  bars,
  indicators = [],
  digits = 5,
  onChartClick,
}: SimulationChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null)
  const smaSeriesRef = useRef<ISeriesApi<"Line"> | null>(null)
  const emaSeriesRef = useRef<ISeriesApi<"Line"> | null>(null)
  const rsiSeriesRef = useRef<ISeriesApi<"Line"> | null>(null)
  const markersRef = useRef<TradeMarker[]>([])
  const digitsRef = useRef<number>(digits)

  const [indicatorVisibility, setIndicatorVisibility] = useState({
    sma: false,
    ema: false,
    rsi: false,
  })
  const [markerPositions, setMarkerPositions] = useState<
    { id: number; x: number; y: number; side: "buy" | "sell" }[]
  >([])

  const updateMarkerPositions = useCallback(() => {
    if (!chartRef.current || !candleSeriesRef.current) return

    const positions = markersRef.current
      .map((marker) => {
        const x = chartRef.current!.timeScale().timeToCoordinate(marker.time)
        const y = candleSeriesRef.current!.priceToCoordinate(marker.price)
        if (x === null || y === null) return null
        return { id: marker.id, x, y, side: marker.side }
      })
      .filter(Boolean) as { id: number; x: number; y: number; side: "buy" | "sell" }[]

    setMarkerPositions(positions)
  }, [])

  // Create chart on mount
  useEffect(() => {
    if (!chartContainerRef.current) return

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#9ca3af",
      },
      width: chartContainerRef.current.clientWidth,
      height,
      grid: {
        vertLines: { color: "rgba(255, 255, 255, 0.05)" },
        horzLines: { color: "rgba(255, 255, 255, 0.05)" },
      },
      rightPriceScale: {
        borderColor: "rgba(255, 255, 255, 0.1)",
      },
      timeScale: {
        borderColor: "rgba(255, 255, 255, 0.1)",
        timeVisible: !isDailyOrHigher(timeframe),
        secondsVisible: false,
        rightOffset: 5,
      },
    })

    const candles = chart.addSeries(CandlestickSeries, {
      upColor: "#10b981",
      downColor: "#ef4444",
      borderVisible: false,
      wickUpColor: "#10b981",
      wickDownColor: "#ef4444",
      priceFormat: {
        type: "price",
        precision: digits,
        minMove: 1 / Math.pow(10, digits),
      },
    })

    const smaSeries = chart.addSeries(LineSeries, {
      color: indicatorColors.sma,
      lineWidth: 1,
      visible: false,
    })
    const emaSeries = chart.addSeries(LineSeries, {
      color: indicatorColors.ema,
      lineWidth: 1,
      visible: false,
    })
    const rsiSeries = chart.addSeries(LineSeries, {
      color: indicatorColors.rsi,
      lineWidth: 1,
      priceScaleId: "rsi",
      visible: false,
    })
    chart.priceScale("rsi").applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    })

    chartRef.current = chart
    candleSeriesRef.current = candles
    smaSeriesRef.current = smaSeries
    emaSeriesRef.current = emaSeries
    rsiSeriesRef.current = rsiSeries

    const resizeObserver = new ResizeObserver((entries) => {
      if (!entries.length || !chartContainerRef.current) return
      const rect = entries[0].contentRect
      chart.applyOptions({ width: rect.width, height: rect.height })
      updateMarkerPositions()
    })
    resizeObserver.observe(chartContainerRef.current)

    if (onChartClick) {
      chart.subscribeClick((param) => {
        if (!param.time || !param.point || !candleSeriesRef.current) return
        const price = candleSeriesRef.current.coordinateToPrice(param.point.y)
        if (price === null) return

        let timeString = ""
        if (typeof param.time === "string") {
          timeString = param.time
        } else if (typeof param.time === "number") {
          timeString = toIsoString(param.time)
        } else {
          const t = param.time as { year: number; month: number; day: number }
          timeString = `${t.year}-${String(t.month).padStart(2, "0")}-${String(t.day).padStart(2, "0")}`
        }

        if (!timeString) return
        onChartClick({ time: timeString, price })
      })
    }

    chart.timeScale().subscribeVisibleTimeRangeChange(updateMarkerPositions)

    return () => {
      resizeObserver.disconnect()
      chart.remove()
      chartRef.current = null
      candleSeriesRef.current = null
      smaSeriesRef.current = null
      emaSeriesRef.current = null
      rsiSeriesRef.current = null
    }
  }, [height, onChartClick, timeframe, updateMarkerPositions, digits])

  // Update bars when they change
  useEffect(() => {
    if (!candleSeriesRef.current || !bars.length) return

    // Update digits if changed
    if (digitsRef.current !== digits) {
      digitsRef.current = digits
      candleSeriesRef.current.applyOptions({
        priceFormat: {
          type: "price",
          precision: digits,
          minMove: 1 / Math.pow(10, digits),
        },
      })
    }

    // Convert bars to chart format and sort
    const chartBars = bars
      .map((bar) => {
        const timeValue = resolveChartTime(bar.time, timeframe)
        if (!timeValue) return null
        return {
          time: timeValue,
          open: Number(bar.open),
          high: Number(bar.high),
          low: Number(bar.low),
          close: Number(bar.close),
        }
      })
      .filter(Boolean) as { time: Time; open: number; high: number; low: number; close: number }[]

    // Sort by time
    chartBars.sort((a, b) => {
      if (typeof a.time === "string" && typeof b.time === "string") {
        return a.time.localeCompare(b.time)
      }
      return (a.time as number) - (b.time as number)
    })

    // Set all data at once
    candleSeriesRef.current.setData(chartBars)

    // Fit content on first load
    if (chartRef.current && chartBars.length <= 10) {
      chartRef.current.timeScale().fitContent()
    }
  }, [bars, timeframe, digits])

  // Update indicators
  useEffect(() => {
    if (!indicators.length) return

    const smaData: { time: Time; value: number }[] = []
    const emaData: { time: Time; value: number }[] = []
    const rsiData: { time: Time; value: number }[] = []

    for (const ind of indicators) {
      const timeValue = resolveChartTime(ind.time, timeframe)
      if (!timeValue) continue

      if (typeof ind.sma === "number") {
        smaData.push({ time: timeValue, value: ind.sma })
      }
      if (typeof ind.ema === "number") {
        emaData.push({ time: timeValue, value: ind.ema })
      }
      if (typeof ind.rsi === "number") {
        rsiData.push({ time: timeValue, value: ind.rsi })
      }
    }

    if (smaSeriesRef.current && smaData.length) {
      smaSeriesRef.current.setData(smaData)
    }
    if (emaSeriesRef.current && emaData.length) {
      emaSeriesRef.current.setData(emaData)
    }
    if (rsiSeriesRef.current && rsiData.length) {
      rsiSeriesRef.current.setData(rsiData)
    }
  }, [indicators, timeframe])

  // Update indicator visibility
  useEffect(() => {
    if (smaSeriesRef.current) {
      smaSeriesRef.current.applyOptions({ visible: indicatorVisibility.sma })
    }
    if (emaSeriesRef.current) {
      emaSeriesRef.current.applyOptions({ visible: indicatorVisibility.ema })
    }
    if (rsiSeriesRef.current) {
      rsiSeriesRef.current.applyOptions({ visible: indicatorVisibility.rsi })
    }
  }, [indicatorVisibility])

  // Update API when indicators are toggled
  useEffect(() => {
    if (!sessionId) return
    const indicatorsEnabled =
      indicatorVisibility.sma ||
      indicatorVisibility.ema ||
      indicatorVisibility.rsi
    simulatorApi.updateSession(sessionId, {
      indicators_enabled: indicatorsEnabled,
      indicator_sma_enabled: indicatorVisibility.sma,
      indicator_ema_enabled: indicatorVisibility.ema,
      indicator_rsi_enabled: indicatorVisibility.rsi,
    }).catch(() => {
      // ignore toggle failures
    })
  }, [indicatorVisibility, sessionId])

  if (!sessionId) {
    return (
      <div className="w-full h-full min-h-[400px] flex items-center justify-center text-muted-foreground bg-muted/10 rounded-lg border border-dashed border-muted">
        Select a session to view chart
      </div>
    )
  }

  return (
    <div className="w-full space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="text-sm font-medium text-muted-foreground">{symbol} Chart</div>
        <div className="flex items-center gap-4 text-sm">
          <div className="flex items-center gap-2">
            <Switch
              checked={indicatorVisibility.sma}
              onCheckedChange={(checked) =>
                setIndicatorVisibility((prev) => ({ ...prev, sma: checked }))
              }
            />
            <Label className="text-xs text-muted-foreground">SMA</Label>
          </div>
          <div className="flex items-center gap-2">
            <Switch
              checked={indicatorVisibility.ema}
              onCheckedChange={(checked) =>
                setIndicatorVisibility((prev) => ({ ...prev, ema: checked }))
              }
            />
            <Label className="text-xs text-muted-foreground">EMA</Label>
          </div>
          <div className="flex items-center gap-2">
            <Switch
              checked={indicatorVisibility.rsi}
              onCheckedChange={(checked) =>
                setIndicatorVisibility((prev) => ({ ...prev, rsi: checked }))
              }
            />
            <Label className="text-xs text-muted-foreground">RSI</Label>
          </div>
        </div>
      </div>

      <div className="relative w-full rounded-lg border border-border/60 bg-muted/10">
        <div ref={chartContainerRef} className="w-full h-full" style={{ height }} />
        {markerPositions.map((marker) => (
          <div
            key={marker.id}
            style={{
              position: "absolute",
              left: marker.x - 10,
              top: marker.y - 10,
              pointerEvents: "none",
              fontSize: "18px",
              fontWeight: 700,
              color: marker.side === "buy" ? "#10b981" : "#ef4444",
              textShadow: "0 0 4px rgba(0,0,0,0.5)",
            }}
          >
            {marker.side === "buy" ? "▲" : "▼"}
          </div>
        ))}
      </div>
    </div>
  )
}
