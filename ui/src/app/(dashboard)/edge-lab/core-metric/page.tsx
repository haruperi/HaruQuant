"use client"

import { useEffect, useState } from "react"
import { Loader2, RefreshCcw, Sigma } from "lucide-react"

import { EdgeLabCollectionState } from "@/components/edge-lab/collection-state"
import { EdgeLabControlToggle } from "@/components/edge-lab/control-toggle"
import { EdgeLabDatasetSummary } from "@/components/edge-lab/dataset-summary"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useEdgeLabData } from "@/contexts/edge-lab-data-context"
import { edgeLabApi, type EdgeCoreMetricRunRow, type EdgeCoreMetricValue } from "@/lib/api/edge"
import { formatEdgeValue, groupCoreMetricValues } from "@/lib/edge-lab-dashboard"
import { cn } from "@/lib/utils"

export default function EdgeLabCoreMetricPage() {
  const { dataset, coreMetricProfile, setCoreMetricProfile } = useEdgeLabData()
  const [saveDb, setSaveDb] = useState(true)
  const [loading, setLoading] = useState(false)
  const [runsLoading, setRunsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [runs, setRuns] = useState<EdgeCoreMetricRunRow[]>([])

  const refreshRuns = async () => {
    setRunsLoading(true)
    try {
      setRuns(await edgeLabApi.getCoreMetricRuns({ limit: 10 }))
    } catch (err) {
      console.error("Failed to load Core Metric runs:", err)
    } finally {
      setRunsLoading(false)
    }
  }

  useEffect(() => {
    refreshRuns()
  }, [])

  const runProfile = async () => {
    if (!dataset) {
      setError("Load a dataset in the Data tab first.")
      return
    }
    setLoading(true)
    setError(null)
    try {
      const response = await edgeLabApi.runCoreMetrics({
        symbol: dataset.request.symbol,
        timeframe: dataset.request.timeframe,
        data_source: dataset.request.data_source,
        range_by: dataset.request.range_by,
        start_date: dataset.request.start_date ?? undefined,
        end_date: dataset.request.end_date ?? undefined,
        number_of_bars: dataset.request.number_of_bars ?? undefined,
        prepared_dataset: dataset,
        save_db: saveDb,
      })
      setCoreMetricProfile(response)
      await refreshRuns()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run Core Metric profile.")
    } finally {
      setLoading(false)
    }
  }

  const loadRun = async (runId: number) => {
    setLoading(true)
    setError(null)
    try {
      setCoreMetricProfile(await edgeLabApi.getCoreMetricRun(runId))
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load Core Metric run.")
    } finally {
      setLoading(false)
    }
  }

  const deleteRun = async (runId: number) => {
    const confirmed = window.confirm(`Delete core metric run #${runId}?`)
    if (!confirmed) return
    try {
      await edgeLabApi.deleteCoreMetricRun(runId)
      if (coreMetricProfile?.run_id === runId) {
        setCoreMetricProfile(null)
      }
      await refreshRuns()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete Core Metric run.")
    }
  }

  const grouped = groupCoreMetricValues((coreMetricProfile?.values || []) as EdgeCoreMetricValue[])

  return (
    <div className="flex flex-col gap-6 p-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sigma className="h-5 w-5 text-primary" />
            Core Metric MVP
          </CardTitle>
          <CardDescription>
            Build a descriptive, cost-aware profile from the session dataset prepared in the Data tab.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <EdgeLabDatasetSummary
            dataset={dataset}
            emptyMessage="Load a dataset in the Data tab before running Core Metric."
          />

          <EdgeLabControlToggle
            label="Save To Database"
            description="Persist normalized profile metrics."
            checked={saveDb}
            onCheckedChange={setSaveDb}
          />

          <div className="flex items-center gap-3">
            <Button onClick={runProfile} disabled={loading || !dataset}>
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Run Core Metric
            </Button>
            <Button variant="outline" onClick={refreshRuns} disabled={runsLoading}>
              <RefreshCcw className={cn("mr-2 h-4 w-4", runsLoading && "animate-spin")} />
              Refresh Saved Runs
            </Button>
            {error && <p className="text-sm text-destructive">{error}</p>}
          </div>
        </CardContent>
      </Card>

      {coreMetricProfile && (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>{coreMetricProfile.symbol} {coreMetricProfile.timeframe}</span>
                <Badge className={coreMetricProfile.summary.is_valid ? "bg-emerald-500/15 text-emerald-600" : "bg-rose-500/15 text-rose-600"}>
                  {coreMetricProfile.summary.is_valid ? "VALID" : "HAS_FATAL_ERRORS"}
                </Badge>
              </CardTitle>
              <CardDescription>{coreMetricProfile.bar_count} bars, {coreMetricProfile.summary.metric_count} persisted metrics.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-5 text-sm">
                <div><div className="text-muted-foreground">Families</div><div>{coreMetricProfile.summary.family_count}</div></div>
                <div><div className="text-muted-foreground">Warnings</div><div>{coreMetricProfile.summary.warning_count}</div></div>
                <div><div className="text-muted-foreground">Fatal Errors</div><div>{coreMetricProfile.summary.fatal_error_count}</div></div>
                <div><div className="text-muted-foreground">Data Source</div><div>{coreMetricProfile.data_source}</div></div>
                <div><div className="text-muted-foreground">Run ID</div><div>{coreMetricProfile.run_id ?? "Not saved"}</div></div>
              </div>
            </CardContent>
          </Card>

          {Object.entries(grouped).map(([family, values]) => (
            <Card key={family}>
              <CardHeader>
                <CardTitle className="capitalize">{family.replaceAll("_", " ")}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="border rounded-lg overflow-hidden">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Metric</TableHead>
                        <TableHead className="text-right">Value</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {values.map((value) => (
                        <TableRow key={`${family}-${value.metric_key}`}>
                          <TableCell className="font-mono">{value.metric_key}</TableCell>
                          <TableCell className="text-right font-mono">{formatEdgeValue(value.value, 4)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          ))}
        </>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Saved Core Metric Runs</CardTitle>
          <CardDescription>Recent profiles persisted in normalized form.</CardDescription>
        </CardHeader>
        <CardContent>
          <EdgeLabCollectionState
            loading={runsLoading}
            hasItems={runs.length > 0}
            emptyMessage="No saved Core Metric runs yet."
          >
            <div className="border rounded-lg overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Run</TableHead>
                    <TableHead>Symbol</TableHead>
                    <TableHead>Timeframe</TableHead>
                    <TableHead>Bars</TableHead>
                    <TableHead>Warnings</TableHead>
                    <TableHead>Fatal</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead className="text-right">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {runs.map((run) => (
                    <TableRow key={run.run_id}>
                      <TableCell className="font-mono">#{run.run_id}</TableCell>
                      <TableCell>{run.symbol}</TableCell>
                      <TableCell>{run.timeframe}</TableCell>
                      <TableCell>{run.bar_count}</TableCell>
                      <TableCell>{run.warning_count}</TableCell>
                      <TableCell>{run.fatal_error_count}</TableCell>
                      <TableCell>{run.created_at}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Button variant="outline" size="sm" onClick={() => loadRun(run.run_id)}>View</Button>
                          <Button variant="outline" size="sm" onClick={() => deleteRun(run.run_id)}>Delete</Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </EdgeLabCollectionState>
        </CardContent>
      </Card>
    </div>
  )
}
