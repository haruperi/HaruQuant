"use client"

import { useMemo, useState } from "react"
import { toast } from "sonner"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
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
import { Textarea } from "@/components/ui/textarea"
import { getErrorMessage } from "@/lib/api-error"
import riskApi, { type RiskAllocationResponse } from "@/lib/api/risk"

const defaultBaseLots = `EURUSD=0.30
GBPUSD=0.30
USDJPY=0.30`

const defaultBudgets = `EURUSD=0.25
GBPUSD=0.25
USDJPY=0.50`

type RegimeOption = "NONE" | "NORMAL" | "STRESS"

function parseKeyValueNumbers(raw: string): Record<string, number> {
  const lines = raw
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)

  const entries: Record<string, number> = {}
  for (const line of lines) {
    const [left, right] = line.split("=")
    if (!left || right === undefined) {
      throw new Error(`Invalid line "${line}". Use SYMBOL=value format.`)
    }
    const key = left.trim().toUpperCase()
    const value = Number(right.trim())
    if (!key || !Number.isFinite(value)) {
      throw new Error(`Invalid line "${line}". Use SYMBOL=value format.`)
    }
    entries[key] = value
  }
  return entries
}

export function RiskAllocationPanel() {
  const [timeframe, setTimeframe] = useState("H1")
  const [barCount, setBarCount] = useState("200")
  const [baseLotsInput, setBaseLotsInput] = useState(defaultBaseLots)
  const [budgetsInput, setBudgetsInput] = useState(defaultBudgets)
  const [regime, setRegime] = useState<RegimeOption>("NONE")
  const [corrTarget, setCorrTarget] = useState("0.50")
  const [corrPenaltyStrength, setCorrPenaltyStrength] = useState("2.0")
  const [corrMinBudgetFrac, setCorrMinBudgetFrac] = useState("0.30")
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState<RiskAllocationResponse | null>(null)

  const previewSymbols = useMemo(() => {
    try {
      return Object.keys(parseKeyValueNumbers(baseLotsInput))
    } catch {
      return []
    }
  }, [baseLotsInput])

  const handleCalculate = async () => {
    try {
      const baseLots = parseKeyValueNumbers(baseLotsInput)
      const budgets = budgetsInput.trim() ? parseKeyValueNumbers(budgetsInput) : {}
      const symbols = Object.keys(baseLots)
      if (symbols.length === 0) {
        toast.error("Add at least one base lot entry.")
        return
      }

      setSubmitting(true)
      const response = await riskApi.calculateRiskAllocation({
        symbols,
        timeframe,
        bar_count: Number(barCount),
        base_lots: baseLots,
        budgets,
        regime_name: regime === "NONE" ? undefined : regime,
        corr_target: Number(corrTarget),
        corr_penalty_strength: Number(corrPenaltyStrength),
        corr_min_budget_frac: Number(corrMinBudgetFrac),
      })
      setResult(response)
      toast.success("Risk allocation calculated.")
    } catch (error) {
      toast.error("Failed to calculate risk allocation.", {
        description: getErrorMessage(error),
      })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(340px,0.8fr)]">
      <Card>
        <CardHeader>
          <CardTitle>Risk Allocation</CardTitle>
          <CardDescription>
            Compute target lots from the live allocation planner using MT5-backed bars.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="grid gap-2">
              <Label htmlFor="allocation-timeframe">Timeframe</Label>
              <Input
                id="allocation-timeframe"
                value={timeframe}
                onChange={(event) => setTimeframe(event.target.value)}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="allocation-bar-count">Bar Count</Label>
              <Input
                id="allocation-bar-count"
                value={barCount}
                onChange={(event) => setBarCount(event.target.value)}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="allocation-regime">Regime</Label>
              <Select value={regime} onValueChange={(value) => setRegime(value as RegimeOption)}>
                <SelectTrigger id="allocation-regime">
                  <SelectValue placeholder="Select regime" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="NONE">None</SelectItem>
                  <SelectItem value="NORMAL">Normal</SelectItem>
                  <SelectItem value="STRESS">Stress</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="allocation-base-lots">Base Lots</Label>
            <Textarea
              id="allocation-base-lots"
              value={baseLotsInput}
              onChange={(event) => setBaseLotsInput(event.target.value)}
              className="min-h-[120px] font-mono text-xs"
            />
            <p className="text-muted-foreground text-sm">
              One symbol per line using <code>SYMBOL=value</code>, for example <code>EURUSD=0.30</code>.
            </p>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="allocation-budgets">Risk Budgets</Label>
            <Textarea
              id="allocation-budgets"
              value={budgetsInput}
              onChange={(event) => setBudgetsInput(event.target.value)}
              className="min-h-[120px] font-mono text-xs"
            />
            <p className="text-muted-foreground text-sm">
              Optional budget weights in the same format. Leave blank for equal risk budgeting.
            </p>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <div className="grid gap-2">
              <Label htmlFor="corr-target">Target Correlation</Label>
              <Input id="corr-target" value={corrTarget} onChange={(event) => setCorrTarget(event.target.value)} />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="corr-penalty">Penalty Strength</Label>
              <Input
                id="corr-penalty"
                value={corrPenaltyStrength}
                onChange={(event) => setCorrPenaltyStrength(event.target.value)}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="corr-min-budget">Min Budget Fraction</Label>
              <Input
                id="corr-min-budget"
                value={corrMinBudgetFrac}
                onChange={(event) => setCorrMinBudgetFrac(event.target.value)}
              />
            </div>
          </div>

          <div className="rounded-lg border p-3 text-sm">
            <div className="font-medium">Symbols</div>
            <div className="text-muted-foreground mt-1">
              {previewSymbols.length > 0 ? previewSymbols.join(", ") : "Add base lot lines to define the portfolio."}
            </div>
          </div>

          <Button onClick={handleCalculate} disabled={submitting}>
            {submitting ? "Calculating..." : "Calculate Allocation"}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Result</CardTitle>
          <CardDescription>
            Target lots and deltas returned by the live allocation planner.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="bg-muted rounded-lg p-4">
            <p className="text-muted-foreground text-sm">Portfolio Symbols</p>
            <p className="text-3xl font-semibold">
              {result ? result.symbols.length : "--"}
            </p>
          </div>

          {result && (
            <>
              <div className="space-y-2 text-sm">
                <div className="flex items-center justify-between gap-4">
                  <span className="text-muted-foreground">Timeframe</span>
                  <span>{result.timeframe}</span>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <span className="text-muted-foreground">Bar Count</span>
                  <span>{result.bar_count}</span>
                </div>
              </div>

              <div className="space-y-2">
                <div className="text-sm font-medium">Target Lots</div>
                {result.symbols.map((symbol) => (
                  <div key={`target-${symbol}`} className="flex items-center justify-between gap-4 rounded-md border p-3 text-sm">
                    <span>{symbol}</span>
                    <span>{result.target_lots[symbol]?.toFixed(4) ?? "0.0000"}</span>
                  </div>
                ))}
              </div>

              <div className="space-y-2">
                <div className="text-sm font-medium">Deltas</div>
                {result.symbols.map((symbol) => (
                  <div key={`delta-${symbol}`} className="flex items-center justify-between gap-4 rounded-md border p-3 text-sm">
                    <span>{symbol}</span>
                    <span>{result.deltas[symbol]?.toFixed(4) ?? "0.0000"}</span>
                  </div>
                ))}
              </div>

              <div className="space-y-2">
                <div className="text-sm font-medium">Normalized Budgets</div>
                {Object.keys(result.normalized_budgets).length === 0 ? (
                  <p className="text-muted-foreground text-sm">Equal budgeting was used.</p>
                ) : (
                  result.symbols
                    .filter((symbol) => symbol in result.normalized_budgets)
                    .map((symbol) => (
                      <div key={`budget-${symbol}`} className="flex items-center justify-between gap-4 rounded-md border p-3 text-sm">
                        <span>{symbol}</span>
                        <span>{(result.normalized_budgets[symbol] * 100).toFixed(1)}%</span>
                      </div>
                    ))
                )}
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
