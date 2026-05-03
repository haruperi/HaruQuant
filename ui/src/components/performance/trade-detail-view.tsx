/**
 * Trade Detail View Component
 *
 * Displays comprehensive trade details with interactive chart and statistics.
 * Features:
 * - Full backtest period OHLCV data loaded once and kept in memory
 * - Initial view shows 20-30 bars before/after current trade
 * - Prev/Next navigation dynamically expands context to show continuous bars between trades
 * - Chart data persists in memory (no re-fetching on navigation)
 * - Responsive design for mobile, tablet, and desktop
 * - Professional loading skeletons and error boundaries
 *
 * @module components/performance/trade-detail-view
 */

"use client"

import * as React from "react"
import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { ArrowLeft, ChevronLeft, ChevronRight } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { parseUtcDate } from "@/lib/utils"
import { tradesApi, Trade, ChartData } from "@/lib/api/trades"
import { TradeStatsSidebar } from "./trade-stats-sidebar"
import { TradeChart } from "./trade-chart"
import { TradeDetailSkeleton } from "./trade-detail-skeleton"

/**
 * Props for TradeDetailView component
 */
interface TradeDetailViewProps {
  /** The unique identifier of the trade to display */
  tradeId: number
}

/**
 * TradeDetailView Component
 *
 * Main container component for trade detail page. Manages data fetching,
 * state management, and navigation between trades.
 *
 * @component
 * @param {TradeDetailViewProps} props - Component props
 * @param {number} props.tradeId - The unique identifier of the trade to display
 *
 * @example
 * ```tsx
 * <TradeDetailView tradeId={12345} />
 * ```
 */
