"use client"

import { useEffect, useMemo, useState } from "react"
import { Award } from "lucide-react"

import { EdgeLabDatasetSummary } from "@/components/edge-lab/dataset-summary"
import { EdgeLabPrerequisiteState } from "@/components/edge-lab/prerequisite-state"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useEdgeLabData } from "@/contexts/edge-lab-data-context"
import {
  buildPairOverviewWidgetModel,
  buildScorecardWidgetModel,
  buildSnapshotComparisonWidgetModel,
  formatEdgeTimestamp,
  formatEdgeValue,
} from "@/lib/edge-lab-dashboard"
import { buildEdgeLabScorecard } from "@/lib/edge-lab-scorecard"
import edgeLabApi, {
  type EdgeLabScorecardSnapshot,
  type EdgeLabScorecardSnapshotArtifact,
  type EdgeLabScorecardSnapshotComparison,
} from "@/lib/api/edge"

export default function EdgeLabScorecardPage() {
  const {
    dataset,
    coreMetricProfile,
    seasonalityResult,
    marketStructureProfile,
    unsupervisedResult,
    marketStructureStability,
    marketStructureRobustness,
  } = useEdgeLabData()
  const [savingSnapshot, setSavingSnapshot] = useState(false)
  const [exportingParquet, setExportingParquet] = useState(false)
  const [savedSnapshot, setSavedSnapshot] = useState<EdgeLabScorecardSnapshot | null>(null)
  const [exportArtifact, setExportArtifact] = useState<EdgeLabScorecardSnapshotArtifact | null>(null)
  const [reportArtifacts, setReportArtifacts] = useState<EdgeLabScorecardSnapshotArtifact[]>([])
  const [snapshotError, setSnapshotError] = useState<string | null>(null)
  const [savedSnapshots, setSavedSnapshots] = useState<EdgeLabScorecardSnapshot[]>([])
  const [leftSnapshotId, setLeftSnapshotId] = useState("")
  const [rightSnapshotId, setRightSnapshotId] = useState("")
  const [comparingSnapshots, setComparingSnapshots] = useState(false)
  const [comparison, setComparison] = useState<EdgeLabScorecardSnapshotComparison | null>(null)
  const [exportingReport, setExportingReport] = useState(false)
  const [exportingComparisonReport, setExportingComparisonReport] = useState(false)
  const [comparisonArtifact, setComparisonArtifact] = useState<EdgeLabScorecardSnapshotArtifact | null>(null)

  const report = useMemo(
    () =>
      buildEdgeLabScorecard({
        dataset,
        coreMetricProfile,
        seasonalityResult,
        marketStructureProfile,
        stability: marketStructureStability,
        robustness: marketStructureRobustness,
      }),
    [
      dataset,
      coreMetricProfile,
      seasonalityResult,
      marketStructureProfile,
      marketStructureStability,
      marketStructureRobustness,
    ]
  )
  const pairOverview = useMemo(
    () =>
      buildPairOverviewWidgetModel({
        dataset,
        marketStructureProfile,
        scorecardReport: report,
        seasonalityResult,
      }),
    [dataset, marketStructureProfile, report, seasonalityResult]
  )
  const scorecardWidget = useMemo(() => buildScorecardWidgetModel(report), [report])
  const comparisonWidget = useMemo(() => buildSnapshotComparisonWidgetModel(comparison), [comparison])

  useEffect(() => {
    let active = true
    async function loadSnapshots() {
      try {
        const rows = await edgeLabApi.getScorecardSnapshots({ limit: 20 })
        if (!active) return
        setSavedSnapshots(rows)
        if (rows.length >= 1 && !leftSnapshotId) setLeftSnapshotId(String(rows[0].snapshot_id))
        if (rows.length >= 2 && !rightSnapshotId) setRightSnapshotId(String(rows[1].snapshot_id))
      } catch {
        if (!active) return
        setSavedSnapshots([])
      }
    }
    void loadSnapshots()
    return () => {
      active = false
    }
  }, [leftSnapshotId, rightSnapshotId])

  if (!unsupervisedResult) {
    return (
      <div className="flex flex-col gap-6 p-6">
        <EdgeLabPrerequisiteState
          title="Scorecard Requires Unsupervised Structure"
          description="Run Unsupervised Structure first. The Scorecard tab is the final progressive step and the saved snapshot now carries the unsupervised regime summary alongside the earlier Edge Lab tabs."
          actionHref="/edge-lab/unsupervised-structure"
          actionLabel="Go To Unsupervised Structure"
        />
      </div>
    )
  }

  async function handleSaveSnapshot() {
    if (!dataset || !coreMetricProfile || !seasonalityResult || !marketStructureProfile || !report) return
    setSavingSnapshot(true)
    setSnapshotError(null)
    try {
      const snapshot = await edgeLabApi.saveScorecardSnapshot({
        dataset,
        core_metric_profile: coreMetricProfile,
        seasonality_result: seasonalityResult,
        market_structure_profile: marketStructureProfile,
        unsupervised_result: unsupervisedResult,
        market_structure_stability: marketStructureStability,
        market_structure_robustness: marketStructureRobustness,
        scorecard_report: report,
      })
      setSavedSnapshot(snapshot)
      setExportArtifact(null)
      setReportArtifacts([])
      const rows = await edgeLabApi.getScorecardSnapshots({ limit: 20 })
      setSavedSnapshots(rows)
      setLeftSnapshotId(String(snapshot.snapshot_id))
    } catch (error) {
      setSnapshotError(error instanceof Error ? error.message : "Failed to save snapshot.")
    } finally {
      setSavingSnapshot(false)
    }
  }

  async function handleExportReport() {
    if (!savedSnapshot?.snapshot_id) return
    setExportingReport(true)
    setSnapshotError(null)
    try {
      const result = await edgeLabApi.exportScorecardSnapshotReport(savedSnapshot.snapshot_id)
      setReportArtifacts(result.artifacts)
    } catch (error) {
      setSnapshotError(error instanceof Error ? error.message : "Failed to export report.")
    } finally {
      setExportingReport(false)
    }
  }

  async function handleExportParquet() {
    if (!savedSnapshot?.snapshot_id) return
    setExportingParquet(true)
    setSnapshotError(null)
    try {
      const artifact = await edgeLabApi.exportScorecardSnapshotParquet(savedSnapshot.snapshot_id)
      setExportArtifact(artifact)
    } catch (error) {
      setSnapshotError(error instanceof Error ? error.message : "Failed to export Parquet.")
    } finally {
      setExportingParquet(false)
    }
  }

  async function handleCompareSnapshots() {
    if (!leftSnapshotId || !rightSnapshotId) return
    setComparingSnapshots(true)
    setSnapshotError(null)
    try {
      const result = await edgeLabApi.compareScorecardSnapshots(Number(leftSnapshotId), Number(rightSnapshotId))
      setComparison(result)
    } catch (error) {
      setSnapshotError(error instanceof Error ? error.message : "Failed to compare snapshots.")
      setComparison(null)
    } finally {
      setComparingSnapshots(false)
    }
  }

  async function handleExportComparisonReport() {
    if (!leftSnapshotId || !rightSnapshotId) return
    setExportingComparisonReport(true)
    setSnapshotError(null)
    try {
      const result = await edgeLabApi.exportScorecardSnapshotComparisonMarkdown(
        Number(leftSnapshotId),
        Number(rightSnapshotId)
      )
      setComparisonArtifact(result.artifact)
      setComparison(result.comparison)
    } catch (error) {
      setSnapshotError(error instanceof Error ? error.message : "Failed to export comparison report.")
    } finally {
      setExportingComparisonReport(false)
    }
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Award className="h-5 w-5 text-primary" />
            Scorecard
          </CardTitle>
          <CardDescription>
            Final explainable score layer built from the session dataset plus the outputs of Core Metric, Seasonality, and Market Structure.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <EdgeLabDatasetSummary dataset={dataset} emptyMessage="Load a dataset in the Data tab first." />
          {report && (
            <div className="space-y-4">
              <div className="flex flex-wrap gap-3">
                <Button onClick={handleSaveSnapshot} disabled={savingSnapshot}>
                  {savingSnapshot ? "Saving Snapshot..." : "Save Snapshot"}
                </Button>
                <Button
                  variant="outline"
                  onClick={handleExportParquet}
                  disabled={!savedSnapshot?.snapshot_id || exportingParquet}
                >
                  {exportingParquet ? "Exporting..." : "Export Metrics Parquet"}
                </Button>
                <Button
                  variant="outline"
                  onClick={handleExportReport}
                  disabled={!savedSnapshot?.snapshot_id || exportingReport}
                >
                  {exportingReport ? "Exporting Report..." : "Export Pair Report"}
                </Button>
              </div>
              {(savedSnapshot || exportArtifact || reportArtifacts.length > 0 || snapshotError) && (
                <div className="rounded-lg border p-4 text-sm">
                  {savedSnapshot && (
                    <div className="text-muted-foreground">
                      Saved snapshot <span className="font-mono text-foreground">#{savedSnapshot.snapshot_id}</span> at{" "}
                      <span className="font-mono text-foreground">{formatEdgeTimestamp(savedSnapshot.created_at)}</span>.
                    </div>
                  )}
                  {exportArtifact && (
                    <div className="mt-2 text-muted-foreground">
                      Parquet export: <span className="font-mono text-foreground">{exportArtifact.artifact_ref}</span>
                    </div>
                  )}
                  {reportArtifacts.map((artifact) => (
                    <div key={`${artifact.artifact_type}-${artifact.artifact_ref}`} className="mt-2 text-muted-foreground">
                      {artifact.artifact_type}: <span className="font-mono text-foreground">{artifact.artifact_ref}</span>
                    </div>
                  ))}
                  {snapshotError && <div className="mt-2 text-destructive">{snapshotError}</div>}
                </div>
              )}
              <div className="grid gap-4 md:grid-cols-4">
                <div className="rounded-lg border p-4">
                  <div className="text-sm text-muted-foreground">Final Score</div>
                  <div className="mt-1 font-mono text-3xl">{formatEdgeValue(scorecardWidget?.finalScore, 1)}</div>
                  <div className="mt-2 text-xs text-muted-foreground">0 low to 100 high overall opportunity</div>
                </div>
                <div className="rounded-lg border p-4">
                  <div className="text-sm text-muted-foreground">Final Label</div>
                  <div className="mt-1 text-2xl font-semibold">{scorecardWidget?.finalLabel ?? "—"}</div>
                  <div className="mt-2 text-xs text-muted-foreground">
                    Comprehensive read across structure, seasonality, cost, and tradability
                  </div>
                </div>
                <div className="rounded-lg border p-4">
                  <div className="text-sm text-muted-foreground">Overall Confidence</div>
                  <div className="mt-1 text-2xl font-semibold">{scorecardWidget?.overallConfidence ?? "—"}</div>
                  <div className="mt-2 text-xs text-muted-foreground">Label derived from the full scorecard mix</div>
                </div>
                <div className="rounded-lg border p-4">
                  <div className="text-sm text-muted-foreground">Pair Overview</div>
                  <div className="mt-1 text-lg font-semibold">
                    {pairOverview ? `${pairOverview.symbol} ${pairOverview.timeframe}` : "—"}
                  </div>
                  <div className="mt-2 text-xs text-muted-foreground">
                    {pairOverview?.primaryStrategy
                      ? `Primary strategy: ${pairOverview.primaryStrategy}`
                      : "Primary strategy will appear after scorecard build."}
                  </div>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {report && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>Snapshot Comparison</CardTitle>
              <CardDescription>
                Compare saved scorecard snapshots across runs so pair-profile changes stay queryable and versioned.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-[1fr_1fr_auto]">
                <div className="space-y-2">
                  <div className="text-sm text-muted-foreground">Left Snapshot ID</div>
                  <Input
                    value={leftSnapshotId}
                    onChange={(event) => setLeftSnapshotId(event.target.value)}
                    list="edge-lab-scorecard-snapshots"
                    placeholder="Snapshot ID"
                  />
                </div>
                <div className="space-y-2">
                  <div className="text-sm text-muted-foreground">Right Snapshot ID</div>
                  <Input
                    value={rightSnapshotId}
                    onChange={(event) => setRightSnapshotId(event.target.value)}
                    list="edge-lab-scorecard-snapshots"
                    placeholder="Snapshot ID"
                  />
                </div>
                <div className="flex items-end">
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      onClick={handleCompareSnapshots}
                      disabled={!leftSnapshotId || !rightSnapshotId || comparingSnapshots}
                    >
                      {comparingSnapshots ? "Comparing..." : "Compare"}
                    </Button>
                    <Button
                      variant="outline"
                      onClick={handleExportComparisonReport}
                      disabled={!leftSnapshotId || !rightSnapshotId || exportingComparisonReport}
                    >
                      {exportingComparisonReport ? "Exporting..." : "Export Comparison"}
                    </Button>
                  </div>
                </div>
              </div>
              <datalist id="edge-lab-scorecard-snapshots">
                {savedSnapshots.map((snapshot) => (
                  <option
                    key={snapshot.snapshot_id}
                    value={String(snapshot.snapshot_id)}
                    label={`${snapshot.snapshot_id} ${snapshot.symbol} ${snapshot.timeframe} ${snapshot.created_at}`}
                  />
                ))}
              </datalist>
              <div className="rounded-lg border p-4 text-sm text-muted-foreground">
                {savedSnapshots.length > 0 ? (
                  <>
                    Latest saved snapshots:{" "}
                    {savedSnapshots
                      .slice(0, 5)
                      .map((snapshot) => `#${snapshot.snapshot_id} ${snapshot.symbol} ${snapshot.timeframe}`)
                      .join(" | ")}
                  </>
                ) : (
                  "Save a snapshot first to compare runs."
                )}
              </div>
              {comparisonArtifact && (
                <div className="rounded-lg border p-4 text-sm text-muted-foreground">
                  Comparison report: <span className="font-mono text-foreground">{comparisonArtifact.artifact_ref}</span>
                </div>
              )}
              {comparison && (
                <>
                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="rounded-lg border p-4">
                      <div className="text-sm text-muted-foreground">Left Snapshot</div>
                      <div className="mt-1 font-mono">#{String(comparisonWidget?.leftSnapshotId ?? "")}</div>
                      <div className="mt-2 text-sm text-muted-foreground">
                        {String(comparison.left_snapshot.symbol ?? "")} {String(comparison.left_snapshot.timeframe ?? "")}
                      </div>
                      <div className="mt-2 text-sm text-muted-foreground">
                        Final Score:{" "}
                        <span className="font-mono text-foreground">
                          {formatEdgeValue(comparisonWidget?.leftFinalScore, 1)}
                        </span>
                      </div>
                    </div>
                    <div className="rounded-lg border p-4">
                      <div className="text-sm text-muted-foreground">Right Snapshot</div>
                      <div className="mt-1 font-mono">#{String(comparisonWidget?.rightSnapshotId ?? "")}</div>
                      <div className="mt-2 text-sm text-muted-foreground">
                        {String(comparison.right_snapshot.symbol ?? "")} {String(comparison.right_snapshot.timeframe ?? "")}
                      </div>
                      <div className="mt-2 text-sm text-muted-foreground">
                        Final Score:{" "}
                        <span className="font-mono text-foreground">
                          {formatEdgeValue(comparisonWidget?.rightFinalScore, 1)}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="rounded-lg border p-4 text-sm text-muted-foreground">
                    Score diffs: <span className="font-mono text-foreground">{formatEdgeValue(comparisonWidget?.scoreDiffCount, 0)}</span>
                    {" | "}
                    Metric diffs: <span className="font-mono text-foreground">{formatEdgeValue(comparisonWidget?.metricDiffCount, 0)}</span>
                  </div>

                  <div className="rounded-lg border overflow-hidden">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Score</TableHead>
                          <TableHead className="text-right">Left</TableHead>
                          <TableHead className="text-right">Right</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {comparison.score_diffs.length > 0 ? (
                          comparison.score_diffs.map((row) => (
                            <TableRow key={row.score_key}>
                              <TableCell className="font-medium">{row.label}</TableCell>
                              <TableCell className="text-right font-mono">{formatEdgeValue(row.left_score, 1)}</TableCell>
                              <TableCell className="text-right font-mono">{formatEdgeValue(row.right_score, 1)}</TableCell>
                            </TableRow>
                          ))
                        ) : (
                          <TableRow>
                            <TableCell colSpan={3} className="text-center text-sm text-muted-foreground">
                              No score differences found.
                            </TableCell>
                          </TableRow>
                        )}
                      </TableBody>
                    </Table>
                  </div>

                  <div className="rounded-lg border overflow-hidden">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Metric</TableHead>
                          <TableHead>Left</TableHead>
                          <TableHead>Right</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {comparison.metric_diffs.slice(0, 15).map((row) => (
                          <TableRow key={row.key}>
                            <TableCell className="font-medium">{row.key}</TableCell>
                            <TableCell className="font-mono text-xs">{formatEdgeValue(row.left_value, 2)}</TableCell>
                            <TableCell className="font-mono text-xs">{formatEdgeValue(row.right_value, 2)}</TableCell>
                          </TableRow>
                        ))}
                        {comparison.metric_diffs.length === 0 && (
                          <TableRow>
                            <TableCell colSpan={3} className="text-center text-sm text-muted-foreground">
                              No metric differences found.
                            </TableCell>
                          </TableRow>
                        )}
                      </TableBody>
                    </Table>
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Strategy-Fit Engine</CardTitle>
              <CardDescription>
                Ranked strategy suitability built from Core Metric, Seasonality, and Market Structure together.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="rounded-lg border p-4 text-sm">
                <div className="font-medium">Fit Scale Reference</div>
                <div className="mt-2 grid gap-2 text-muted-foreground md:grid-cols-4">
                  <div><span className="font-mono text-foreground">0-39</span> Poor fit</div>
                  <div><span className="font-mono text-foreground">40-59</span> Usable / mixed fit</div>
                  <div><span className="font-mono text-foreground">60-74</span> Good fit</div>
                  <div><span className="font-mono text-foreground">75-100</span> Strong fit</div>
                </div>
              </div>
              {report.strategyFit.primary && (
                <div className="rounded-lg border p-4">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <div className="text-sm text-muted-foreground">Primary Recommendation</div>
                      <div className="mt-1 text-2xl font-semibold">{report.strategyFit.primary.archetype}</div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm text-muted-foreground">Fit Score</div>
                      <div className="mt-1 font-mono text-3xl">
                        {formatEdgeValue(report.strategyFit.primary.fitScore, 1)}
                      </div>
                    </div>
                  </div>
                  <div className="mt-3 text-sm text-muted-foreground">{report.strategyFit.primary.rationale}</div>
                  {report.strategyFit.primary.warnings.length > 0 && (
                    <div className="mt-4">
                      <div className="text-xs font-medium uppercase text-muted-foreground">Warnings</div>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {report.strategyFit.primary.warnings.map((warning) => (
                          <Badge key={warning} variant="secondary">
                            {warning}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                  {report.strategyFit.primary.antiFitConditions.length > 0 && (
                    <div className="mt-4">
                      <div className="text-xs font-medium uppercase text-muted-foreground">Anti-Fit Conditions</div>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {report.strategyFit.primary.antiFitConditions.map((warning) => (
                          <Badge key={warning} variant="outline">
                            {warning}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              <div className="rounded-lg border overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Rank</TableHead>
                      <TableHead>Archetype</TableHead>
                      <TableHead className="text-right">Fit</TableHead>
                      <TableHead>Rationale</TableHead>
                      <TableHead>Warnings</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {report.strategyFit.ranked.map((row, index) => (
                      <TableRow key={`${row.archetype}-${index}`}>
                        <TableCell>{index + 1}</TableCell>
                        <TableCell className="font-medium">{row.archetype}</TableCell>
                        <TableCell className="text-right font-mono">{formatEdgeValue(row.fitScore, 1)}</TableCell>
                        <TableCell className="text-sm text-muted-foreground">{row.rationale}</TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {row.warnings.length > 0 ? row.warnings.join(" | ") : "None"}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Scorecard Section</CardTitle>
              <CardDescription>Explainable decision-support scores built from the earlier Edge Lab tabs.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="rounded-lg border overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Score</TableHead>
                      <TableHead className="text-right">Value</TableHead>
                      <TableHead>Confidence</TableHead>
                      <TableHead>Explanation</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {report.rows.map((row) => (
                      <TableRow key={row.key}>
                        <TableCell className="font-medium">{row.label}</TableCell>
                        <TableCell className="text-right font-mono">{formatEdgeValue(row.score, 1)}</TableCell>
                        <TableCell>
                          <Badge variant="secondary">{row.confidence}</Badge>
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">{row.explanation}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Score Explanations</CardTitle>
              <CardDescription>
                Raw inputs used for each score so the scorecard stays reproducible and explainable.
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 xl:grid-cols-2">
              {report.rows.map((row) => (
                <div key={row.key} className="rounded-lg border p-4">
                  <div className="flex items-center justify-between">
                    <div className="font-medium">{row.label}</div>
                    <div className="font-mono">{formatEdgeValue(row.score, 1)}</div>
                  </div>
                  <div className="mt-2 text-sm text-muted-foreground">{row.explanation}</div>
                  <div className="mt-3 space-y-1 text-xs font-mono">
                    {Object.entries(row.inputs).map(([key, value]) => (
                      <div key={key} className="flex items-center justify-between gap-3">
                        <span>{key}</span>
                        <span>{formatEdgeValue(value, 1)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
