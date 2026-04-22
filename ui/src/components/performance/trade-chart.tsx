/**
 * Trade Chart Component
 *
 * Interactive OHLCV candlestick chart using lightweight-charts library.
 * Displays trade entry/exit with MT5-style visualization.
 *
 * Features:
 * - Client-side data filtering for fast performance
 * - MT5-style entry/exit visualization with dotted trendline
 * - Hover tooltip showing trade details
 * - Responsive chart height (400px mobile, 600px desktop)
 * - Automatic resize handling
 *
 * @module components/performance/trade-chart
 */

"use client"

import * as React from "react"
import { useEffect, useRef } from "react"
import { SemanticSnapshotScript } from "@/components/ai-chat/SemanticSnapshotScript"
import {
  createChart,
  ColorType,
  IChartApi,
  ISeriesApi,
  Time,
  MouseEventParams,
  CandlestickSeries,
  LineSeries,
} from "lightweight-charts"
import { parseUtcDate } from "@/lib/utils"
import { Trade, ChartData } from "@/lib/api/trades"

/**
 * Props for TradeChart component
 */
interface TradeChartProps {
  /** Complete OHLCV dataset for entire backtest period (kept in memory) */
  fullChartData: ChartData[]
  /** The trade being viewed */
  currentTrade: Trade
  /** Time window defining which bars to display (Unix timestamps) */
  visibleWindow: { start: number; end: number }
  /** All trades in the backtest (for showing additional markers) */
  allTrades?: Trade[]
}

/**
 * TradeChart Component
 *
 * Renders an interactive candlestick chart with MT5-style trade visualization.
 * Filters the full dataset client-side based on the visible window for optimal performance.
 *
 * @component
 */
