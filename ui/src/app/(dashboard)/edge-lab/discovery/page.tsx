"use client"

import { useEffect, useState } from "react"
import { FlaskConical, Loader2, MoreVertical, RefreshCcw } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import {
  edgeLabApi,
  type EdgeLabDbTrade,
  type EdgeLabEdsType,
  type EdgeLabResult,
  type EdgeLabRunStats,
  type EdgeLabStats,
  type EdgeLabSummaryRow,
} from "@/lib/api/edge"
import { cn } from "@/lib/utils"
import { useEdgeLabData } from "@/contexts/edge-lab-data-context"

const verdictFromStats = (stats: EdgeLabStats) => {
  if (stats.n_trades < 30) return "INSUFFICIENT_DATA"
  if (stats.ci_low > 0 && stats.p_value_perm < 0.05) return "EDGE_CONFIRMED"
  if (stats.ci_low > 0) return "POTENTIAL_EDGE"
  if (stats.expectancy_r > 0) return "WEAK_SIGNAL"
  return "NO_EDGE"
}

const verdictTone = (verdict: string) => {
  if (verdict === "EDGE_CONFIRMED") return "bg-emerald-500/15 text-emerald-600"
  if (verdict === "POTENTIAL_EDGE") return "bg-blue-500/15 text-blue-600"
  if (verdict === "WEAK_SIGNAL") return "bg-amber-500/15 text-amber-600"
  if (verdict === "INSUFFICIENT_DATA") return "bg-slate-500/15 text-slate-600"
  return "bg-rose-500/15 text-rose-600"
}

const formatValue = (value: number | null | undefined, digits = 2) => {
  if (value === null || value === undefined || Number.isNaN(value)) return "—"
  return value.toFixed(digits)
}

