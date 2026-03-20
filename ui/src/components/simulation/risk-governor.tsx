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
import riskApi, { type GovernanceReportPayload, type GovernanceResponse } from "@/lib/api/risk"

const defaultPositions = `EURUSD=0.30
GBPUSD=0.25
USDJPY=-0.20`

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

function ReportCard({
  title,
  report,
}: {
  title: string
  report: GovernanceReportPayload
}) {
  return (
    <div className="space-y-4 rounded-lg border p-4">
      <div>
        <div className="text-sm font-medium">{title}</div>
        <div className="mt-1 text-2xl font-semibold">{report.decision}</div>
        <div className="text-muted-foreground mt-1 text-sm">{report.reason}</div>
      </div>

      <div className="space-y-2 text-sm">
        <div className="flex items-center justify-between gap-4">
          <span className="text-muted-foreground">Compliance</span>
          <span>{report.compliance_status ?? "--"}</span>
        </div>
        <div className="flex items-center justify-between gap-4">
          <span className="text-muted-foreground">Current VaR</span>
          <span>{report.current_var.toFixed(2)}</span>
        </div>
        <div className="flex items-center justify-between gap-4">
          <span className="text-muted-foreground">New VaR</span>
          <span>{report.new_var.toFixed(2)}</span>
        </div>
        <div className="flex items-center justify-between gap-4">
          <span className="text-muted-foreground">Delta VaR</span>
          <span>{report.delta_var.toFixed(2)}</span>
        </div>
        <div className="flex items-center justify-between gap-4">
          <span className="text-muted-foreground">Current ES</span>
          <span>{report.current_es.toFixed(2)}</span>
        </div>
        <div className="flex items-center justify-between gap-4">
          <span className="text-muted-foreground">New ES</span>
          <span>{report.new_es.toFixed(2)}</span>
        </div>
        <div className="flex items-center justify-between gap-4">
          <span className="text-muted-foreground">Delta ES</span>
          <span>{report.delta_es.toFixed(2)}</span>
        </div>
      </div>

      <div className="space-y-2">
        <div className="text-sm font-medium">Warnings</div>
        {report.warnings.length === 0 ? (
          <p className="text-muted-foreground text-sm">No warnings.</p>
        ) : (
          report.warnings.map((event) => (
            <div key={`${title}-warn-${event.rule_key}-${event.message}`} className="rounded-md border p-3 text-sm">
              <div className="font-medium">{event.rule_key}</div>
              <div className="text-muted-foreground mt-1">{event.message}</div>
            </div>
          ))
        )}
      </div>

      <div className="space-y-2">
        <div className="text-sm font-medium">Breaches</div>
        {report.breaches.length === 0 ? (
          <p className="text-muted-foreground text-sm">No breaches.</p>
        ) : (
          report.breaches.map((event) => (
            <div key={`${title}-breach-${event.rule_key}-${event.message}`} className="rounded-md border p-3 text-sm">
              <div className="font-medium">{event.rule_key}</div>
              <div className="text-muted-foreground mt-1">{event.message}</div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export function RiskGovernorPanel() {
  const [timeframe, setTimeframe] = useState("H1")
  const [barCount, setBarCount] = useState("200")
  const [positionsInput, setPositionsInput] = useState(defaultPositions)
  const [candidateSymbol, setCandidateSymbol] = useState("EURUSD")
  const [candidateLots, setCandidateLots] = useState("0.15")
  const [regime, setRegime] = useState<RegimeOption>("NONE")
  const [varCapFrac, setVarCapFrac] = useState("0.10")
  const [esCapFrac, setEsCapFrac] = useState("0.15")
  const [deltaVarCapFrac, setDeltaVarCapFrac] = useState("0.02")
  const [deltaEsCapFrac, setDeltaEsCapFrac] = useState("0.03")
  const [maxMarginUsedFrac, setMaxMarginUsedFrac] = useState("0.50")
  const [maxSingleRcFrac, setMaxSingleRcFrac] = useState("0.20")
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState<GovernanceResponse | null>(null)

  const previewSymbols = useMemo(() => {
    try {
      return Object.keys(parseKeyValueNumbers(positionsInput))
    } catch {
      return []
    }
  }, [positionsInput])

  const handleEvaluate = async () => {
    try {
      const currentPositions = parseKeyValueNumbers(positionsInput)
      const symbols = Array.from(new Set([...Object.keys(currentPositions), candidateSymbol.trim().toUpperCase()])).filter(Boolean)
      if (symbols.length === 0) {
        toast.error("Add at least one current position.")
        return
      }

      setSubmitting(true)
      const response = await riskApi.evaluateGovernance({
        symbols,
        timeframe,
        bar_count: Number(barCount),
        current_positions: currentPositions,
        candidate_symbol: candidateSymbol.trim().toUpperCase(),
        candidate_lots: Number(candidateLots),
        regime_name: regime === "NONE" ? undefined : regime,
        var_cap_frac: Number(varCapFrac),
        es_cap_frac: Number(esCapFrac),
        delta_var_cap_frac: Number(deltaVarCapFrac),
        delta_es_cap_frac: Number(deltaEsCapFrac),
        max_margin_used_frac: Number(maxMarginUsedFrac),
        max_single_rc_frac: Number(maxSingleRcFrac),
      })
      setResult(response)
      toast.success("Risk governance evaluated.")
    } catch (error) {
      toast.error("Failed to evaluate risk governance.", {
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
          <CardTitle>Risk Governor</CardTitle>
          <CardDescription>
            Evaluate current compliance and one candidate position change using the live governance engine.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="grid gap-2">
              <Label htmlFor="governor-timeframe">Timeframe</Label>
              <Input id="governor-timeframe" value={timeframe} onChange={(event) => setTimeframe(event.target.value)} />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="governor-bar-count">Bar Count</Label>
              <Input id="governor-bar-count" value={barCount} onChange={(event) => setBarCount(event.target.value)} />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="governor-candidate-symbol">Candidate Symbol</Label>
              <Input
                id="governor-candidate-symbol"
                value={candidateSymbol}
                onChange={(event) => setCandidateSymbol(event.target.value)}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="governor-candidate-lots">Candidate Lots</Label>
              <Input
                id="governor-candidate-lots"
                value={candidateLots}
                onChange={(event) => setCandidateLots(event.target.value)}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="governor-regime">Regime</Label>
              <Select value={regime} onValueChange={(value) => setRegime(value as RegimeOption)}>
                <SelectTrigger id="governor-regime">
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
            <Label htmlFor="governor-positions">Current Positions</Label>
            <Textarea
              id="governor-positions"
              value={positionsInput}
              onChange={(event) => setPositionsInput(event.target.value)}
              className="min-h-[120px] font-mono text-xs"
            />
            <p className="text-muted-foreground text-sm">
              One symbol per line using <code>SYMBOL=value</code>. Use negative lots for short positions.
            </p>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="grid gap-2">
              <Label htmlFor="var-cap-frac">VaR Cap Fraction</Label>
              <Input id="var-cap-frac" value={varCapFrac} onChange={(event) => setVarCapFrac(event.target.value)} />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="es-cap-frac">ES Cap Fraction</Label>
              <Input id="es-cap-frac" value={esCapFrac} onChange={(event) => setEsCapFrac(event.target.value)} />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="delta-var-cap-frac">Delta VaR Cap Fraction</Label>
              <Input id="delta-var-cap-frac" value={deltaVarCapFrac} onChange={(event) => setDeltaVarCapFrac(event.target.value)} />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="delta-es-cap-frac">Delta ES Cap Fraction</Label>
              <Input id="delta-es-cap-frac" value={deltaEsCapFrac} onChange={(event) => setDeltaEsCapFrac(event.target.value)} />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="max-margin-used-frac">Max Margin Used Fraction</Label>
              <Input
                id="max-margin-used-frac"
                value={maxMarginUsedFrac}
                onChange={(event) => setMaxMarginUsedFrac(event.target.value)}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="max-single-rc-frac">Max Single RC Fraction</Label>
              <Input
                id="max-single-rc-frac"
                value={maxSingleRcFrac}
                onChange={(event) => setMaxSingleRcFrac(event.target.value)}
              />
            </div>
          </div>

          <div className="rounded-lg border p-3 text-sm">
            <div className="font-medium">Symbols</div>
            <div className="text-muted-foreground mt-1">
              {previewSymbols.length > 0 ? previewSymbols.join(", ") : "Add current position lines to define the portfolio."}
            </div>
          </div>

          <Button onClick={handleEvaluate} disabled={submitting}>
            {submitting ? "Evaluating..." : "Evaluate Governance"}
          </Button>
        </CardContent>
      </Card>

      <div className="grid gap-6">
        {result ? (
          <>
            <ReportCard title="Current Portfolio" report={result.current_report} />
            <ReportCard title="Candidate Position" report={result.candidate_report} />
          </>
        ) : (
          <Card>
            <CardHeader>
              <CardTitle>Result</CardTitle>
              <CardDescription>
                Governance results will appear here after evaluation.
              </CardDescription>
            </CardHeader>
            <CardContent className="text-muted-foreground text-sm">
              Enter current positions, candidate trade inputs, and limits to run the live governance check.
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
