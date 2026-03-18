"use client"

import { useMemo, useState } from "react"
import { Bot, Play, RotateCcw } from "lucide-react"

import { EdgeLabDatasetSummary } from "@/components/edge-lab/dataset-summary"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useEdgeLabData } from "@/contexts/edge-lab-data-context"
import edgeLabApi, {
  type EdgeLabAutomationBatchResult,
  type EdgeLabAutomationResult,
} from "@/lib/api/edge"

function fmt(value: number | null | undefined, digits = 1) {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—"
  return value.toFixed(digits)
}

export default function EdgeLabAutomationPage() {
  const { dataset } = useEdgeLabData()
  const [symbol, setSymbol] = useState(dataset?.request.symbol ?? "")
  const [symbolsText, setSymbolsText] = useState(dataset?.request.symbol ?? "")
  const [timeframe, setTimeframe] = useState(dataset?.request.timeframe ?? "M15")
  const [dataSource, setDataSource] = useState<"mt5" | "dukascopy">(dataset?.request.data_source ?? "mt5")
  const [rangeBy, setRangeBy] = useState<"dates" | "bars">(dataset?.request.range_by ?? "bars")
  const [startDate, setStartDate] = useState(dataset?.request.start_date ?? "")
  const [endDate, setEndDate] = useState(dataset?.request.end_date ?? "")
  const [numberOfBars, setNumberOfBars] = useState(String(dataset?.request.number_of_bars ?? 1500))
  const [familiesText, setFamiliesText] = useState("")
  const [saveSnapshot, setSaveSnapshot] = useState(true)
  const [useCache, setUseCache] = useState(true)
  const [forceRerun, setForceRerun] = useState(false)
  const [triggerType, setTriggerType] = useState("manual")
  const [runReason, setRunReason] = useState("")
  const [loadingSingle, setLoadingSingle] = useState(false)
  const [loadingBatch, setLoadingBatch] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [singleResult, setSingleResult] = useState<EdgeLabAutomationResult | null>(null)
  const [batchResult, setBatchResult] = useState<EdgeLabAutomationBatchResult | null>(null)

  const parsedFamilies = useMemo(
    () =>
      familiesText
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean) as Array<"core_metric" | "seasonality" | "market_structure" | "scorecard">,
    [familiesText]
  )

  const basePayload = {
    timeframe,
    data_source: dataSource,
    range_by: rangeBy,
    start_date: rangeBy === "dates" ? startDate || undefined : undefined,
    end_date: rangeBy === "dates" ? endDate || undefined : undefined,
    number_of_bars: rangeBy === "bars" ? Number(numberOfBars) || undefined : undefined,
    metric_families: parsedFamilies.length > 0 ? parsedFamilies : undefined,
    save_snapshot: saveSnapshot,
    use_cache: useCache,
    force_rerun: forceRerun,
    trigger_type: triggerType || "manual",
    run_reason: runReason || undefined,
  } as const

  async function handleSingleRun() {
    if (!symbol.trim()) {
      setError("Provide a symbol for single-symbol automation.")
      return
    }
    setLoadingSingle(true)
    setError(null)
    setBatchResult(null)
    try {
      const result = await edgeLabApi.runAutomation({
        symbol: symbol.trim(),
        ...basePayload,
      })
      setSingleResult(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Automation run failed.")
      setSingleResult(null)
    } finally {
      setLoadingSingle(false)
    }
  }

  async function handleBatchRun() {
    const symbols = symbolsText
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean)
    if (symbols.length === 0) {
      setError("Provide one or more comma-separated symbols for batch automation.")
      return
    }
    setLoadingBatch(true)
    setError(null)
    setSingleResult(null)
    try {
      const result = await edgeLabApi.runAutomationBatch({
        symbols,
        ...basePayload,
      })
      setBatchResult(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Batch automation failed.")
      setBatchResult(null)
    } finally {
      setLoadingBatch(false)
    }
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bot className="h-5 w-5 text-primary" />
            Automation
          </CardTitle>
          <CardDescription>
            Run the full Edge Lab chain server-side for one symbol or a batch, with cache and rerun controls.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <EdgeLabDatasetSummary
            dataset={dataset}
            emptyMessage="Automation can run without a loaded session dataset, but the active dataset can be used to prefill inputs."
          />

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <div className="space-y-2">
              <Label>Single Symbol</Label>
              <Input value={symbol} onChange={(e) => setSymbol(e.target.value)} placeholder="EURUSD" />
            </div>
            <div className="space-y-2">
              <Label>Batch Symbols</Label>
              <Input
                value={symbolsText}
                onChange={(e) => setSymbolsText(e.target.value)}
                placeholder="EURUSD, GBPUSD, XAUUSD"
              />
            </div>
            <div className="space-y-2">
              <Label>Timeframe</Label>
              <Input value={timeframe} onChange={(e) => setTimeframe(e.target.value)} placeholder="M15" />
            </div>
            <div className="space-y-2">
              <Label>Data Source</Label>
              <Select value={dataSource} onValueChange={(value) => setDataSource(value as "mt5" | "dukascopy")}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="mt5">MT5</SelectItem>
                  <SelectItem value="dukascopy">Dukascopy</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Range By</Label>
              <Select value={rangeBy} onValueChange={(value) => setRangeBy(value as "dates" | "bars")}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="bars">Bars</SelectItem>
                  <SelectItem value="dates">Dates</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Number Of Bars</Label>
              <Input
                value={numberOfBars}
                onChange={(e) => setNumberOfBars(e.target.value)}
                placeholder="1500"
                disabled={rangeBy !== "bars"}
              />
            </div>
            <div className="space-y-2">
              <Label>Start Date</Label>
              <Input
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                placeholder="2025-01-01"
                disabled={rangeBy !== "dates"}
              />
            </div>
            <div className="space-y-2">
              <Label>End Date</Label>
              <Input
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                placeholder="2025-12-31"
                disabled={rangeBy !== "dates"}
              />
            </div>
            <div className="space-y-2 xl:col-span-2">
              <Label>Metric Families</Label>
              <Input
                value={familiesText}
                onChange={(e) => setFamiliesText(e.target.value)}
                placeholder="Leave blank for full run, or core_metric,seasonality"
              />
            </div>
            <div className="space-y-2">
              <Label>Trigger Type</Label>
              <Input value={triggerType} onChange={(e) => setTriggerType(e.target.value)} placeholder="manual" />
            </div>
            <div className="space-y-2">
              <Label>Run Reason</Label>
              <Input value={runReason} onChange={(e) => setRunReason(e.target.value)} placeholder="daily_refresh" />
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <Button variant={saveSnapshot ? "secondary" : "outline"} onClick={() => setSaveSnapshot((v) => !v)}>
              {saveSnapshot ? "Save Snapshot: On" : "Save Snapshot: Off"}
            </Button>
            <Button variant={useCache ? "secondary" : "outline"} onClick={() => setUseCache((v) => !v)}>
              {useCache ? "Use Cache: On" : "Use Cache: Off"}
            </Button>
            <Button variant={forceRerun ? "secondary" : "outline"} onClick={() => setForceRerun((v) => !v)}>
              {forceRerun ? "Force Rerun: On" : "Force Rerun: Off"}
            </Button>
          </div>

          <div className="flex flex-wrap gap-3">
            <Button onClick={handleSingleRun} disabled={loadingSingle}>
              <Play className="mr-2 h-4 w-4" />
              {loadingSingle ? "Running..." : "Run Single Symbol"}
            </Button>
            <Button variant="outline" onClick={handleBatchRun} disabled={loadingBatch}>
              <RotateCcw className="mr-2 h-4 w-4" />
              {loadingBatch ? "Running Batch..." : "Run Batch"}
            </Button>
          </div>

          {error && <div className="text-sm text-destructive">{error}</div>}
        </CardContent>
      </Card>

      {singleResult && (
        <Card>
          <CardHeader>
            <CardTitle>Single Run Result</CardTitle>
            <CardDescription>
              Server-side progressive automation result for {singleResult.symbol} {singleResult.timeframe}.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-4">
            <div className="rounded-lg border p-4">
              <div className="text-sm text-muted-foreground">Status</div>
              <div className="mt-2 text-lg font-semibold capitalize">{singleResult.status}</div>
            </div>
            <div className="rounded-lg border p-4">
              <div className="text-sm text-muted-foreground">Final Score</div>
              <div className="mt-2 font-mono text-2xl">{fmt(singleResult.scorecard_summary?.final_score ?? null, 1)}</div>
            </div>
            <div className="rounded-lg border p-4">
              <div className="text-sm text-muted-foreground">Final Label</div>
              <div className="mt-2 text-lg font-semibold">{singleResult.scorecard_summary?.final_label ?? "—"}</div>
            </div>
            <div className="rounded-lg border p-4">
              <div className="text-sm text-muted-foreground">Snapshot</div>
              <div className="mt-2 text-lg font-semibold">
                {singleResult.snapshot_saved && singleResult.snapshot?.snapshot_id
                  ? `#${singleResult.snapshot.snapshot_id}`
                  : "Not saved"}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {batchResult && (
        <Card>
          <CardHeader>
            <CardTitle>Batch Results</CardTitle>
            <CardDescription>
              {batchResult.symbol_count} symbols were submitted through the backend automation runner.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="rounded-lg border overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Symbol</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Final Score</TableHead>
                    <TableHead>Final Label</TableHead>
                    <TableHead>Snapshot</TableHead>
                    <TableHead>Cache</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {batchResult.results.map((row, index) => (
                    <TableRow key={`${row.symbol}-${index}`}>
                      <TableCell className="font-medium">
                        {row.symbol} {row.timeframe}
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary">{row.status}</Badge>
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {fmt(row.scorecard_summary?.final_score ?? null, 1)}
                      </TableCell>
                      <TableCell>{row.scorecard_summary?.final_label ?? "—"}</TableCell>
                      <TableCell>
                        {row.snapshot?.snapshot_id ? `#${row.snapshot.snapshot_id}` : "—"}
                      </TableCell>
                      <TableCell>
                        {row.automation_metadata?.cache_hit ? "Hit" : "Miss"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
