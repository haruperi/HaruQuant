"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import type {
  SimulationGovernanceReport,
  SimulationRecommendationSummary,
  SimulationRiskSnapshotSummary,
  SimulationRiskScorecardSummary,
  SimulationWhatIfAction,
  SimulationWhatIfComparison,
} from "@/lib/api/simulator"

export interface AccountMetrics {
  balance: number
  equity: number
  margin: number
  margin_free?: number
  margin_level?: number
  profit: number
  has_errors?: boolean
  has_warnings?: boolean
  validation_issues?: any[] | number
}

interface AccountMetricsProps {
  metrics: AccountMetrics
  riskSnapshot?: SimulationRiskSnapshotSummary
  riskScorecard?: SimulationRiskScorecardSummary
  recommendations?: SimulationRecommendationSummary
  governanceReport?: SimulationGovernanceReport | null
  whatIfComparison?: SimulationWhatIfComparison | null
  whatIfLoading?: boolean
  positions?: Array<{
    id: number
    symbol: string
    type: string
    volume: number
  }>
  symbols?: string[]
  currentLeverage?: number | null
  onEvaluateWhatIf?: (payload: {
    actions?: SimulationWhatIfAction[]
    leverage_override?: number
  }) => Promise<void> | void
}

function formatRiskValue(label: string, value: number | string | null | undefined) {
  if (value === null || value === undefined || value === "") return "--"
  if (typeof value === "string") return value
  if (label.includes("%")) return `${(value * 100).toFixed(2)}%`
  return value.toFixed(2)
}

