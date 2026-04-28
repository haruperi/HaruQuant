"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { SemanticSnapshotScript } from "@/components/ai-chat/SemanticSnapshotScript"
import {
  CandlestickSeries,
  ColorType,
  IChartApi,
  ISeriesApi,
  LineSeries,
  Time,
  createChart,
} from "lightweight-charts"
import type { IndicatorSelection } from "@/components/simulation/indicator-control"

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
  symbol?: string
  timeframe?: string
  height?: number
  bars: ChartBarData[]
  indicators?: ChartIndicatorData[]
  digits?: number
  indicatorVisibility?: IndicatorSelection
  positions?: any[]
  trades?: any[]
  currentPrice?: number
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
  symbol = "EURUSD",
  timeframe,
  height = 520,
  bars,
  indicators = [],
  digits = 5,
  indicatorVisibility = { sma: false, ema: false, rsi: false },
  positions = [],
  trades = [],
  currentPrice,
}: SimulationChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null)
  const smaSeriesRef = useRef<ISeriesApi<"Line"> | null>(null)
  const emaSeriesRef = useRef<ISeriesApi<"Line"> | null>(null)
  const rsiSeriesRef = useRef<ISeriesApi<"Line"> | null>(null)
  const markersRef = useRef<TradeMarker[]>([])
  const digitsRef = useRef<number>(digits)

  const [markerPositions, setMarkerPositions] = useState<
    { id: number; x: number; y: number; side: "buy" | "sell" }[]
  >([])
  const [linePositions, setLinePositions] = useState<
    {
      id: string | number
      x1: number
      y1: number
      x2: number
      y2: number
      color: string
      side: "buy" | "sell"
      status: "open" | "closed"
    }[]
  >([])

  const updateMarkerPositions = useCallback(() => {
    if (!chartRef.current || !candleSeriesRef.current) return

    const positions_coords = markersRef.current
      .map((marker) => {
        const x = chartRef.current!.timeScale().timeToCoordinate(marker.time)
        const y = candleSeriesRef.current!.priceToCoordinate(marker.price)
        if (x === null || y === null) return null
        return { id: marker.id, x, y, side: marker.side }
      })
      .filter(Boolean) as { id: number; x: number; y: number; side: "buy" | "sell" }[]

    setMarkerPositions(positions_coords)

    // Calculate line positions
    const lines: typeof linePositions = []

    // 1. Process open positions
    if (positions && positions.length > 0) {
      const lastBar = bars[bars.length - 1]
      const lastBarTime = lastBar ? resolveChartTime(lastBar.time, timeframe) : null

      for (const pos of positions) {
        if (pos.symbol !== symbol) continue
        const openTimeValue = pos.time || pos.openTime
        const openTime = resolveChartTime(openTimeValue, timeframe)
        if (!openTime) continue

        const x1 = chartRef.current!.timeScale().timeToCoordinate(openTime)
        const y1 = candleSeriesRef.current!.priceToCoordinate(pos.openPrice)

        // For open positions, end point follows current price and time
        const x2 = lastBarTime
          ? chartRef.current!.timeScale().timeToCoordinate(lastBarTime)
          : null
        const y2 = candleSeriesRef.current!.priceToCoordinate(pos.currentPrice || currentPrice || 0)

        if (x1 !== null && y1 !== null && x2 !== null && y2 !== null) {
          lines.push({
            id: `pos-${pos.id}`,
            x1,
            y1,
            x2,
            y2,
            color: pos.type === "buy" ? "#10b981" : "#ef4444",
            side: pos.type,
            status: "open",
          })
        }
      }
    }

    // 2. Process completed trades
    if (trades && trades.length > 0) {
      for (const trade of trades) {
        if (trade.symbol !== symbol) continue
        const openTimeValue = trade.open_time || trade.time_open
        const closeTimeValue = trade.close_time || trade.time_close
        const openTime = resolveChartTime(openTimeValue, timeframe)
        const closeTime = resolveChartTime(closeTimeValue, timeframe)
        if (!openTime || !closeTime) continue

        const x1 = chartRef.current!.timeScale().timeToCoordinate(openTime)
        const y1 = candleSeriesRef.current!.priceToCoordinate(trade.open_price)
        const x2 = chartRef.current!.timeScale().timeToCoordinate(closeTime)
        const y2 = candleSeriesRef.current!.priceToCoordinate(trade.close_price)

        if (x1 !== null && y1 !== null && x2 !== null && y2 !== null) {
          lines.push({
            id: `trade-${trade.ticket || trade.id}`,
            x1,
            y1,
            x2,
            y2,
            color: (trade.type === 0 || trade.type === "buy") ? "#10b981" : "#ef4444",
            side: (trade.type === 0 || trade.type === "buy") ? "buy" : "sell",
            status: "closed",
          })
        }
      }
    }

    setLinePositions(lines)
  }, [bars, currentPrice, positions, symbol, timeframe, trades])

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
  }, [height, timeframe, updateMarkerPositions, digits])

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
    
    updateMarkerPositions()
  }, [bars, timeframe, digits, updateMarkerPositions])

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

  // Re-calculate positions when props change
  useEffect(() => {
    updateMarkerPositions()
  }, [positions, trades, currentPrice, updateMarkerPositions])

  return (
    <div className="w-full space-y-3">
      <SemanticSnapshotScript
        block={{
          id: `simulation-chart:${symbol}:${timeframe || "unknown"}`,
          blockType: "chart",
          title: `${symbol} Chart`,
          summary: `Simulation candlestick chart for ${symbol}${timeframe ? ` on ${timeframe}` : ""}.`,
          keywords: [symbol, timeframe || "timeframe", "simulation", "candles", "ohlc"],
          metrics: [
            { label: "Bar Count", value: String(bars.length) },
            { label: "Indicator Points", value: String(indicators.length) },
            {
              label: "Latest Close",
              value: bars.length > 0 ? bars[bars.length - 1].close.toFixed(digits) : "N/A",
            },
          ],
          series: [
            {
              label: "OHLC",
              points: bars.slice(-160).map((bar) => ({
                x: String(bar.time),
                y: `O=${bar.open.toFixed(digits)} H=${bar.high.toFixed(digits)} L=${bar.low.toFixed(digits)} C=${bar.close.toFixed(digits)}`,
              })),
            },
            {
              label: "SMA",
              points: indicators
                .filter((indicator) => typeof indicator.sma === "number")
                .slice(-160)
                .map((indicator) => ({ x: String(indicator.time || ""), y: String(indicator.sma) })),
            },
            {
              label: "EMA",
              points: indicators
                .filter((indicator) => typeof indicator.ema === "number")
                .slice(-160)
                .map((indicator) => ({ x: String(indicator.time || ""), y: String(indicator.ema) })),
            },
            {
              label: "RSI",
              points: indicators
                .filter((indicator) => typeof indicator.rsi === "number")
                .slice(-160)
                .map((indicator) => ({ x: String(indicator.time || ""), y: String(indicator.rsi) })),
            },
          ],
        }}
      />
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="text-sm font-medium text-muted-foreground">{symbol} Chart</div>
      </div>

      <div className="relative w-full rounded-lg border border-border/60 bg-muted/10 overflow-hidden" style={{ height }}>
        <div ref={chartContainerRef} className="w-full h-full" />
        
        {/* SVG Overlay for Trendlines */}
        <svg 
          className="absolute inset-0 pointer-events-none" 
          width="100%" 
          height="100%"
          style={{ zIndex: 10 }}
        >
          {linePositions.map((line) => (
            <g key={line.id}>
              <line
                x1={line.x1}
                y1={line.y1}
                x2={line.x2}
                y2={line.y2}
                stroke={line.color}
                strokeWidth={2}
                strokeDasharray={line.status === "open" ? "4 2" : "0"}
                className={line.status === "open" ? "animate-pulse" : ""}
                opacity={0.8}
              />
              <circle cx={line.x1} cy={line.y1} r={3} fill={line.color} />
              {line.status === "closed" && (
                <circle cx={line.x2} cy={line.y2} r={3} fill={line.color} />
              )}
            </g>
          ))}
        </svg>

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
              zIndex: 20,
            }}
          >
            {marker.side === "buy" ? "▲" : "▼"}
          </div>
        ))}
      </div>
    </div>
  )
}
