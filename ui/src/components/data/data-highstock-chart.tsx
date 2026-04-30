"use client"

import React, { useEffect, useMemo, useRef, useState } from "react"
import Highcharts from "highcharts/highstock"
import HighchartsReact from "highcharts-react-official"

// Load Highcharts modules using common patterns
import IndicatorsAll from "highcharts/indicators/indicators-all"
import DragPanes from "highcharts/modules/drag-panes"
import AnnotationsAdvanced from "highcharts/modules/annotations-advanced"
import PriceIndicator from "highcharts/modules/price-indicator"
import FullScreen from "highcharts/modules/full-screen"
import HeikinAshi from "highcharts/modules/heikinashi"
import HollowCandlestick from "highcharts/modules/hollowcandlestick"
import StockTools from "highcharts/modules/stock-tools"

// Import Highcharts CSS for Stock Tools GUI
import "highcharts/css/stocktools/gui.css"
import "highcharts/css/annotations/popup.css"

import type { MarketPreparedDataset } from "@/lib/api/data"
import type { TradeLike } from "@/lib/api/strategies"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"

// Initialize modules - checking for both default and direct function
const modules = [
  IndicatorsAll,
  DragPanes,
  AnnotationsAdvanced,
  PriceIndicator,
  FullScreen,
  HeikinAshi,
  HollowCandlestick,
  StockTools
]

if (typeof Highcharts === "object") {
  modules.forEach(module => {
    if (typeof module === "function") {
      module(Highcharts)
    } else if (module && typeof (module as { default?: unknown }).default === "function") {
      ;(module as { default: (highcharts: typeof Highcharts) => void }).default(Highcharts)
    }
  })
}

interface DataHighstockChartProps {
  symbol: string
  timeframe: string
  rows: Array<Record<string, unknown>>
  schema: MarketPreparedDataset["schema"]
  trades?: TradeLike[]
  replayMode?: boolean
  className?: string
}

type OhlcPoint = [number, number, number, number, number]
type NullableOhlcPoint = [number, number | null, number | null, number | null, number | null]

function parseTimestamp(row: Record<string, unknown>) {
  const directValue =
    row.time ??
    row.timestamp ??
    row.datetime ??
    row.date_time ??
    row.index

  if (typeof directValue === "number") {
    // Highcharts expects milliseconds
    return directValue > 1e12 ? directValue : directValue * 1000
  }

  if (typeof directValue === "string" && directValue.trim()) {
    const raw = directValue.trim()
    const normalized = /[zZ]|[+-]\d{2}:?\d{2}$/.test(raw) ? raw : `${raw}Z`
    const parsed = Date.parse(normalized)
    if (Number.isFinite(parsed)) {
      return parsed
    }
  }

  if (typeof row.date === "string" && typeof row.time === "string") {
    const combined = `${row.date}T${row.time}`
    const parsed = Date.parse(`${combined}Z`)
    if (Number.isFinite(parsed)) {
      return parsed
    }
  }

  if (typeof row.date === "string") {
    const parsed = Date.parse(`${row.date}T00:00:00Z`)
    if (Number.isFinite(parsed)) {
      return parsed
    }
  }

  return null
}

function parseTradeTimestamp(value: unknown) {
  if (typeof value === "number") {
    return value > 1e12 ? value : value * 1000
  }

  if (typeof value === "string" && value.trim()) {
    const raw = value.trim()
    const normalized = /[zZ]|[+-]\d{2}:?\d{2}$/.test(raw) ? raw : `${raw}Z`
    const parsed = Date.parse(normalized)
    if (Number.isFinite(parsed)) return parsed
  }

  return null
}

function firstFiniteNumber(...values: unknown[]) {
  for (const value of values) {
    if (value === null || value === undefined || value === "") continue
    const numberValue = typeof value === "string"
      ? Number(value.replace(/[$,%\s,]/g, ""))
      : Number(value)
    if (Number.isFinite(numberValue)) return numberValue
  }
  return null
}

function formatTradeTime(value: unknown) {
  const timestamp = parseTradeTimestamp(value)
  if (timestamp === null) return "N/A"
  return new Date(timestamp).toISOString().replace("T", " ").slice(0, 19)
}

function isLongTrade(trade: TradeLike) {
  const side = String(trade.side ?? trade.type ?? trade.direction ?? "").toUpperCase()
  return side === "BUY" || side === "LONG"
}

