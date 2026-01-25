"use client"

import { useEffect, useState } from "react"
import { format } from "date-fns"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Calendar } from "@/components/ui/calendar"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Loader2, FlaskConical, RefreshCcw, CalendarIcon, MoreVertical } from "lucide-react"
import {
  BarChart,
  Bar,
  CartesianGrid,
  Cell,
  Legend,
  ResponsiveContainer,
  Tooltip as ChartTooltip,
  XAxis,
  YAxis,
} from "recharts"
import { cn } from "@/lib/utils"
import {
  edgeLabApi,
  type EdgeLabDbTrade,
  type EdgeLabEdsType,
  type EdgeLabResult,
  type EdgeLabSummaryRow,
  type EdgeLabRunStats,
  type EdgeLabStats,
} from "@/lib/api/edge"

const verdictFromStats = (stats: EdgeLabStats) => {
  if (stats.n_trades < 30) return "INSUFFICIENT_DATA"
  if (stats.ci_low > 0 && stats.p_value_perm < 0.05) return "EDGE_CONFIRMED"
  if (stats.ci_low > 0) return "POTENTIAL_EDGE"
  if (stats.expectancy_r > 0) return "WEAK_SIGNAL"
  return "NO_EDGE"
}

const verdictTone = (verdict: string) => {
  if (verdict === "Strong Trend Persistence") return "bg-emerald-500/15 text-emerald-600"
  if (verdict === "Strong Mean Reversion") return "bg-emerald-500/15 text-emerald-600"
  if (verdict === "Weak Trend Persistence") return "bg-amber-500/15 text-amber-600"
  if (verdict === "Weak Mean Reversion") return "bg-amber-500/15 text-amber-600"
  if (verdict === "Mixed / Regime-Dependent") return "bg-blue-500/15 text-blue-600"
  if (verdict === "No Clear Edge") return "bg-slate-500/15 text-slate-600"
  if (verdict === "EDGE_CONFIRMED") return "bg-emerald-500/15 text-emerald-600"
  if (verdict === "POTENTIAL_EDGE") return "bg-blue-500/15 text-blue-600"
  if (verdict === "WEAK_SIGNAL") return "bg-amber-500/15 text-amber-600"
  if (verdict === "INSUFFICIENT_DATA") return "bg-slate-500/15 text-slate-600"
  return "bg-rose-500/15 text-rose-600"
}

const formatValue = (value: number | null | undefined, digits = 2) => {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "—"
  }
  return value.toFixed(digits)
}

const edgeColor = (expectancy: number | null | undefined, ciLow: number | null | undefined) => {
  if (expectancy === null || expectancy === undefined || Number.isNaN(expectancy)) {
    return "#cbd5e1"
  }
  if (expectancy <= 0) {
    return "#f87171"
  }
  if (ciLow !== null && ciLow !== undefined && ciLow > 0) {
    return "#34d399"
  }
  return "#cbd5e1"
}

const edgeOutline = (expectancy: number | null | undefined, ciLow: number | null | undefined) => {
  if (expectancy === null || expectancy === undefined || Number.isNaN(expectancy)) {
    return { stroke: "none", strokeWidth: 0 }
  }
  if (expectancy <= 0) {
    return { stroke: "none", strokeWidth: 0 }
  }
  if (ciLow !== null && ciLow !== undefined && ciLow > 0) {
    return { stroke: "#22c55e", strokeWidth: 2 }
  }
  return { stroke: "#94a3b8", strokeWidth: 1 }
}

const legendLabel = (value: string) => {
  const color = value === "MR" ? "#94a3b8" : "#fb7185"
  return <span style={{ color }}>{value}</span>
}

