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
import { cn } from "@/lib/utils"

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
      (module as any)(Highcharts)
    } else if (module && typeof (module as any).default === "function") {
      (module as any).default(Highcharts)
    }
  })
}

interface DataHighstockChartProps {
  symbol: string
  timeframe: string
  rows: Array<Record<string, unknown>>
  schema: MarketPreparedDataset["schema"]
  className?: string
}

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

export function DataHighstockChart({
  symbol,
  timeframe,
  rows,
  schema,
  className,
}: DataHighstockChartProps) {
  const chartComponentRef = useRef<HighchartsReact.RefObject>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const containerHeightRef = useRef<number>(600)

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
    const data: Array<[number, number, number, number, number]> = []
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

  const [containerHeight, setContainerHeight] = useState<number>(600)

  const options: Highcharts.Options = useMemo(() => ({
    chart: {
      backgroundColor: "transparent",
      height: containerHeightRef.current,
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
      text: `${symbol} - ${timeframe}`,
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
        data: ohlcData.ohlc,
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
  }), [ohlcData, symbol, timeframe])

  return (
    <div className={cn("relative h-full w-full bg-[#070b14] overflow-hidden", className)}>
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
