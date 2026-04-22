"use client"

import { useEffect, useRef, useState, useCallback } from "react"
import { createChart, ColorType, CandlestickSeries, Time, IChartApi, ISeriesApi } from "lightweight-charts"
import { SemanticSnapshotScript } from "@/components/ai-chat/SemanticSnapshotScript"
import { LiveTradingAPI } from "@/lib/api/live"

interface LiveCandleChartProps {
  sessionId?: number
  symbol?: string
  timeframe?: string
}

interface Candle {
  time: number
  open: number
  high: number
  low: number
  close: number
  volume: number
}

interface MarketDataResponse {
    candles: Candle[]
    digits: number
}

export const LiveCandleChart = ({
  sessionId,
  symbol = "EURUSD",
  timeframe = "M5"
}: LiveCandleChartProps) => {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candlestickSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [latestCandles, setLatestCandles] = useState<Candle[]>([])
  const isMountedRef = useRef(true)

  // Fetch market data from API
  const fetchMarketData = useCallback(async () => {
    if (!sessionId) {
      return null
    }

    try {
      const data = await LiveTradingAPI.getMarketData(sessionId, symbol, timeframe, 500) as MarketDataResponse
      return data
    } catch (err) {
      console.error("[Chart] Error fetching market data:", err)
      if (isMountedRef.current) {
        setError(err instanceof Error ? err.message : "Failed to load chart data")
      }
      return null
    }
  }, [sessionId, symbol, timeframe])

  // Track mount state
  useEffect(() => {
    isMountedRef.current = true
    return () => {
      isMountedRef.current = false
    }
  }, [])

  useEffect(() => {
    if (!chartContainerRef.current || !sessionId) return

    let chart: IChartApi | null = null
    let resizeObserver: ResizeObserver | null = null
    let updateTimeout: NodeJS.Timeout | null = null
    let isCancelled = false

    const initChart = async () => {
      try {
        if (isCancelled) return

        if (!chartRef.current) {
            setIsLoading(true)
        }
        setError(null)

        if (!chartContainerRef.current) return

        // Create chart
        if (!chartRef.current) {
            chart = createChart(chartContainerRef.current, {
                layout: {
                    background: { type: ColorType.Solid, color: 'transparent' },
                    textColor: '#9ca3af', // gray-400
                },
                width: chartContainerRef.current.clientWidth,
                height: 400,
                grid: {
                    vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
                    horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
                },
                rightPriceScale: {
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                },
                timeScale: {
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    timeVisible: true,
                    secondsVisible: false,
                    rightOffset: 12,
                    visible: true,
                }
            })

            const candlestickSeries = chart.addSeries(CandlestickSeries, {
                upColor: '#10b981', // emerald-500
                downColor: '#ef4444', // red-500
                borderVisible: false,
                wickUpColor: '#10b981',
                wickDownColor: '#ef4444',
            })

            chartRef.current = chart
            candlestickSeriesRef.current = candlestickSeries
        } else {
            chart = chartRef.current
        }

        // Apply options
        chart.applyOptions({
            width: chartContainerRef.current.clientWidth,
             // height managed by resize observer mostly
        })

        // Fetch initial data
        const data = await fetchMarketData()

        if (isCancelled) return

        if (data && data.candles && data.candles.length > 0) {
          const sortedCandles = [...data.candles].sort((a, b) => (a.time as number) - (b.time as number))
          setLatestCandles(sortedCandles)
          if (candlestickSeriesRef.current) {
               candlestickSeriesRef.current.applyOptions({
                  priceFormat: {
                      type: 'price',
                      precision: data.digits,
                      minMove: 1 / Math.pow(10, data.digits),
                  },
              })

              candlestickSeriesRef.current.setData(sortedCandles.map(c => ({
                time: c.time as Time,
                open: c.open,
                high: c.high,
                low: c.low,
                close: c.close,
              })))
          }

          if (isMountedRef.current) {
            setIsLoading(false)
          }
        } else {
            if (isMountedRef.current) {
                // Don't show error immediately on empty Data, just stop loading
                setIsLoading(false)
            }
        }

        // Resize observer
        resizeObserver = new ResizeObserver(entries => {
          if (entries.length === 0 || entries[0].target !== chartContainerRef.current) return
          if (!chart) return
          const newRect = entries[0].contentRect
          chart.applyOptions({ width: newRect.width, height: newRect.height })
        })

        resizeObserver.observe(chartContainerRef.current)

        // Schedule updates
        const scheduleNextUpdate = () => {
          if (isCancelled) return

          const now = new Date()
          const msUntilNextMinute = (60 - now.getSeconds()) * 1000 - now.getMilliseconds() + 500 // +500ms safety

          updateTimeout = setTimeout(async () => {
            if (isCancelled) return
            const data = await fetchMarketData()

            if (data && data.candles && data.candles.length > 0) {
               const sortedCandles = [...data.candles].sort((a, b) => (a.time as number) - (b.time as number))
               setLatestCandles(sortedCandles)
               const latestCandle = sortedCandles[sortedCandles.length - 1]

               if (candlestickSeriesRef.current) {
                   candlestickSeriesRef.current.update({
                        time: latestCandle.time as Time,
                        open: latestCandle.open,
                        high: latestCandle.high,
                        low: latestCandle.low,
                        close: latestCandle.close,
                    })
               }
            }
            scheduleNextUpdate()
          }, msUntilNextMinute)
        }

        scheduleNextUpdate()

      } catch (err) {
        console.error("[Chart] Error initializing chart:", err)
        if (isMountedRef.current) {
            setError(err instanceof Error ? err.message : "Failed to initialize chart")
            setIsLoading(false)
        }
      }
    }

    initChart()

    return () => {
      isCancelled = true
      if (updateTimeout) clearTimeout(updateTimeout)
      if (resizeObserver) resizeObserver.disconnect()
      if (chart) {
        chart.remove()
        chartRef.current = null
        candlestickSeriesRef.current = null
      }
    }
  }, [sessionId, symbol, timeframe, fetchMarketData])

  if (!sessionId) {
    return (
      <div className="w-full h-full min-h-[400px] flex items-center justify-center text-muted-foreground bg-muted/10 rounded-lg border border-dashed border-muted">
        Select a session to view chart
      </div>
    )
  }

  const latestCandleSummary = latestCandles.length > 0
    ? (() => {
        const candle = latestCandles[latestCandles.length - 1]
        return `O=${candle.open} H=${candle.high} L=${candle.low} C=${candle.close}`
      })()
    : "N/A"

  return (
      <div className="w-full h-full relative group" style={{ minHeight: '400px' }}>
        <SemanticSnapshotScript
            block={{
                id: `live-candle:${sessionId || "none"}:${symbol}:${timeframe}`,
                blockType: "chart",
                title: `${symbol} ${timeframe} Live Candle Chart`,
                summary: `Live candlestick chart for ${symbol} on ${timeframe}.`,
                keywords: [symbol, timeframe, "live chart", "candles", "ohlc", "latest candle"],
                metrics: [
                    { label: "Session ID", value: sessionId ? String(sessionId) : "N/A" },
                    { label: "Loaded Candle Count", value: String(latestCandles.length) },
                    { label: "Latest Candle", value: latestCandleSummary },
                ],
                series: [
                    {
                        label: "OHLC",
                        points: latestCandles.slice(-160).map((candle) => ({
                            x: String(candle.time),
                            y: `O=${candle.open} H=${candle.high} L=${candle.low} C=${candle.close} V=${candle.volume}`,
                        })),
                    },
                ],
            }}
        />
        {error && (
            <div className="absolute inset-0 flex items-center justify-center flex-col bg-background/80 z-20 backdrop-blur-sm rounded-lg">
                <p className="text-destructive font-semibold">Error Loading Chart</p>
                <p className="text-sm text-muted-foreground mb-4">{error}</p>
                <button
                    onClick={() => { setError(null); setIsLoading(true); }}
                    className="px-4 py-2 bg-secondary rounded-md text-sm hover:bg-secondary/80 pointer-events-auto transition-colors"
                >
                    Retry
                </button>
            </div>
        )}

        {isLoading && (
            <div className="absolute inset-0 flex items-center justify-center bg-background/50 z-10 transition-opacity duration-300 backdrop-blur-[1px] rounded-lg">
                <div className="text-muted-foreground animate-pulse text-sm font-medium">Loading market data...</div>
            </div>
        )}

        <div ref={chartContainerRef} className="w-full h-full rounded-lg overflow-hidden" />
    </div>
  )
}