export function DataHighstockChart({
  symbol,
  timeframe,
  rows,
  schema,
  trades,
  replayMode = false,
  className,
}: DataHighstockChartProps) {
  const chartComponentRef = useRef<HighchartsReact.RefObject>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const containerHeightRef = useRef<number>(600)
  const [containerHeight, setContainerHeight] = useState<number>(600)
  const [isReplayPlaying, setIsReplayPlaying] = useState(replayMode)
  const [replayIndex, setReplayIndex] = useState(0)
  const [replaySpeedMs, setReplaySpeedMs] = useState(180)

  useEffect(() => {
    const el = containerRef.current
    if (!el) return

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const h = entry.contentRect.height
        if (h > 0) {
          containerHeightRef.current = h
          // Imperatively resize so options never re-compute (prevents type reset)
          const chart = chartComponentRef.current?.chart
          if (chart) chart.setSize(null, h, false)
        }
      }
    })
    observer.observe(el)

    // Set initial height
    const h = el.getBoundingClientRect().height
    if (h > 0) {
      containerHeightRef.current = h
      // Will be applied on first chart render via chart.height in options
      setContainerHeight(h)
    }

    return () => observer.disconnect()
  }, [])

  const ohlcData = useMemo(() => {
    const data: OhlcPoint[] = []
    const volume: Array<[number, number]> = []

    for (const row of rows) {
      const timestamp = parseTimestamp(row)
      const open = Number(row[schema.open])
      const high = Number(row[schema.high])
      const low = Number(row[schema.low])
      const close = Number(row[schema.close])
      const vol = row[schema.volume] !== undefined ? Number(row[schema.volume]) : 0

      if (
        timestamp !== null &&
        Number.isFinite(open) &&
        Number.isFinite(high) &&
        Number.isFinite(low) &&
        Number.isFinite(close)
      ) {
        data.push([timestamp, open, high, low, close])
        volume.push([timestamp, vol])
      }
    }

    data.sort((a, b) => a[0] - b[0])
    volume.sort((a, b) => a[0] - b[0])

    return { ohlc: data, volume }
  }, [rows, schema])

  const visibleOhlc = useMemo(() => {
    if (!replayMode) return ohlcData.ohlc
    return ohlcData.ohlc.slice(0, Math.min(replayIndex + 1, ohlcData.ohlc.length))
  }, [ohlcData.ohlc, replayIndex, replayMode])

  const replayCursor = visibleOhlc.at(-1)
  const replayTime = replayMode ? replayCursor?.[0] ?? null : null
  const replayClose = replayMode ? replayCursor?.[4] ?? null : null
  const replayWindowSize = Math.min(120, Math.max(30, Math.floor(ohlcData.ohlc.length * 0.08)))
  const replayPaddingPoint = useMemo(() => {
    if (!replayMode || visibleOhlc.length === 0) return null
    const lastPoint = visibleOhlc.at(-1)
    const previousPoint = visibleOhlc.at(-2)
    if (!lastPoint) return null

    const barDuration = previousPoint ? Math.max(1, lastPoint[0] - previousPoint[0]) : 60 * 60 * 1000
    const rightPaddingBars = Math.ceil(replayWindowSize * 0.2)
    return lastPoint[0] + barDuration * rightPaddingBars
  }, [replayMode, replayWindowSize, visibleOhlc])

  const seriesOhlc = useMemo<NullableOhlcPoint[]>(() => {
    const data: NullableOhlcPoint[] = [...visibleOhlc]
    if (!replayMode || visibleOhlc.length === 0) return data

    const lastPoint = visibleOhlc.at(-1)
    const previousPoint = visibleOhlc.at(-2)
    if (!lastPoint) return data

    const barDuration = previousPoint ? Math.max(1, lastPoint[0] - previousPoint[0]) : 60 * 60 * 1000
    const rightPaddingBars = Math.ceil(replayWindowSize * 0.2)

    for (let index = 1; index <= rightPaddingBars; index += 1) {
      data.push([lastPoint[0] + barDuration * index, null, null, null, null])
    }

    return data
  }, [replayMode, replayWindowSize, visibleOhlc])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setReplayIndex(0)
      setIsReplayPlaying(replayMode)
    }, 0)
    return () => window.clearTimeout(timer)
  }, [ohlcData.ohlc.length, replayMode])

  useEffect(() => {
    if (!replayMode || !isReplayPlaying || ohlcData.ohlc.length <= 1) return

    const timer = window.setInterval(() => {
      setReplayIndex((current) => {
        if (current >= ohlcData.ohlc.length - 1) {
          window.clearInterval(timer)
          return current
        }
        return current + 1
      })
    }, replaySpeedMs)

    return () => window.clearInterval(timer)
  }, [isReplayPlaying, ohlcData.ohlc.length, replayMode, replaySpeedMs])

  useEffect(() => {
    if (!replayMode || visibleOhlc.length === 0) return

    const chart = chartComponentRef.current?.chart
    const lastPoint = visibleOhlc.at(-1)
    if (!chart || !lastPoint) return

    const firstVisibleIndex = Math.max(0, visibleOhlc.length - replayWindowSize)
    const min = visibleOhlc[firstVisibleIndex]?.[0]
    const max = replayPaddingPoint ?? lastPoint[0]

    if (min !== undefined && max !== undefined) {
      chart.xAxis[0]?.setExtremes(min, max, true, false)
    }
  }, [replayMode, replayPaddingPoint, replayWindowSize, visibleOhlc])

  const tradeOverlay = useMemo(() => {
    const lineSeries: Highcharts.SeriesLineOptions[] = []
    const entries: Highcharts.PointOptionsObject[] = []
    const exits: Highcharts.PointOptionsObject[] = []

    for (const trade of trades || []) {
      const entryTime = parseTradeTimestamp(trade.open_time ?? trade.entry_time ?? trade.time)
      const exitTime = parseTradeTimestamp(trade.close_time ?? trade.exit_time)
      const entryPrice = firstFiniteNumber(trade.open_price, trade.entry_price, trade.price)
      const exitPrice = firstFiniteNumber(trade.close_price, trade.exit_price)

      if (entryTime === null || exitTime === null || entryPrice === null || exitPrice === null) continue
      if (replayMode && (replayTime === null || entryTime > replayTime)) continue

      const isLong = isLongTrade(trade)
      const entryColor = isLong ? "#2563eb" : "#ff1493"
      const exitColor = isLong ? "#ff1493" : "#2563eb"
      const lineColor = isLong ? "#2563eb" : "#ff1493"
      const tradeTicket = trade.ticket ?? trade.order ?? trade.position_id ?? trade.deal_id ?? trade.trade_id ?? trade.id ?? ""
      const pips = firstFiniteNumber(
        trade.profit_loss_pips,
        trade.pnl_pips,
        trade.profit_pips,
        trade.pips,
        trade.pl_pips
      )
      const pnl = firstFiniteNumber(
        trade.pnl,
        trade.profit_loss,
        trade.net_profit,
        trade.profit,
        trade.pl,
        trade.p_l,
        trade.final_profit
      )
      const commonCustom = {
        tradeTicket,
        entryPrice,
        exitPrice,
        entryTime: formatTradeTime(trade.open_time ?? trade.entry_time ?? trade.time),
        exitTime: formatTradeTime(trade.close_time ?? trade.exit_time),
        pips: pips ?? "N/A",
        pnl: pnl ?? "N/A",
      }

      const hasClosedInReplay = !replayMode || exitTime <= (replayTime ?? exitTime)
      const lineEndTime = hasClosedInReplay ? exitTime : replayTime
      const lineEndPrice = hasClosedInReplay ? exitPrice : replayClose

      if (lineEndTime !== null && lineEndPrice !== null) {
        lineSeries.push({
        type: "line",
        name: `Trade ${tradeTicket}`,
        data: [[entryTime, entryPrice], [lineEndTime, lineEndPrice]],
        color: lineColor,
        dashStyle: "ShortDash",
        lineWidth: 1,
        opacity: 0.5,
        enableMouseTracking: false,
        linkedTo: "main-series",
        showInLegend: false,
        zIndex: 4,
        })
      }
      entries.push({
        x: entryTime,
        y: entryPrice,
        marker: { fillColor: entryColor, lineColor: "#e2e8f0", symbol: isLong ? "triangle" : "triangle-down" },
        custom: { ...commonCustom, label: "Entry" },
      })
      if (hasClosedInReplay) {
        exits.push({
          x: exitTime,
          y: exitPrice,
          marker: { fillColor: exitColor, lineColor: "#e2e8f0", symbol: isLong ? "triangle-down" : "triangle" },
          custom: { ...commonCustom, label: "Exit" },
        })
      }
    }

    return { lineSeries, entries, exits, count: entries.length }
  }, [replayClose, replayMode, replayTime, trades])

  const options: Highcharts.Options = useMemo(() => ({
    chart: {
      backgroundColor: "transparent",
      height: containerHeight,
      style: {
        fontFamily: "inherit",
      },
      panning: {
        enabled: true,
        type: "x"
      },
      zooming: {
        type: "x",
        resetButton: {
          position: { align: "right", verticalAlign: "top", x: -10, y: 10 },
          theme: {
            fill: "rgba(15, 23, 42, 0.9)",
            stroke: "#334155",
            r: 6,
            style: { color: "#94a3b8", fontSize: "11px", fontWeight: "600" },
            states: {
              hover: {
                fill: "#1e293b",
                stroke: "#475569",
                style: { color: "#f1f5f9" }
              }
            }
          }
        }
      },
      resetZoomButton: {
        position: { align: "right", verticalAlign: "top", x: -10, y: 10 },
        theme: {
          fill: "rgba(15, 23, 42, 0.9)",
          stroke: "#334155",
          r: 6,
          style: { color: "#94a3b8", fontSize: "11px", fontWeight: "600" },
          states: {
            hover: {
              fill: "#1e293b",
              stroke: "#475569",
              style: { color: "#f1f5f9" }
            }
          }
        }
      },
      spacingLeft: 50,
    },
    title: {
      text: `${symbol} - ${timeframe}${replayMode ? " Replay" : ""}`,
      align: "center",
      style: { 
        color: "#f8fafc",
        fontSize: "16px",
        fontWeight: "bold",
        letterSpacing: "0.025em"
      },
      y: 20
    },
    time: {
      useUTC: true,
    } as Highcharts.TimeOptions,
    rangeSelector: {
      enabled: true,
      buttonTheme: {
        fill: "transparent",
        stroke: "none",
        width: 42,
        style: { 
          color: "#94a3b8",
          fontWeight: "500",
          fontSize: "11px"
        },
        states: {
          hover: { 
            fill: "rgba(51, 65, 85, 0.3)", 
            style: { color: "#f1f5f9" } 
          },
          select: { 
            fill: "rgba(59, 130, 246, 0.2)", 
            style: { 
              color: "#60a5fa",
              fontWeight: "700"
            },
            stroke: "rgba(59, 130, 246, 0.5)",
            strokeWidth: 1
          },
        },
      },
      inputBoxBorderColor: "rgba(51, 65, 85, 0.3)",
      inputStyle: { color: "#94a3b8", backgroundColor: "#0f172a" },
      labelStyle: { 
        color: "#64748b",
        textTransform: "uppercase",
        fontSize: "10px",
        letterSpacing: "0.05em"
      },
      buttons: [
        { type: "hour",  count: 1,  text: "1h" },
        { type: "day",   count: 1,  text: "1d" },
        { type: "week",  count: 1,  text: "1w" },
        { type: "month", count: 1,  text: "1m" },
        { type: "year",  count: 1,  text: "1y" },
        { type: "all",              text: "All" }
      ],
      selected: 5
    },
    navigator: {
      enabled: true,
      maskFill: "rgba(59, 130, 246, 0.1)",
      outlineColor: "rgba(51, 65, 85, 0.3)",
      xAxis: {
        gridLineColor: "rgba(30, 41, 59, 0.2)",
        labels: { style: { color: "#475569" } }
      },
      handles: {
        backgroundColor: "#1e293b",
        borderColor: "#334155"
      },
      series: {
        color: "#3b82f6",
        fillOpacity: 0.05
      }
    },
    scrollbar: {
      barBackgroundColor: "rgba(30, 41, 59, 0.5)",
      barBorderColor: "transparent",
      buttonBackgroundColor: "transparent",
      buttonBorderColor: "transparent",
      trackBackgroundColor: "transparent",
      trackBorderColor: "transparent",
      height: 6
    },
    xAxis: {
      gridLineColor: "rgba(30, 41, 59, 0.4)",
      lineColor: "rgba(51, 65, 85, 0.3)",
      tickColor: "rgba(51, 65, 85, 0.3)",
      labels: { style: { color: "#94a3b8", fontSize: "10px" } },
      crosshair: {
        color: "rgba(148, 163, 184, 0.3)",
        dashStyle: "Dash"
      }
    },
    yAxis: [
      {
        labels: { 
          align: "right", 
          x: -8, 
          style: { color: "#94a3b8", fontSize: "10px" } 
        },
        title: { text: "" },
        height: "100%",
        lineWidth: 0,
        gridLineColor: "rgba(30, 41, 59, 0.4)",
        resize: { enabled: true },
        opposite: true,
        crosshair: {
          color: "rgba(148, 163, 184, 0.3)",
          dashStyle: "Dash"
        }
      },
    ],
    series: [
      {
        type: "candlestick",
        name: symbol,
        data: seriesOhlc,
        id: "main-series",
        upColor: "#00ffbd",
        color: "#ff3b69",
        upLineColor: "#00ffbd",
        lineColor: "#ff3b69",
        dataGrouping: {
          enabled: false
        },
        lastPriceAnimation: {
          enabled: true
        }
      },
      ...(tradeOverlay.count > 0 ? [
        ...tradeOverlay.lineSeries,
        {
          type: "scatter" as const,
          name: "Trade entries",
          data: tradeOverlay.entries,
          color: "#2563eb",
          marker: {
            enabled: true,
            radius: 8,
            lineWidth: 1,
            lineColor: "#e2e8f0",
          },
          tooltip: {
            pointFormat: '<b>Trade #{point.custom.tradeTicket}</b><br/>Entry Price: <b>{point.custom.entryPrice}</b><br/>Entry Time: <b>{point.custom.entryTime}</b><br/>'
          },
          zIndex: 6,
        },
        {
          type: "scatter" as const,
          name: "Trade exits",
          data: tradeOverlay.exits,
          color: "#ff1493",
          marker: {
            enabled: true,
            radius: 8,
            lineWidth: 1,
            lineColor: "#e2e8f0",
          },
          tooltip: {
            pointFormat: '<b>Trade #{point.custom.tradeTicket}</b><br/>Exit Price: <b>{point.custom.exitPrice}</b><br/>Exit Time: <b>{point.custom.exitTime}</b><br/>Pips: <b>{point.custom.pips}</b><br/>P&L: <b>{point.custom.pnl}</b><br/>'
          },
          zIndex: 6,
        },
      ] satisfies Highcharts.SeriesOptionsType[] : []),
    ],
    stockTools: {
      gui: {
        enabled: true,
        buttons: [
          'typeChange',
          'separator',
          'indicators',
          'separator',
          'simpleShapes',
          'lines',
          'crookedLines',
          'measure',
          'advanced',
          'separator',
          'verticalLabels',
          'flags',
          'separator',
          'zoomChange',
          'fullScreen',
          'separator',
          'currentPriceIndicator',
          'saveChart'
        ]
      },
    },
    plotOptions: {
      series: {
        dataGrouping: {
          enabled: false
        }
      },
      candlestick: {
        lineColor: "#ff3b69",
        upLineColor: "#00ffbd",
        wickColor: "#94a3b8"
      }
    },
    tooltip: {
      backgroundColor: "rgba(15, 23, 42, 0.98)",
      style: { color: "#f1f5f9", fontSize: "11px" },
      borderColor: "#334155",
      split: false,
      shared: true,
      shadow: true
    },
    credits: {
      enabled: false,
    },
  }), [containerHeight, replayMode, seriesOhlc, symbol, timeframe, tradeOverlay])

  return (
    <div className={cn("relative h-full w-full bg-[#070b14] overflow-hidden", className)}>
      {replayMode && (
        <div className="absolute right-4 top-4 z-20 flex items-center gap-2 rounded-md border border-slate-700 bg-slate-950/90 px-3 py-2 text-xs text-slate-200 shadow-lg">
          <span className="font-mono text-slate-400">
            {visibleOhlc.length}/{ohlcData.ohlc.length}
          </span>
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="h-7 border-slate-700 bg-slate-900 px-2 text-xs text-slate-100 hover:bg-slate-800"
            onClick={() => setIsReplayPlaying((playing) => !playing)}
          >
            {isReplayPlaying ? "Pause" : "Play"}
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="h-7 border-slate-700 bg-slate-900 px-2 text-xs text-slate-100 hover:bg-slate-800"
            onClick={() => {
              setReplayIndex(0)
              setIsReplayPlaying(true)
            }}
          >
            Reset
          </Button>
          <select
            value={replaySpeedMs}
            onChange={(event) => setReplaySpeedMs(Number(event.target.value))}
            className="h-7 rounded border border-slate-700 bg-slate-900 px-2 text-xs text-slate-100"
          >
            <option value={320}>1x</option>
            <option value={180}>2x</option>
            <option value={80}>4x</option>
            <option value={30}>8x</option>
          </select>
        </div>
      )}
      <style dangerouslySetInnerHTML={{ __html: `
        /* ── Stock Tools sidebar: colors only, no structural overrides ── */

        /* Sidebar background */
        .highcharts-stocktools-wrapper {
          background-color: #0f172a !important;
          border-right: 1px solid #1e293b !important;
          box-shadow: 4px 0 20px rgba(0,0,0,0.3) !important;
        }

        /* Remove white li/button backgrounds — keep background-image (the icon) */
        .highcharts-stocktools-toolbar li {
          background-color: #1e293b !important; /* darker background for contrast */
          border: none !important;
          display: flex !important;
          justify-content: center !important;
          align-items: center !important;
        }
        .highcharts-stocktools-toolbar li button,
        .highcharts-stocktools-toolbar li .highcharts-menu-item-btn {
          background-color: transparent !important;
          border: none !important;
          box-shadow: none !important;
          /* Invert the dark SVG icon to appear light on dark background */
          filter: invert(1) brightness(0.85) !important;
        }

        /* Span text labels inside buttons (if any) */
        .highcharts-stocktools-toolbar li button span,
        .highcharts-stocktools-toolbar li .highcharts-menu-item-btn span {
          color: #94a3b8 !important;
        }

        /* Toolbar item hover / active states */
        .highcharts-stocktools-toolbar li:not(.highcharts-separator):hover {
          background-color: #1e293b !important;
        }
        .highcharts-stocktools-toolbar li.highcharts-active {
          background-color: #1e293b !important;
          border-left: 2px solid #3b82f6 !important;
        }

        /* Separator line */
        .highcharts-stocktools-toolbar .highcharts-separator > span {
          background-color: #1e293b !important;
        }

        /* Submenu popup */
        .highcharts-submenu-wrapper {
          background-color: #0f172a !important;
          border: 1px solid #334155 !important;
          border-radius: 0 6px 6px 0 !important;
          box-shadow: 8px 0 20px rgba(0,0,0,0.4) !important;
        }
        .highcharts-submenu-wrapper li button,
        .highcharts-submenu-wrapper li .highcharts-menu-item-btn {
          background-color: transparent !important;
          border: none !important;
          box-shadow: none !important;
        }
        .highcharts-submenu-wrapper li button span {
          filter: invert(1) brightness(0.8) !important;
        }
        .highcharts-submenu-wrapper li:not(.highcharts-separator):hover {
          background-color: #1e293b !important;
        }

        /* Annotation popup dialogs */
        .highcharts-popup {
          background-color: #1e293b !important;
          border: 1px solid #334155 !important;
          color: #f1f5f9 !important;
          border-radius: 8px !important;
          box-shadow: 0 10px 30px rgba(0,0,0,0.5) !important;
        }
        .highcharts-popup input,
        .highcharts-popup select {
          background-color: #0f172a !important;
          border-color: #334155 !important;
          color: #f1f5f9 !important;
        }
        .highcharts-popup .highcharts-popup-bottom-row button {
          background-color: #3b82f6 !important;
          color: #ffffff !important;
          border-radius: 4px !important;
        }

        /* Reset zoom button */
        .highcharts-reset-zoom rect {
          fill: rgba(15, 23, 42, 0.9) !important;
          stroke: #334155 !important;
        }
        .highcharts-reset-zoom text {
          fill: #94a3b8 !important;
        }
        .highcharts-reset-zoom:hover rect {
          fill: #1e293b !important;
          stroke: #475569 !important;
        }
        .highcharts-reset-zoom:hover text {
          fill: #f1f5f9 !important;
        }

        /* Axis title hidden to avoid overlap */
        .highcharts-axis-title {
          display: none !important;
        }
      `}} />
      <div ref={containerRef} className="absolute inset-0">
        <HighchartsReact
          highcharts={Highcharts}
          constructorType={"stockChart"}
          options={options}
          ref={chartComponentRef}
          containerProps={{ style: { height: `${containerHeight}px`, width: '100%' } }}
        />
      </div>
    </div>
  )
}
