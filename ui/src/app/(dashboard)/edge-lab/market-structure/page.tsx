"use client"

import { useEffect, useMemo, useState } from "react"
import { GitBranch, Loader2, RefreshCcw } from "lucide-react"
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"

import { EdgeLabCollectionState } from "@/components/edge-lab/collection-state"
import { EdgeLabControlToggle } from "@/components/edge-lab/control-toggle"
import { EdgeLabDatasetSummary } from "@/components/edge-lab/dataset-summary"
import { EdgeLabPrerequisiteState } from "@/components/edge-lab/prerequisite-state"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useEdgeLabData } from "@/contexts/edge-lab-data-context"
import {
  edgeLabApi,
  type EdgeMarketStructureLeg,
  type EdgeMarketStructureProfile,
  type EdgeMarketStructureRunRow,
  type EdgeMarketStructureScoreRow,
  type EdgeMarketStructureSwingPoint,
  type EdgeMarketStructureCalibrationReport,
  type EdgeMarketStructureEvaluationRow,
  type EdgeMarketStructureMetricCalibrationReport,
  type EdgeMarketStructureProfileCalibrationReport,
  type EdgeMarketStructureValidationReport,
} from "@/lib/api/edge"
import {
  buildCurrentProfileCalibration,
  buildMarketStructureEdgeChartData,
  buildMarketStructureQualityModel,
  buildRegimeTimelineModel,
  buildTradeabilityModel,
} from "@/lib/edge-lab-dashboard"
import { cn } from "@/lib/utils"

function fmt(value: unknown, digits = 2) {
  if (value === null || value === undefined) return "—"
  if (typeof value === "number") return Number.isFinite(value) ? value.toFixed(digits) : "—"
  if (typeof value === "boolean") return value ? "Yes" : "No"
  if (typeof value === "object") return JSON.stringify(value)
  return String(value)
}

function pct(value: number | null | undefined, digits = 1) {
  return value === null || value === undefined ? "—" : `${(value * 100).toFixed(digits)}%`
}

function ts(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")} ${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`
}

function verdictTone(verdict: string) {
  if (verdict === "TREND_BIASED") return "bg-blue-500/15 text-blue-600"
  if (verdict === "REVERSION_BIASED") return "bg-amber-500/15 text-amber-700"
  return "bg-slate-500/15 text-slate-600"
}

function groupTone(group?: string) {
  if (group === "direction") return "bg-blue-500/10 text-blue-700"
  if (group === "confidence") return "bg-emerald-500/10 text-emerald-700"
  if (group === "reversion") return "bg-amber-500/10 text-amber-700"
  if (group === "chop") return "bg-rose-500/10 text-rose-700"
  return "bg-slate-500/10 text-slate-700"
}

function referenceText(row: EdgeMarketStructureScoreRow) {
  const byKey: Record<string, string> = {
    swing_bias_balance: "Near 0 mixed. Positive bullish. Negative bearish.",
    chain_strength: "Average chain length. Around 1 weak, 3 solid, 5+ strong.",
    follow_through_probability: "0.50 neutral. 0.70+ means structure often resumes.",
    pullback_quality: "Higher when pullbacks are shallow and resumptions are strong.",
    directional_efficiency: "Higher when legs travel cleanly with less churn.",
    sample_quality: "0..100 trend-confidence scale from structure sample size.",
    structural_cleanliness: "0..100 trend-confidence scale from fewer breaks and more continuity.",
    directional_asymmetry: "0..1. Higher means one direction clearly dominates.",
    eds2_confirmation: "0..100 trend-confidence support scale from EDS-2 trend persistence.",
    range_state_detection: "Higher when price spends more time in bounded ranges.",
    false_break_reentry: "Higher when breakouts fail and price reenters the range.",
    mean_reversion_metrics: "Higher when half-life is short and reentries are common.",
    eds1_confirmation: "0..100 support scale from EDS-1 mean reversion.",
    choppiness_whipsaw: "Higher when chop, whipsaws, and direction flips dominate.",
  }
  return byKey[row.key] ?? (row.group === "direction" ? "Signed -100..100 scale." : "0..100 support scale.")
}

function meaningText(row: EdgeMarketStructureScoreRow) {
  if (row.group === "direction") {
    if (row.score >= 25) return "Supports trend direction"
    if (row.score <= -25) return "Supports opposite trend direction"
    return "Mixed directional evidence"
  }
  if (row.group === "reversion") return row.score >= 40 ? "Supports reversion bias" : "Weak reversion support"
  if (row.group === "chop") return row.score >= 40 ? "Supports chop / whipsaw bias" : "Weak chop support"
  return row.score >= 40 ? "Raises trend confidence" : "Low trend-confidence support"
}

function groupWeightTotal(
  rows: EdgeMarketStructureScoreRow[],
  group: "direction" | "confidence" | "reversion" | "chop"
) {
  return rows
    .filter((row) => row.group === group)
    .reduce((total, row) => total + row.weight, 0)
}

function normalizeContinuation(value: EdgeMarketStructureLeg["continuation_after_pullback"]) {
  if (typeof value === "boolean") return value
  if (typeof value === "number") return value > 0
  return null
}

function chartBarColor(score: number) {
  if (score >= 25) return "#2563eb"
  if (score <= -25) return "#d97706"
  return "#64748b"
}

function confidenceLabel(value: number | null | undefined) {
  if (value === null || value === undefined) return "Unknown"
  if (value >= 70) return "High"
  if (value >= 45) return "Moderate"
  return "Low"
}

function conciseVerdict(verdict: string) {
  if (verdict === "TREND_BIASED") return "Trend-biased"
  if (verdict === "REVERSION_BIASED") return "Reversion-biased"
  return "Mixed"
}

function titleCase(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase())
}

function stabilityLabel(value: string | null | undefined) {
  return value ?? "Not run"
}

function recommendationSummary(
  verdict: string,
  strategyFit: EdgeMarketStructureProfile["summary"]["strategy_fit"],
  tradeabilityLabel: string | null | undefined
) {
  const archetype = strategyFit?.primary?.archetype?.replaceAll("_", " ") ?? "no recommendation"
  const friction = tradeabilityLabel ? `${tradeabilityLabel.toLowerCase()} tradeability` : "unknown tradeability"
  if (verdict === "TREND_BIASED") return `Bias favors trend structures. Best current fit is ${archetype} with ${friction}.`
  if (verdict === "REVERSION_BIASED") return `Bias favors range and reversion behavior. Best current fit is ${archetype} with ${friction}.`
  return `Structure is mixed. Treat ${archetype} cautiously and confirm with ${friction}.`
}

function modelQualityLabel(
  validationAccuracy: number | null | undefined,
  stabilityValue: string | null | undefined,
  robustnessValue: string | null | undefined
) {
  const strongValidation = (validationAccuracy ?? 0) >= 0.65
  const stable = stabilityValue === "HIGH" || stabilityValue === "MEDIUM"
  const robust = robustnessValue === "HIGH" || robustnessValue === "MEDIUM"
  if (strongValidation && stable && robust) return "Strong"
  if ((validationAccuracy ?? 0) >= 0.5 && (stable || robust)) return "Moderate"
  return "Early / weak"
}