export default function EdgeLabPage() {
  const [symbol, setSymbol] = useState("EURUSD")
  const [timeframe, setTimeframe] = useState("M15")
  const [dataSource, setDataSource] = useState<"mt5" | "dukascopy">("mt5")
  const [rangeBy, setRangeBy] = useState<"dates" | "bars">("dates")
  const [startDate, setStartDate] = useState<Date | undefined>(
    new Date(new Date().setFullYear(new Date().getFullYear() - 1))
  )
  const [endDate, setEndDate] = useState<Date | undefined>(new Date())
  const [numberOfBars, setNumberOfBars] = useState("5000")
  const [eds, setEds] = useState("all")
  const [nBoot, setNBoot] = useState("2000")
  const [nPerm, setNPerm] = useState("2000")
  const [saveDb, setSaveDb] = useState(true)
  const [saveTrades, setSaveTrades] = useState(true)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [results, setResults] = useState<EdgeLabResult[]>([])
  const [summary, setSummary] = useState<{ total: number; confirmed: number } | null>(
    null
  )
  const [runs, setRuns] = useState<EdgeLabSummaryRow[]>([])
  const [loadingRuns, setLoadingRuns] = useState(false)
  const [selectedRun, setSelectedRun] = useState<EdgeLabSummaryRow | null>(null)
  const [selectedStats, setSelectedStats] = useState<EdgeLabRunStats | null>(null)
  const [selectedTrades, setSelectedTrades] = useState<EdgeLabDbTrade[]>([])
  const [loadingDetails, setLoadingDetails] = useState(false)
  const [runsSymbol, setRunsSymbol] = useState("")
  const [runsTimeframe, setRunsTimeframe] = useState("")
  const [runsVerdict, setRunsVerdict] = useState("")
  const [runsConfirmedOnly, setRunsConfirmedOnly] = useState(false)
  const [runsSortBy, setRunsSortBy] = useState("latest_created_at")
  const [runsSortDir, setRunsSortDir] = useState<"asc" | "desc">("desc")
  const [runsLimit, setRunsLimit] = useState(25)
  const [runsOffset, setRunsOffset] = useState(0)
  const [runsTotal, setRunsTotal] = useState(0)
  const [chartMetric, setChartMetric] = useState<"expectancy" | "total_r">("expectancy")

  const refreshRuns = async () => {
    setLoadingRuns(true)
    try {
      const response = await edgeLabApi.getSummary({
        symbol: runsSymbol.trim() || undefined,
        timeframe: runsTimeframe || undefined,
        verdict: runsVerdict || undefined,
        edge_confirmed_only: runsConfirmedOnly || undefined,
        sort_by: runsSortBy,
        sort_dir: runsSortDir,
        limit: runsLimit,
        offset: runsOffset,
      })
      setRuns(response.rows)
      setRunsTotal(response.total || 0)
    } catch (err) {
      console.error("Failed to load runs:", err)
    } finally {
      setLoadingRuns(false)
    }
  }

  const loadRunDetails = async (run: EdgeLabSummaryRow) => {
    if (!run.latest_run_id) {
      return
    }
    setSelectedRun(run)
    setLoadingDetails(true)
    try {
      const [stats, trades] = await Promise.all([
        edgeLabApi.getRunStats(run.latest_run_id),
        edgeLabApi.getRunTrades(run.latest_run_id),
      ])
      setSelectedStats(stats)
      setSelectedTrades(trades)
    } catch (err) {
      console.error("Failed to load run details:", err)
      setSelectedStats(null)
      setSelectedTrades([])
    } finally {
      setLoadingDetails(false)
    }
  }

  const handleDeleteRun = async (run: EdgeLabSummaryRow) => {
    if (!run.latest_run_id) {
      return
    }
    const confirmed = window.confirm(`Delete run #${run.latest_run_id}?`)
    if (!confirmed) return

    try {
      await edgeLabApi.deleteRun(run.latest_run_id)
      if (selectedRun?.latest_run_id === run.latest_run_id) {
        setSelectedRun(null)
        setSelectedStats(null)
        setSelectedTrades([])
      }
      await refreshRuns()
    } catch (err) {
      console.error("Failed to delete run:", err)
    }
  }

  useEffect(() => {
    refreshRuns()
  }, [
    runsSymbol,
    runsTimeframe,
    runsVerdict,
    runsConfirmedOnly,
    runsSortBy,
    runsSortDir,
    runsLimit,
    runsOffset,
  ])

  const runEdgeLab = async () => {
    setLoading(true)
    setError(null)
    setResults([])
    setSummary(null)

    try {
      const symbols = symbol
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean)

      const payload: any = {
        timeframe,
        data_source: dataSource,
        range_by: rangeBy,
        eds: eds as EdgeLabEdsType,
        n_boot: Number(nBoot) || 2000,
        n_perm: Number(nPerm) || 2000,
        save_db: saveDb,
        save_trades: saveTrades,
      }

      if (symbols.length > 1) {
        payload.symbols = symbols
      } else {
        payload.symbol = symbols[0] || symbol
      }

      if (rangeBy === "dates") {
        payload.start_date = startDate ? format(startDate, "yyyy-MM-dd") : undefined
        payload.end_date = endDate ? format(endDate, "yyyy-MM-dd") : undefined
      } else {
        payload.number_of_bars = Number(numberOfBars) || 5000
      }

      const response = await edgeLabApi.run(payload)
      setResults(response.results || [])
      setSummary({
        total: response.summary.total_results,
        confirmed: response.summary.edges_confirmed,
      })
      await refreshRuns()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run Edge Lab.")
    } finally {
      setLoading(false)
    }
  }

  const chartRows = runs
    .map((run) => {
      const mrVal =
        chartMetric === "expectancy" ? run.mr.expectancy_r ?? null : run.mr.total_r ?? null
      const boVal =
        chartMetric === "expectancy" ? run.bo.expectancy_r ?? null : run.bo.total_r ?? null
      return {
        key: `${run.symbol}-${run.timeframe}`,
        label: `${run.symbol} ${run.timeframe}`,
        mr: mrVal,
        bo: boVal,
        mr_expectancy: run.mr.expectancy_r ?? null,
        bo_expectancy: run.bo.expectancy_r ?? null,
        mr_ci_low: run.mr.ci_low ?? null,
        bo_ci_low: run.bo.ci_low ?? null,
        sortValue: (mrVal || 0) + (boVal || 0),
      }
    })
    .sort((a, b) => a.sortValue - b.sortValue)

  return (
    <div className="flex flex-col gap-6 p-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FlaskConical className="h-5 w-5 text-primary" />
            Run Edge Discovery
          </CardTitle>
          <CardDescription>Configure a quick run to validate edge hypotheses.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <Label htmlFor="symbol">Symbol</Label>
              <Input
                id="symbol"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                placeholder="EURUSD or EURUSD, GBPUSD"
              />
            </div>
            <div className="space-y-2">
              <Label>Timeframe</Label>
              <Select value={timeframe} onValueChange={setTimeframe}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="M1">M1</SelectItem>
                  <SelectItem value="M5">M5</SelectItem>
                  <SelectItem value="M15">M15</SelectItem>
                  <SelectItem value="M30">M30</SelectItem>
                  <SelectItem value="H1">H1</SelectItem>
                  <SelectItem value="H4">H4</SelectItem>
                  <SelectItem value="D1">D1</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Data Source</Label>
              <Select value={dataSource} onValueChange={(val) => setDataSource(val as any)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="mt5">MetaTrader 5</SelectItem>
                  <SelectItem value="dukascopy">Dukascopy</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <Label>Range By</Label>
              <Select value={rangeBy} onValueChange={(val) => setRangeBy(val as any)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="dates">Dates</SelectItem>
                  <SelectItem value="bars">Bars</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {rangeBy === "dates" ? (
              <>
                <div className="space-y-2 flex flex-col">
                  <Label>Start Date</Label>
                  <Popover>
                    <PopoverTrigger asChild>
                      <Button
                        variant="outline"
                        className={cn(
                          "w-full justify-start text-left font-normal",
                          !startDate && "text-muted-foreground"
                        )}
                      >
                        <CalendarIcon className="mr-2 h-4 w-4" />
                        {startDate ? format(startDate, "PPP") : <span>Pick a date</span>}
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-auto p-0" align="start">
                      <Calendar
                        mode="single"
                        selected={startDate}
                        onSelect={setStartDate}
                        initialFocus
                        captionLayout="dropdown"
                        fromYear={2000}
                        toYear={new Date().getFullYear() + 1}
                      />
                    </PopoverContent>
                  </Popover>
                </div>
                <div className="space-y-2 flex flex-col">
                  <Label>End Date</Label>
                  <Popover>
                    <PopoverTrigger asChild>
                      <Button
                        variant="outline"
                        className={cn(
                          "w-full justify-start text-left font-normal",
                          !endDate && "text-muted-foreground"
                        )}
                      >
                        <CalendarIcon className="mr-2 h-4 w-4" />
                        {endDate ? format(endDate, "PPP") : <span>Pick a date</span>}
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-auto p-0" align="start">
                      <Calendar
                        mode="single"
                        selected={endDate}
                        onSelect={setEndDate}
                        initialFocus
                        captionLayout="dropdown"
                        fromYear={2000}
                        toYear={new Date().getFullYear() + 1}
                      />
                    </PopoverContent>
                  </Popover>
                </div>
              </>
            ) : (
              <div className="space-y-2 md:col-span-2">
                <Label htmlFor="numberOfBars">Number of Bars</Label>
                <Input
                  id="numberOfBars"
                  type="number"
                  value={numberOfBars}
                  onChange={(e) => setNumberOfBars(e.target.value)}
                />
              </div>
            )}
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <Label>EDS Type</Label>
              <Select value={eds} onValueChange={setEds}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All</SelectItem>
                  <SelectItem value="null">EDS-0 Null</SelectItem>
                  <SelectItem value="mr">EDS-1 Mean Reversion</SelectItem>
                  <SelectItem value="tp">EDS-2 Trend Persistence</SelectItem>
                  <SelectItem value="session">EDS-3 Session Edge</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="nBoot">Bootstrap Iterations</Label>
              <Input
                id="nBoot"
                type="number"
                value={nBoot}
                onChange={(e) => setNBoot(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="nPerm">Permutation Iterations</Label>
              <Input
                id="nPerm"
                type="number"
                value={nPerm}
                onChange={(e) => setNPerm(e.target.value)}
              />
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <div className="flex items-center justify-between rounded-lg border p-3">
              <div>
                <Label>Save To Database</Label>
                <p className="text-xs text-muted-foreground">Store run and stats.</p>
              </div>
              <Switch checked={saveDb} onCheckedChange={setSaveDb} />
            </div>
            <div className="flex items-center justify-between rounded-lg border p-3">
              <div>
                <Label>Save Trades</Label>
                <p className="text-xs text-muted-foreground">Trade-level records.</p>
              </div>
              <Switch checked={saveTrades} onCheckedChange={setSaveTrades} />
            </div>
            <div className="flex items-center justify-between rounded-lg border p-3">
              <div>
                <Label>Refresh History</Label>
                <p className="text-xs text-muted-foreground">Reload saved runs.</p>
              </div>
              <Button variant="outline" size="sm" onClick={refreshRuns} disabled={loadingRuns}>
                <RefreshCcw className={cn("h-4 w-4", loadingRuns && "animate-spin")} />
              </Button>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Button onClick={runEdgeLab} disabled={loading || !symbol.trim()}>
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Run Edge Lab
            </Button>
            {error && <p className="text-sm text-destructive">{error}</p>}
          </div>
        </CardContent>
      </Card>

      {summary && (
        <Card>
          <CardHeader>
            <CardTitle>Run Summary</CardTitle>
            <CardDescription>
              {summary.total} results, {summary.confirmed} confirmed edges.
            </CardDescription>
          </CardHeader>
        </Card>
      )}

      {results.length > 0 && (
        <div className="grid gap-4 lg:grid-cols-2">
          {results.map((result) => {
            const verdict = verdictFromStats(result.stats)
            return (
              <Card key={`${result.symbol}-${result.eds_name}-${result.timestamp}`}>
                <CardHeader>
                  <CardTitle className="flex items-center justify-between gap-2">
                    <span>
                      {result.symbol} {result.timeframe}
                    </span>
                    <Badge className={verdictTone(verdict)}>{verdict}</Badge>
                  </CardTitle>
                  <CardDescription>{result.eds_name}</CardDescription>
                </CardHeader>
                <CardContent className="grid gap-2 text-sm">
                  <div className="flex items-center justify-between">
                    <span>Trades</span>
                    <span className="font-mono">{result.stats.n_trades}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Expectancy (R)</span>
                    <span className="font-mono">
                      {(result.stats.expectancy_r ?? 0).toFixed(4)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Win Rate</span>
                    <span className="font-mono">
                      {(((result.stats.win_rate ?? 0) * 100) || 0).toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Profit Factor</span>
                    <span className="font-mono">
                      {(result.stats.profit_factor ?? 0).toFixed(2)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>CI (Low/High)</span>
                    <span className="font-mono">
                      {(result.stats.ci_low ?? 0).toFixed(4)} / {(result.stats.ci_high ?? 0).toFixed(4)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Permutation p</span>
                    <span className="font-mono">
                      {(result.stats.p_value_perm ?? 0).toFixed(4)}
                    </span>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Saved Runs</CardTitle>
          <CardDescription>Recent edge discovery runs stored in the database.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-7 pb-4">
            <div className="space-y-1 md:col-span-2">
              <Label htmlFor="runsSymbol">Symbol</Label>
              <Input
                id="runsSymbol"
                value={runsSymbol}
                onChange={(e) => {
                  setRunsSymbol(e.target.value.toUpperCase())
                  setRunsOffset(0)
                }}
                placeholder="EURUSD"
              />
            </div>
            <div className="space-y-1">
              <Label>Timeframe</Label>
              <Select
                value={runsTimeframe || "all"}
                onValueChange={(val) => {
                  setRunsTimeframe(val === "all" ? "" : val)
                  setRunsOffset(0)
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Any" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Any</SelectItem>
                  <SelectItem value="M1">M1</SelectItem>
                  <SelectItem value="M5">M5</SelectItem>
                  <SelectItem value="M15">M15</SelectItem>
                  <SelectItem value="M30">M30</SelectItem>
                  <SelectItem value="H1">H1</SelectItem>
                  <SelectItem value="H4">H4</SelectItem>
                  <SelectItem value="D1">D1</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label>Verdict</Label>
              <Select
                value={runsVerdict || "all"}
                onValueChange={(val) => {
                  setRunsVerdict(val === "all" ? "" : val)
                  setRunsOffset(0)
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Any" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Any</SelectItem>
                  <SelectItem value="Strong Trend Persistence">
                    Strong Trend Persistence
                  </SelectItem>
                  <SelectItem value="Weak Trend Persistence">
                    Weak Trend Persistence
                  </SelectItem>
                  <SelectItem value="Strong Mean Reversion">
                    Strong Mean Reversion
                  </SelectItem>
                  <SelectItem value="Weak Mean Reversion">
                    Weak Mean Reversion
                  </SelectItem>
                  <SelectItem value="Mixed / Regime-Dependent">
                    Mixed / Regime-Dependent
                  </SelectItem>
                  <SelectItem value="No Clear Edge">No Clear Edge</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label>Sort By</Label>
              <Select
                value={runsSortBy}
                onValueChange={(val) => {
                  setRunsSortBy(val)
                  setRunsOffset(0)
                }}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="latest_created_at">Latest Run</SelectItem>
                  <SelectItem value="symbol">Symbol</SelectItem>
                  <SelectItem value="verdict">Verdict</SelectItem>
                  <SelectItem value="mr_expectancy">MR Exp (R)</SelectItem>
                  <SelectItem value="bo_expectancy">BO Exp (R)</SelectItem>
                  <SelectItem value="confidence">Confidence</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center justify-between rounded-lg border p-3">
              <div>
                <Label>Confirmed Only</Label>
                <p className="text-xs text-muted-foreground">Edge confirmed</p>
              </div>
              <Switch
                checked={runsConfirmedOnly}
                onCheckedChange={(val) => {
                  setRunsConfirmedOnly(val)
                  setRunsOffset(0)
                }}
              />
            </div>
            <div className="flex items-center justify-between rounded-lg border p-3">
              <div>
                <Label>Sort Dir</Label>
                <p className="text-xs text-muted-foreground">Asc/Desc</p>
              </div>
              <Select
                value={runsSortDir}
                onValueChange={(val) => {
                  setRunsSortDir(val as "asc" | "desc")
                  setRunsOffset(0)
                }}
              >
                <SelectTrigger className="w-24">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="desc">Desc</SelectItem>
                  <SelectItem value="asc">Asc</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center justify-between rounded-lg border p-3">
              <div>
                <Label>Clear Filters</Label>
                <p className="text-xs text-muted-foreground">Reset search</p>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setRunsSymbol("")
                  setRunsTimeframe("")
                  setRunsVerdict("")
                  setRunsConfirmedOnly(false)
                  setRunsSortBy("latest_created_at")
                  setRunsSortDir("desc")
                  setRunsOffset(0)
                }}
              >
                Clear
              </Button>
            </div>
          </div>

          {loadingRuns ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading runs...
            </div>
          ) : runs.length === 0 ? (
            <div className="text-sm text-muted-foreground">No saved runs yet.</div>
          ) : (
            <div className="overflow-x-auto">
              <Table className="min-w-[1400px]">
                <TableHeader className="sticky top-0 z-10 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
                  <TableRow>
                  <TableHead className="whitespace-nowrap">Symbol</TableHead>
                  <TableHead className="text-right whitespace-nowrap">MR Exp (R)</TableHead>
                  <TableHead className="text-right whitespace-nowrap">MR Total R</TableHead>
                  <TableHead className="text-right whitespace-nowrap">MR CI Low</TableHead>
                  <TableHead className="text-right whitespace-nowrap">MR p-val</TableHead>
                  <TableHead className="text-right whitespace-nowrap">MR Trades</TableHead>
                  <TableHead className="text-right whitespace-nowrap">BO Exp (R)</TableHead>
                  <TableHead className="text-right whitespace-nowrap">BO Total R</TableHead>
                  <TableHead className="text-right whitespace-nowrap">BO CI Low</TableHead>
                  <TableHead className="text-right whitespace-nowrap">BO p-val</TableHead>
                  <TableHead className="text-right whitespace-nowrap">BO Trades</TableHead>
                  <TableHead className="whitespace-nowrap">Verdict</TableHead>
                  <TableHead className="text-right whitespace-nowrap">Confidence</TableHead>
                  <TableHead className="text-right whitespace-nowrap">Robustness</TableHead>
                  <TableHead className="whitespace-nowrap">Range</TableHead>
                  <TableHead className="text-center whitespace-nowrap">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {runs.map((run) => (
                    <TableRow key={`${run.symbol}-${run.timeframe}`}>
                    <TableCell className="font-medium whitespace-nowrap">
                      {run.symbol} {run.timeframe}
                    </TableCell>
                    <TableCell className="text-right">
                      {formatValue(run.mr.expectancy_r, 2)}
                    </TableCell>
                    <TableCell className="text-right">{formatValue(run.mr.total_r, 2)}</TableCell>
                    <TableCell className="text-right">{formatValue(run.mr.ci_low, 2)}</TableCell>
                    <TableCell className="text-right">{formatValue(run.mr.p_value_perm, 3)}</TableCell>
                    <TableCell className="text-right">{run.mr.n_trades ?? "—"}</TableCell>
                    <TableCell className="text-right">{formatValue(run.bo.expectancy_r, 2)}</TableCell>
                    <TableCell className="text-right">{formatValue(run.bo.total_r, 2)}</TableCell>
                    <TableCell className="text-right">{formatValue(run.bo.ci_low, 2)}</TableCell>
                    <TableCell className="text-right">{formatValue(run.bo.p_value_perm, 3)}</TableCell>
                    <TableCell className="text-right">{run.bo.n_trades ?? "—"}</TableCell>
                    <TableCell>
                      {run.verdict ? (
                        <Badge className={verdictTone(run.verdict)}>{run.verdict}</Badge>
                      ) : (
                        "—"
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      {run.confidence !== undefined ? (
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <span className="underline decoration-dotted cursor-help">
                              {run.confidence}
                            </span>
                          </TooltipTrigger>
                          <TooltipContent side="top">
                            <div className="space-y-1">
                              <div>
                                Robustness: {run.robustness ?? 0}
                              </div>
                              <div>
                                Bonus: {run.score_breakdown?.bonus ?? 0}
                              </div>
                            </div>
                          </TooltipContent>
                        </Tooltip>
                      ) : (
                        "—"
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      {run.robustness !== undefined ? (
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <span className="underline decoration-dotted cursor-help">
                              {run.robustness}
                            </span>
                          </TooltipTrigger>
                          <TooltipContent side="top">
                            <div className="space-y-1">
                              <div>
                                Trade Score: {run.score_breakdown?.trade_score ?? 0}
                              </div>
                              <div>
                                CI Score: {run.score_breakdown?.ci_score ?? 0}
                              </div>
                              <div>
                                Exp Score: {run.score_breakdown?.exp_score ?? 0}
                              </div>
                            </div>
                          </TooltipContent>
                        </Tooltip>
                      ) : (
                        "—"
                      )}
                    </TableCell>
                    <TableCell className="whitespace-nowrap">{run.range || "—"}</TableCell>
                    <TableCell className="text-center">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon">
                            <MoreVertical className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem
                            onClick={() => loadRunDetails(run)}
                            disabled={!run.latest_run_id}
                          >
                            View Latest
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            onClick={() => {
                              if (run.mr.run_id) {
                                loadRunDetails({ ...run, latest_run_id: run.mr.run_id })
                              }
                            }}
                            disabled={!run.mr.run_id}
                          >
                            View MR
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            onClick={() => {
                              if (run.bo.run_id) {
                                loadRunDetails({ ...run, latest_run_id: run.bo.run_id })
                              }
                            }}
                            disabled={!run.bo.run_id}
                          >
                            View BO
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            onClick={() => handleDeleteRun(run)}
                            disabled={!run.latest_run_id}
                            className="text-destructive focus:text-destructive"
                          >
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
              </Table>
            </div>
          )}

          <div className="flex items-center justify-between pt-4">
            <div className="flex items-center gap-2">
              <Label>Rows</Label>
              <Select
                value={runsLimit.toString()}
                onValueChange={(val) => {
                  setRunsLimit(parseInt(val, 10))
                  setRunsOffset(0)
                }}
              >
                <SelectTrigger className="w-24">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="10">10</SelectItem>
                  <SelectItem value="25">25</SelectItem>
                  <SelectItem value="50">50</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setRunsOffset(Math.max(0, runsOffset - runsLimit))}
                disabled={runsOffset === 0 || loadingRuns}
              >
                Previous
              </Button>
              <div className="text-sm text-muted-foreground">
                {runsTotal === 0
                  ? "0 - 0"
                  : `${runsOffset + 1} - ${runsOffset + runs.length} of ${runsTotal}`}
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setRunsOffset(runsOffset + runsLimit)}
                disabled={runsOffset + runs.length >= runsTotal || loadingRuns}
              >
                Next
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Run Details</CardTitle>
          <CardDescription>Stats and trade-level breakdown.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {!selectedRun ? (
            <div className="text-sm text-muted-foreground">Select a run to view details.</div>
          ) : (
            <>
              <div className="grid gap-4 md:grid-cols-3 text-sm">
                <div>
                  <div className="text-muted-foreground">Run</div>
                  <div className="font-mono">
                    {selectedRun.latest_run_id ? `#${selectedRun.latest_run_id}` : "—"}
                  </div>
                </div>
                <div>
                  <div className="text-muted-foreground">Symbol</div>
                  <div>{selectedRun.symbol}</div>
                </div>
                <div>
                  <div className="text-muted-foreground">Timeframe</div>
                  <div>{selectedRun.timeframe}</div>
                </div>
                <div>
                  <div className="text-muted-foreground">Verdict</div>
                  {selectedRun.verdict ? (
                    <Badge className={verdictTone(selectedRun.verdict)}>
                      {selectedRun.verdict}
                    </Badge>
                  ) : (
                    "—"
                  )}
                </div>
                <div>
                  <div className="text-muted-foreground">Range</div>
                  <div>{selectedRun.range || "—"}</div>
                </div>
                <div>
                  <div className="text-muted-foreground">Trades</div>
                  <div>{selectedStats?.n_trades ?? "—"}</div>
                </div>
              </div>

              {loadingDetails ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Loading details...
                </div>
              ) : (
                <>
                  {selectedStats && (
                    <div className="grid gap-4 md:grid-cols-3 text-sm">
                      <div>
                        <div className="text-muted-foreground">Expectancy (R)</div>
                        <div className="font-mono">
                          {(selectedStats.expectancy_r ?? 0).toFixed(4)}
                        </div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">Win Rate</div>
                        <div className="font-mono">
                          {(((selectedStats.win_rate ?? 0) * 100) || 0).toFixed(1)}%
                        </div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">Profit Factor</div>
                        <div className="font-mono">
                          {(selectedStats.profit_factor ?? 0).toFixed(2)}
                        </div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">CI Low</div>
                        <div className="font-mono">
                          {(selectedStats.ci_low ?? 0).toFixed(4)}
                        </div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">CI High</div>
                        <div className="font-mono">
                          {(selectedStats.ci_high ?? 0).toFixed(4)}
                        </div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">Permutation p</div>
                        <div className="font-mono">
                          {(selectedStats.p_value_perm ?? 0).toFixed(4)}
                        </div>
                      </div>
                    </div>
                  )}

                  <div className="border rounded-lg overflow-hidden">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Entry</TableHead>
                          <TableHead>Exit</TableHead>
                          <TableHead>Side</TableHead>
                          <TableHead>R</TableHead>
                          <TableHead>MAE</TableHead>
                          <TableHead>MFE</TableHead>
                          <TableHead>Hold</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {selectedTrades.length === 0 ? (
                          <TableRow>
                            <TableCell colSpan={7} className="text-sm text-muted-foreground">
                              No trades stored for this run.
                            </TableCell>
                          </TableRow>
                        ) : (
                          selectedTrades.map((trade) => (
                            <TableRow key={trade.trade_id}>
                              <TableCell>{trade.entry_time}</TableCell>
                              <TableCell>{trade.exit_time}</TableCell>
                              <TableCell>{trade.side}</TableCell>
                              <TableCell className="font-mono">
                                {trade.r_multiple.toFixed(2)}
                              </TableCell>
                              <TableCell className="font-mono">
                                {trade.mae_r.toFixed(2)}
                              </TableCell>
                              <TableCell className="font-mono">
                                {trade.mfe_r.toFixed(2)}
                              </TableCell>
                              <TableCell className="font-mono">{trade.hold_bars}</TableCell>
                            </TableRow>
                          ))
                        )}
                      </TableBody>
                    </Table>
                  </div>
                </>
              )}
            </>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Edge Expectancy Chart</CardTitle>
          <CardDescription>
            Bars show MR and BO values sorted by combined total.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2 pb-4">
            <Label>Metric</Label>
            <Select
              value={chartMetric}
              onValueChange={(val) => setChartMetric(val as "expectancy" | "total_r")}
            >
              <SelectTrigger className="w-44">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="expectancy">Expectancy (R)</SelectItem>
                <SelectItem value="total_r">Total R</SelectItem>
              </SelectContent>
            </Select>
          </div>
          {chartRows.length === 0 ? (
            <div className="text-sm text-muted-foreground">No summary data to chart yet.</div>
          ) : (
            <div className="h-[360px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={chartRows}
                  margin={{ top: 10, right: 20, left: 0, bottom: 60 }}
                >
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis
                    dataKey="label"
                    angle={-45}
                    textAnchor="end"
                    height={70}
                    interval={0}
                  />
                  <YAxis />
                  <ChartTooltip
                    formatter={(value: any, name: string) => [
                      typeof value === "number" ? value.toFixed(3) : "—",
                      name.toUpperCase(),
                    ]}
                  />
                  <Legend formatter={legendLabel} />
                  <Bar dataKey="mr" name="MR" barSize={10} fill="#60a5fa">
                    {chartRows.map((row, idx) => (
                      <Cell
                        key={`mr-${row.key}-${idx}`}
                        fill="#60a5fa"
                        {...edgeOutline(row.mr_expectancy, row.mr_ci_low)}
                      />
                    ))}
                  </Bar>
                  <Bar dataKey="bo" name="BO" barSize={10} fill="#f97316">
                    {chartRows.map((row, idx) => (
                      <Cell
                        key={`bo-${row.key}-${idx}`}
                        fill="#f97316"
                        {...edgeOutline(row.bo_expectancy, row.bo_ci_low)}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
          <div className="text-xs text-muted-foreground pt-3">
            Green: CI low &gt; 0. Gray: CI overlaps 0. Red: negative expectancy.
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