export default function EdgeLabDiscoveryPage() {
  const { dataset } = useEdgeLabData()
  const [eds, setEds] = useState<EdgeLabEdsType>("all")
  const [nBoot, setNBoot] = useState("2000")
  const [nPerm, setNPerm] = useState("2000")
  const [saveDb, setSaveDb] = useState(true)
  const [saveTrades, setSaveTrades] = useState(true)
  const [loading, setLoading] = useState(false)
  const [loadingRuns, setLoadingRuns] = useState(false)
  const [loadingDetails, setLoadingDetails] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [results, setResults] = useState<EdgeLabResult[]>([])
  const [summary, setSummary] = useState<{ total: number; confirmed: number } | null>(null)
  const [runs, setRuns] = useState<EdgeLabSummaryRow[]>([])
  const [selectedRun, setSelectedRun] = useState<EdgeLabSummaryRow | null>(null)
  const [selectedStats, setSelectedStats] = useState<EdgeLabRunStats | null>(null)
  const [selectedTrades, setSelectedTrades] = useState<EdgeLabDbTrade[]>([])

  const refreshRuns = async () => {
    setLoadingRuns(true)
    try {
      const response = await edgeLabApi.getSummary({
        symbol: dataset?.request.symbol,
        timeframe: dataset?.request.timeframe,
        limit: 25,
      })
      setRuns(response.rows)
    } catch (err) {
      console.error("Failed to load discovery runs:", err)
    } finally {
      setLoadingRuns(false)
    }
  }

  useEffect(() => {
    refreshRuns()
  // Refresh is intentionally keyed to the active shared dataset identity.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dataset?.request.symbol, dataset?.request.timeframe])

  const runDiscovery = async () => {
    if (!dataset) {
      setError("Load a dataset in the Data tab first.")
      return
    }
    setLoading(true)
    setError(null)
    setResults([])
    setSummary(null)
    try {
      const response = await edgeLabApi.run({
        symbol: dataset.request.symbol,
        timeframe: dataset.request.timeframe,
        data_source: dataset.request.data_source,
        range_by: dataset.request.range_by,
        start_date: dataset.request.start_date ?? undefined,
        end_date: dataset.request.end_date ?? undefined,
        number_of_bars: dataset.request.number_of_bars ?? undefined,
        eds,
        n_boot: Number(nBoot) || 2000,
        n_perm: Number(nPerm) || 2000,
        save_db: saveDb,
        save_trades: saveTrades,
        prepared_dataset: dataset,
      })
      setResults(response.results || [])
      setSummary({
        total: response.summary.total_results,
        confirmed: response.summary.edges_confirmed,
      })
      await refreshRuns()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run Discovery.")
    } finally {
      setLoading(false)
    }
  }

  const loadRunDetails = async (run: EdgeLabSummaryRow) => {
    if (!run.latest_run_id) return
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
      console.error("Failed to load discovery details:", err)
      setSelectedStats(null)
      setSelectedTrades([])
    } finally {
      setLoadingDetails(false)
    }
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FlaskConical className="h-5 w-5 text-primary" />
            Discovery
          </CardTitle>
          <CardDescription>Run edge discovery strategies against the prepared session dataset.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {!dataset ? (
            <div className="text-sm text-muted-foreground">Load a dataset in the Data tab before running Discovery.</div>
          ) : (
            <div className="grid gap-4 md:grid-cols-4 text-sm">
              <div><div className="text-muted-foreground">Symbol</div><div>{dataset.request.symbol}</div></div>
              <div><div className="text-muted-foreground">Timeframe</div><div>{dataset.request.timeframe}</div></div>
              <div><div className="text-muted-foreground">Rows</div><div>{dataset.meta.n_rows}</div></div>
              <div><div className="text-muted-foreground">Warnings</div><div>{dataset.report.warnings.length}</div></div>
            </div>
          )}

          <div className="grid gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <Label>EDS Type</Label>
              <Select value={eds} onValueChange={(value) => setEds(value as EdgeLabEdsType)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
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
              <Label>Bootstrap Iterations</Label>
              <Select value={nBoot} onValueChange={setNBoot}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="500">500</SelectItem>
                  <SelectItem value="1000">1000</SelectItem>
                  <SelectItem value="2000">2000</SelectItem>
                  <SelectItem value="5000">5000</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Permutation Iterations</Label>
              <Select value={nPerm} onValueChange={setNPerm}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="500">500</SelectItem>
                  <SelectItem value="1000">1000</SelectItem>
                  <SelectItem value="2000">2000</SelectItem>
                  <SelectItem value="5000">5000</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="flex items-center justify-between rounded-lg border p-3">
              <div>
                <Label>Save To Database</Label>
                <p className="text-xs text-muted-foreground">Store run and summary stats.</p>
              </div>
              <Switch checked={saveDb} onCheckedChange={setSaveDb} />
            </div>
            <div className="flex items-center justify-between rounded-lg border p-3">
              <div>
                <Label>Save Trades</Label>
                <p className="text-xs text-muted-foreground">Persist trade-level records with the run.</p>
              </div>
              <Switch checked={saveTrades} onCheckedChange={setSaveTrades} />
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Button onClick={runDiscovery} disabled={loading || !dataset}>
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Run Discovery
            </Button>
            <Button variant="outline" onClick={refreshRuns} disabled={loadingRuns}>
              <RefreshCcw className={cn("mr-2 h-4 w-4", loadingRuns && "animate-spin")} />
              Refresh History
            </Button>
            {error && <p className="text-sm text-destructive">{error}</p>}
          </div>
        </CardContent>
      </Card>

      {summary && (
        <Card>
          <CardHeader>
            <CardTitle>Run Summary</CardTitle>
            <CardDescription>{summary.total} results, {summary.confirmed} confirmed edges.</CardDescription>
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
                    <span>{result.symbol} {result.timeframe}</span>
                    <Badge className={verdictTone(verdict)}>{verdict}</Badge>
                  </CardTitle>
                  <CardDescription>{result.eds_name}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid gap-4 md:grid-cols-3 text-sm">
                    <div><div className="text-muted-foreground">Trades</div><div>{result.stats.n_trades}</div></div>
                    <div><div className="text-muted-foreground">Expectancy</div><div>{formatValue(result.stats.expectancy_r, 4)}</div></div>
                    <div><div className="text-muted-foreground">Profit Factor</div><div>{formatValue(result.stats.profit_factor, 2)}</div></div>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Saved Discovery Runs</CardTitle>
          <CardDescription>Latest persisted runs for the current symbol/timeframe.</CardDescription>
        </CardHeader>
        <CardContent>
          {loadingRuns ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading runs...
            </div>
          ) : runs.length === 0 ? (
            <div className="text-sm text-muted-foreground">No saved runs yet.</div>
          ) : (
            <div className="border rounded-lg overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Symbol</TableHead>
                    <TableHead>Timeframe</TableHead>
                    <TableHead>MR Exp</TableHead>
                    <TableHead>BO Exp</TableHead>
                    <TableHead>Verdict</TableHead>
                    <TableHead className="text-right">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {runs.map((run) => (
                    <TableRow key={`${run.symbol}-${run.timeframe}`}>
                      <TableCell>{run.symbol}</TableCell>
                      <TableCell>{run.timeframe}</TableCell>
                      <TableCell>{formatValue(run.mr.expectancy_r, 2)}</TableCell>
                      <TableCell>{formatValue(run.bo.expectancy_r, 2)}</TableCell>
                      <TableCell>{run.verdict ? <Badge className={verdictTone(run.verdict)}>{run.verdict}</Badge> : "—"}</TableCell>
                      <TableCell className="text-right">
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon">
                              <MoreVertical className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={() => loadRunDetails(run)} disabled={!run.latest_run_id}>
                              View Latest
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
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Run Details</CardTitle>
          <CardDescription>Stats and trade-level breakdown.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {!selectedRun ? (
            <div className="text-sm text-muted-foreground">Select a saved run to view details.</div>
          ) : loadingDetails ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading details...
            </div>
          ) : (
            <>
              <div className="grid gap-4 md:grid-cols-3 text-sm">
                <div><div className="text-muted-foreground">Run</div><div className="font-mono">{selectedRun.latest_run_id ? `#${selectedRun.latest_run_id}` : "—"}</div></div>
                <div><div className="text-muted-foreground">Symbol</div><div>{selectedRun.symbol}</div></div>
                <div><div className="text-muted-foreground">Timeframe</div><div>{selectedRun.timeframe}</div></div>
              </div>

              {selectedStats && (
                <div className="grid gap-4 md:grid-cols-3 text-sm">
                  <div><div className="text-muted-foreground">Expectancy (R)</div><div className="font-mono">{(selectedStats.expectancy_r ?? 0).toFixed(4)}</div></div>
                  <div><div className="text-muted-foreground">Win Rate</div><div className="font-mono">{(((selectedStats.win_rate ?? 0) * 100) || 0).toFixed(1)}%</div></div>
                  <div><div className="text-muted-foreground">Profit Factor</div><div className="font-mono">{(selectedStats.profit_factor ?? 0).toFixed(2)}</div></div>
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
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {selectedTrades.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={6} className="text-sm text-muted-foreground">No trades stored for this run.</TableCell>
                      </TableRow>
                    ) : (
                      selectedTrades.map((trade) => (
                        <TableRow key={trade.trade_id}>
                          <TableCell>{trade.entry_time}</TableCell>
                          <TableCell>{trade.exit_time}</TableCell>
                          <TableCell>{trade.side}</TableCell>
                          <TableCell className="font-mono">{trade.r_multiple.toFixed(2)}</TableCell>
                          <TableCell className="font-mono">{trade.mae_r.toFixed(2)}</TableCell>
                          <TableCell className="font-mono">{trade.mfe_r.toFixed(2)}</TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