export default function EdgeLabMarketStructurePage() {
  const {
    dataset,
    seasonalityResult,
    marketStructureProfile,
    setMarketStructureProfile,
    marketStructureStability,
    setMarketStructureStability,
    marketStructureRobustness,
    setMarketStructureRobustness,
  } = useEdgeLabData()
  const [saveDb, setSaveDb] = useState(true)
  const [loading, setLoading] = useState(false)
  const [runsLoading, setRunsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [runs, setRuns] = useState<EdgeMarketStructureRunRow[]>([])
  const [validation, setValidation] = useState<EdgeMarketStructureValidationReport | null>(null)
  const [evaluations, setEvaluations] = useState<EdgeMarketStructureEvaluationRow[]>([])
  const [calibration, setCalibration] = useState<EdgeMarketStructureCalibrationReport | null>(null)
  const [metricCalibration, setMetricCalibration] = useState<EdgeMarketStructureMetricCalibrationReport | null>(null)
  const [profileCalibration, setProfileCalibration] = useState<EdgeMarketStructureProfileCalibrationReport | null>(null)
  const [stabilityLoading, setStabilityLoading] = useState(false)
  const [robustnessLoading, setRobustnessLoading] = useState(false)
  const [evaluationsRefreshing, setEvaluationsRefreshing] = useState(false)

  const refreshRuns = async () => {
    setRunsLoading(true)
    try {
      const [runsResponse, validationResponse, evaluationsResponse, calibrationResponse, metricCalibrationResponse, profileCalibrationResponse] = await Promise.all([
        edgeLabApi.getMarketStructureRuns({ limit: 10 }),
        edgeLabApi.getMarketStructureValidation({ limit: 10, horizon_bars: 48 }),
        edgeLabApi.getMarketStructureEvaluations({ limit: 25 }),
        edgeLabApi.getMarketStructureCalibration({ limit: 25, horizon_bars: 48 }),
        edgeLabApi.getMarketStructureMetricCalibration({ limit: 25, horizon_bars: 48 }),
        edgeLabApi.getMarketStructureProfileCalibration({ limit: 100, horizon_bars: 48 }),
      ])
      setRuns(runsResponse)
      setValidation(validationResponse)
      setEvaluations(evaluationsResponse)
      setCalibration(calibrationResponse)
      setMetricCalibration(metricCalibrationResponse)
      setProfileCalibration(profileCalibrationResponse)
    } catch (err) {
      console.error("Failed to load Market Structure runs:", err)
    } finally {
      setRunsLoading(false)
    }
  }

  const refreshEvaluations = async () => {
    setEvaluationsRefreshing(true)
    setError(null)
    try {
      const validationResponse = await edgeLabApi.refreshMarketStructureEvaluations({ limit: 25, horizon_bars: 48 })
      setValidation(validationResponse)
      setEvaluations(await edgeLabApi.getMarketStructureEvaluations({ limit: 25 }))
      setCalibration(await edgeLabApi.getMarketStructureCalibration({ limit: 25, horizon_bars: 48 }))
      setMetricCalibration(await edgeLabApi.getMarketStructureMetricCalibration({ limit: 25, horizon_bars: 48 }))
      setProfileCalibration(await edgeLabApi.getMarketStructureProfileCalibration({ limit: 100, horizon_bars: 48 }))
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to refresh Market Structure evaluations.")
    } finally {
      setEvaluationsRefreshing(false)
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
      const response = await edgeLabApi.runMarketStructure({
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
      setMarketStructureProfile(response)
      await refreshRuns()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run Market Structure profile.")
    } finally {
      setLoading(false)
    }
  }

  const runStability = async () => {
    if (!dataset) {
      setError("Load a dataset in the Data tab first.")
      return
    }
    setStabilityLoading(true)
    setError(null)
    try {
      setMarketStructureStability(await edgeLabApi.getMarketStructureStability({
        symbol: dataset.request.symbol,
        timeframe: dataset.request.timeframe,
        data_source: dataset.request.data_source,
        range_by: dataset.request.range_by,
        start_date: dataset.request.start_date ?? undefined,
        end_date: dataset.request.end_date ?? undefined,
        number_of_bars: dataset.request.number_of_bars ?? undefined,
        prepared_dataset: dataset,
        save_db: false,
      }))
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run Market Structure stability.")
    } finally {
      setStabilityLoading(false)
    }
  }

  const runRobustness = async () => {
    if (!dataset) {
      setError("Load a dataset in the Data tab first.")
      return
    }
    setRobustnessLoading(true)
    setError(null)
    try {
      setMarketStructureRobustness(await edgeLabApi.getMarketStructureRobustness({
        symbol: dataset.request.symbol,
        timeframe: dataset.request.timeframe,
        data_source: dataset.request.data_source,
        range_by: dataset.request.range_by,
        start_date: dataset.request.start_date ?? undefined,
        end_date: dataset.request.end_date ?? undefined,
        number_of_bars: dataset.request.number_of_bars ?? undefined,
        prepared_dataset: dataset,
        save_db: false,
      }))
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run Market Structure robustness.")
    } finally {
      setRobustnessLoading(false)
    }
  }

  const loadRun = async (runId: number) => {
    setLoading(true)
    setError(null)
    try {
      setMarketStructureProfile(await edgeLabApi.getMarketStructureRun(runId))
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load Market Structure run.")
    } finally {
      setLoading(false)
    }
  }

  const deleteRun = async (runId: number) => {
    if (!window.confirm(`Delete market structure run #${runId}?`)) return
    try {
      await edgeLabApi.deleteMarketStructureRun(runId)
      if (marketStructureProfile?.run_id === runId) setMarketStructureProfile(null)
      await refreshRuns()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete Market Structure run.")
    }
  }

  const scoreRows = marketStructureProfile?.score_rows ?? []
  const swings: EdgeMarketStructureSwingPoint[] = marketStructureProfile?.swing_points ?? []
  const legs: EdgeMarketStructureLeg[] = marketStructureProfile?.trend_legs ?? []
  const edgeChartData = useMemo(() => buildMarketStructureEdgeChartData(runs), [runs])
  const tradeability = useMemo(() => buildTradeabilityModel(dataset), [dataset])
  const strategyFit = marketStructureProfile?.summary.strategy_fit
  const distribution = marketStructureProfile?.summary.distribution
  const breakoutAnalysis = marketStructureProfile?.summary.breakout_analysis
  const excursions = marketStructureProfile?.summary.excursions ?? {}
  const phase6Commentary = marketStructureProfile?.summary.phase6_commentary
  const regimeShare = marketStructureProfile?.summary.regime_share
  const regimeDurations = marketStructureProfile?.summary.regime_durations
  const regimeTransitions = marketStructureProfile?.summary.regime_transition_matrix
  const regimeConditionedMetrics = marketStructureProfile?.summary.regime_conditioned_metrics
  const regimeScoreInputs = marketStructureProfile?.summary.regime_score_inputs
  const currentProfileCalibration = useMemo(
    () => buildCurrentProfileCalibration(marketStructureProfile?.summary.profile_key, profileCalibration),
    [marketStructureProfile?.summary.profile_key, profileCalibration]
  )
  const regimeTimeline = useMemo(() => buildRegimeTimelineModel(marketStructureProfile), [marketStructureProfile])
  const qualityModel = useMemo(
    () =>
      buildMarketStructureQualityModel({
        profile: marketStructureProfile,
        stability: marketStructureStability,
        robustness: marketStructureRobustness,
      }),
    [marketStructureProfile, marketStructureStability, marketStructureRobustness]
  )

  if (!seasonalityResult) {
    return (
      <div className="flex flex-col gap-6 p-6">
        <EdgeLabPrerequisiteState
          title="Market Structure Requires Seasonality"
          description="Run Seasonality first so Market Structure can be treated as the next progressive step in the Edge Lab flow."
          actionHref="/edge-lab/seasonality"
          actionLabel="Go To Seasonality"
        />
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <GitBranch className="h-5 w-5 text-primary" />
            Market Structure
          </CardTitle>
          <CardDescription>
            Compare trend, range, mean-reversion, and chop evidence from the prepared dataset.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <EdgeLabDatasetSummary
            dataset={dataset}
            emptyMessage="Load a dataset in the Data tab before running Market Structure."
          />
          <EdgeLabControlToggle
            label="Save To Database"
            description="Persist score rows, swing points, and structure legs."
            checked={saveDb}
            onCheckedChange={setSaveDb}
          />
          <div className="flex items-center gap-3">
            <Button onClick={runProfile} disabled={loading || !dataset}>
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Run Market Structure
            </Button>
            <Button variant="outline" onClick={runStability} disabled={stabilityLoading || !dataset}>
              {stabilityLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Run Stability Snapshot
            </Button>
            <Button variant="outline" onClick={runRobustness} disabled={robustnessLoading || !dataset}>
              {robustnessLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Run Robustness Snapshot
            </Button>
            <Button variant="outline" onClick={refreshRuns} disabled={runsLoading}>
              <RefreshCcw className={cn("mr-2 h-4 w-4", runsLoading && "animate-spin")} />
              Refresh Saved Runs
            </Button>
            {error && <p className="text-sm text-destructive">{error}</p>}
          </div>
        </CardContent>
      </Card>

      {marketStructureProfile && (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>{marketStructureProfile.symbol} {marketStructureProfile.timeframe}</span>
                <Badge className={verdictTone(marketStructureProfile.summary.verdict)}>{marketStructureProfile.summary.verdict}</Badge>
              </CardTitle>
              <CardDescription>
                Final score {fmt(marketStructureProfile.summary.final_score, 2)}. Positive leans trend, negative leans reversion.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="mb-4 grid gap-4 md:grid-cols-2 xl:grid-cols-6">
                <div className="rounded-lg border p-4 xl:col-span-2">
                  <div className="text-sm text-muted-foreground">Research Conclusion</div>
                  <div className="mt-1 text-2xl font-semibold">{conciseVerdict(marketStructureProfile.summary.verdict)}</div>
                  <div className="mt-2 text-sm text-muted-foreground">
                    {recommendationSummary(marketStructureProfile.summary.verdict, strategyFit, tradeability?.label)}
                  </div>
                </div>
                <div className="rounded-lg border p-4">
                  <div className="text-sm text-muted-foreground">Decision Confidence</div>
                  <div className="mt-1 font-mono text-2xl">{fmt(marketStructureProfile.summary.decision_confidence_score, 1)}</div>
                  <div className="mt-2 text-xs text-muted-foreground">{confidenceLabel(marketStructureProfile.summary.decision_confidence_score)} confidence</div>
                </div>
                <div className="rounded-lg border p-4">
                  <div className="text-sm text-muted-foreground">Stability</div>
                  <div className="mt-1 text-2xl font-semibold">{stabilityLabel(marketStructureStability?.stability)}</div>
                  <div className="mt-2 text-xs text-muted-foreground">{marketStructureStability ? pct(marketStructureStability.agreement_rate, 1) : "Run snapshot to evaluate"}</div>
                </div>
                <div className="rounded-lg border p-4">
                  <div className="text-sm text-muted-foreground">Robustness</div>
                  <div className="mt-1 text-2xl font-semibold">{stabilityLabel(marketStructureRobustness?.robustness)}</div>
                  <div className="mt-2 text-xs text-muted-foreground">{marketStructureRobustness ? pct(marketStructureRobustness.verdict_agreement_rate, 1) : "Run snapshot to evaluate"}</div>
                </div>
                <div className="rounded-lg border p-4">
                  <div className="text-sm text-muted-foreground">Primary Strategy Fit</div>
                  <div className="mt-1 text-xl font-semibold capitalize">
                    {strategyFit?.primary?.archetype?.replaceAll("_", " ") ?? "Not run"}
                  </div>
                  <div className="mt-2 text-xs text-muted-foreground">
                    {strategyFit?.primary ? `${fmt(strategyFit.primary.fit_score, 1)} fit score` : "Run Market Structure to score archetypes"}
                  </div>
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
                <div className="rounded-lg border p-4">
                  <div className="text-sm text-muted-foreground">Trend Bias</div>
                  <div className="mt-1 font-mono text-2xl">{fmt(marketStructureProfile.summary.trend_bias_score, 2)}</div>
                  <div className="mt-2 text-xs text-muted-foreground">0 low to 100 strong trend bias</div>
                </div>
                <div className="rounded-lg border p-4">
                  <div className="text-sm text-muted-foreground">Trend Confidence</div>
                  <div className="mt-1 font-mono text-2xl">{fmt(marketStructureProfile.summary.trend_confidence_score, 2)}</div>
                  <div className="mt-2 text-xs text-muted-foreground">0 low to 100 trust in the trend-side read</div>
                </div>
                <div className="rounded-lg border p-4">
                  <div className="text-sm text-muted-foreground">Reversion Bias</div>
                  <div className="mt-1 font-mono text-2xl">{fmt(marketStructureProfile.summary.reversion_bias_score, 2)}</div>
                  <div className="mt-2 text-xs text-muted-foreground">0 low to 100 strong reversion bias</div>
                </div>
                <div className="rounded-lg border p-4">
                  <div className="text-sm text-muted-foreground">Reversion Confidence</div>
                  <div className="mt-1 font-mono text-2xl">{fmt(marketStructureProfile.summary.reversion_confidence_score, 2)}</div>
                  <div className="mt-2 text-xs text-muted-foreground">0 low to 100 trust in the reversion-side read</div>
                </div>
                <div className="rounded-lg border p-4">
                  <div className="text-sm text-muted-foreground">Decision Confidence</div>
                  <div className="mt-1 font-mono text-2xl">{fmt(marketStructureProfile.summary.decision_confidence_score, 2)}</div>
                  <div className="mt-2 text-xs text-muted-foreground">Confidence attached to the currently winning bias side</div>
                </div>
              </div>

              <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-6 text-sm">
                <div className="rounded-lg border p-4">
                  <div className="text-muted-foreground">Chop Score</div>
                  <div className="mt-1 font-mono text-xl">{fmt(marketStructureProfile.summary.chop_score, 2)}</div>
                  <div className="mt-2 text-xs text-muted-foreground">0 low to 100 high chop</div>
                </div>
                <div className="rounded-lg border p-4">
                  <div className="text-muted-foreground">Structure Direction</div>
                  <div className="mt-1 text-xl capitalize">{marketStructureProfile.summary.direction}</div>
                  <div className="mt-2 text-xs text-muted-foreground">Swing-based direction before reversion evidence is applied</div>
                </div>
                <div className="rounded-lg border p-4">
                  <div className="text-muted-foreground">Chains</div>
                  <div className="mt-1 font-mono text-xl">{marketStructureProfile.summary.chain_count}</div>
                  <div className="mt-2 text-xs text-muted-foreground">Directional sequence count</div>
                </div>
                <div className="rounded-lg border p-4">
                  <div className="text-muted-foreground">Pullbacks</div>
                  <div className="mt-1 font-mono text-xl">{marketStructureProfile.summary.pullback_leg_count}</div>
                  <div className="mt-2 text-xs text-muted-foreground">Pullback sample count</div>
                </div>
                <div className="rounded-lg border p-4">
                  <div className="text-muted-foreground">Continuation</div>
                  <div className="mt-1 font-mono text-xl">{pct(marketStructureProfile.summary.continuation_after_pullback_rate)}</div>
                  <div className="mt-2 text-xs text-muted-foreground">Continuation after pullbacks</div>
                </div>
                <div className="rounded-lg border p-4">
                  <div className="text-muted-foreground">Range Duration</div>
                  <div className="mt-1 font-mono text-xl">{fmt(marketStructureProfile.summary.range_duration_bars, 1)}</div>
                  <div className="mt-2 text-xs text-muted-foreground">Average bars spent in a detected range</div>
                </div>
                <div className="rounded-lg border p-4">
                  <div className="text-muted-foreground">False Breaks</div>
                  <div className="mt-1 font-mono text-xl">{pct(marketStructureProfile.summary.false_break_frequency)}</div>
                  <div className="mt-2 text-xs text-muted-foreground">Higher supports reversion / chop</div>
                </div>
                <div className="rounded-lg border p-4">
                  <div className="text-muted-foreground">Half-Life</div>
                  <div className="mt-1 font-mono text-xl">{fmt(marketStructureProfile.summary.half_life_bars, 1)}</div>
                  <div className="mt-2 text-xs text-muted-foreground">Lower means faster mean reversion</div>
                </div>
                <div className="rounded-lg border p-4">
                  <div className="text-muted-foreground">EDS-1 Exp</div>
                  <div className="mt-1 font-mono text-xl">{fmt(marketStructureProfile.summary.eds1_expectancy_r, 3)}</div>
                  <div className="mt-2 text-xs text-muted-foreground">Positive supports mean reversion</div>
                </div>
                <div className="rounded-lg border p-4">
                  <div className="text-muted-foreground">EDS-2 Exp</div>
                  <div className="mt-1 font-mono text-xl">{fmt(marketStructureProfile.summary.eds2_expectancy_r, 3)}</div>
                  <div className="mt-2 text-xs text-muted-foreground">Positive supports trend persistence</div>
                </div>
                <div className="rounded-lg border p-4">
                  <div className="text-muted-foreground">Whipsaw Rate</div>
                  <div className="mt-1 font-mono text-xl">{pct(marketStructureProfile.summary.whipsaw_rate)}</div>
                  <div className="mt-2 text-xs text-muted-foreground">Higher means more chop</div>
                </div>
                <div className="rounded-lg border p-4">
                  <div className="text-muted-foreground">Range Reentry</div>
                  <div className="mt-1 font-mono text-xl">{pct(marketStructureProfile.summary.reentry_probability)}</div>
                  <div className="mt-2 text-xs text-muted-foreground">Probability price reenters after breakout</div>
                </div>
                <div className="rounded-lg border p-4">
                  <div className="text-muted-foreground">Z-Score Reentry</div>
                  <div className="mt-1 font-mono text-xl">{pct(marketStructureProfile.summary.zscore_reentry_rate)}</div>
                  <div className="mt-2 text-xs text-muted-foreground">Rate extreme z-scores revert back inward</div>
                </div>
                <div className="rounded-lg border p-4">
                  <div className="text-muted-foreground">Run ID</div>
                  <div className="mt-1 font-mono text-xl">{marketStructureProfile.run_id ?? "Not saved"}</div>
                  <div className="mt-2 text-xs text-muted-foreground">Persisted database identifier</div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Tradeability Overlay</CardTitle>
              <CardDescription>
                Structural bias stays separate. This overlay estimates execution friction and basic exploitable movement from the loaded dataset.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {!tradeability ? (
                <p className="text-sm text-muted-foreground">Load a prepared dataset to evaluate tradeability.</p>
              ) : (
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-8">
                  <div className="rounded-lg border p-4">
                    <div className="text-sm text-muted-foreground">Tradeability</div>
                    <div className="mt-1 text-2xl font-semibold">{tradeability.label}</div>
                    <div className="mt-2 text-xs text-muted-foreground">Separate from the structural verdict</div>
                  </div>
                  <div className="rounded-lg border p-4">
                    <div className="text-sm text-muted-foreground">Tradeability Score</div>
                    <div className="mt-1 font-mono text-2xl">{fmt(tradeability.tradeabilityScore, 1)}</div>
                    <div className="mt-2 text-xs text-muted-foreground">0 low to 100 high execution friendliness</div>
                  </div>
                  <div className="rounded-lg border p-4">
                    <div className="text-sm text-muted-foreground">Avg Spread</div>
                    <div className="mt-1 font-mono text-2xl">{fmt(tradeability.avgSpreadPips, 2)}</div>
                    <div className="mt-2 text-xs text-muted-foreground">Average spread converted to pips</div>
                  </div>
                  <div className="rounded-lg border p-4">
                    <div className="text-sm text-muted-foreground">Spread / Range</div>
                    <div className="mt-1 font-mono text-2xl">{pct(tradeability.spreadToRange, 1)}</div>
                    <div className="mt-2 text-xs text-muted-foreground">Lower means structure leaves more room after friction</div>
                  </div>
                  <div className="rounded-lg border p-4">
                    <div className="text-sm text-muted-foreground">Active Bar Rate</div>
                    <div className="mt-1 font-mono text-2xl">{pct(tradeability.activityScore / 100, 1)}</div>
                    <div className="mt-2 text-xs text-muted-foreground">Share of bars with at least 5 pips of range</div>
                  </div>
                  <div className="rounded-lg border p-4">
                    <div className="text-sm text-muted-foreground">Worst Session</div>
                    <div className="mt-1 text-2xl font-semibold capitalize">{tradeability.worstSession ?? "Unknown"}</div>
                    <div className="mt-2 text-xs text-muted-foreground">
                      Avg spread {fmt(tradeability.worstSessionSpreadPips, 2)} pips
                    </div>
                  </div>
                  <div className="rounded-lg border p-4">
                    <div className="text-sm text-muted-foreground">Rollover Penalty</div>
                    <div className="mt-1 font-mono text-2xl">{fmt(tradeability.rolloverPenalty, 1)}</div>
                    <div className="mt-2 text-xs text-muted-foreground">Lower means rollover spreads are materially worse</div>
                  </div>
                  <div className="rounded-lg border p-4">
                    <div className="text-sm text-muted-foreground">Vol-Adj Burden</div>
                    <div className="mt-1 font-mono text-2xl">{fmt(tradeability.volatilityAdjustedBurden, 1)}</div>
                    <div className="mt-2 text-xs text-muted-foreground">Spread burden as a percent of average bar range</div>
                  </div>
                  <div className="rounded-lg border p-4">
                    <div className="text-sm text-muted-foreground">Liquidity Consistency</div>
                    <div className="mt-1 font-mono text-2xl">{fmt(tradeability.liquidityConsistencyScore, 1)}</div>
                    <div className="mt-2 text-xs text-muted-foreground">Higher means active movement is more consistent bar to bar</div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Distribution Deep Dive</CardTitle>
              <CardDescription>
                Return-shape diagnostics for tail behavior, percentiles, normality, and asymmetry.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {!distribution ? (
                <p className="text-sm text-muted-foreground">Run Market Structure to inspect distribution behavior.</p>
              ) : (
                <>
                  <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                    <div className="rounded-lg border p-4">
                      <div className="text-sm text-muted-foreground">Distribution Risk</div>
                      <div className="mt-1 text-2xl font-semibold">{phase6Commentary?.distribution_risk ?? "Unknown"}</div>
                      <div className="mt-2 text-xs text-muted-foreground">Normality-based read of tail and shape risk.</div>
                    </div>
                  </div>
                  <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                    <div className="rounded-lg border p-4">
                      <div className="text-sm text-muted-foreground">Normality Label</div>
                      <div className="mt-1 text-2xl font-semibold">{distribution.normality?.label ?? "Unknown"}</div>
                      <div className="mt-2 text-xs text-muted-foreground">Approximate diagnostic from skew, kurtosis, and Jarque-Bera shape</div>
                    </div>
                    <div className="rounded-lg border p-4">
                      <div className="text-sm text-muted-foreground">Skewness</div>
                      <div className="mt-1 font-mono text-2xl">{fmt(distribution.normality?.skewness, 3)}</div>
                      <div className="mt-2 text-xs text-muted-foreground">Positive means upside tail bias, negative means downside tail bias</div>
                    </div>
                    <div className="rounded-lg border p-4">
                      <div className="text-sm text-muted-foreground">Excess Kurtosis</div>
                      <div className="mt-1 font-mono text-2xl">{fmt(distribution.normality?.excess_kurtosis, 3)}</div>
                      <div className="mt-2 text-xs text-muted-foreground">Above 0 means fatter tails than a normal distribution</div>
                    </div>
                    <div className="rounded-lg border p-4">
                      <div className="text-sm text-muted-foreground">Tail Balance</div>
                      <div className="mt-1 font-mono text-2xl">{fmt(distribution.asymmetry?.tail_balance_ratio, 2)}</div>
                      <div className="mt-2 text-xs text-muted-foreground">Above 1 means upside tail is larger than downside tail</div>
                    </div>
                  </div>

                  <div className="grid gap-4 xl:grid-cols-2">
                    <div className="rounded-lg border">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Tail Metric</TableHead>
                            <TableHead className="text-right">Value</TableHead>
                            <TableHead>Meaning</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {Object.entries(distribution.tail_metrics ?? {}).map(([key, value]) => (
                            <TableRow key={key}>
                              <TableCell className="font-medium">{titleCase(key)}</TableCell>
                              <TableCell className="text-right font-mono">{fmt(value, 4)}</TableCell>
                              <TableCell className="text-sm text-muted-foreground">
                                Tail percentile or extreme return marker.
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                    <div className="rounded-lg border">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Distribution</TableHead>
                            <TableHead className="text-right">P05</TableHead>
                            <TableHead className="text-right">P25</TableHead>
                            <TableHead className="text-right">P50</TableHead>
                            <TableHead className="text-right">P75</TableHead>
                            <TableHead className="text-right">P95</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {Object.entries(distribution.percentile_tables ?? {}).map(([key, row]) => (
                            <TableRow key={key}>
                              <TableCell className="font-medium">{titleCase(key)}</TableCell>
                              <TableCell className="text-right font-mono">{fmt(row.p05, 4)}</TableCell>
                              <TableCell className="text-right font-mono">{fmt(row.p25, 4)}</TableCell>
                              <TableCell className="text-right font-mono">{fmt(row.p50, 4)}</TableCell>
                              <TableCell className="text-right font-mono">{fmt(row.p75, 4)}</TableCell>
                              <TableCell className="text-right font-mono">{fmt(row.p95, 4)}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Breakout and Retracement</CardTitle>
              <CardDescription>
                Deep-dive measures for breakout quality, retests, false breaks, and retracement behavior.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {!breakoutAnalysis ? (
                <p className="text-sm text-muted-foreground">Run Market Structure to inspect breakout quality.</p>
              ) : (
                <>
                  <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-2">
                    <div className="rounded-lg border p-4">
                      <div className="text-sm text-muted-foreground">Breakout Quality</div>
                      <div className="mt-1 text-2xl font-semibold">{phase6Commentary?.breakout_quality ?? "Unknown"}</div>
                      <div className="mt-2 text-xs text-muted-foreground">Combines follow-through, false-break pressure, and retest success.</div>
                    </div>
                    <div className="rounded-lg border p-4">
                      <div className="text-sm text-muted-foreground">Retracement Profile</div>
                      <div className="mt-1 text-2xl font-semibold">{phase6Commentary?.retracement_profile ?? "Unknown"}</div>
                      <div className="mt-2 text-xs text-muted-foreground">Healthy means shallower retracements with usable extension after breaks.</div>
                    </div>
                  </div>
                  <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
                    <div className="rounded-lg border p-4">
                      <div className="text-sm text-muted-foreground">Follow-Through</div>
                      <div className="mt-1 font-mono text-2xl">{pct(breakoutAnalysis.follow_through_probability)}</div>
                      <div className="mt-2 text-xs text-muted-foreground">Breakouts that continue instead of stalling</div>
                    </div>
                    <div className="rounded-lg border p-4">
                      <div className="text-sm text-muted-foreground">Failure Rate</div>
                      <div className="mt-1 font-mono text-2xl">{pct(breakoutAnalysis.failure_rate)}</div>
                      <div className="mt-2 text-xs text-muted-foreground">Breakouts that reverse back into failure</div>
                    </div>
                    <div className="rounded-lg border p-4">
                      <div className="text-sm text-muted-foreground">False-Break Reversal</div>
                      <div className="mt-1 font-mono text-2xl">{fmt(breakoutAnalysis.false_break_reversal_size_pips, 1)}</div>
                      <div className="mt-2 text-xs text-muted-foreground">Average reversal size after failed breaks, in pips</div>
                    </div>
                    <div className="rounded-lg border p-4">
                      <div className="text-sm text-muted-foreground">Retest Success</div>
                      <div className="mt-1 font-mono text-2xl">{pct(breakoutAnalysis.retest_success_rate)}</div>
                      <div className="mt-2 text-xs text-muted-foreground">Retests that still resolve in breakout direction</div>
                    </div>
                    <div className="rounded-lg border p-4">
                      <div className="text-sm text-muted-foreground">Avg Extension</div>
                      <div className="mt-1 font-mono text-2xl">{fmt(breakoutAnalysis.extension_behavior?.avg_extension_pips, 1)}</div>
                      <div className="mt-2 text-xs text-muted-foreground">Average favorable extension after break, in pips</div>
                    </div>
                  </div>

                  <div className="grid gap-4 xl:grid-cols-2">
                    <div className="rounded-lg border">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Retracement Depth</TableHead>
                            <TableHead className="text-right">Value</TableHead>
                            <TableHead>Meaning</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {Object.entries(breakoutAnalysis.retracement_depth_distribution ?? {}).map(([key, value]) => (
                            <TableRow key={key}>
                              <TableCell className="font-medium uppercase">{key}</TableCell>
                              <TableCell className="text-right font-mono">{fmt(value, 3)}</TableCell>
                              <TableCell className="text-sm text-muted-foreground">Retracement depth ratio after breakouts.</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                    <div className="rounded-lg border">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Extension Metric</TableHead>
                            <TableHead className="text-right">Value</TableHead>
                            <TableHead>Meaning</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {Object.entries(breakoutAnalysis.extension_behavior ?? {}).map(([key, value]) => (
                            <TableRow key={key}>
                              <TableCell className="font-medium">{titleCase(key)}</TableCell>
                              <TableCell className="text-right font-mono">{fmt(value, 2)}</TableCell>
                              <TableCell className="text-sm text-muted-foreground">Helps judge breakout quality and extension potential.</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Excursion Studies</CardTitle>
              <CardDescription>
                MFE/MAE, time-to-excursion, and stop/target proxy hit rates for breakout and pullback-resumption events.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {Object.keys(excursions).length === 0 ? (
                <p className="text-sm text-muted-foreground">Run Market Structure to inspect event excursions.</p>
              ) : (
                <div className="grid gap-4 xl:grid-cols-2">
                  {Object.entries(excursions).map(([eventType, study]) => (
                    <div key={eventType} className="rounded-lg border p-4 space-y-3">
                      <div>
                        <div className="text-sm text-muted-foreground">{titleCase(eventType)}</div>
                        <div className="mt-1 text-xl font-semibold">{study.count} events</div>
                        <div className="mt-1 text-xs text-muted-foreground">
                          {eventType === "breakout"
                            ? `Stop/target fit: ${phase6Commentary?.breakout_excursion_fit ?? "Unknown"}`
                            : `Stop/target fit: ${phase6Commentary?.pullback_excursion_fit ?? "Unknown"}`}
                        </div>
                      </div>
                      <div className="grid gap-3 md:grid-cols-2">
                        <div className="rounded border p-3 text-sm">
                          <div className="text-muted-foreground">Avg MFE</div>
                          <div className="mt-1 font-mono">{fmt(study.avg_mfe_pips, 2)} pips</div>
                        </div>
                        <div className="rounded border p-3 text-sm">
                          <div className="text-muted-foreground">Avg MAE</div>
                          <div className="mt-1 font-mono">{fmt(study.avg_mae_pips, 2)} pips</div>
                        </div>
                        <div className="rounded border p-3 text-sm">
                          <div className="text-muted-foreground">Time to MFE</div>
                          <div className="mt-1 font-mono">{fmt(study.time_to_mfe_bars, 1)} bars</div>
                        </div>
                        <div className="rounded border p-3 text-sm">
                          <div className="text-muted-foreground">Time to MAE</div>
                          <div className="mt-1 font-mono">{fmt(study.time_to_mae_bars, 1)} bars</div>
                        </div>
                      </div>
                      <div className="grid gap-3 md:grid-cols-2">
                        <div className="rounded border p-3 text-sm">
                          <div className="text-muted-foreground">Target Proxy Hit Rates</div>
                          <div className="mt-2 space-y-1 font-mono text-xs">
                            {Object.entries(study.target_hit_rates ?? {}).map(([key, value]) => (
                              <div key={key}>{key}: {pct(value, 1)}</div>
                            ))}
                          </div>
                        </div>
                        <div className="rounded border p-3 text-sm">
                          <div className="text-muted-foreground">Stop Proxy Hit Rates</div>
                          <div className="mt-2 space-y-1 font-mono text-xs">
                            {Object.entries(study.stop_hit_rates ?? {}).map(([key, value]) => (
                              <div key={key}>{key}: {pct(value, 1)}</div>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Regime Engine</CardTitle>
              <CardDescription>
                Trend, volatility, and liquidity states mapped bar by bar so analytics can be conditioned on market state instead of only global averages.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {!regimeShare || !regimeDurations || !regimeTransitions || !regimeConditionedMetrics || !regimeScoreInputs ? (
                <p className="text-sm text-muted-foreground">Run Market Structure to build the regime map and regime-aware inputs.</p>
              ) : (
                <>
                  <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-7">
                    <div className="rounded-lg border p-4">
                      <div className="text-sm text-muted-foreground">Timeline Bars</div>
                      <div className="mt-1 font-mono text-2xl">{regimeTimeline.length}</div>
                      <div className="mt-2 text-xs text-muted-foreground">Serialized regime timeline rows for dashboard consumers</div>
                    </div>
                    {Object.entries(regimeScoreInputs).map(([key, value]) => (
                      <div key={key} className="rounded-lg border p-4">
                        <div className="text-sm text-muted-foreground">{titleCase(key)}</div>
                        <div className="mt-1 font-mono text-2xl">{pct(value, 1)}</div>
                        <div className="mt-2 text-xs text-muted-foreground">Regime-conditioned score input share</div>
                      </div>
                    ))}
                  </div>

                  <div className="grid gap-4 xl:grid-cols-2">
                    <div className="rounded-lg border">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Trend Regime</TableHead>
                            <TableHead className="text-right">Share</TableHead>
                            <TableHead className="text-right">Avg Duration</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {Object.entries(regimeShare.trend ?? {}).map(([label, share]) => (
                            <TableRow key={label}>
                              <TableCell className="font-medium">{titleCase(label)}</TableCell>
                              <TableCell className="text-right font-mono">{pct(share, 1)}</TableCell>
                              <TableCell className="text-right font-mono">{fmt(regimeDurations.trend?.[label], 1)}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                    <div className="rounded-lg border">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Volatility / Liquidity</TableHead>
                            <TableHead className="text-right">Share</TableHead>
                            <TableHead className="text-right">Avg Duration</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {[
                            ...Object.entries(regimeShare.volatility ?? {}).map(([label, share]) => ({
                              group: "volatility",
                              label,
                              share,
                              duration: regimeDurations.volatility?.[label],
                            })),
                            ...Object.entries(regimeShare.liquidity ?? {}).map(([label, share]) => ({
                              group: "liquidity",
                              label,
                              share,
                              duration: regimeDurations.liquidity?.[label],
                            })),
                          ].map((row) => (
                            <TableRow key={`${row.group}-${row.label}`}>
                              <TableCell className="font-medium">{titleCase(row.group)}: {titleCase(row.label)}</TableCell>
                              <TableCell className="text-right font-mono">{pct(row.share, 1)}</TableCell>
                              <TableCell className="text-right font-mono">{fmt(row.duration, 1)}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </div>

                  <div className="grid gap-4 xl:grid-cols-2">
                    <div className="rounded-lg border">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Trend Transition</TableHead>
                            <TableHead className="text-right">Probability</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {Object.entries(regimeTransitions.trend ?? {}).flatMap(([from, row]) =>
                            Object.entries(row).map(([to, probability]) => (
                              <TableRow key={`${from}-${to}`}>
                                <TableCell className="font-medium">{titleCase(from)} {"->"} {titleCase(to)}</TableCell>
                                <TableCell className="text-right font-mono">{pct(probability, 1)}</TableCell>
                              </TableRow>
                            ))
                          )}
                        </TableBody>
                      </Table>
                    </div>
                    <div className="rounded-lg border">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Top Combined Regimes</TableHead>
                            <TableHead className="text-right">Share</TableHead>
                            <TableHead className="text-right">Avg Range</TableHead>
                            <TableHead className="text-right">Avg Spread</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {(regimeConditionedMetrics.combined ?? []).slice(0, 8).map((row, index) => (
                            <TableRow key={`${row.regime}-${index}`}>
                              <TableCell className="font-medium">{titleCase(row.regime)}</TableCell>
                              <TableCell className="text-right font-mono">{pct(row.share, 1)}</TableCell>
                              <TableCell className="text-right font-mono">{fmt(row.avg_range_pips, 1)}</TableCell>
                              <TableCell className="text-right font-mono">{fmt(row.avg_spread, 2)}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Calibration Metadata</CardTitle>
              <CardDescription>
                Runtime overrides and confidence adjustments applied to this Market Structure run.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {!marketStructureProfile.summary.calibration_metadata ? (
                <p className="text-sm text-muted-foreground">No calibration metadata stored for this run.</p>
              ) : (
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4 text-sm">
                  <div className="rounded-lg border p-4">
                    <div className="text-muted-foreground">Profile Overrides</div>
                    <div className="mt-2 font-mono text-xs whitespace-pre-wrap break-words">
                      {fmt((marketStructureProfile.summary.calibration_metadata as Record<string, unknown>).profile_overrides ?? {}, 2)}
                    </div>
                  </div>
                  <div className="rounded-lg border p-4">
                    <div className="text-muted-foreground">Stability Adjustment</div>
                    <div className="mt-2 font-mono text-xs whitespace-pre-wrap break-words">
                      {fmt((marketStructureProfile.summary.calibration_metadata as Record<string, unknown>).stability ?? {}, 2)}
                    </div>
                  </div>
                  <div className="rounded-lg border p-4">
                    <div className="text-muted-foreground">Robustness Adjustment</div>
                    <div className="mt-2 font-mono text-xs whitespace-pre-wrap break-words">
                      {fmt((marketStructureProfile.summary.calibration_metadata as Record<string, unknown>).robustness ?? {}, 2)}
                    </div>
                  </div>
                  <div className="rounded-lg border p-4">
                    <div className="text-muted-foreground">Confidence Deltas</div>
                    <div className="mt-2 font-mono text-xs whitespace-pre-wrap break-words">
                      {fmt({
                        trend: (marketStructureProfile.summary.calibration_metadata as Record<string, unknown>).trend_confidence_delta,
                        reversion: (marketStructureProfile.summary.calibration_metadata as Record<string, unknown>).reversion_confidence_delta,
                      }, 2)}
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Strategy Fit</CardTitle>
              <CardDescription>
                Archetype recommendations mapped from the current Market Structure profile, not a separate model.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {!strategyFit?.primary ? (
                <p className="text-sm text-muted-foreground">Run Market Structure to generate strategy-fit recommendations.</p>
              ) : (
                <>
                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="rounded-lg border p-4">
                      <div className="text-sm text-muted-foreground">Primary Archetype</div>
                      <div className="mt-1 text-2xl font-semibold capitalize">
                        {strategyFit.primary.archetype.replaceAll("_", " ")}
                      </div>
                      <div className="mt-2 font-mono text-lg">{fmt(strategyFit.primary.fit_score, 1)}</div>
                      <div className="mt-2 text-xs text-muted-foreground">{strategyFit.primary.rationale}</div>
                    </div>
                    <div className="rounded-lg border p-4">
                      <div className="text-sm text-muted-foreground">Interpretation</div>
                      <div className="mt-1 text-sm text-muted-foreground">
                        Higher fit means the current structure aligns better with that strategy archetype. Compare the primary fit against the alternatives before treating the recommendation as decisive.
                      </div>
                    </div>
                  </div>
                  <div className="rounded-lg border">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Rank</TableHead>
                          <TableHead>Archetype</TableHead>
                          <TableHead className="text-right">Fit</TableHead>
                          <TableHead>Rationale</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {(strategyFit.all ?? []).map((row, index) => (
                          <TableRow key={`${row.archetype}-${index}`}>
                            <TableCell>{index + 1}</TableCell>
                            <TableCell className="font-medium capitalize">{row.archetype.replaceAll("_", " ")}</TableCell>
                            <TableCell className="text-right font-mono">{fmt(row.fit_score, 1)}</TableCell>
                            <TableCell className="text-sm text-muted-foreground">{row.rationale}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Stability Snapshot</CardTitle>
              <CardDescription>
                Block-by-block Market Structure agreement across the currently loaded dataset.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {!marketStructureStability ? (
                <p className="text-sm text-muted-foreground">Run Market Structure to evaluate regime stability.</p>
              ) : !marketStructureStability.is_evaluable ? (
                <p className="text-sm text-muted-foreground">Not enough bars to evaluate stability with the current block settings.</p>
              ) : (
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                  <div className="rounded-lg border p-4">
                    <div className="text-sm text-muted-foreground">Stability</div>
                    <div className="mt-1 text-2xl font-semibold">{marketStructureStability.stability}</div>
                  </div>
                  <div className="rounded-lg border p-4">
                    <div className="text-sm text-muted-foreground">Verdict Agreement</div>
                    <div className="mt-1 font-mono text-2xl">{pct(marketStructureStability.agreement_rate, 1)}</div>
                  </div>
                  <div className="rounded-lg border p-4">
                    <div className="text-sm text-muted-foreground">Direction Agreement</div>
                    <div className="mt-1 font-mono text-2xl">{pct(marketStructureStability.direction_agreement_rate, 1)}</div>
                  </div>
                  <div className="rounded-lg border p-4">
                    <div className="text-sm text-muted-foreground">Score Drift</div>
                    <div className="mt-1 font-mono text-2xl">{fmt(marketStructureStability.final_score_std, 2)}</div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Robustness Snapshot</CardTitle>
              <CardDescription>
                Verdict consistency across nearby swing-window and ATR-threshold variants.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {!marketStructureRobustness ? (
                <p className="text-sm text-muted-foreground">Run Market Structure to evaluate parameter robustness.</p>
              ) : (
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                  <div className="rounded-lg border p-4">
                    <div className="text-sm text-muted-foreground">Robustness</div>
                    <div className="mt-1 text-2xl font-semibold">{marketStructureRobustness.robustness}</div>
                  </div>
                  <div className="rounded-lg border p-4">
                    <div className="text-sm text-muted-foreground">Verdict Agreement</div>
                    <div className="mt-1 font-mono text-2xl">{pct(marketStructureRobustness.verdict_agreement_rate, 1)}</div>
                  </div>
                  <div className="rounded-lg border p-4">
                    <div className="text-sm text-muted-foreground">Direction Agreement</div>
                    <div className="mt-1 font-mono text-2xl">{pct(marketStructureRobustness.direction_agreement_rate, 1)}</div>
                  </div>
                  <div className="rounded-lg border p-4">
                    <div className="text-sm text-muted-foreground">Score Drift</div>
                    <div className="mt-1 font-mono text-2xl">{fmt(marketStructureRobustness.final_score_std, 2)}</div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Profile Calibration</CardTitle>
              <CardDescription>
                Best calibration snapshot for this symbol/timeframe profile class.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {!marketStructureProfile?.summary.profile_key ? (
                <p className="text-sm text-muted-foreground">Run Market Structure to resolve the current symbol profile.</p>
              ) : !currentProfileCalibration ? (
                <p className="text-sm text-muted-foreground">No profile-specific calibration snapshot is available yet.</p>
              ) : (
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
                  <div className="rounded-lg border p-4">
                    <div className="text-sm text-muted-foreground">Profile</div>
                    <div className="mt-1 font-mono text-lg">{currentProfileCalibration.profile_key}</div>
                  </div>
                  <div className="rounded-lg border p-4">
                    <div className="text-sm text-muted-foreground">Best Accuracy</div>
                    <div className="mt-1 font-mono text-2xl">{pct(currentProfileCalibration.best.accuracy, 1)}</div>
                  </div>
                  <div className="rounded-lg border p-4">
                    <div className="text-sm text-muted-foreground">Gap</div>
                    <div className="mt-1 font-mono text-2xl">{fmt(currentProfileCalibration.best.settings.bias_verdict_min_gap, 0)}</div>
                  </div>
                  <div className="rounded-lg border p-4">
                    <div className="text-sm text-muted-foreground">Trend Conf Min</div>
                    <div className="mt-1 font-mono text-2xl">{fmt(currentProfileCalibration.best.settings.trend_confidence_min, 0)}</div>
                  </div>
                  <div className="rounded-lg border p-4">
                    <div className="text-sm text-muted-foreground">Reversion Conf Min</div>
                    <div className="mt-1 font-mono text-2xl">{fmt(currentProfileCalibration.best.settings.reversion_confidence_min, 0)}</div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Score Table</CardTitle>
              <CardDescription>
                Elements are listed in execution order with a reference scale for interpretation.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="mb-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                <div className="rounded-lg border p-3 text-sm">
                  <div className="text-muted-foreground">Direction Group Weight Total</div>
                  <div className="mt-1 font-mono">{fmt(groupWeightTotal(scoreRows, "direction"), 2)}</div>
                </div>
                <div className="rounded-lg border p-3 text-sm">
                  <div className="text-muted-foreground">Trend Confidence Group Weight Total</div>
                  <div className="mt-1 font-mono">{fmt(groupWeightTotal(scoreRows, "confidence"), 2)}</div>
                </div>
                <div className="rounded-lg border p-3 text-sm">
                  <div className="text-muted-foreground">Reversion Group Weight Total</div>
                  <div className="mt-1 font-mono">{fmt(groupWeightTotal(scoreRows, "reversion"), 2)}</div>
                </div>
                <div className="rounded-lg border p-3 text-sm">
                  <div className="text-muted-foreground">Chop Group Weight Total</div>
                  <div className="mt-1 font-mono">{fmt(groupWeightTotal(scoreRows, "chop"), 2)}</div>
                </div>
              </div>
              <div className="border rounded-lg overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Step</TableHead>
                      <TableHead>Group</TableHead>
                      <TableHead>Element</TableHead>
                      <TableHead>Raw</TableHead>
                      <TableHead className="min-w-[240px]">Reference</TableHead>
                      <TableHead className="text-right">Score</TableHead>
                      <TableHead className="min-w-[180px]">Meaning</TableHead>
                      <TableHead className="text-right">Group Weight</TableHead>
                      <TableHead className="text-right">Group Contribution</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {scoreRows.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={9} className="text-sm text-muted-foreground">
                          Score rows are empty for this profile.
                        </TableCell>
                      </TableRow>
                    ) : (
                      scoreRows.map((row, index) => (
                        <TableRow key={`${row.group ?? "group"}-${row.key}-${index}`}>
                          <TableCell className="font-mono">{index + 1}</TableCell>
                          <TableCell><Badge className={groupTone(row.group)} variant="secondary">{row.group ?? "unknown"}</Badge></TableCell>
                          <TableCell className="min-w-[220px]">
                            <div className="font-medium">{row.label}</div>
                            <div className="text-xs text-muted-foreground">{row.notes}</div>
                          </TableCell>
                          <TableCell className="max-w-[220px] whitespace-normal break-words font-mono text-xs align-top">{fmt(row.raw_value, 3)}</TableCell>
                          <TableCell className="min-w-[240px] max-w-[280px] whitespace-normal break-words text-xs text-muted-foreground align-top">{referenceText(row)}</TableCell>
                          <TableCell className="whitespace-nowrap text-right font-mono align-top">{fmt(row.score, 2)}</TableCell>
                          <TableCell className="min-w-[180px] max-w-[220px] whitespace-normal break-words text-sm align-top">{meaningText(row)}</TableCell>
                          <TableCell className="whitespace-nowrap text-right font-mono align-top">{fmt(row.weight, 2)}</TableCell>
                          <TableCell className="whitespace-nowrap text-right font-mono align-top">{fmt(row.contribution, 2)}</TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>

          <div className="grid gap-6 xl:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Swing Audit</CardTitle>
                <CardDescription>Confirmed swing points and HH / HL / LH / LL labels.</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="border rounded-lg overflow-hidden">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Time</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead>Label</TableHead>
                        <TableHead className="text-right">Price</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {swings.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={4} className="text-sm text-muted-foreground">No swing points detected.</TableCell>
                        </TableRow>
                      ) : (
                        swings.map((point, index) => (
                          <TableRow key={`${point.timestamp}-${index}`}>
                            <TableCell>{ts(point.timestamp)}</TableCell>
                            <TableCell>{point.swing_type}</TableCell>
                            <TableCell><Badge variant="outline">{point.label}</Badge></TableCell>
                            <TableCell className="text-right font-mono">{fmt(point.price, 5)}</TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Structure Legs</CardTitle>
                <CardDescription>Amplitude, duration, efficiency, and pullback continuation detail.</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="border rounded-lg overflow-hidden">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Direction</TableHead>
                        <TableHead className="text-right">Amp</TableHead>
                        <TableHead className="text-right">Bars</TableHead>
                        <TableHead className="text-right">Eff.</TableHead>
                        <TableHead className="text-right">Consistency</TableHead>
                        <TableHead className="text-right">Cont.</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {legs.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={6} className="text-sm text-muted-foreground">No structure legs detected.</TableCell>
                        </TableRow>
                      ) : (
                        legs.map((leg, index) => (
                          <TableRow key={`${leg.start_time}-${leg.end_time}-${index}`}>
                            <TableCell>{leg.direction}</TableCell>
                            <TableCell className="text-right font-mono">{fmt(leg.amplitude_pips, 1)}</TableCell>
                            <TableCell className="text-right font-mono">{leg.duration_bars}</TableCell>
                            <TableCell className="text-right font-mono">{fmt(leg.efficiency_ratio, 2)}</TableCell>
                            <TableCell className="text-right font-mono">{fmt(leg.directional_consistency, 2)}</TableCell>
                            <TableCell className="text-right font-mono">
                              {normalizeContinuation(leg.continuation_after_pullback) === null
                                ? "—"
                                : normalizeContinuation(leg.continuation_after_pullback)
                                  ? "Yes"
                                  : "No"}
                            </TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          </div>
        </>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Saved Market Structure Runs</CardTitle>
          <CardDescription>Recent persisted market-structure profiles for review and comparison.</CardDescription>
        </CardHeader>
        <CardContent>
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>Model Quality</CardTitle>
              <CardDescription>
                Compact read of current validation, calibration, stability, and robustness quality.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
                <div className="rounded-lg border p-4">
                  <div className="text-sm text-muted-foreground">Overall</div>
                  <div className="mt-1 text-2xl font-semibold">
                    {modelQualityLabel(validation?.summary.accuracy, qualityModel?.stability, qualityModel?.robustness)}
                  </div>
                  <div className="mt-2 text-xs text-muted-foreground">High-level read of current model evidence quality</div>
                </div>
                <div className="rounded-lg border p-4">
                  <div className="text-sm text-muted-foreground">Validation Accuracy</div>
                  <div className="mt-1 font-mono text-2xl">{validation ? pct(validation.summary.accuracy, 1) : "â€”"}</div>
                  <div className="mt-2 text-xs text-muted-foreground">Predicted versus realized verdict agreement</div>
                </div>
                <div className="rounded-lg border p-4">
                  <div className="text-sm text-muted-foreground">Top-Level Calibration</div>
                  <div className="mt-1 font-mono text-2xl">{calibration?.best ? pct(calibration.best.accuracy, 1) : "â€”"}</div>
                  <div className="mt-2 text-xs text-muted-foreground">Best verdict-threshold snapshot accuracy</div>
                </div>
                <div className="rounded-lg border p-4">
                  <div className="text-sm text-muted-foreground">Metric Calibration</div>
                  <div className="mt-1 font-mono text-2xl">{metricCalibration?.best ? pct(metricCalibration.best.accuracy, 1) : "â€”"}</div>
                  <div className="mt-2 text-xs text-muted-foreground">Best lower-level band snapshot accuracy</div>
                </div>
                <div className="rounded-lg border p-4">
                  <div className="text-sm text-muted-foreground">Stability / Robustness</div>
                  <div className="mt-1 text-xl font-semibold">
                    {qualityModel?.stability ?? "Not run"} / {qualityModel?.robustness ?? "Not run"}
                  </div>
                  <div className="mt-2 text-xs text-muted-foreground">Dataset block stability and nearby-parameter resilience</div>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="mb-6">
            <CardHeader>
              <div className="flex items-center justify-between gap-3">
                <div>
                  <CardTitle>Forward Validation</CardTitle>
                  <CardDescription>
                    Saved runs compared against a simple realized-behavior label over the next 48 bars.
                  </CardDescription>
                </div>
                <Button variant="outline" size="sm" onClick={refreshEvaluations} disabled={evaluationsRefreshing}>
                  <RefreshCcw className={cn("mr-2 h-4 w-4", evaluationsRefreshing && "animate-spin")} />
                  Refresh Evaluations
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {!validation ? (
                <p className="text-sm text-muted-foreground">No validation data available yet.</p>
              ) : (
                <>
                  <div className="grid gap-4 md:grid-cols-3">
                  <div className="rounded-lg border p-4">
                    <div className="text-sm text-muted-foreground">Evaluated Runs</div>
                    <div className="mt-1 font-mono text-2xl">{validation.summary.evaluated_runs}</div>
                  </div>
                    <div className="rounded-lg border p-4">
                      <div className="text-sm text-muted-foreground">Matched Runs</div>
                      <div className="mt-1 font-mono text-2xl">{validation.summary.matched_runs}</div>
                    </div>
                    <div className="rounded-lg border p-4">
                      <div className="text-sm text-muted-foreground">Accuracy</div>
                      <div className="mt-1 font-mono text-2xl">{pct(validation.summary.accuracy, 1)}</div>
                    </div>
                    <div className="rounded-lg border p-4">
                      <div className="text-sm text-muted-foreground">Persisted Eval Rows</div>
                      <div className="mt-1 font-mono text-2xl">{evaluations.length}</div>
                    </div>
                  </div>
                  <div className="grid gap-4 md:grid-cols-3">
                    <div className="rounded-lg border p-4">
                      <div className="text-sm text-muted-foreground">By Verdict</div>
                      <div className="mt-2 space-y-1 text-sm">
                        {Object.entries(validation.summary.by_predicted_verdict).slice(0, 3).map(([key, value]) => (
                          <div key={key} className="flex items-center justify-between gap-2">
                            <span>{key}</span>
                            <span className="font-mono">{value.total}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                    <div className="rounded-lg border p-4">
                      <div className="text-sm text-muted-foreground">By Confidence</div>
                      <div className="mt-2 space-y-1 text-sm">
                        {Object.entries(validation.summary.by_confidence_bucket).slice(0, 3).map(([key, value]) => (
                          <div key={key} className="flex items-center justify-between gap-2">
                            <span>{key}</span>
                            <span className="font-mono">{value.correct}/{value.total}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                    <div className="rounded-lg border p-4">
                      <div className="text-sm text-muted-foreground">By Timeframe</div>
                      <div className="mt-2 space-y-1 text-sm">
                        {Object.entries(validation.summary.by_timeframe).slice(0, 3).map(([key, value]) => (
                          <div key={key} className="flex items-center justify-between gap-2">
                            <span>{key}</span>
                            <span className="font-mono">{value.correct}/{value.total}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                  <div className="border rounded-lg overflow-hidden">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Run</TableHead>
                          <TableHead>Symbol</TableHead>
                          <TableHead>Predicted</TableHead>
                          <TableHead>Realized</TableHead>
                          <TableHead>Match</TableHead>
                          <TableHead>Conf.</TableHead>
                          <TableHead>Continuation</TableHead>
                          <TableHead>Reentry</TableHead>
                          <TableHead>Break Fail</TableHead>
                          <TableHead>Chop</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {validation.rows.length === 0 ? (
                          <TableRow>
                            <TableCell colSpan={10} className="text-sm text-muted-foreground">
                              No runs had enough forward data for validation.
                            </TableCell>
                          </TableRow>
                        ) : (
                          validation.rows.map((row, index) => (
                            <TableRow key={`${row.run_id}-${index}`}>
                              <TableCell className="font-mono">#{row.run_id}</TableCell>
                              <TableCell>{row.symbol}</TableCell>
                              <TableCell>{row.predicted_verdict}</TableCell>
                              <TableCell>{row.realized_verdict}</TableCell>
                              <TableCell>{row.matched ? "Yes" : "No"}</TableCell>
                              <TableCell>{row.confidence_bucket}</TableCell>
                              <TableCell>{row.continuation_label ?? "â€”"}</TableCell>
                              <TableCell>{row.range_reentry_label ?? "â€”"}</TableCell>
                              <TableCell>{row.breakout_failure_label ?? "â€”"}</TableCell>
                              <TableCell>{row.chop_label ?? "â€”"}</TableCell>
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
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>Persisted Evaluations</CardTitle>
              <CardDescription>
                Stored forward-evaluation rows for research review and traceability.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="border rounded-lg overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Run</TableHead>
                      <TableHead>Symbol</TableHead>
                      <TableHead>Timeframe</TableHead>
                      <TableHead>Predicted</TableHead>
                      <TableHead>Realized</TableHead>
                      <TableHead>Match</TableHead>
                      <TableHead>Confidence</TableHead>
                      <TableHead>Metadata</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {evaluations.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={8} className="text-sm text-muted-foreground">
                          No persisted evaluations yet. Use Refresh Evaluations to build the research dataset.
                        </TableCell>
                      </TableRow>
                    ) : (
                      evaluations.map((row, index) => (
                        <TableRow key={`${row.run_id}-${index}`}>
                          <TableCell className="font-mono">#{row.run_id}</TableCell>
                          <TableCell>{row.symbol}</TableCell>
                          <TableCell>{row.timeframe}</TableCell>
                          <TableCell>{row.predicted_verdict}</TableCell>
                          <TableCell>{row.realized_verdict}</TableCell>
                          <TableCell>{row.matched ? "Yes" : "No"}</TableCell>
                          <TableCell>{row.confidence_bucket}</TableCell>
                          <TableCell>{row.calibration_metadata ? "Stored" : "—"}</TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>Calibration Snapshot</CardTitle>
              <CardDescription>
                Best top-level verdict settings from a small threshold grid, ranked against the current forward-validation sample.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {!calibration?.best ? (
                <p className="text-sm text-muted-foreground">No calibration snapshot available yet.</p>
              ) : (
                <div className="grid gap-4 md:grid-cols-3 xl:grid-cols-6">
                  <div className="rounded-lg border p-4">
                    <div className="text-sm text-muted-foreground">Best Accuracy</div>
                    <div className="mt-1 font-mono text-2xl">{pct(calibration.best.accuracy, 1)}</div>
                  </div>
                  <div className="rounded-lg border p-4">
                    <div className="text-sm text-muted-foreground">Gap</div>
                    <div className="mt-1 font-mono text-2xl">{fmt(calibration.best.settings.bias_verdict_min_gap, 0)}</div>
                  </div>
                  <div className="rounded-lg border p-4">
                    <div className="text-sm text-muted-foreground">Trend Conf Min</div>
                    <div className="mt-1 font-mono text-2xl">{fmt(calibration.best.settings.trend_confidence_min, 0)}</div>
                  </div>
                  <div className="rounded-lg border p-4">
                    <div className="text-sm text-muted-foreground">Reversion Conf Min</div>
                    <div className="mt-1 font-mono text-2xl">{fmt(calibration.best.settings.reversion_confidence_min, 0)}</div>
                  </div>
                  <div className="rounded-lg border p-4">
                    <div className="text-sm text-muted-foreground">Reversion Weight</div>
                    <div className="mt-1 font-mono text-2xl">{fmt(calibration.best.settings.reversion_score_weight, 2)}</div>
                  </div>
                  <div className="rounded-lg border p-4">
                    <div className="text-sm text-muted-foreground">Chop Weight</div>
                    <div className="mt-1 font-mono text-2xl">{fmt(calibration.best.settings.chop_score_weight, 2)}</div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>Metric Calibration</CardTitle>
              <CardDescription>
                Best lower-level score bands from a small grid over chain strength, half-life, choppiness, and direction-flip normalization.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {!metricCalibration?.best ? (
                <p className="text-sm text-muted-foreground">No metric calibration snapshot available yet.</p>
              ) : (
                <div className="grid gap-4 md:grid-cols-3 xl:grid-cols-5">
                  <div className="rounded-lg border p-4">
                    <div className="text-sm text-muted-foreground">Best Accuracy</div>
                    <div className="mt-1 font-mono text-2xl">{pct(metricCalibration.best.accuracy, 1)}</div>
                  </div>
                  <div className="rounded-lg border p-4">
                    <div className="text-sm text-muted-foreground">Chain Band</div>
                    <div className="mt-1 font-mono text-2xl">
                      {fmt(metricCalibration.best.settings.chain_strength_lo, 1)}-{fmt(metricCalibration.best.settings.chain_strength_hi, 1)}
                    </div>
                  </div>
                  <div className="rounded-lg border p-4">
                    <div className="text-sm text-muted-foreground">Pullback Band</div>
                    <div className="mt-1 font-mono text-2xl">
                      {fmt(metricCalibration.best.settings.pullback_depth_lo, 1)}-{fmt(metricCalibration.best.settings.pullback_depth_hi, 1)}
                    </div>
                  </div>
                  <div className="rounded-lg border p-4">
                    <div className="text-sm text-muted-foreground">Half-Life Band</div>
                    <div className="mt-1 font-mono text-2xl">
                      {fmt(metricCalibration.best.settings.half_life_lo, 0)}-{fmt(metricCalibration.best.settings.half_life_hi, 0)}
                    </div>
                  </div>
                  <div className="rounded-lg border p-4">
                    <div className="text-sm text-muted-foreground">False-Break Band</div>
                    <div className="mt-1 font-mono text-2xl">
                      {fmt(metricCalibration.best.settings.false_break_lo, 2)}-{fmt(metricCalibration.best.settings.false_break_hi, 2)}
                    </div>
                  </div>
                  <div className="rounded-lg border p-4">
                    <div className="text-sm text-muted-foreground">Choppiness Band</div>
                    <div className="mt-1 font-mono text-2xl">
                      {fmt(metricCalibration.best.settings.choppiness_lo, 0)}-{fmt(metricCalibration.best.settings.choppiness_hi, 0)}
                    </div>
                  </div>
                  <div className="rounded-lg border p-4">
                    <div className="text-sm text-muted-foreground">Flip-Rate Band</div>
                    <div className="mt-1 font-mono text-2xl">
                      {fmt(metricCalibration.best.settings.direction_flip_lo, 2)}-{fmt(metricCalibration.best.settings.direction_flip_hi, 2)}
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>Market Structure Edge Chart</CardTitle>
              <CardDescription>
                Latest saved run per symbol, compared by final Market Structure score.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[320px]">
                {edgeChartData.length === 0 ? (
                  <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                    Save Market Structure runs to compare symbols here.
                  </div>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={edgeChartData} margin={{ top: 12, right: 20, left: 0, bottom: 12 }}>
                      <CartesianGrid vertical={false} strokeDasharray="3 3" opacity={0.25} />
                      <XAxis dataKey="symbol" tickLine={false} axisLine={false} />
                      <YAxis tickLine={false} axisLine={false} domain={[-100, 100]} />
                      <Tooltip
                        cursor={{ fill: "transparent" }}
                        contentStyle={{
                          backgroundColor: "hsl(var(--card))",
                          borderColor: "hsl(var(--border))",
                          borderRadius: "var(--radius)",
                        }}
                        formatter={(value: number, _name, item) => [
                          `${value.toFixed(2)}`,
                          `${item.payload.verdict} (#${item.payload.runId})`,
                        ]}
                      />
                      <Bar dataKey="score" radius={[6, 6, 0, 0]} maxBarSize={56}>
                        {edgeChartData.map((entry, index) => (
                          <Cell key={`${entry.symbol}-${index}`} fill={chartBarColor(entry.score)} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </div>
            </CardContent>
          </Card>
          <EdgeLabCollectionState loading={runsLoading} hasItems={runs.length > 0} emptyMessage="No saved Market Structure runs yet.">
            <div className="border rounded-lg overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Run</TableHead>
                    <TableHead>Symbol</TableHead>
                    <TableHead>Timeframe</TableHead>
                    <TableHead className="text-right">Score</TableHead>
                    <TableHead>Verdict</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead className="text-right">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {runs.map((run, index) => (
                    <TableRow key={`${run.run_id}-${index}`}>
                      <TableCell className="font-mono">#{run.run_id}</TableCell>
                      <TableCell>{run.symbol}</TableCell>
                      <TableCell>{run.timeframe}</TableCell>
                      <TableCell className="text-right font-mono">{fmt(run.summary?.final_score, 2)}</TableCell>
                      <TableCell>
                        {run.summary?.verdict ? <Badge className={verdictTone(String(run.summary.verdict))}>{String(run.summary.verdict)}</Badge> : "—"}
                      </TableCell>
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
