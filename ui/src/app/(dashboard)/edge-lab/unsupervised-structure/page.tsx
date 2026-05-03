"use client"

import { useState } from "react"
import { BrainCircuit, Loader2 } from "lucide-react"

import { EdgeLabDatasetSummary } from "@/components/edge-lab/dataset-summary"
import { EdgeLabPrerequisiteState } from "@/components/edge-lab/prerequisite-state"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useEdgeLabData } from "@/contexts/edge-lab-data-context"
import edgeLabApi from "@/lib/api/edge"

function fmt(value: number | null | undefined, digits = 2) {
  if (value === null || value === undefined || !Number.isFinite(value)) return "-"
  return value.toFixed(digits)
}

export default function EdgeLabUnsupervisedStructurePage() {
  const { dataset, marketStructureProfile, unsupervisedResult, setUnsupervisedResult } = useEdgeLabData()
  const [fastPeriod, setFastPeriod] = useState("20")
  const [slowPeriod, setSlowPeriod] = useState("50")
  const [nComponents, setNComponents] = useState("2")
  const [nClusters, setNClusters] = useState("3")
  const [forwardReturnHorizon, setForwardReturnHorizon] = useState("1")
  const [minRows, setMinRows] = useState("40")
  const [randomState, setRandomState] = useState("42")
  const [scaleFeatures, setScaleFeatures] = useState(true)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!marketStructureProfile || !dataset) {
    return (
      <div className="flex flex-col gap-6 p-6">
        <EdgeLabPrerequisiteState
          title="Unsupervised Structure Requires Market Structure"
          description="Run Market Structure first so the unsupervised regime view becomes the next progressive step in the Edge Lab flow."
          actionHref="/edge-lab/market-structure"
          actionLabel="Go To Market Structure"
        />
      </div>
    )
  }

  const activeDataset = dataset

  async function handleRun() {
    setLoading(true)
    setError(null)
    try {
      const response = await edgeLabApi.runUnsupervisedStructure({
        symbol: activeDataset.request.symbol,
        timeframe: activeDataset.request.timeframe,
        data_source: activeDataset.request.data_source,
        range_by: activeDataset.request.range_by,
        start_date: activeDataset.request.start_date ?? undefined,
        end_date: activeDataset.request.end_date ?? undefined,
        number_of_bars: activeDataset.request.number_of_bars ?? undefined,
        prepared_dataset: activeDataset,
        save_db: false,
        fast_period: Number(fastPeriod) || 20,
        slow_period: Number(slowPeriod) || 50,
        n_components: Number(nComponents) || 2,
        n_clusters: Number(nClusters) || 3,
        random_state: Number(randomState) || 42,
        forward_return_horizon: Number(forwardReturnHorizon) || 1,
        min_rows: Number(minRows) || 40,
        scale_features: scaleFeatures,
      })
      setUnsupervisedResult(response)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run unsupervised structure.")
    } finally {
      setLoading(false)
    }
  }

  const summary = unsupervisedResult?.summary
  const report = unsupervisedResult?.report

  return (
    <div className="flex flex-col gap-6 p-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BrainCircuit className="h-5 w-5 text-primary" />
            Unsupervised Structure
          </CardTitle>
          <CardDescription>
            Explore PCA and K-Means regime structure, dominant factors, and cluster outperformance for the active dataset.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <EdgeLabDatasetSummary dataset={activeDataset} emptyMessage="Load a dataset in the Data tab first." />

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <div className="space-y-2">
              <Label>Fast EMA</Label>
              <Input value={fastPeriod} onChange={(e) => setFastPeriod(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Slow EMA</Label>
              <Input value={slowPeriod} onChange={(e) => setSlowPeriod(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>PCA Components</Label>
              <Input value={nComponents} onChange={(e) => setNComponents(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>K-Means Clusters</Label>
              <Input value={nClusters} onChange={(e) => setNClusters(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Forward Horizon</Label>
              <Input value={forwardReturnHorizon} onChange={(e) => setForwardReturnHorizon(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Minimum Rows</Label>
              <Input value={minRows} onChange={(e) => setMinRows(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Random State</Label>
              <Input value={randomState} onChange={(e) => setRandomState(e.target.value)} />
            </div>
            <div className="flex items-end">
              <div className="flex w-full items-center justify-between rounded-md border px-3 py-2">
                <div>
                  <div className="text-sm font-medium">Scale Features</div>
                  <div className="text-xs text-muted-foreground">Standardize before PCA and clustering.</div>
                </div>
                <Switch checked={scaleFeatures} onCheckedChange={setScaleFeatures} />
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Button onClick={handleRun} disabled={loading}>
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Run Unsupervised Structure
            </Button>
            {error && <div className="text-sm text-destructive">{error}</div>}
          </div>
        </CardContent>
      </Card>

      {unsupervisedResult && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>Result Summary</CardTitle>
              <CardDescription>Top-line clustering and factor view for the current dataset.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-4">
              <div className="rounded-lg border p-4">
                <div className="text-sm text-muted-foreground">Status</div>
                <div className="mt-2 text-lg font-semibold">{summary?.status ?? unsupervisedResult.status}</div>
              </div>
              <div className="rounded-lg border p-4">
                <div className="text-sm text-muted-foreground">Clusters</div>
                <div className="mt-2 font-mono text-3xl">{fmt(summary?.cluster_count ?? null, 0)}</div>
              </div>
              <div className="rounded-lg border p-4">
                <div className="text-sm text-muted-foreground">Top Cluster</div>
                <div className="mt-2 text-lg font-semibold">
                  {summary?.top_outperforming_cluster?.cluster_label !== undefined
                    ? `Cluster ${summary.top_outperforming_cluster.cluster_label}`
                    : "-"}
                </div>
                <div className="mt-1 text-xs text-muted-foreground">
                  Outperformance {fmt(summary?.top_outperforming_cluster?.outperformance_vs_overall ?? null, 4)}
                </div>
              </div>
              <div className="rounded-lg border p-4">
                <div className="text-sm text-muted-foreground">Weakest Cluster</div>
                <div className="mt-2 text-lg font-semibold">
                  {summary?.weakest_cluster?.cluster_label !== undefined
                    ? `Cluster ${summary.weakest_cluster.cluster_label}`
                    : "-"}
                </div>
                <div className="mt-1 text-xs text-muted-foreground">
                  Outperformance {fmt(summary?.weakest_cluster?.outperformance_vs_overall ?? null, 4)}
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Feature Space</CardTitle>
              <CardDescription>Feature set and PCA coverage used for clustering.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-wrap gap-2">
                {(summary?.feature_columns ?? []).map((column) => (
                  <Badge key={column} variant="secondary" className="font-mono">
                    {column}
                  </Badge>
                ))}
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-lg border p-4">
                  <div className="text-sm text-muted-foreground">Feature Set</div>
                  <div className="mt-2 font-medium">{summary?.feature_set ?? "-"}</div>
                </div>
                <div className="rounded-lg border p-4">
                  <div className="text-sm text-muted-foreground">PCA Explained Variance</div>
                  <div className="mt-2 font-mono">
                    {(summary?.pca_explained_variance_ratio ?? []).map((value) => fmt(value, 4)).join(", ") || "-"}
                  </div>
                </div>
              </div>
              {summary?.reason && <div className="text-sm text-muted-foreground">{summary.reason}</div>}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Risk Factors</CardTitle>
              <CardDescription>Largest PCA loadings interpreted as dominant structure factors.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="rounded-lg overflow-hidden border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Component</TableHead>
                      <TableHead>Feature</TableHead>
                      <TableHead className="text-right">Loading</TableHead>
                      <TableHead>Direction</TableHead>
                      <TableHead className="text-right">Explained Variance</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(report?.risk_factors ?? []).map((row) => (
                      <TableRow key={`${row.component}-${row.feature}`}>
                        <TableCell>{row.component}</TableCell>
                        <TableCell className="font-mono">{row.feature}</TableCell>
                        <TableCell className="text-right font-mono">{fmt(row.loading, 4)}</TableCell>
                        <TableCell>{row.direction ?? "-"}</TableCell>
                        <TableCell className="text-right font-mono">{fmt(row.explained_variance_ratio ?? null, 4)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Cluster Outperformance</CardTitle>
              <CardDescription>Forward-return behavior for each discovered regime cluster.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="rounded-lg overflow-hidden border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Cluster</TableHead>
                      <TableHead className="text-right">Observations</TableHead>
                      <TableHead className="text-right">Mean Forward Return</TableHead>
                      <TableHead className="text-right">Hit Rate</TableHead>
                      <TableHead className="text-right">Outperformance</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(report?.cluster_outperformance ?? []).map((row) => (
                      <TableRow key={row.cluster_label}>
                        <TableCell>{row.cluster_label}</TableCell>
                        <TableCell className="text-right font-mono">{fmt(row.observations, 0)}</TableCell>
                        <TableCell className="text-right font-mono">{fmt(row.mean_forward_return, 4)}</TableCell>
                        <TableCell className="text-right font-mono">{fmt(row.hit_rate, 4)}</TableCell>
                        <TableCell className="text-right font-mono">{fmt(row.outperformance_vs_overall, 4)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Guardrails</CardTitle>
              <CardDescription>Constraints applied to keep the unsupervised output interpretable for trading research.</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              {(summary?.guardrails ?? unsupervisedResult.guardrails ?? []).map((item) => (
                <Badge key={item} variant="outline" className="font-mono text-[11px]">
                  {item}
                </Badge>
              ))}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