export function TradeDetailView({ tradeId }: TradeDetailViewProps) {
  const router = useRouter()

  // State
  const [currentTrade, setCurrentTrade] = useState<Trade | null>(null)
  const [allTrades, setAllTrades] = useState<Trade[]>([])
  const [fullChartData, setFullChartData] = useState<ChartData[]>([])
  const [currentTradeIndex, setCurrentTradeIndex] = useState<number>(0)
  const [visibleWindow, setVisibleWindow] = useState<{ start: number; end: number } | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [symbol, setSymbol] = useState<string>("")
  const [barDuration, setBarDuration] = useState<number>(3600) // Default: 1 hour in seconds

  /**
   * Calculate the visible time window for the chart
   *
   * @param {Trade} trade - The trade object
   * @param {number} barDurationSeconds - Duration of one bar in seconds
   * @param {Object} context - Context configuration
   * @param {number} context.before - Number of bars to show before trade entry
   * @param {number} context.after - Number of bars to show after trade exit
   * @returns {{ start: number; end: number }} Time window in Unix timestamps
   */
  const calculateVisibleWindow = (
    trade: Trade,
    barDurationSeconds: number,
    context: { before: number; after: number }
  ): { start: number; end: number } => {

    const openTime = parseUtcDate(trade.open_time)
    const closeTime = parseUtcDate(trade.close_time)

    return {
      start: openTime - context.before * barDurationSeconds,
      end: closeTime + context.after * barDurationSeconds,
    }
  }

  /**
   * Convert timeframe string to bar duration in seconds
   *
   * @param {string} timeframeStr - Timeframe string (e.g., "M1", "H1", "D1")
   * @returns {number} Duration in seconds (defaults to 3600 for H1 if unknown)
   */
  const getBarDuration = (timeframeStr: string): number => {
    const timeframeMap: Record<string, number> = {
      M1: 60,
      M5: 300,
      M15: 900,
      M30: 1800,
      H1: 3600,
      H4: 14400,
      D1: 86400,
      W1: 604800,
      MN1: 2592000,
    }
    return timeframeMap[timeframeStr.toUpperCase()] || 3600
  }

  // Fetch data on mount and when tradeId changes
  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true)
        setError(null)

        // Fetch trade and chart data in parallel
        const [tradeData, chartResponse] = await Promise.all([
          tradesApi.getTradeById(tradeId),
          tradesApi.getBacktestChartData(tradeId, 25, 25),
        ])

        // Set trade data
        setCurrentTrade(tradeData)

        // Set chart data
        setFullChartData(chartResponse.chart_data)
        setAllTrades(chartResponse.all_trades)
        setCurrentTradeIndex(chartResponse.current_trade_index)
        setSymbol(chartResponse.symbol)
        // Calculate bar duration
        const duration = getBarDuration(chartResponse.timeframe)
        setBarDuration(duration)

        // Calculate initial visible window (25 bars before/after)
        const initialWindow = calculateVisibleWindow(tradeData, duration, {
          before: 25,
          after: 25,
        })
        setVisibleWindow(initialWindow)
      } catch (err: unknown) {
        console.error("Error fetching trade data:", err)
        setError(err instanceof Error ? err.message : "Failed to load trade data")
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [tradeId])

  /**
   * Navigate to the previous trade in the backtest
   *
   * Expands the visible window to show continuous bars from the previous
   * trade's close time to the current trade's close time. Updates URL without scrolling.
   */
  const handlePrevTrade = () => {
    if (currentTradeIndex > 0 && currentTrade) {
      const prevTrade = allTrades[currentTradeIndex - 1]
      const prevTradeCloseTime = parseUtcDate(prevTrade.close_time)
      const currentTradeCloseTime = parseUtcDate(currentTrade.close_time)

      // Expand window to show continuous bars from prev trade close to current trade close
      setVisibleWindow({
        start: prevTradeCloseTime - 20 * barDuration,
        end: currentTradeCloseTime + 30 * barDuration,
      })

      setCurrentTradeIndex(currentTradeIndex - 1)
      setCurrentTrade(prevTrade)

      // Update URL without scrolling
      router.push(`/performance/trades-calender/${prevTrade.trade_id}`, { scroll: false })
    }
  }

  /**
   * Navigate to the next trade in the backtest
   *
   * Expands the visible window to show continuous bars from the current
   * trade's close time to the next trade's close time. Updates URL without scrolling.
   */
  const handleNextTrade = () => {
    if (currentTradeIndex < allTrades.length - 1 && currentTrade) {
      const nextTrade = allTrades[currentTradeIndex + 1]
      const currentTradeCloseTime = parseUtcDate(currentTrade.close_time)
      const nextTradeCloseTime = parseUtcDate(nextTrade.close_time)

      // Expand window to show continuous bars from current trade close to next trade close
      setVisibleWindow({
        start: currentTradeCloseTime - 20 * barDuration,
        end: nextTradeCloseTime + 30 * barDuration,
      })

      setCurrentTradeIndex(currentTradeIndex + 1)
      setCurrentTrade(nextTrade)

      // Update URL without scrolling
      router.push(`/performance/trades-calender/${nextTrade.trade_id}`, { scroll: false })
    }
  }

  /**
   * Navigate back to the trades calendar view
   */
  const handleBack = () => {
    router.push("/performance/trades-calender")
  }

  // Loading state
  if (loading) {
    return <TradeDetailSkeleton />
  }

  // Error state - Trade not found (404)
  if (error && error.includes("404")) {
    return (
      <div className="flex h-full w-full items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <p className="text-lg text-muted-foreground">Trade not found</p>
          <Button onClick={handleBack}>Return to Trades Calendar</Button>
        </div>
      </div>
    )
  }

  // Error state - MT5 unavailable or other errors
  if (error) {
    return (
      <div className="flex h-full w-full items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <p className="text-lg text-destructive">Failed to load trade data</p>
          <p className="text-sm text-muted-foreground">{error}</p>
          <div className="flex gap-2">
            <Button onClick={handleBack}>Return to Trades Calendar</Button>
            <Button variant="outline" onClick={() => window.location.reload()}>
              Retry
            </Button>
          </div>
        </div>
      </div>
    )
  }

  // No data state
  if (!currentTrade || !visibleWindow) {
    return (
      <div className="flex h-full w-full items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <p className="text-lg text-muted-foreground">No trade data available</p>
          <Button onClick={handleBack}>Return to Trades Calendar</Button>
        </div>
      </div>
    )
  }

  // Main render
  return (
    <div className="flex h-full w-full flex-col overflow-hidden">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between border-b bg-background px-4 sm:px-6 py-3 sm:py-4 gap-3 sm:gap-0">
        <div className="flex items-center gap-2 sm:gap-4 w-full sm:w-auto">
          <Button variant="ghost" size="sm" onClick={handleBack} className="gap-2">
            <ArrowLeft className="h-4 w-4" />
            <span className="hidden sm:inline">Back</span>
          </Button>
          <div className="flex items-center gap-2">
            <h1 className="text-base sm:text-xl font-semibold truncate">
              Trade #{currentTrade.trade_id} - {symbol}
            </h1>
          </div>
        </div>

        <TooltipProvider>
          <div className="flex items-center gap-2 w-full sm:w-auto justify-between sm:justify-end">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handlePrevTrade}
                  disabled={currentTradeIndex === 0}
                  className="gap-1 sm:gap-2"
                >
                  <ChevronLeft className="h-4 w-4" />
                  <span className="hidden sm:inline">Previous</span>
                  <span className="sm:hidden">Prev</span>
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>Previous Trade (expands context)</p>
              </TooltipContent>
            </Tooltip>
            <span className="text-xs sm:text-sm text-muted-foreground">
              {currentTradeIndex + 1} / {allTrades.length}
            </span>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleNextTrade}
                  disabled={currentTradeIndex === allTrades.length - 1}
                  className="gap-1 sm:gap-2"
                >
                  <span className="hidden sm:inline">Next</span>
                  <span className="sm:hidden">Nxt</span>
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>Next Trade (expands context)</p>
              </TooltipContent>
            </Tooltip>
          </div>
        </TooltipProvider>
      </div>

      {/* Main Content */}
      <div className="flex flex-1 overflow-hidden flex-col lg:flex-row">
        {/* Left Sidebar - Stats */}
        <div className="w-full lg:w-[30%] xl:w-[25%] overflow-y-auto border-b lg:border-b-0 lg:border-r bg-background max-h-[50vh] lg:max-h-none">
          <TradeStatsSidebar trade={currentTrade} onBack={handleBack} />
        </div>

        {/* Right Content - Chart */}
        <div className="flex-1 overflow-hidden bg-background p-3 sm:p-6">
          {fullChartData.length > 0 ? (
            <TradeChart
              fullChartData={fullChartData}
              currentTrade={currentTrade}
              visibleWindow={visibleWindow}
              allTrades={allTrades}
            />
          ) : (
            <div className="flex h-full items-center justify-center">
              <p className="text-muted-foreground">No chart data available</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