export function TradeChart({
  fullChartData,
  currentTrade,
  visibleWindow,
  allTrades = [],
}: TradeChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null)
  const tooltipRef = useRef<HTMLDivElement>(null)
  const entryArrowRef = useRef<HTMLDivElement>(null)
  const exitArrowRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!chartContainerRef.current || fullChartData.length === 0) return

    // Calculate responsive height
    const isMobile = window.innerWidth < 640
    const chartHeight = isMobile ? 400 : 600

    // Create chart instance
    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#9ca3af",
      },
      width: chartContainerRef.current.clientWidth,
      height: chartHeight,
      grid: {
        vertLines: { color: "rgba(42, 46, 57, 0.1)" },
        horzLines: { color: "rgba(42, 46, 57, 0.1)" },
      },
      rightPriceScale: {
        borderColor: "rgba(42, 46, 57, 0.1)",
      },
      timeScale: {
        borderColor: "rgba(42, 46, 57, 0.1)",
        timeVisible: true,
        secondsVisible: false,
      },
      crosshair: {
        mode: 1, // Normal crosshair mode
      },
    })

    // Add candlestick series
    const candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#10b981",
      downColor: "#ef4444",
      borderVisible: false,
      wickUpColor: "#10b981",
      wickDownColor: "#ef4444",
      priceFormat: {
        type: 'price',
        precision: 5,
        minMove: 0.00001,
      },
    })

    // Filter data by visible window
    const visibleData = fullChartData.filter(
      (bar) => bar.time >= visibleWindow.start && bar.time <= visibleWindow.end
    )

    // Set candlestick data
    if (visibleData.length > 0) {
      candlestickSeries.setData(
        visibleData.map((bar) => ({
          time: bar.time as Time,
          open: bar.open,
          high: bar.high,
          low: bar.low,
          close: bar.close,
        }))
      )
    }

    // Determine trade direction
    const isLong = currentTrade.side?.toUpperCase() === "BUY" || currentTrade.side?.toUpperCase() === "LONG"

    // MT5-style colors: BUY start=blue, end=deepPink; SELL start=deepPink, end=blue
    const entryColor = isLong ? "#2563eb" : "#ff1493" // blue : deepPink
    // Store update function for later use
    let updateArrowPositions: (() => void) | null = null

    // Add dotted trendline connecting entry to exit
    if (currentTrade.open_time && currentTrade.close_time && currentTrade.open_price && currentTrade.close_price) {
      const entryTime = parseUtcDate(currentTrade.open_time)
      const exitTime = parseUtcDate(currentTrade.close_time)

      // Debug logging
      console.log('Trade Times:', {
        openTime: currentTrade.open_time,
        closeTime: currentTrade.close_time,
        entryTimestamp: entryTime,
        exitTimestamp: exitTime,
        entryDate: new Date(entryTime * 1000).toISOString(),
        exitDate: new Date(exitTime * 1000).toISOString()
      })

      const trendLineSeries = chart.addSeries(LineSeries, {
        color: entryColor,
        lineWidth: 2,
        lineStyle: 1, // 0=Solid, 1=Dotted, 2=Dashed, 3=LargeDashed, 4=SparseDotted
        crosshairMarkerVisible: false,
        lastValueVisible: false,
        priceLineVisible: false,
      })

      trendLineSeries.setData([
        { time: entryTime as Time, value: currentTrade.open_price },
        { time: exitTime as Time, value: currentTrade.close_price },
      ])

      // Position arrow markers using HTML overlays
      updateArrowPositions = () => {
        if (!entryArrowRef.current || !exitArrowRef.current || !chartContainerRef.current) return

        try {
          // Find the chart canvas element (lightweight-charts uses a table with canvas inside)
          const canvasElement = chartContainerRef.current.querySelector('canvas')
          if (!canvasElement) {
            console.error('Canvas element not found')
            return
          }

          // Get the canvas position relative to the container
          const containerRect = chartContainerRef.current.getBoundingClientRect()
          const canvasRect = canvasElement.getBoundingClientRect()

          // Calculate offset of canvas from container
          const offsetX = canvasRect.left - containerRect.left
          const offsetY = canvasRect.top - containerRect.top

          // Get pixel coordinates for entry point (relative to chart canvas)
          const entryX = chart.timeScale().timeToCoordinate(entryTime as Time)
          const entryY = currentTrade.open_price !== null ? candlestickSeries.priceToCoordinate(currentTrade.open_price) : null

          // Get pixel coordinates for exit point (relative to chart canvas)
          const exitX = chart.timeScale().timeToCoordinate(exitTime as Time)
          const exitY = currentTrade.close_price !== null ? candlestickSeries.priceToCoordinate(currentTrade.close_price) : null

          console.log('Arrow Coordinates:', {
            entryX,
            entryY,
            exitX,
            exitY,
            offsetX,
            offsetY,
            canvasWidth: canvasRect.width,
            canvasHeight: canvasRect.height
          })

          // Position entry arrow (add canvas offset and center the 20px arrow)
          if (entryX !== null && entryY !== null) {
            entryArrowRef.current.style.left = `${offsetX + entryX - 10}px`
            entryArrowRef.current.style.top = `${offsetY + entryY - 10}px`
            entryArrowRef.current.style.display = 'block'
          } else {
            entryArrowRef.current.style.display = 'none'
          }

          // Position exit arrow (add canvas offset and center the 20px arrow)
          if (exitX !== null && exitY !== null) {
            exitArrowRef.current.style.left = `${offsetX + exitX - 10}px`
            exitArrowRef.current.style.top = `${offsetY + exitY - 10}px`
            exitArrowRef.current.style.display = 'block'
          } else {
            exitArrowRef.current.style.display = 'none'
          }
        } catch (e) {
          console.error('Error positioning arrows:', e)
        }
      }

    }

    // Fit content to visible range BEFORE positioning arrows
    chart.timeScale().fitContent()

    // Position arrows after chart is fitted
    if (updateArrowPositions) {
      // Initial positioning
      setTimeout(updateArrowPositions, 150)

      // Update positions on time scale changes (zoom, pan)
      chart.timeScale().subscribeVisibleTimeRangeChange(updateArrowPositions)
    }

    // Tooltip functionality
    if (tooltipRef.current) {
      const tooltip = tooltipRef.current

      chart.subscribeCrosshairMove((param: MouseEventParams) => {
        if (!param.time || !param.point) {
          tooltip.style.display = "none"
          return
        }

        // Check if hovering near the trade trendline
        const entryTime = parseUtcDate(currentTrade.open_time)
        const exitTime = parseUtcDate(currentTrade.close_time)

        if (entryTime && exitTime && (param.time as number) >= entryTime && (param.time as number) <= exitTime) {
          const pnlPips = currentTrade.pnl_pips || 0
          const pnlColor = pnlPips >= 0 ? "#10b981" : "#ef4444"

          tooltip.style.display = "block"
          tooltip.style.left = param.point.x + 15 + "px"
          tooltip.style.top = param.point.y + 15 + "px"
          tooltip.innerHTML = `
            <div style="background: rgba(0, 0, 0, 0.9); color: white; padding: 8px 12px; border-radius: 4px; font-size: 12px; line-height: 1.5; box-shadow: 0 2px 8px rgba(0,0,0,0.3);">
              <div style="font-weight: 600; margin-bottom: 4px;">Trade #${currentTrade.trade_id}</div>
              <div>Entry: ${currentTrade.open_price?.toFixed(5)}</div>
              <div>Exit: ${currentTrade.close_price?.toFixed(5)}</div>
              <div style="color: ${pnlColor}; font-weight: 600;">P&L: ${pnlPips.toFixed(1)} pips</div>
            </div>
          `
        } else {
          tooltip.style.display = "none"
        }
      })
    }

    // Handle resize
    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth })
        // Update arrow positions after resize
        if (updateArrowPositions) {
          setTimeout(updateArrowPositions, 100)
        }
      }
    }

    window.addEventListener("resize", handleResize)

    // Store refs
    chartRef.current = chart
    seriesRef.current = candlestickSeries

    // Cleanup
    return () => {
      window.removeEventListener("resize", handleResize)
      chart.remove()
    }
  }, [fullChartData, currentTrade, visibleWindow, allTrades])

  // Determine trade direction for arrow colors
  const isLong = currentTrade.side?.toUpperCase() === "BUY" || currentTrade.side?.toUpperCase() === "LONG"
  const entryColor = isLong ? "#2563eb" : "#ff1493" // blue : deepPink
  const exitColor = isLong ? "#ff1493" : "#2563eb" // deepPink : blue

  return (
    <div className="relative h-full w-full">
      <SemanticSnapshotScript
        block={{
          id: `trade-chart:${currentTrade.trade_id}`,
          blockType: "chart",
          title: `Trade ${currentTrade.trade_id} Chart`,
          summary: "Trade detail candlestick chart with entry, exit, and trade PnL context.",
          keywords: [
            "trade chart",
            String(currentTrade.trade_id),
            currentTrade.side || "side",
            currentTrade.symbol || "symbol",
            "entry",
            "exit",
            "pnl",
          ],
          metrics: [
            { label: "Trade ID", value: String(currentTrade.trade_id) },
            { label: "Side", value: currentTrade.side || "N/A" },
            { label: "Entry Price", value: currentTrade.open_price?.toFixed(5) || "N/A" },
            { label: "Exit Price", value: currentTrade.close_price?.toFixed(5) || "N/A" },
            { label: "PnL Pips", value: currentTrade.pnl_pips !== undefined && currentTrade.pnl_pips !== null ? String(currentTrade.pnl_pips) : "N/A" },
          ],
          series: [
            {
              label: "OHLC",
              points: fullChartData.slice(-160).map((bar) => ({
                x: String(bar.time),
                y: `O=${bar.open} H=${bar.high} L=${bar.low} C=${bar.close}`,
              })),
            },
            {
              label: "Trade line",
              points: currentTrade.open_time && currentTrade.close_time && currentTrade.open_price && currentTrade.close_price
                ? [
                    { x: currentTrade.open_time, y: String(currentTrade.open_price) },
                    { x: currentTrade.close_time, y: String(currentTrade.close_price) },
                  ]
                : [],
            },
          ],
        }}
      />
      <div ref={chartContainerRef} className="h-full w-full" />

      {/* Entry arrow marker */}
      <div
        ref={entryArrowRef}
        style={{
          position: "absolute",
          display: "none",
          pointerEvents: "none",
          fontSize: "20px",
          fontWeight: "bold",
          color: entryColor,
          textShadow: "0 0 3px rgba(0,0,0,0.5)",
          zIndex: 100,
        }}
      >
        →
      </div>

      {/* Exit arrow marker */}
      <div
        ref={exitArrowRef}
        style={{
          position: "absolute",
          display: "none",
          pointerEvents: "none",
          fontSize: "20px",
          fontWeight: "bold",
          color: exitColor,
          textShadow: "0 0 3px rgba(0,0,0,0.5)",
          zIndex: 100,
        }}
      >
        ←
      </div>

      {/* Tooltip */}
      <div
        ref={tooltipRef}
        style={{
          position: "absolute",
          display: "none",
          pointerEvents: "none",
          zIndex: 1000,
        }}
      />
    </div>
  )
}
