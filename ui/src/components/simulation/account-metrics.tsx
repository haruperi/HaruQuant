"use client"

import { useState } from "react"
import { ChevronDown, ChevronRight } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts"
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
  const [recommendationsOpen, setRecommendationsOpen] = useState(false)
  const [whatIfOpen, setWhatIfOpen] = useState(false)
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
  const currencyExposure = riskSnapshot?.currency_exposure || []
  const currencyWeights = riskSnapshot?.currency_weights || []
  const currencyExposureByCode = new Map(
    currencyExposure.map((item) => [item.currency, item.value])
  )
  const currencyGovernanceByCode = new Map<
    string,
    {
      severity: string
    }
  >()
  for (const event of governanceEvents) {
    if (event.scope !== "currency" || !event.scope_key) {
      continue
    }
    const existing = currencyGovernanceByCode.get(event.scope_key)
    if (existing?.severity === "breach") {
      continue
    }
    currencyGovernanceByCode.set(event.scope_key, {
      severity: event.severity || "warning",
    })
  }
  const currencyPieData = currencyWeights.map((item, index) => ({
    currency: item.currency,
    weight:
      typeof item.value === "number" && Number.isFinite(item.value)
        ? `${(item.value * 100).toFixed(2)}%`
        : "--",
    exposure: formatRiskValue(item.currency, currencyExposureByCode.get(item.currency)),
    severity: currencyGovernanceByCode.get(item.currency)?.severity || null,
    numericWeight:
      typeof item.value === "number" && Number.isFinite(item.value)
        ? item.value * 100
        : 0,
  }))
  const currencyColors = [
    "var(--color-chart-1)",
    "var(--color-chart-2)",
    "var(--color-chart-3)",
    "var(--color-chart-4)",
    "var(--color-chart-5)",
  ]
  const recommendationItems = recommendations?.items || []
  const marginalRiskRecommendation = recommendations?.marginal_risk_recommendation
  const allocationCandidates = recommendations?.allocation_candidates || []
  const hedgeCandidates = recommendations?.hedge_candidates || []
  const rebalanceCandidates = recommendations?.rebalance_candidates || []
  const capitalEfficiencyItems = recommendations?.capital_efficiency || []
  const whatIfSummary = whatIfComparison?.summary
  const whatIfProjected = whatIfComparison?.projected
  const whatIfRecommendations = whatIfComparison?.projected_recommendations?.items || []
  const whatIfStressScenarios = whatIfComparison?.stress_scenarios || []
  const whatIfStressSummary = whatIfComparison?.stress_summary
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

  const renderRecommendationCard = (item: SimulationRecommendationSummary["items"][number], key: string) => (
    <div
      key={key}
      className="rounded-md border border-border/60 bg-background/60 p-3"
    >
      <div className="font-medium">
        {formatRecommendationAction(item.display_action || item.action_type, item.symbol)}
      </div>
      <div className="mt-1 text-xs text-muted-foreground">
        {item.explanation || item.rationale || "--"}
      </div>
      <div className="mt-2 grid grid-cols-2 gap-3 text-xs md:grid-cols-6">
        <div>
          <div className="text-muted-foreground">Lots Delta</div>
          <div className="font-medium">{formatRiskValue("Lots", item.delta_lots)}</div>
        </div>
        <div>
          <div className="text-muted-foreground">Score Delta</div>
          <div className="font-medium">{formatRiskValue("Score", item.score_delta)}</div>
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
          <div className="text-muted-foreground">Stress Delta</div>
          <div className="font-medium">{formatRiskValue("Loss", item.worst_scenario_loss_delta)}</div>
        </div>
        <div>
          <div className="text-muted-foreground">Useful</div>
          <div className="font-medium">{formatRiskValue("Score", item.usefulness_score)}</div>
        </div>
      </div>
      <div className="mt-2 text-xs text-muted-foreground">
        Feasible: <span className="text-foreground">{item.governance_feasible ? "Yes" : "No"}</span>
        {" | "}Decision: <span className="text-foreground">{item.governance_decision || "--"}</span>
      </div>
    </div>
  )

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
    <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4 text-sm md:grid-cols-3">
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
        <div className="mt-4 rounded-lg border border-border/60 p-4">
          <button
            type="button"
            className="flex w-full items-center justify-between text-left"
            onClick={() => setRecommendationsOpen((prev) => !prev)}
          >
            <span className="text-sm font-medium">Recommendations</span>
            {recommendationsOpen ? (
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            ) : (
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
            )}
          </button>
          {recommendationsOpen ? (
            recommendationItems.length > 0 ||
            marginalRiskRecommendation ||
            allocationCandidates.length > 0 ||
            hedgeCandidates.length > 0 ||
            rebalanceCandidates.length > 0 ||
            capitalEfficiencyItems.length > 0 ? (
              <div className="mt-3 space-y-4">
                <div className="space-y-2">
                  <div className="text-xs font-medium text-muted-foreground">01: Marginal Risk Engine Recommendation</div>
                  {marginalRiskRecommendation
                    ? renderRecommendationCard(marginalRiskRecommendation, "marginal-risk")
                    : <div className="text-sm text-muted-foreground">No marginal risk recommendation.</div>}
                </div>
                <div className="space-y-2">
                  <div className="text-xs font-medium text-muted-foreground">02: Add / Remove / Resize Evaluation Recommendation</div>
                  {allocationCandidates.length > 0
                    ? allocationCandidates.map((item, index) =>
                        renderRecommendationCard(
                          item,
                          `allocation-${item.display_action || item.action_type || "item"}-${item.symbol || "none"}-${index}`
                        )
                      )
                    : <div className="text-sm text-muted-foreground">No allocation candidates.</div>}
                </div>
                <div className="space-y-2">
                  <div className="text-xs font-medium text-muted-foreground">03: Hedge Candidate Evaluation Recommendation</div>
                  {hedgeCandidates.length > 0
                    ? hedgeCandidates.map((item, index) =>
                        renderRecommendationCard(
                          item,
                          `hedge-${item.symbol || "none"}-${index}`
                        )
                      )
                    : <div className="text-sm text-muted-foreground">No hedge candidates.</div>}
                </div>
                <div className="space-y-2">
                  <div className="text-xs font-medium text-muted-foreground">04: Rebalance Suggestion Logic</div>
                  {rebalanceCandidates.length > 0
                    ? rebalanceCandidates.map((item, index) =>
                        renderRecommendationCard(
                          item,
                          `rebalance-${item.symbol || "none"}-${index}`
                        )
                      )
                    : <div className="text-sm text-muted-foreground">No rebalance suggestions.</div>}
                </div>
                <div className="space-y-2">
                  <div className="text-xs font-medium text-muted-foreground">05: Capital-Efficiency Ranking</div>
                  {capitalEfficiencyItems.length > 0 ? (
                    <div className="overflow-x-auto rounded-md border border-border/60 bg-background/60">
                      <table className="min-w-full text-xs">
                        <thead>
                          <tr className="border-b border-border/60 text-left">
                            <th className="px-3 py-2 font-medium text-muted-foreground">Symbol</th>
                            <th className="px-3 py-2 text-right font-medium text-muted-foreground">Ratio</th>
                            <th className="px-3 py-2 text-right font-medium text-muted-foreground">Weight</th>
                            <th className="px-3 py-2 text-right font-medium text-muted-foreground">RC</th>
                          </tr>
                        </thead>
                        <tbody>
                          {capitalEfficiencyItems.map((item, index) => (
                            <tr key={`${item.symbol || "ce"}-${index}`} className="border-b border-border/40 last:border-b-0">
                              <td className="px-3 py-2 text-muted-foreground">{item.symbol || "--"}</td>
                              <td className="px-3 py-2 text-right font-medium">{formatRiskValue("Ratio", item.capital_efficiency_ratio)}</td>
                              <td className="px-3 py-2 text-right font-medium">{formatRiskValue("%", item.portfolio_weight)}</td>
                              <td className="px-3 py-2 text-right font-medium">{formatRiskValue("%", item.risk_contribution_frac)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="text-sm text-muted-foreground">No capital-efficiency ranking.</div>
                  )}
                </div>
                <div className="space-y-2">
                  <div className="text-xs font-medium text-muted-foreground">06: Action Recommendation Scoring</div>
                  {recommendationItems.length > 0
                    ? recommendationItems.map((item, index) =>
                        renderRecommendationCard(
                          item,
                          `scoring-${item.display_action || item.action_type || "item"}-${item.symbol || "none"}-${index}`
                        )
                      )
                    : <div className="text-sm text-muted-foreground">No scored recommendations.</div>}
                </div>
                <div className="space-y-2">
                  <div className="text-xs font-medium text-muted-foreground">07: Governance Feasibility Checks</div>
                  {recommendationItems.length > 0 ? (
                    <div className="overflow-x-auto rounded-md border border-border/60 bg-background/60">
                      <table className="min-w-full text-xs">
                        <thead>
                          <tr className="border-b border-border/60 text-left">
                            <th className="px-3 py-2 font-medium text-muted-foreground">Action</th>
                            <th className="px-3 py-2 font-medium text-muted-foreground">Symbol</th>
                            <th className="px-3 py-2 text-right font-medium text-muted-foreground">Feasible</th>
                            <th className="px-3 py-2 text-right font-medium text-muted-foreground">Decision</th>
                          </tr>
                        </thead>
                        <tbody>
                          {recommendationItems.map((item, index) => (
                            <tr key={`feasible-${item.symbol || "none"}-${index}`} className="border-b border-border/40 last:border-b-0">
                              <td className="px-3 py-2 text-muted-foreground">{item.display_action || item.action_type || "--"}</td>
                              <td className="px-3 py-2 text-muted-foreground">{item.symbol || "--"}</td>
                              <td className="px-3 py-2 text-right font-medium">{item.governance_feasible ? "Yes" : "No"}</td>
                              <td className="px-3 py-2 text-right font-medium">{item.governance_decision || "--"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="text-sm text-muted-foreground">No governance feasibility checks.</div>
                  )}
                </div>
                <div className="space-y-2">
                  <div className="text-xs font-medium text-muted-foreground">08: Ranked Recommendation Batch</div>
                  {recommendationItems.length > 0 ? (
                    <>
                      <div className="text-xs text-muted-foreground">
                        Summary: {recommendations?.recommendation_count || recommendationItems.length} total, {recommendations?.feasible_count || 0} feasible, top action {recommendations?.top_action_type || "--"} {recommendations?.top_action_symbol || "--"}
                      </div>
                      <div className="space-y-2">
                        {recommendationItems.map((item, index) => (
                          <div
                            key={`ranked-${item.display_action || item.action_type || "item"}-${item.symbol || "none"}-${index}`}
                            className="rounded-md border border-border/60 bg-background/60 p-3"
                          >
                            <div className="font-medium">
                              {index + 1}. {formatRecommendationAction(item.display_action || item.action_type, item.symbol)}
                            </div>
                            <div className="mt-1 text-xs text-muted-foreground">
                              usefulness={formatRiskValue("Score", item.usefulness_score)} | delta={formatRiskValue("Lots", item.delta_lots)}
                            </div>
                          </div>
                        ))}
                      </div>
                    </>
                  ) : (
                    <div className="text-sm text-muted-foreground">No ranked recommendation batch.</div>
                  )}
                </div>
              </div>
            ) : (
              <div className="mt-3 text-sm text-muted-foreground">No live recommendations yet.</div>
            )
          ) : null}
        </div>
        <div className="mt-4 rounded-lg border border-border/60 p-4">
          <button
            type="button"
            className="flex w-full items-center justify-between text-left"
            onClick={() => setWhatIfOpen((prev) => !prev)}
          >
            <span className="text-sm font-medium">What-If</span>
            {whatIfOpen ? (
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            ) : (
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
            )}
          </button>
          {whatIfOpen ? (
            <>
              <div className="mt-3 grid gap-4 xl:grid-cols-3">
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
                    {whatIfStressScenarios.length > 0 ? (
                      <div className="space-y-2">
                        <div className="text-xs font-medium text-muted-foreground">Stress Scenarios</div>
                        <div className="overflow-x-auto rounded-md border border-border/60 bg-background/60">
                          <table className="min-w-full text-xs">
                            <thead>
                              <tr className="border-b border-border/60 text-left">
                                <th className="px-3 py-2 font-medium text-muted-foreground">Scenario</th>
                                <th className="px-3 py-2 text-right font-medium text-muted-foreground">Baseline Loss</th>
                                <th className="px-3 py-2 text-right font-medium text-muted-foreground">Projected Loss</th>
                                <th className="px-3 py-2 text-right font-medium text-muted-foreground">Delta</th>
                                <th className="px-3 py-2 text-right font-medium text-muted-foreground">Projected VaR</th>
                                <th className="px-3 py-2 text-right font-medium text-muted-foreground">Projected CVaR</th>
                              </tr>
                            </thead>
                            <tbody>
                              {whatIfStressScenarios.map((scenario) => (
                                <tr key={scenario.scenario} className="border-b border-border/40 last:border-b-0">
                                  <td className="px-3 py-2 text-muted-foreground">{scenario.scenario}</td>
                                  <td className="px-3 py-2 text-right font-medium">
                                    {formatRiskValue("Loss", scenario.baseline_loss)}
                                  </td>
                                  <td className="px-3 py-2 text-right font-medium">
                                    {formatRiskValue("Loss", scenario.projected_loss)}
                                  </td>
                                  <td className="px-3 py-2 text-right font-medium">
                                    {formatRiskValue("Loss", scenario.loss_delta)}
                                  </td>
                                  <td className="px-3 py-2 text-right font-medium">
                                    {formatRiskValue("VaR", scenario.projected_stressed_var)}
                                  </td>
                                  <td className="px-3 py-2 text-right font-medium">
                                    {formatRiskValue("CVaR", scenario.projected_stressed_es)}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                        {whatIfStressSummary ? (
                          <div className="grid gap-3 text-xs md:grid-cols-2">
                            <div className="rounded-md border border-border/60 bg-background/60 p-3">
                              <div className="text-muted-foreground">Baseline Worst Case</div>
                              <div className="mt-1 font-medium">
                                {whatIfStressSummary.baseline_worst_scenario_name || "--"}
                              </div>
                              <div className="mt-1 text-muted-foreground">
                                {formatRiskValue("Loss", whatIfStressSummary.baseline_worst_scenario_loss)}
                              </div>
                            </div>
                            <div className="rounded-md border border-border/60 bg-background/60 p-3">
                              <div className="text-muted-foreground">Projected Worst Case</div>
                              <div className="mt-1 font-medium">
                                {whatIfStressSummary.projected_worst_scenario_name || "--"}
                              </div>
                              <div className="mt-1 text-muted-foreground">
                                {formatRiskValue("Loss", whatIfStressSummary.projected_worst_scenario_loss)}
                              </div>
                            </div>
                          </div>
                        ) : null}
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </div>
            </>
          ) : null}
        </div>
        <div className="mt-4 grid gap-4 lg:grid-cols-3">
          <div className="space-y-2">
            <div className="text-sm font-medium">Correlations Table</div>
            <div className="rounded-lg border p-4 text-sm">
              {(riskSnapshot?.pair_correlations || []).length > 0 ? (
                <div className="max-h-80 overflow-auto">
                  <table className="min-w-full text-sm">
                    <thead>
                      <tr className="border-b text-left">
                        <th className="pb-2 pr-3 font-medium text-muted-foreground">Pair</th>
                        <th className="pb-2 text-right font-medium text-muted-foreground">Correlation</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(riskSnapshot?.pair_correlations || []).map((item) => (
                        <tr key={item.pair} className="border-b border-border/40 last:border-b-0">
                          <td className="py-2 pr-3 text-muted-foreground">{item.pair}</td>
                          <td className="py-2 text-right font-medium text-emerald-500">
                            {typeof item.value === "number" && Number.isFinite(item.value)
                              ? item.value.toFixed(2)
                              : "--"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-sm text-muted-foreground">No pair correlations yet.</div>
              )}
            </div>
          </div>
          <div className="space-y-2">
            <div className="text-sm font-medium">Warnings / Breaches</div>
            <div className={`rounded-lg border p-4 text-sm ${riskStatusTone}`}>
              <div className="font-medium">
                {governanceReport?.decision || riskSnapshot?.governance_decision || "Status"}
              </div>
              <div className="mt-1 text-muted-foreground">
                {governanceReport?.reason || riskSnapshot?.governance_reason || "All risk limits satisfied."}
              </div>
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
            <div className="text-sm font-medium">Currency Mix</div>
            <div className="rounded-lg border p-4 text-sm">
              {currencyPieData.length > 0 ? (
                <>
                  <div className="h-56">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={currencyPieData}
                          dataKey="numericWeight"
                          nameKey="currency"
                          cx="50%"
                          cy="50%"
                          outerRadius={76}
                          innerRadius={34}
                          paddingAngle={2}
                        >
                          {currencyPieData.map((entry, index) => (
                            <Cell
                              key={`currency-slice-${entry.currency}`}
                              fill={currencyColors[index % currencyColors.length]}
                            />
                          ))}
                        </Pie>
                        <Tooltip
                          formatter={(_value, _name, item) => {
                            const payload = item?.payload as
                              | {
                                  currency?: string
                                  weight?: string
                                  exposure?: string
                                }
                              | undefined
                            return [
                              `Weight ${payload?.weight || "--"} | Exposure ${payload?.exposure || "--"}`,
                              payload?.currency || "Currency",
                            ]
                          }}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="mt-4 grid grid-cols-1 gap-2 text-xs md:grid-cols-2">
                    {currencyPieData.map((item, index) => (
                      <div
                        key={`currency-legend-${item.currency}`}
                        className={`flex items-center justify-between gap-3 rounded-md border px-2 py-1 ${
                          item.severity === "breach"
                            ? "border-red-500/40 bg-red-500/10"
                            : item.severity === "warning"
                              ? "border-amber-500/40 bg-amber-500/10"
                              : "border-border/60 bg-muted/30"
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <span
                            className="h-2.5 w-2.5 rounded-full"
                            style={{ backgroundColor: currencyColors[index % currencyColors.length] }}
                          />
                          <span className="text-muted-foreground">{item.currency}</span>
                        </div>
                        <span className="font-medium text-emerald-500 whitespace-nowrap">
                          {item.weight} | {item.exposure}
                        </span>
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                <div className="text-sm text-muted-foreground">No currency mix yet.</div>
              )}
            </div>
          </div>
        </div>
    </div>
  )
}
