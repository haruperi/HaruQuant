"use client"

import { useState, useEffect, useMemo, useRef } from "react"
import { useParams, useRouter } from "next/navigation"
import { DataHighstockChart } from "@/components/data/data-highstock-chart"
import { useMarketData } from "@/contexts/market-data-context"
import { SymbolSelector } from "@/components/dashboard/symbol-selector"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Search, Loader2, Download } from "lucide-react"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import type { TradeLike } from "@/lib/api/strategies"

type RangeMode = "bars" | "dates"

interface TradesChartOverlay {
  backtest_id?: number
  symbol?: string | null
  timeframe?: string | null
  start_date?: string | null
  end_date?: string | null
  trades?: TradeLike[]
}

export default function DataPageContent() {
  const { dataset, loading, loadDataset } = useMarketData()
  const router = useRouter()
  const params = useParams()
  const slug = params?.slug as string[] | undefined

  // Parse initial values from slug if present
  const initialSymbol = slug?.[0] || ""
  const initialTimeframe = slug?.[1] || "H1"
  const initialMode = (slug?.[2] === "dates" ? "dates" : "bars") as RangeMode
  const initialBars = initialMode === "bars" && slug?.[3] ? slug[3] : "1000"
  const initialStart = initialMode === "dates" && slug?.[3] ? slug[3] : ""
  const initialEnd = initialMode === "dates" && slug?.[4] ? slug[4] : ""
  const showTradesChart = slug?.includes("trades-charts") ?? false

  const [selectorOpen, setSelectorOpen] = useState(false)
  const [timeframe, setTimeframe] = useState(initialTimeframe)

  // Range controls
  const [rangeMode, setRangeMode] = useState<RangeMode>(initialMode)
  const [numBars, setNumBars] = useState(initialBars)
  const [startDate, setStartDate] = useState(initialStart === "null" ? "" : initialStart)
  const [endDate, setEndDate] = useState(initialEnd === "null" ? "" : initialEnd)

  const hasInitialLoadFired = useRef(false)

  const tradesOverlay = useMemo(() => {
    if (!showTradesChart || typeof window === "undefined") return null
    const raw = window.sessionStorage.getItem("haruquant:trades-chart-overlay")
    if (!raw) return null

    try {
      const overlay = JSON.parse(raw) as TradesChartOverlay
      const matchesSymbol = !overlay.symbol || !initialSymbol || overlay.symbol === initialSymbol
      const matchesTimeframe = !overlay.timeframe || !initialTimeframe || overlay.timeframe === initialTimeframe
      if (matchesSymbol && matchesTimeframe) {
        return overlay
      }
    } catch {
      return null
    }
    return null
  }, [showTradesChart, initialSymbol, initialTimeframe])

  // Build the payload
  const buildPayload = (symbol: string, tf: string, mode: RangeMode, bars: string, start: string, end: string) => {
    if (mode === "bars") {
      return {
        symbol,
        timeframe: tf,
        data_source: "mt5" as const,
        range_by: "bars" as const,
        number_of_bars: Math.max(1, parseInt(bars) || 1000),
      }
    }
    return {
      symbol,
      timeframe: tf,
      data_source: "mt5" as const,
      range_by: "dates" as const,
      ...(start && start !== "null" && { start_date: start }),
      ...(end && end !== "null" && { end_date: end }),
    }
  }

  // Auto load if slug exists
  useEffect(() => {
    if (slug && slug.length >= 4 && !hasInitialLoadFired.current) {
      hasInitialLoadFired.current = true
      void loadDataset(buildPayload(initialSymbol, initialTimeframe, initialMode, initialBars, initialStart, initialEnd))
    }
  }, [slug, loadDataset, initialSymbol, initialTimeframe, initialMode, initialBars, initialStart, initialEnd])

  const updateUrl = (symbol: string, tf: string, mode: RangeMode, bars: string, start: string, end: string) => {
    const suffix = showTradesChart ? "/trades-charts" : ""
    if (mode === "bars") {
      router.push(`/data/${symbol}/${tf}/bars/${bars}${suffix}`)
    } else {
      router.push(`/data/${symbol}/${tf}/dates/${start || "null"}/${end || "null"}${suffix}`)
    }
  }

  const handleSymbolSelect = (newSymbol: string) => {
    void loadDataset(buildPayload(newSymbol, timeframe, rangeMode, numBars, startDate, endDate))
    updateUrl(newSymbol, timeframe, rangeMode, numBars, startDate, endDate)
  }

  const handleTimeframeChange = (newTimeframe: string) => {
    setTimeframe(newTimeframe)
    const symbol = dataset?.request.symbol || initialSymbol
    if (symbol) {
      void loadDataset(buildPayload(symbol, newTimeframe, rangeMode, numBars, startDate, endDate))
      updateUrl(symbol, newTimeframe, rangeMode, numBars, startDate, endDate)
    }
  }

  const handleDownload = () => {
    const symbol = dataset?.request.symbol || initialSymbol
    if (!symbol) return
    void loadDataset(buildPayload(symbol, timeframe, rangeMode, numBars, startDate, endDate))
    updateUrl(symbol, timeframe, rangeMode, numBars, startDate, endDate)
  }


  return (
    <div className="flex h-full flex-col gap-4 p-4">
      <div className="flex items-center justify-between rounded-2xl border border-slate-800 bg-[#0c121e] p-4 shadow-xl">
        <div className="flex items-center gap-3 flex-wrap">

          {/* Symbol picker */}
          <Button
            variant="outline"
            onClick={() => setSelectorOpen(true)}
            className="border-slate-700 bg-slate-800/50 text-slate-100 hover:bg-slate-800"
          >
            <Search className="mr-2 h-4 w-4" />
            {dataset ? dataset.request.symbol : "Select Symbol"}
          </Button>

          {/* Timeframe */}
          <Select value={timeframe} onValueChange={handleTimeframeChange}>
            <SelectTrigger className="w-[90px] border-slate-700 bg-slate-800/50 text-slate-100">
              <SelectValue placeholder="Timeframe" />
            </SelectTrigger>
            <SelectContent className="border-slate-800 bg-slate-900 text-slate-100">
              {["M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1"].map((tf) => (
                <SelectItem key={tf} value={tf}>{tf}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Divider */}
          <div className="h-6 w-px bg-slate-700" />

          {/* Range mode selector */}
          <Select value={rangeMode} onValueChange={(v) => setRangeMode(v as RangeMode)}>
            <SelectTrigger className="w-[90px] border-slate-700 bg-slate-800/50 text-slate-100">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="border-slate-800 bg-slate-900 text-slate-100">
              <SelectItem value="bars">Bars</SelectItem>
              <SelectItem value="dates">Dates</SelectItem>
            </SelectContent>
          </Select>

          {/* Conditional: bars input OR date pickers */}
          {rangeMode === "bars" ? (
            <Input
              id="num-bars-input"
              type="number"
              min={1}
              value={numBars}
              onChange={(e) => setNumBars(e.target.value)}
              className="w-[110px] border-slate-700 bg-slate-800/50 text-slate-100 placeholder:text-slate-500"
              placeholder="e.g. 1000"
            />
          ) : (
            <div className="flex items-center gap-2">
              <Input
                id="start-date-input"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-[150px] border-slate-700 bg-slate-800/50 text-slate-100 [color-scheme:dark]"
                placeholder="Start date"
              />
              <span className="text-slate-500 text-sm">→</span>
              <Input
                id="end-date-input"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-[150px] border-slate-700 bg-slate-800/50 text-slate-100 [color-scheme:dark]"
                placeholder="End date"
              />
            </div>
          )}

          {/* Download / refresh button */}
          <Button
            id="download-data-btn"
            size="sm"
            onClick={handleDownload}
            disabled={!dataset || loading}
            className="bg-indigo-600 hover:bg-indigo-500 text-white border-0"
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Download className="h-4 w-4" />
            )}
          </Button>

          {/* Info badges */}
          {dataset && (
            <div className="flex items-center gap-2">
              <Badge variant="secondary" className="bg-slate-800 text-slate-400">
                {dataset.meta.n_rows.toLocaleString()} Bars
              </Badge>
              <Badge variant="secondary" className="bg-slate-800 text-slate-400">
                {dataset.request.data_source.toUpperCase()}
              </Badge>
            </div>
          )}
        </div>

        {loading && (
          <div className="flex items-center gap-2 text-sm text-slate-400">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading Data...
          </div>
        )}
      </div>

      <div className="flex-1 min-h-0 relative overflow-hidden rounded-2xl border border-slate-800 bg-[#070b14] shadow-2xl">
        {dataset ? (
          <DataHighstockChart
            className="h-full w-full"
            symbol={dataset.request.symbol}
            timeframe={dataset.request.timeframe}
            rows={dataset.rows}
            schema={dataset.schema}
            trades={showTradesChart ? tradesOverlay?.trades : undefined}
          />
        ) : (
          <div className="flex h-full flex-col items-center justify-center text-slate-500">
            <Search className="mb-4 h-12 w-12 opacity-20" />
            <p className="text-lg font-medium">No dataset loaded</p>
            <p className="text-sm">Select a symbol to start visualizing market data</p>
            <Button
              variant="link"
              onClick={() => setSelectorOpen(true)}
              className="mt-2 text-indigo-400"
            >
              Open Symbol Selector
            </Button>
          </div>
        )}
      </div>

      <SymbolSelector
        open={selectorOpen}
        onOpenChange={setSelectorOpen}
        onSelect={handleSymbolSelect}
        currentSymbol={dataset?.request.symbol}
      />
    </div>
  )
}
