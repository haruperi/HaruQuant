"use client"

import { useMemo, useState } from "react"
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
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
import riskApi, {
  type RegimeDetectionMode,
  type RegimeDetectionSource,
  type RegimeDetectionResponse,
} from "@/lib/api/risk"

const defaultReturnsCsv = `step,EURUSD,GBPUSD,XAUUSD
1,0.0012,0.0008,-0.0020
2,-0.0007,-0.0005,0.0015
3,0.0010,0.0011,-0.0012
4,-0.0015,-0.0010,0.0028
5,0.0009,0.0007,-0.0016
6,-0.0008,-0.0006,0.0010
7,0.0014,0.0010,-0.0024
8,-0.0011,-0.0009,0.0022
9,0.0006,0.0005,-0.0008
10,-0.0013,-0.0011,0.0020`

const defaultEquityCurve = "10000,10040,10010,9960,9920,9890,9855,9830,9810,9795"

interface EquityCurvePoint {
  step: number
  equity: number
}

export function RiskRegimeDetectionPanel() {
  const [source, setSource] = useState<RegimeDetectionSource>("mt5")
  const [mode, setMode] = useState<RegimeDetectionMode>("crisis")
  const [symbols, setSymbols] = useState("EURUSD,GBPUSD,XAUUSD")
  const [timeframe, setTimeframe] = useState("H1")
  const [barCount, setBarCount] = useState("300")
  const [returnsCsv, setReturnsCsv] = useState(defaultReturnsCsv)
  const [equityCurve, setEquityCurve] = useState(defaultEquityCurve)
  const [spreadBps, setSpreadBps] = useState("2.0")
  const [lookback, setLookback] = useState("10")
  const [volSpikeMult, setVolSpikeMult] = useState("1.8")
  const [corrSpikeLevel, setCorrSpikeLevel] = useState("0.55")
  const [ddTriggerFrac, setDdTriggerFrac] = useState("0.05")

  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState<RegimeDetectionResponse | null>(null)

  const equityCurvePoints = useMemo<EquityCurvePoint[]>(() => {
    return equityCurve
      .split(/[\n,]+/)
      .map((value) => Number(value.trim()))
      .filter((value) => Number.isFinite(value))
      .map((value, index) => ({
        step: index + 1,
        equity: value,
      }))
  }, [equityCurve])

  const handleDetect = async () => {
    if (source === "manual" && !returnsCsv.trim()) {
      toast.error("Returns CSV is required.")
      return
    }
    if (source === "mt5" && !symbols.trim()) {
      toast.error("At least one symbol is required.")
      return
    }

    try {
      setSubmitting(true)
      const response = await riskApi.detectRegime({
        source,
        mode,
        symbols:
          source === "mt5"
            ? symbols.split(",").map((value) => value.trim()).filter(Boolean)
            : undefined,
        timeframe: source === "mt5" ? timeframe : undefined,
        bar_count: source === "mt5" ? Number(barCount) : undefined,
        returns_csv: source === "manual" ? returnsCsv : undefined,
        equity_curve: equityCurve.trim() || undefined,
        spread_bps: Number(spreadBps),
        lookback: Number(lookback),
        vol_spike_mult: Number(volSpikeMult),
        corr_spike_level: Number(corrSpikeLevel),
        dd_trigger_frac: Number(ddTriggerFrac),
      })
      setResult(response)
      toast.success("Regime detected.")
    } catch (error) {
      toast.error("Failed to detect regime.", {
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
          <CardTitle>Regime Detection</CardTitle>
          <CardDescription>
            Run the current Phase 6 regime detectors from MT5-backed bars or manual returns input.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="grid gap-2">
              <Label htmlFor="regime-source">Source</Label>
              <Select value={source} onValueChange={(value) => setSource(value as RegimeDetectionSource)}>
                <SelectTrigger id="regime-source">
                  <SelectValue placeholder="Select source" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="mt5">MT5 Real Data</SelectItem>
                  <SelectItem value="manual">Manual Returns</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="regime-mode">Mode</Label>
              <Select value={mode} onValueChange={(value) => setMode(value as RegimeDetectionMode)}>
                <SelectTrigger id="regime-mode">
                  <SelectValue placeholder="Select mode" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="crisis">Crisis Only</SelectItem>
                  <SelectItem value="full">Full Regime Engine</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {source === "mt5" && (
              <>
                <div className="grid gap-2">
                  <Label htmlFor="symbols">Symbols</Label>
                  <Input id="symbols" value={symbols} onChange={(event) => setSymbols(event.target.value)} />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="timeframe">Timeframe</Label>
                  <Input id="timeframe" value={timeframe} onChange={(event) => setTimeframe(event.target.value)} />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="bar-count">Bar Count</Label>
                  <Input id="bar-count" value={barCount} onChange={(event) => setBarCount(event.target.value)} />
                </div>
              </>
            )}
            <div className="grid gap-2">
              <Label htmlFor="lookback">Lookback</Label>
              <Input id="lookback" value={lookback} onChange={(event) => setLookback(event.target.value)} />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="vol-spike-mult">Vol Spike Multiplier</Label>
              <Input id="vol-spike-mult" value={volSpikeMult} onChange={(event) => setVolSpikeMult(event.target.value)} />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="corr-spike-level">Correlation Spike Level</Label>
              <Input id="corr-spike-level" value={corrSpikeLevel} onChange={(event) => setCorrSpikeLevel(event.target.value)} />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="dd-trigger-frac">Drawdown Trigger Fraction</Label>
              <Input id="dd-trigger-frac" value={ddTriggerFrac} onChange={(event) => setDdTriggerFrac(event.target.value)} />
            </div>
            {mode === "full" && source === "manual" && (
              <div className="grid gap-2">
                <Label htmlFor="spread-bps">Synthetic Spread (bps)</Label>
                <Input id="spread-bps" value={spreadBps} onChange={(event) => setSpreadBps(event.target.value)} />
              </div>
            )}
          </div>

          {source === "manual" && (
            <div className="grid gap-2">
              <Label htmlFor="returns-csv">Returns CSV</Label>
              <Textarea
                id="returns-csv"
                value={returnsCsv}
                onChange={(event) => setReturnsCsv(event.target.value)}
                className="min-h-[240px] font-mono text-xs"
              />
              <p className="text-muted-foreground text-sm">
                Use a header row with one column per symbol. A leading label column is allowed.
              </p>
            </div>
          )}

          <div className="grid gap-2">
            <Label htmlFor="equity-curve">Equity Curve</Label>
            <Textarea
              id="equity-curve"
              value={equityCurve}
              onChange={(event) => setEquityCurve(event.target.value)}
              className="min-h-[100px] font-mono text-xs"
            />
            <p className="text-muted-foreground text-sm">
              Optional comma- or newline-separated equity values used for drawdown-trigger checks. Leave blank to use returns-only logic.
            </p>
            <div className="rounded-lg border p-3">
              {equityCurvePoints.length > 0 ? (
                <div className="h-[220px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={equityCurvePoints}>
                      <defs>
                        <linearGradient id="regime-equity-curve-fill" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                          <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
                      <XAxis
                        dataKey="step"
                        stroke="#888888"
                        fontSize={12}
                        tickLine={false}
                        axisLine={false}
                      />
                      <YAxis
                        stroke="#888888"
                        fontSize={12}
                        tickLine={false}
                        axisLine={false}
                        domain={["auto", "auto"]}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "hsl(var(--card))",
                          borderColor: "hsl(var(--border))",
                          borderRadius: "var(--radius)",
                        }}
                        formatter={(value: number) => [value.toFixed(2), "Equity"]}
                        labelFormatter={(label) => `Point ${label}`}
                      />
                      <Area
                        type="monotone"
                        dataKey="equity"
                        stroke="#10b981"
                        strokeWidth={2}
                        fillOpacity={1}
                        fill="url(#regime-equity-curve-fill)"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="flex h-[220px] items-center justify-center rounded-md bg-muted/40 text-sm text-muted-foreground">
                  Enter equity values to preview the curve.
                </div>
              )}
            </div>
          </div>

          <Button onClick={handleDetect} disabled={submitting}>
            {submitting ? "Detecting..." : "Detect Regime"}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Result</CardTitle>
          <CardDescription>
            Current aggregate regime state and triggered signals.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="bg-muted rounded-lg p-4">
            <p className="text-muted-foreground text-sm">Current Regime</p>
            <p className="text-3xl font-semibold">
              {result ? result.current.name : "--"}
            </p>
            <p className="text-muted-foreground mt-1 text-sm">
              Confidence: {result ? result.current.confidence.toFixed(2) : "--"}
            </p>
          </div>

          {result && (
            <>
              <div className="space-y-2 text-sm">
                <div className="flex items-center justify-between gap-4">
                  <span className="text-muted-foreground">Source</span>
                  <span>{result.source === "mt5" ? "MT5 Real Data" : "Manual Returns"}</span>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <span className="text-muted-foreground">Family</span>
                  <span>{result.current.family}</span>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <span className="text-muted-foreground">Signals Triggered</span>
                  <span>{result.current.signals_triggered.join(", ") || "None"}</span>
                </div>
              </div>

              {result.mode === "full" && (
                <div className="grid gap-3">
                  {result.market && (
                    <div className="rounded-md border p-3 text-sm">
                      <div className="font-medium">Market</div>
                      <div className="text-muted-foreground">{result.market.name}</div>
                    </div>
                  )}
                  {result.volatility && (
                    <div className="rounded-md border p-3 text-sm">
                      <div className="font-medium">Volatility</div>
                      <div className="text-muted-foreground">{result.volatility.name}</div>
                    </div>
                  )}
                  {result.liquidity && (
                    <div className="rounded-md border p-3 text-sm">
                      <div className="font-medium">Liquidity</div>
                      <div className="text-muted-foreground">{result.liquidity.name}</div>
                    </div>
                  )}
                  {result.crisis && (
                    <div className="rounded-md border p-3 text-sm">
                      <div className="font-medium">Crisis</div>
                      <div className="text-muted-foreground">{result.crisis.name}</div>
                    </div>
                  )}
                </div>
              )}

              <div className="space-y-2">
                <div className="text-sm font-medium">Signal Checks</div>
                {result.signals.length === 0 ? (
                  <p className="text-muted-foreground text-sm">No explicit signal rows returned.</p>
                ) : (
                  result.signals.map((signal) => (
                    <div key={signal.signal_key} className="rounded-md border p-3 text-sm">
                      <div className="flex items-center justify-between gap-4">
                        <span className="font-medium">{signal.signal_key}</span>
                        <span>{signal.triggered ? "Triggered" : "Not Triggered"}</span>
                      </div>
                      {signal.message ? (
                        <p className="text-muted-foreground mt-1">{signal.message}</p>
                      ) : null}
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
