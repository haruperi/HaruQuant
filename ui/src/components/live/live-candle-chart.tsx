"use client"

import { useEffect, useRef, useState, useCallback } from "react"
import { createChart, ColorType, CandlestickSeries, Time } from "lightweight-charts"
import { useAuth } from "@/lib/auth-context"

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
  const { authenticatedFetch } = useAuth()
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<any>(null)
  const candlestickSeriesRef = useRef<any>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const isMountedRef = useRef(true)

  // Fetch market data from API
  const fetchMarketData = useCallback(async () => {
    if (!sessionId) {
      return null
    }

    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"
      const url = `${baseUrl}/api/live/sessions/${sessionId}/market-data?symbol=${symbol}&timeframe=${timeframe}&count=500`

      const response = await authenticatedFetch(url)

      if (!response.ok) {
        throw new Error(`Failed to fetch market data: ${response.status}`)
      }

      const data = await response.json() as MarketDataResponse
      return data
    } catch (err) {
      console.error("[Chart] Error fetching market data:", err)
      if (isMountedRef.current) {
        setError(err instanceof Error ? err.message : "Failed to load chart data")
      }
      return null
    }
  }, [sessionId, symbol, timeframe, authenticatedFetch])

  // Track mount state
  useEffect(() => {
    isMountedRef.current = true
    return () => {
      isMountedRef.current = false
    }
  }, [])

  useEffect(() => {
    // If container is not available yet, we can't do anything.
    // Given the structure change, it SHOULD be available unless unmounted.
    if (!chartContainerRef.current || !sessionId) return

    let chart: any = null
    let resizeObserver: ResizeObserver | null = null
    let updateTimeout: NodeJS.Timeout | null = null
    let isCancelled = false

    const initChart = async () => {
      try {
        if (isCancelled) return

        // Only set loading if we don't have a chart yet (first load)
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
                    textColor: '#d1d5db', // Lighter gray for better visibility
                },
                width: chartContainerRef.current.clientWidth,
                height: 400,
                grid: {
                    vertLines: { color: 'rgba(255, 255, 255, 0.1)' },
                    horzLines: { color: 'rgba(255, 255, 255, 0.1)' },
                },
                rightPriceScale: {
                    borderColor: 'rgba(255, 255, 255, 0.2)',
                },
                timeScale: {
                    borderColor: 'rgba(255, 255, 255, 0.2)',
                    timeVisible: true,
                    secondsVisible: false,
                    rightOffset: 12,
                    visible: true,
                }
            })

            const candlestickSeries = chart.addSeries(CandlestickSeries, {
                upColor: '#10b981',
                downColor: '#ef4444',
                borderVisible: false,
                wickUpColor: '#10b981',
                wickDownColor: '#ef4444',
            })

            chartRef.current = chart
            candlestickSeriesRef.current = candlestickSeries
        } else {
            chart = chartRef.current
        }

        // Apply options unconditionally to ensure HMR and updates work
        chart.applyOptions({
            layout: {
                background: { type: ColorType.Solid, color: 'transparent' },
                textColor: '#d1d5db',
            },
            grid: {
                vertLines: { color: 'rgba(255, 255, 255, 0.1)' },
                horzLines: { color: 'rgba(255, 255, 255, 0.1)' },
            },
            rightPriceScale: {
                borderColor: 'rgba(255, 255, 255, 0.2)',
            },
            timeScale: {
                borderColor: 'rgba(255, 255, 255, 0.2)',
                timeVisible: true,
                secondsVisible: false,
                rightOffset: 12,
                visible: true,
            }
        })

        // Fetch initial data
        const data = await fetchMarketData()

        if (isCancelled) {
             // Cleanup handled by return function
            return
        }

        if (data && data.candles && data.candles.length > 0) {
          // Update series options with precision
          if (candlestickSeriesRef.current) {
               candlestickSeriesRef.current.applyOptions({
                  priceFormat: {
                      type: 'price',
                      precision: data.digits,
                      minMove: 1 / Math.pow(10, data.digits),
                  },
              })

              // Sort candles by time
              const sortedCandles = [...data.candles].sort((a, b) => (a.time as number) - (b.time as number))

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
                if (!error) setError("No data available")
                setIsLoading(false)
            }
        }

        // Resize observer
        resizeObserver = new ResizeObserver(entries => {
          if (entries.length === 0 || entries[0].target !== chartContainerRef.current) return
          if (!chart) return
          const newRect = entries[0].contentRect
          // Subtract 20px from height to ensure x-axis labels are not clipped by parent container
          chart.applyOptions({ width: newRect.width, height: newRect.height - 20 })
        })

        resizeObserver.observe(chartContainerRef.current)

        // Schedule updates
        const scheduleNextUpdate = () => {
          if (isCancelled) return

          const now = new Date()
          const msUntilNextMinute = (60 - now.getSeconds()) * 1000 - now.getMilliseconds()

          updateTimeout = setTimeout(async () => {
            if (isCancelled) return
            const data = await fetchMarketData()

            if (data && data.candles && data.candles.length > 0) {
               const sortedCandles = [...data.candles].sort((a, b) => (a.time as number) - (b.time as number))
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
      <div className="w-full h-full min-h-[400px] flex items-center justify-center text-muted-foreground">
        Select a session to view chart
      </div>
    )
  }

  return (
      <div className="w-full h-full relative" style={{ minHeight: '0' }}>
        {error && (
            <div className="absolute inset-0 flex items-center justify-center flex-col bg-background/80 z-20">
                <p className="text-destructive font-semibold">Error Loading Chart</p>
                <p className="text-sm text-muted-foreground">{error}</p>
                <button
                    onClick={() => { setError(null); setIsLoading(true); }}
                    className="mt-4 px-3 py-1 bg-secondary rounded text-xs hover:bg-secondary/80 pointer-events-auto"
                >
                    Retry
                </button>
            </div>
        )}

        {isLoading && (
            <div className="absolute inset-0 flex items-center justify-center bg-background/50 z-10 transition-opacity duration-300">
                <div className="text-muted-foreground animate-pulse">Loading chart...</div>
            </div>
        )}

        <div ref={chartContainerRef} className="w-full h-full min-h-[400px]" />
    </div>
  )
}
