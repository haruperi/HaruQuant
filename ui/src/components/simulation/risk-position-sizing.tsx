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
import { getErrorMessage } from "@/lib/api-error"
import riskApi, {
  type PositionSizingMethod,
  type PositionSizingRequest,
  type PositionSizingResponse,
} from "@/lib/api/risk"

const methodLabels: Record<PositionSizingMethod, string> = {
  fixed_lot: "Fixed Lot",
  milestone: "Milestone",
  fixed_risk: "Fixed Risk",
  kelly: "Kelly",
  volatility: "Volatility",
  fixed_fractional: "Fixed Fractional",
}

export function RiskPositionSizingPanel() {
  const [method, setMethod] = useState<PositionSizingMethod>("fixed_lot")
  const [accountBalance, setAccountBalance] = useState("10000")
  const [entryPrice, setEntryPrice] = useState("1.1000")
  const [stopLossPips, setStopLossPips] = useState("50")
  const [pipSize, setPipSize] = useState("0.0001")
  const [signalType, setSignalType] = useState("buy")

  const [lotSize, setLotSize] = useState("0.10")
  const [initialBalance, setInitialBalance] = useState("10000")
  const [baseLotSize, setBaseLotSize] = useState("0.10")
  const [milestoneAmount, setMilestoneAmount] = useState("3000")
  const [lotIncrement, setLotIncrement] = useState("0.20")
  const [riskPercent, setRiskPercent] = useState("1.0")
  const [kellyLimit, setKellyLimit] = useState("0.25")
  const [winRate, setWinRate] = useState("0.55")
  const [avgWin, setAvgWin] = useState("150")
  const [avgLoss, setAvgLoss] = useState("100")
  const [atr, setAtr] = useState("0.0080")
  const [atrMultiplier, setAtrMultiplier] = useState("1.0")
  const [fraction, setFraction] = useState("2.0")

  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState<PositionSizingResponse | null>(null)

  const requiresStopLoss = method === "fixed_risk"

  const methodDescription = useMemo(() => {
    switch (method) {
      case "fixed_lot":
        return "Always return the configured lot size."
      case "milestone":
        return "Increase lot size as account balance crosses configured milestones."
      case "fixed_risk":
        return "Risk a fixed percent of account balance using entry and stop loss distance."
      case "kelly":
        return "Size from Kelly fraction inputs such as win rate and average win/loss."
      case "volatility":
        return "Size inversely to ATR-style volatility supplied as input."
      case "fixed_fractional":
        return "Use a fixed percentage of account capital per position."
    }
  }, [method])

  const handleCalculate = async () => {
    const payload: PositionSizingRequest = {
      method,
      account_balance: Number(accountBalance),
      entry_price: Number(entryPrice),
      signal_type: signalType,
      config: {},
      context: {},
    }

    if (!Number.isFinite(payload.account_balance) || payload.account_balance <= 0) {
      toast.error("Account balance must be greater than zero.")
      return
    }

    if (!Number.isFinite(payload.entry_price) || payload.entry_price <= 0) {
      toast.error("Entry price must be greater than zero.")
      return
    }

    if (requiresStopLoss) {
      const stopLossPipsValue = Number(stopLossPips)
      const pipSizeValue = Number(pipSize)
      if (!Number.isFinite(stopLossPipsValue) || stopLossPipsValue <= 0) {
        toast.error("Stop loss in pips must be greater than zero for fixed-risk sizing.")
        return
      }
      if (!Number.isFinite(pipSizeValue) || pipSizeValue <= 0) {
        toast.error("Pip size must be greater than zero for fixed-risk sizing.")
        return
      }
      const stopDistance = stopLossPipsValue * pipSizeValue
      payload.stop_loss =
        signalType === "sell"
          ? payload.entry_price + stopDistance
          : payload.entry_price - stopDistance
    }

    if (method === "fixed_lot") {
      payload.config = { lot_size: Number(lotSize) }
    }

    if (method === "milestone") {
      payload.config = {
        initial_balance: Number(initialBalance),
        base_lot_size: Number(baseLotSize),
        milestone_amount: Number(milestoneAmount),
        lot_increment: Number(lotIncrement),
      }
    }

    if (method === "fixed_risk") {
      payload.config = {
        risk_percent: Number(riskPercent),
        use_dynamic_stop_loss: false,
      }
    }

    if (method === "kelly") {
      payload.config = {
        kelly_fraction_limit: Number(kellyLimit),
      }
      payload.context = {
        win_rate: Number(winRate),
        avg_win: Number(avgWin),
        avg_loss: Number(avgLoss),
      }
    }

    if (method === "volatility") {
      payload.config = {
        risk_percent: Number(riskPercent),
        atr_multiplier: Number(atrMultiplier),
      }
      payload.context = {
        atr: Number(atr),
      }
    }

    if (method === "fixed_fractional") {
      payload.config = {
        fraction: Number(fraction),
      }
    }

    try {
      setSubmitting(true)
      const response = await riskApi.calculatePositionSize(payload)
      setResult(response)
      toast.success("Position size calculated.")
    } catch (error) {
      toast.error("Failed to calculate position size.", {
        description: getErrorMessage(error),
      })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1.3fr)_minmax(320px,0.7fr)]">
      <Card>
        <CardHeader>
          <CardTitle>Position Sizing</CardTitle>
          <CardDescription>
            Choose a sizing method, enter the required inputs, and calculate the
            lot size using the live Python risk engine.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid gap-2">
            <Label htmlFor="sizing-method">Method</Label>
            <Select value={method} onValueChange={(value) => setMethod(value as PositionSizingMethod)}>
              <SelectTrigger id="sizing-method">
                <SelectValue placeholder="Select method" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="fixed_lot">Fixed Lot</SelectItem>
                <SelectItem value="milestone">Milestone</SelectItem>
                <SelectItem value="fixed_risk">Fixed Risk</SelectItem>
                <SelectItem value="kelly">Kelly</SelectItem>
                <SelectItem value="volatility">Volatility</SelectItem>
                <SelectItem value="fixed_fractional">Fixed Fractional</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-muted-foreground text-sm">{methodDescription}</p>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="grid gap-2">
              <Label htmlFor="account-balance">Account Balance</Label>
              <Input id="account-balance" value={accountBalance} onChange={(event) => setAccountBalance(event.target.value)} />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="entry-price">Entry Price</Label>
              <Input id="entry-price" value={entryPrice} onChange={(event) => setEntryPrice(event.target.value)} />
            </div>
          </div>

          {requiresStopLoss && (
            <div className="grid gap-4 md:grid-cols-3">
              <div className="grid gap-2">
                <Label htmlFor="stop-loss-pips">Stop Loss (Pips)</Label>
                <Input
                  id="stop-loss-pips"
                  value={stopLossPips}
                  onChange={(event) => setStopLossPips(event.target.value)}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="pip-size">Pip Size</Label>
                <Input
                  id="pip-size"
                  value={pipSize}
                  onChange={(event) => setPipSize(event.target.value)}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="signal-type">Signal Type</Label>
                <Select value={signalType} onValueChange={setSignalType}>
                  <SelectTrigger id="signal-type">
                    <SelectValue placeholder="Select side" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="buy">Buy</SelectItem>
                    <SelectItem value="sell">Sell</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}

          {method === "fixed_lot" && (
            <div className="grid gap-2 md:max-w-xs">
              <Label htmlFor="lot-size">Lot Size</Label>
              <Input id="lot-size" value={lotSize} onChange={(event) => setLotSize(event.target.value)} />
            </div>
          )}

          {method === "milestone" && (
            <div className="grid gap-4 md:grid-cols-2">
              <div className="grid gap-2">
                <Label htmlFor="initial-balance">Initial Balance</Label>
                <Input id="initial-balance" value={initialBalance} onChange={(event) => setInitialBalance(event.target.value)} />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="base-lot-size">Base Lot Size</Label>
                <Input id="base-lot-size" value={baseLotSize} onChange={(event) => setBaseLotSize(event.target.value)} />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="milestone-amount">Milestone Amount</Label>
                <Input id="milestone-amount" value={milestoneAmount} onChange={(event) => setMilestoneAmount(event.target.value)} />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="lot-increment">Lot Increment</Label>
                <Input id="lot-increment" value={lotIncrement} onChange={(event) => setLotIncrement(event.target.value)} />
              </div>
            </div>
          )}

          {method === "fixed_risk" && (
            <div className="grid gap-2 md:max-w-xs">
              <Label htmlFor="risk-percent">Risk Percent</Label>
              <Input id="risk-percent" value={riskPercent} onChange={(event) => setRiskPercent(event.target.value)} />
            </div>
          )}

          {method === "kelly" && (
            <div className="grid gap-4 md:grid-cols-2">
              <div className="grid gap-2">
                <Label htmlFor="kelly-limit">Kelly Fraction Limit</Label>
                <Input id="kelly-limit" value={kellyLimit} onChange={(event) => setKellyLimit(event.target.value)} />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="win-rate">Win Rate</Label>
                <Input id="win-rate" value={winRate} onChange={(event) => setWinRate(event.target.value)} />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="avg-win">Average Win</Label>
                <Input id="avg-win" value={avgWin} onChange={(event) => setAvgWin(event.target.value)} />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="avg-loss">Average Loss</Label>
                <Input id="avg-loss" value={avgLoss} onChange={(event) => setAvgLoss(event.target.value)} />
              </div>
            </div>
          )}

          {method === "volatility" && (
            <div className="grid gap-4 md:grid-cols-2">
              <div className="grid gap-2">
                <Label htmlFor="vol-risk-percent">Risk Percent</Label>
                <Input id="vol-risk-percent" value={riskPercent} onChange={(event) => setRiskPercent(event.target.value)} />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="atr">ATR</Label>
                <Input id="atr" value={atr} onChange={(event) => setAtr(event.target.value)} />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="atr-multiplier">ATR Multiplier</Label>
                <Input id="atr-multiplier" value={atrMultiplier} onChange={(event) => setAtrMultiplier(event.target.value)} />
              </div>
            </div>
          )}

          {method === "fixed_fractional" && (
            <div className="grid gap-2 md:max-w-xs">
              <Label htmlFor="fraction">Capital Fraction Percent</Label>
              <Input id="fraction" value={fraction} onChange={(event) => setFraction(event.target.value)} />
            </div>
          )}

          <Button onClick={handleCalculate} disabled={submitting}>
            {submitting ? "Calculating..." : "Calculate Position Size"}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Result</CardTitle>
          <CardDescription>
            Calculated size for {methodLabels[method]}.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="bg-muted rounded-lg p-4">
            <p className="text-muted-foreground text-sm">Calculated Lots</p>
            <p className="text-3xl font-semibold">
              {result ? result.size.toFixed(4) : "--"}
            </p>
          </div>

          {result && (
            <div className="space-y-2 text-sm">
              <div className="flex items-center justify-between gap-4">
                <span className="text-muted-foreground">Method</span>
                <span>{methodLabels[result.method]}</span>
              </div>
              <div className="flex items-center justify-between gap-4">
                <span className="text-muted-foreground">Account Balance</span>
                <span>{String(result.normalized_inputs.account_balance ?? "--")}</span>
              </div>
              <div className="flex items-center justify-between gap-4">
                <span className="text-muted-foreground">Entry Price</span>
                <span>{String(result.normalized_inputs.entry_price ?? "--")}</span>
              </div>
              {result.normalized_inputs.stop_loss !== null && result.normalized_inputs.stop_loss !== undefined && (
                <div className="flex items-center justify-between gap-4">
                  <span className="text-muted-foreground">Stop Loss</span>
                  <span>{String(result.normalized_inputs.stop_loss)}</span>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