export function AccountMetricsBar({
  metrics,
  riskSnapshot,
  riskScorecard,
  recommendations,
  governanceReport,
  whatIfComparison,
  whatIfLoading,
  positions = [],
  symbols = [],
  currentLeverage,
  onEvaluateWhatIf,
}: AccountMetricsProps) {
  const [selectedPositionId, setSelectedPositionId] = useState<string>("")
  const [hedgeSymbol, setHedgeSymbol] = useState<string>(symbols[0] || "")
  const [hedgeSide, setHedgeSide] = useState<"buy" | "sell">("sell")
  const [hedgeLots, setHedgeLots] = useState("0.10")
  const [proposedLeverage, setProposedLeverage] = useState(
    currentLeverage ? String(currentLeverage) : "100"
  )
  const profitClass = metrics.profit >= 0 ? "text-emerald-500" : "text-red-500"
  const marginUsed = Number(metrics.margin ?? 0)
  const marginUsedFrac =
    typeof riskSnapshot?.margin_used_frac === "number"
      ? riskSnapshot.margin_used_frac
      : metrics.equity > 0
        ? marginUsed / metrics.equity
        : null
  const riskSummaryItems = [
    { label: "Gross Exposure", value: riskSnapshot?.gross_exposure },
    { label: "Net Exposure", value: riskSnapshot?.net_exposure },
    { label: "Portfolio VaR", value: riskSnapshot?.portfolio_var },
    { label: "Portfolio CVaR", value: riskSnapshot?.portfolio_es },
    { label: "Max Single Exposure %", value: riskSnapshot?.max_single_exposure_frac },
    { label: "Avg Correlation", value: riskSnapshot?.average_pair_correlation },
    { label: "Max Correlation", value: riskSnapshot?.max_pair_correlation },
    { label: "Hidden Overlap", value: riskSnapshot?.hidden_overlap_score },
    { label: "Compliance", value: riskSnapshot?.compliance_state },
  ]
  const scoreItems = [
    { label: "Portfolio Health", value: riskScorecard?.portfolio_health_score },
    { label: "Leverage Safety", value: riskScorecard?.leverage_safety_score },
    { label: "Margin Safety", value: riskScorecard?.margin_safety_score },
    { label: "Diversification", value: riskScorecard?.diversification_score },
    { label: "Governance Compliance", value: riskScorecard?.governance_compliance_score },
    { label: "Overall Risk Quality", value: riskScorecard?.overall_risk_quality_score },
  ]
  const riskStatusTone =
    (governanceReport?.compliance_state || riskSnapshot?.compliance_state) === "breach"
      ? "border-red-500/40 bg-red-500/10"
      : (governanceReport?.compliance_state || riskSnapshot?.compliance_state) === "warning"
        ? "border-amber-500/40 bg-amber-500/10"
        : "border-border bg-muted/20"
  const governanceEvents = [
    ...(governanceReport?.breaches || []),
    ...(governanceReport?.warnings || []),
  ]
  const regimeWarnings = riskSnapshot?.regime_warnings || []
  const regimeSignals = riskSnapshot?.regime_signals_triggered || []
  const currencyExposure = riskSnapshot?.currency_exposure || []
  const currencyWeights = riskSnapshot?.currency_weights || []
  const recommendationItems = recommendations?.items || []
  const whatIfSummary = whatIfComparison?.summary
  const whatIfProjected = whatIfComparison?.projected
  const whatIfRecommendations = whatIfComparison?.projected_recommendations?.items || []
  const effectiveSelectedPositionId =
    positions.some((position) => String(position.id) === selectedPositionId)
      ? selectedPositionId
      : positions[0]
        ? String(positions[0].id)
        : ""
  const effectiveHedgeSymbol = symbols.includes(hedgeSymbol) ? hedgeSymbol : (symbols[0] || "")
  const effectiveProposedLeverage =
    proposedLeverage.trim() !== ""
      ? proposedLeverage
      : currentLeverage && currentLeverage > 0
        ? String(currentLeverage)
        : "100"

  const formatRecommendationAction = (action?: string | null, symbol?: string | null) => {
    const symbolLabel = symbol || "symbol"
    if (action === "reduce") return `Reduce ${symbolLabel}`
    if (action === "hedge") return `Hedge ${symbolLabel}`
    if (action === "cut_margin") return `Cut Margin Pressure`
    if (action === "rebalance") return `Rebalance ${symbolLabel}`
    return `${action || "Action"} ${symbolLabel}`.trim()
  }

  const handleCloseHalfWhatIf = () => {
    const position = positions.find((item) => String(item.id) === effectiveSelectedPositionId)
    if (!position || !onEvaluateWhatIf) {
      return
    }
    onEvaluateWhatIf({
      actions: [
        {
          action_type: "reduce",
          symbol: position.symbol,
          delta_lots: Math.abs(Number(position.volume || 0)) / 2,
          rationale: `Close half of ${position.symbol}`,
        },
      ],
    })
  }

  const handleHedgeWhatIf = () => {
    if (!effectiveHedgeSymbol || !onEvaluateWhatIf) {
      return
    }
    const lots = Number(hedgeLots)
    if (!lots || Number.isNaN(lots) || lots <= 0) {
      return
    }
    onEvaluateWhatIf({
      actions: [
        {
          action_type: "hedge",
          symbol: effectiveHedgeSymbol,
          delta_lots: hedgeSide === "buy" ? lots : -lots,
          rationale: `Add ${hedgeSide} hedge on ${effectiveHedgeSymbol}`,
        },
      ],
    })
  }

  const handleLeverageWhatIf = () => {
    const leverage = Number(effectiveProposedLeverage)
    if (!leverage || Number.isNaN(leverage) || leverage <= 0 || !onEvaluateWhatIf) {
      return
    }
    onEvaluateWhatIf({
      leverage_override: leverage,
    })
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">Portfolio State</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-4 text-sm md:grid-cols-5 lg:grid-cols-10">
          <div className="space-y-1">
            <div className="text-muted-foreground">Balance</div>
            <div className="font-medium">{metrics.balance.toFixed(2)}</div>
          </div>
          <div className="space-y-1">
            <div className="text-muted-foreground">Equity</div>
            <div className="font-medium">{metrics.equity.toFixed(2)}</div>
          </div>
          <div className="space-y-1">
            <div className="text-muted-foreground">Free Margin</div>
            <div className="font-medium">
              {Number(metrics.margin_free ?? 0).toFixed(2)}
            </div>
          </div>
          <div className="space-y-1">
            <div className="text-muted-foreground">Margin Used</div>
            <div className="font-medium">{marginUsed.toFixed(2)}</div>
          </div>
          <div className="space-y-1">
            <div className="text-muted-foreground">Margin Used %</div>
            <div className="font-medium">{formatRiskValue("Margin Used %", marginUsedFrac)}</div>
          </div>
          <div className="space-y-1">
            <div className="text-muted-foreground">Margin Level</div>
            <div className="font-medium">
              {Number(metrics.margin_level ?? 0).toFixed(2)}%
            </div>
          </div>
          <div className="space-y-1">
            <div className="text-muted-foreground">Profit</div>
            <div className={`font-medium ${profitClass}`}>{metrics.profit.toFixed(2)}</div>
          </div>
          <div className="space-y-1">
            <div className="text-muted-foreground">Errors</div>
            <div className="font-medium">{metrics.has_errors ? "Yes" : "No"}</div>
          </div>
          <div className="space-y-1">
            <div className="text-muted-foreground">Warnings</div>
            <div className="font-medium">{metrics.has_warnings ? "Yes" : "No"}</div>
          </div>
          <div className="space-y-1">
            <div className="text-muted-foreground">Issues</div>
            <div className="font-medium">
              {Array.isArray(metrics.validation_issues) ? metrics.validation_issues.length : (metrics.validation_issues || 0)}
            </div>
          </div>
        </div>
        <div className="mt-4 grid grid-cols-2 gap-4 text-sm md:grid-cols-4 xl:grid-cols-8">
          {riskSummaryItems.map((item) => (
            <div key={item.label} className="space-y-1">
              <div className="text-muted-foreground">{item.label}</div>
              <div className="font-medium">{formatRiskValue(item.label, item.value)}</div>
            </div>
          ))}
        </div>
        <div className="mt-4 rounded-lg border border-border/60 p-4">
          <div className="mb-3 text-sm font-medium">Risk Scores</div>
          <div className="grid grid-cols-2 gap-4 text-sm md:grid-cols-3 xl:grid-cols-6">
            {scoreItems.map((item) => (
              <div key={item.label} className="space-y-1">
                <div className="text-muted-foreground">{item.label}</div>
                <div className="font-medium">{formatRiskValue(item.label, item.value)}</div>
              </div>
            ))}
          </div>
          <div className="mt-3 text-xs text-muted-foreground">
            Scorecard confidence:{" "}
            <span className="text-foreground">
              {riskScorecard?.overall_confidence_label || "--"}
            </span>
          </div>
        </div>
        <div className="mt-4 rounded-lg border border-border/60 p-4">
          <div className="mb-3 text-sm font-medium">Recommendations</div>
          {recommendationItems.length > 0 ? (
            <div className="space-y-3">
              {recommendationItems.map((item, index) => (
                <div
                  key={`${item.display_action || item.action_type || "rec"}-${item.symbol || "none"}-${index}`}
                  className="rounded-md border border-border/60 bg-background/60 p-3"
                >
                  <div className="font-medium">
                    {formatRecommendationAction(item.display_action || item.action_type, item.symbol)}
                  </div>
                  <div className="mt-1 text-xs text-muted-foreground">
                    {item.explanation || "--"}
                  </div>
                  <div className="mt-2 grid grid-cols-2 gap-3 text-xs md:grid-cols-5">
                    <div>
                      <div className="text-muted-foreground">Lots Delta</div>
                      <div className="font-medium">{formatRiskValue("Lots", item.delta_lots)}</div>
                    </div>
                    <div>
                      <div className="text-muted-foreground">VaR Delta</div>
                      <div className="font-medium">{formatRiskValue("VaR", item.var_delta)}</div>
                    </div>
                    <div>
                      <div className="text-muted-foreground">CVaR Delta</div>
                      <div className="font-medium">{formatRiskValue("CVaR", item.es_delta)}</div>
                    </div>
                    <div>
                      <div className="text-muted-foreground">Margin Delta</div>
                      <div className="font-medium">{formatRiskValue("Margin", item.margin_used_delta)}</div>
                    </div>
                    <div>
                      <div className="text-muted-foreground">Useful</div>
                      <div className="font-medium">{formatRiskValue("Score", item.usefulness_score)}</div>
                    </div>
                  </div>
                  <div className="mt-2 text-xs text-muted-foreground">
                    Feasible: <span className="text-foreground">{item.governance_feasible ? "Yes" : "No"}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-sm text-muted-foreground">No live recommendations yet.</div>
          )}
        </div>
        <div className="mt-4 rounded-lg border border-border/60 p-4">
          <div className="mb-3 text-sm font-medium">What-If</div>
          <div className="grid gap-4 xl:grid-cols-3">
            <div className="space-y-3 rounded-md border border-border/60 bg-background/60 p-3">
              <div className="text-sm font-medium">Close Half Position</div>
              <div className="space-y-2">
                <Label>Position</Label>
                <Select value={effectiveSelectedPositionId} onValueChange={setSelectedPositionId}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select position" />
                  </SelectTrigger>
                  <SelectContent>
                    {positions.map((position) => (
                      <SelectItem key={position.id} value={String(position.id)}>
                        {position.symbol} {position.type} {position.volume.toFixed(2)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <Button
                variant="outline"
                onClick={handleCloseHalfWhatIf}
                disabled={!effectiveSelectedPositionId || !onEvaluateWhatIf || whatIfLoading}
              >
                {whatIfLoading ? "Evaluating..." : "Run Close Half"}
              </Button>
            </div>
            <div className="space-y-3 rounded-md border border-border/60 bg-background/60 p-3">
              <div className="text-sm font-medium">Add Hedge</div>
              <div className="grid gap-3 md:grid-cols-3">
                <div className="space-y-2">
                  <Label>Symbol</Label>
                  <Select value={effectiveHedgeSymbol} onValueChange={setHedgeSymbol}>
                    <SelectTrigger>
                      <SelectValue placeholder="Symbol" />
                    </SelectTrigger>
                    <SelectContent>
                      {symbols.map((symbol) => (
                        <SelectItem key={symbol} value={symbol}>
                          {symbol}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Side</Label>
                  <Select value={hedgeSide} onValueChange={(value) => setHedgeSide(value as "buy" | "sell")}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="buy">Buy</SelectItem>
                      <SelectItem value="sell">Sell</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Lots</Label>
                  <Input value={hedgeLots} onChange={(e) => setHedgeLots(e.target.value)} />
                </div>
              </div>
              <Button
                variant="outline"
                onClick={handleHedgeWhatIf}
                disabled={!effectiveHedgeSymbol || !onEvaluateWhatIf || whatIfLoading}
              >
                {whatIfLoading ? "Evaluating..." : "Run Hedge"}
              </Button>
            </div>
            <div className="space-y-3 rounded-md border border-border/60 bg-background/60 p-3">
              <div className="text-sm font-medium">Reduce Leverage</div>
              <div className="text-xs text-muted-foreground">
                Current leverage: <span className="text-foreground">{currentLeverage || "--"}</span>
              </div>
              <div className="space-y-2">
                <Label>Proposed Leverage</Label>
                <Input
                  type="number"
                  min="1"
                  value={effectiveProposedLeverage}
                  onChange={(e) => setProposedLeverage(e.target.value)}
                />
              </div>
              <Button
                variant="outline"
                onClick={handleLeverageWhatIf}
                disabled={!onEvaluateWhatIf || whatIfLoading}
              >
                {whatIfLoading ? "Evaluating..." : "Run Leverage"}
              </Button>
            </div>
          </div>
          <div className="mt-4 rounded-md border border-border/60 bg-background/60 p-3">
            <div className="text-sm font-medium">
              {whatIfProjected?.governance_decision || whatIfSummary?.projected_governance_decision || "What-If Result"}
            </div>
            <div className="mt-1 text-xs text-muted-foreground">
              {whatIfProjected?.governance_reason ||
                "Run a what-if scenario to compare before and projected portfolio risk without mutating the simulation."}
            </div>
            {whatIfSummary ? (
              <div className="mt-4 space-y-3">
                <div className="grid grid-cols-3 gap-3 text-sm">
                  <div className="space-y-1">
                    <div className="text-xs text-muted-foreground">Current VaR</div>
                    <div className="font-medium">{formatRiskValue("Current VaR", whatIfSummary.baseline_var)}</div>
                  </div>
                  <div className="space-y-1">
                    <div className="text-xs text-muted-foreground">Projected VaR</div>
                    <div className="font-medium">{formatRiskValue("Projected VaR", whatIfSummary.projected_var)}</div>
                  </div>
                  <div className="space-y-1">
                    <div className="text-xs text-muted-foreground">Delta VaR</div>
                    <div className="font-medium">{formatRiskValue("Delta VaR", whatIfSummary.var_delta)}</div>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-3 text-sm">
                  <div className="space-y-1">
                    <div className="text-xs text-muted-foreground">Current CVaR</div>
                    <div className="font-medium">{formatRiskValue("Current CVaR", whatIfSummary.baseline_es)}</div>
                  </div>
                  <div className="space-y-1">
                    <div className="text-xs text-muted-foreground">Projected CVaR</div>
                    <div className="font-medium">{formatRiskValue("Projected CVaR", whatIfSummary.projected_es)}</div>
                  </div>
                  <div className="space-y-1">
                    <div className="text-xs text-muted-foreground">Delta CVaR</div>
                    <div className="font-medium">{formatRiskValue("Delta CVaR", whatIfSummary.es_delta)}</div>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-3 text-sm">
                  <div className="space-y-1">
                    <div className="text-xs text-muted-foreground">Current Margin</div>
                    <div className="font-medium">{formatRiskValue("Current Margin", whatIfSummary.baseline_margin_used)}</div>
                  </div>
                  <div className="space-y-1">
                    <div className="text-xs text-muted-foreground">Projected Margin</div>
                    <div className="font-medium">{formatRiskValue("Projected Margin", whatIfSummary.projected_margin_used)}</div>
                  </div>
                  <div className="space-y-1">
                    <div className="text-xs text-muted-foreground">Delta Margin</div>
                    <div className="font-medium">{formatRiskValue("Delta Margin", whatIfSummary.margin_used_delta)}</div>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
                  <div className="space-y-1">
                    <div className="text-xs text-muted-foreground">Current Score</div>
                    <div className="font-medium">{formatRiskValue("Score", whatIfSummary.baseline_overall_score)}</div>
                  </div>
                  <div className="space-y-1">
                    <div className="text-xs text-muted-foreground">Projected Score</div>
                    <div className="font-medium">{formatRiskValue("Score", whatIfSummary.projected_overall_score)}</div>
                  </div>
                  <div className="space-y-1">
                    <div className="text-xs text-muted-foreground">Delta Score</div>
                    <div className="font-medium">{formatRiskValue("Score", whatIfSummary.overall_score_delta)}</div>
                  </div>
                  <div className="space-y-1">
                    <div className="text-xs text-muted-foreground">Leverage Override</div>
                    <div className="font-medium">
                      {whatIfSummary.leverage_override ? String(whatIfSummary.leverage_override) : "--"}
                    </div>
                  </div>
                </div>
                {whatIfRecommendations.length > 0 ? (
                  <div className="space-y-2">
                    <div className="text-xs font-medium text-muted-foreground">Projected Recommendations</div>
                    <div className="space-y-2">
                      {whatIfRecommendations.slice(0, 3).map((item, index) => (
                        <div
                          key={`${item.display_action || item.action_type || "whatif"}-${item.symbol || "none"}-${index}`}
                          className="rounded-md border border-border/60 bg-background/60 p-2 text-xs"
                        >
                          <div className="font-medium">
                            {formatRecommendationAction(item.display_action || item.action_type, item.symbol)}
                          </div>
                          <div className="mt-1 text-muted-foreground">{item.explanation || "--"}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>
            ) : null}
          </div>
        </div>
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <div className="space-y-2">
            <div className="text-sm font-medium">Warnings / Breaches</div>
            <div className={`rounded-lg border p-4 text-sm ${riskStatusTone}`}>
              <div className="font-medium">
                {governanceReport?.decision || riskSnapshot?.governance_decision || "Status"}
              </div>
              <div className="mt-1 text-muted-foreground">
                {governanceReport?.reason || riskSnapshot?.governance_reason || "All risk limits satisfied."}
              </div>
              {governanceReport ? (
                <div className="mt-4 space-y-3">
                  <div className="grid grid-cols-3 gap-3 text-sm">
                    <div className="space-y-1">
                      <div className="text-xs text-muted-foreground">Current VaR</div>
                      <div className="font-medium">{formatRiskValue("Current VaR", governanceReport.current_var)}</div>
                    </div>
                    <div className="space-y-1">
                      <div className="text-xs text-muted-foreground">Proposed VaR</div>
                      <div className="font-medium">{formatRiskValue("Proposed VaR", governanceReport.new_var)}</div>
                    </div>
                    <div className="space-y-1">
                      <div className="text-xs text-muted-foreground">Delta VaR</div>
                      <div className="font-medium">{formatRiskValue("Delta VaR", governanceReport.delta_var)}</div>
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-3 text-sm">
                    <div className="space-y-1">
                      <div className="text-xs text-muted-foreground">Current CVaR</div>
                      <div className="font-medium">{formatRiskValue("Current CVaR", governanceReport.current_es)}</div>
                    </div>
                    <div className="space-y-1">
                      <div className="text-xs text-muted-foreground">Proposed CVaR</div>
                      <div className="font-medium">{formatRiskValue("Proposed CVaR", governanceReport.new_es)}</div>
                    </div>
                    <div className="space-y-1">
                      <div className="text-xs text-muted-foreground">Delta CVaR</div>
                      <div className="font-medium">{formatRiskValue("Delta CVaR", governanceReport.delta_es)}</div>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-sm md:grid-cols-3">
                    <div className="space-y-1">
                      <div className="text-xs text-muted-foreground">Current Margin</div>
                      <div className="font-medium">{formatRiskValue("Current Margin", governanceReport.current_margin_used)}</div>
                    </div>
                    <div className="space-y-1">
                      <div className="text-xs text-muted-foreground">Proposed Margin</div>
                      <div className="font-medium">{formatRiskValue("Proposed Margin", governanceReport.new_margin_used)}</div>
                    </div>
                  </div>
                </div>
              ) : null}
              {governanceEvents.length > 0 ? (
                <div className="mt-4 space-y-2">
                  {governanceEvents.map((event, index) => (
                    <div key={`${event.rule_key || "event"}-${index}`} className="rounded-md border border-border/60 bg-background/60 p-3">
                      <div className="font-medium">
                        {(event.severity || "event").toUpperCase()}: {event.rule_key || "Risk Event"}
                      </div>
                      <div className="mt-1 text-muted-foreground">{event.message || "--"}</div>
                      {(event.observed_value !== null && event.observed_value !== undefined) ||
                      (event.threshold_value !== null && event.threshold_value !== undefined) ? (
                        <div className="mt-2 text-xs text-muted-foreground">
                          Observed: {formatRiskValue("Observed", event.observed_value)} | Threshold:{" "}
                          {formatRiskValue("Threshold", event.threshold_value)}
                        </div>
                      ) : null}
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          </div>
          <div className="space-y-2">
            <div className="text-sm font-medium">Current Regime</div>
            <div className="rounded-lg border p-4 text-sm">
              <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
                <div className="space-y-1">
                  <div className="text-xs text-muted-foreground">Aggregate</div>
                  <div className="font-medium">{riskSnapshot?.regime_name || "--"}</div>
                </div>
                <div className="space-y-1">
                  <div className="text-xs text-muted-foreground">Confidence</div>
                  <div className="font-medium">
                    {formatRiskValue("Regime Confidence %", riskSnapshot?.regime_confidence)}
                  </div>
                </div>
                <div className="space-y-1">
                  <div className="text-xs text-muted-foreground">Transition Changed</div>
                  <div className="font-medium">
                    {riskSnapshot?.regime_transition_changed ? "Yes" : "No"}
                  </div>
                </div>
                <div className="space-y-1">
                  <div className="text-xs text-muted-foreground">Market</div>
                  <div className="font-medium">{riskSnapshot?.market_regime || "--"}</div>
                </div>
                <div className="space-y-1">
                  <div className="text-xs text-muted-foreground">Volatility</div>
                  <div className="font-medium">{riskSnapshot?.volatility_regime || "--"}</div>
                </div>
                <div className="space-y-1">
                  <div className="text-xs text-muted-foreground">Liquidity</div>
                  <div className="font-medium">{riskSnapshot?.liquidity_regime || "--"}</div>
                </div>
                <div className="space-y-1">
                  <div className="text-xs text-muted-foreground">Crisis</div>
                  <div className="font-medium">{riskSnapshot?.crisis_regime || "--"}</div>
                </div>
              </div>
              {regimeWarnings.length > 0 ? (
                <div className="mt-4 space-y-1">
                  <div className="text-xs font-medium text-muted-foreground">Warnings</div>
                  <div className="text-xs text-muted-foreground">{regimeWarnings.join(" | ")}</div>
                </div>
              ) : null}
              {regimeSignals.length > 0 ? (
                <div className="mt-4 space-y-1">
                  <div className="text-xs font-medium text-muted-foreground">Signals Triggered</div>
                  <div className="text-xs text-muted-foreground">{regimeSignals.join(" | ")}</div>
                </div>
              ) : null}
              {currencyExposure.length > 0 ? (
                <div className="mt-4 space-y-2">
                  <div className="text-xs font-medium text-muted-foreground">Currency Exposure</div>
                  <div className="grid gap-2 md:grid-cols-2">
                    {currencyExposure.slice(0, 8).map((item) => (
                      <div
                        key={`currency-exposure-${item.currency}`}
                        className="rounded-md border border-border/60 bg-background/60 p-2 text-xs"
                      >
                        <div className="font-medium">{item.currency}</div>
                        <div className="mt-1 text-muted-foreground">
                          {formatRiskValue(item.currency, item.value)}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}
              {currencyWeights.length > 0 ? (
                <div className="mt-4 space-y-2">
                  <div className="text-xs font-medium text-muted-foreground">Currency Weights</div>
                  <div className="grid gap-2 md:grid-cols-2">
                    {currencyWeights.slice(0, 8).map((item) => (
                      <div
                        key={`currency-weight-${item.currency}`}
                        className="rounded-md border border-border/60 bg-background/60 p-2 text-xs"
                      >
                        <div className="font-medium">{item.currency}</div>
                        <div className="mt-1 text-muted-foreground">
                          {typeof item.value === "number"
                            ? `${(item.value * 100).toFixed(2)}%`
                            : "--"}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
