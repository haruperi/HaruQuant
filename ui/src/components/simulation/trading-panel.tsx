"use client"

import { useEffect, useState } from "react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { validatePendingOrder } from "@/components/simulation/order-validation"
import { getErrorMessage } from "@/lib/api-error"
import riskApi, { type PositionSizingMethod } from "@/lib/api/risk"
import simulatorApi, {
  type Position,
  type Order,
  type SimulationGovernanceReport,
  type SimulationMode,
  type SimulationTradePreviewResponse,
  type SimulationRecommendationSummary,
  type SimulationRiskSnapshotSummary,
  type SimulationRiskScorecardSummary,
} from "@/lib/api/simulator"
import { useSimulatorTradeNotifications } from "@/lib/hooks/use-simulator-trade-notifications"

interface TradingPanelProps {
  sessionId?: number
  mode?: SimulationMode
  symbol?: string
  symbols?: string[]
  currentPrice?: number
  currentPricesBySymbol?: Record<string, number>
  accountEquity?: number
  onTradeExecuted?: (positions: Position[], orders: Order[]) => void
  onTradeAttemptResult?: (result: { accepted: boolean; kind: "market" | "pending" }) => void
  onGovernanceEvaluated?: (report: SimulationGovernanceReport) => void
  onRiskSnapshotUpdate?: (snapshot: SimulationRiskSnapshotSummary) => void
  onRiskScorecardUpdate?: (scorecard: SimulationRiskScorecardSummary) => void
  onRecommendationsUpdate?: (recommendations: SimulationRecommendationSummary) => void
  onPauseForManualReview?: () => Promise<void> | void
}

export function TradingPanel({
  sessionId,
  mode = "manual",
  symbol = "EURUSD",
  symbols,
  currentPrice,
  currentPricesBySymbol,
  accountEquity,
  onTradeExecuted,
  onTradeAttemptResult,
  onGovernanceEvaluated,
  onRiskSnapshotUpdate,
  onRiskScorecardUpdate,
  onRecommendationsUpdate,
  onPauseForManualReview,
}: TradingPanelProps) {
  const availableSymbols = symbols && symbols.length > 0 ? symbols : [symbol]
  const availableSymbolsKey = (symbols && symbols.length > 0 ? symbols : [symbol]).join("|")
  const [selectedSymbol, setSelectedSymbol] = useState(availableSymbols[0] || symbol)
  const [volume, setVolume] = useState("0.1")
  const [sl, setSl] = useState("")
  const [tp, setTp] = useState("")
  const [sizingMode, setSizingMode] = useState<PositionSizingMethod>("fixed_lot")
  const [riskPercent, setRiskPercent] = useState("1.0")
  const [initialBalance, setInitialBalance] = useState("10000")
  const [baseLotSize, setBaseLotSize] = useState("0.10")
  const [milestoneAmount, setMilestoneAmount] = useState("3000")
  const [lotIncrement, setLotIncrement] = useState("0.20")
  const [kellyLimit, setKellyLimit] = useState("0.25")
  const [winRate, setWinRate] = useState("0.55")
  const [avgWin, setAvgWin] = useState("150")
  const [avgLoss, setAvgLoss] = useState("100")
  const [atr, setAtr] = useState("0.0080")
  const [atrMultiplier, setAtrMultiplier] = useState("1.0")
  const [fraction, setFraction] = useState("2.0")
  const [tradeMode, setTradeMode] = useState<"market" | "pending">("market")
  const [pendingType, setPendingType] = useState<
    "buy_limit" | "sell_limit" | "buy_stop" | "sell_stop" | "buy_stop_limit" | "sell_stop_limit"
  >("buy_limit")
  const [pendingPrice, setPendingPrice] = useState("")
  const [submitting, setSubmitting] = useState(false)
  const [confirmedSizingKey, setConfirmedSizingKey] = useState<string | null>(null)
  const [previewOpen, setPreviewOpen] = useState(false)
  const [previewSide, setPreviewSide] = useState<"buy" | "sell">("buy")
  const [previewData, setPreviewData] = useState<SimulationTradePreviewResponse | null>(null)
  const { notifyTrade } = useSimulatorTradeNotifications()

  const selectedCurrentPrice =
    currentPricesBySymbol?.[selectedSymbol] ??
    (availableSymbols.length === 1 ? currentPrice : undefined)

  useEffect(() => {
    const nextSymbols = symbols && symbols.length > 0 ? symbols : [symbol]
    if (nextSymbols.length > 0 && !nextSymbols.includes(selectedSymbol)) {
      setSelectedSymbol(nextSymbols[0])
    }
  }, [availableSymbolsKey, selectedSymbol, symbol, symbols])

  const resetSizingConfirmation = () => setConfirmedSizingKey(null)
  const renderGovernanceMessages = (report?: SimulationGovernanceReport | null) => {
    if (!report) {
      return ""
    }
    const warningMessages = (report.warnings || [])
      .map((item) => item.message)
      .filter(Boolean)
    const breachMessages = (report.breaches || [])
      .map((item) => item.message)
      .filter(Boolean)
    return [...breachMessages, ...warningMessages].join(" | ")
  }

  const extractGovernanceFromError = (error: unknown): SimulationGovernanceReport | null => {
    if (!(error instanceof Error)) {
      return null
    }
    const detail = (error as Error & { detail?: unknown }).detail
    if (!detail || typeof detail !== "object") {
      return null
    }
    const governance = (detail as { governance?: unknown }).governance
    if (!governance || typeof governance !== "object") {
      return null
    }
    return governance as SimulationGovernanceReport
  }

  const requiresStopLossForSizing = sizingMode === "fixed_risk"

  const buildSizingKey = (entryPrice: number) =>
    [
      selectedSymbol,
      tradeMode,
      entryPrice.toFixed(10),
      pendingType,
      sl.trim(),
      sizingMode,
      riskPercent.trim(),
      initialBalance.trim(),
      baseLotSize.trim(),
      milestoneAmount.trim(),
      lotIncrement.trim(),
      kellyLimit.trim(),
      winRate.trim(),
      avgWin.trim(),
      avgLoss.trim(),
      atr.trim(),
      atrMultiplier.trim(),
      fraction.trim(),
      sizingMode,
    ].join("|")

  const calculateSuggestedSize = async (entryPrice: number, signalType: "buy" | "sell") => {
    if (!accountEquity || accountEquity <= 0) {
      toast.error("Account equity is unavailable for position sizing.")
      return null
    }

    const payload: {
      method: PositionSizingMethod
      account_balance: number
      entry_price: number
      stop_loss?: number
      signal_type: string
      config?: Record<string, unknown>
      context?: Record<string, unknown>
    } = {
      method: sizingMode,
      account_balance: accountEquity,
      entry_price: entryPrice,
      signal_type: signalType,
      config: {},
      context: {},
    }

    if (sizingMode === "fixed_lot") {
      const lotSizeValue = Number(volume.replace(",", "."))
      if (!lotSizeValue || Number.isNaN(lotSizeValue) || lotSizeValue <= 0) {
        toast.error("Enter a valid lot size.")
        return null
      }
      payload.config = { lot_size: lotSizeValue }
    }

    if (sizingMode === "milestone") {
      payload.config = {
        initial_balance: Number(initialBalance),
        base_lot_size: Number(baseLotSize),
        milestone_amount: Number(milestoneAmount),
        lot_increment: Number(lotIncrement),
      }
    }

    if (sizingMode === "fixed_risk") {
      const stopLoss = Number(sl.replace(",", "."))
      if (!sl.trim() || Number.isNaN(stopLoss)) {
        toast.error("Fixed-risk sizing requires a valid Stop Loss.")
        return null
      }
      if (stopLoss === entryPrice) {
        toast.error("Stop Loss must differ from the entry price for fixed-risk sizing.")
        return null
      }
      const riskPercentValue = Number(riskPercent.replace(",", "."))
      if (!riskPercentValue || Number.isNaN(riskPercentValue) || riskPercentValue <= 0) {
        toast.error("Enter a valid Risk %.")
        return null
      }
      payload.stop_loss = stopLoss
      payload.config = {
        risk_percent: riskPercentValue,
        use_dynamic_stop_loss: false,
      }
    }

    if (sizingMode === "kelly") {
      payload.config = {
        kelly_fraction_limit: Number(kellyLimit),
      }
      payload.context = {
        win_rate: Number(winRate),
        avg_win: Number(avgWin),
        avg_loss: Number(avgLoss),
      }
    }

    if (sizingMode === "volatility") {
      payload.config = {
        risk_percent: Number(riskPercent),
        atr_multiplier: Number(atrMultiplier),
      }
      payload.context = {
        atr: Number(atr),
      }
    }

    if (sizingMode === "fixed_fractional") {
      payload.config = {
        fraction: Number(fraction),
      }
    }

    const response = await riskApi.calculatePositionSize(payload)
    const suggestedSize = Number(response.size)
    if (!suggestedSize || Number.isNaN(suggestedSize) || suggestedSize <= 0) {
      toast.error("Position sizing returned an invalid lot size.")
      return null
    }

    setVolume(suggestedSize.toFixed(2))
    setConfirmedSizingKey(buildSizingKey(entryPrice))
    toast.success("Suggested lot size updated. Review it, then submit the order.")
    return suggestedSize
  }

  const executeApprovedTrade = async (side: "buy" | "sell", manualReviewAccepted = false) => {
    const vol = Number(volume.replace(",", "."))
    try {
      setSubmitting(true)
      const response = await simulatorApi.executeTrade(sessionId!, {
        symbol: selectedSymbol,
        side,
        volume: vol,
        sl: sl ? Number(sl) : undefined,
        tp: tp ? Number(tp) : undefined,
        manual_review_accepted: manualReviewAccepted,
      })

      onTradeAttemptResult?.({ accepted: true, kind: "market" })
      toast.success(`Trade executed (${side.toUpperCase()})`)
      if (onTradeExecuted && response.positions) {
        onTradeExecuted(response.positions, response.orders || [])
      }
      if (response.governance?.warnings?.length) {
        onGovernanceEvaluated?.(response.governance)
        toast.warning(response.governance.reason || "Trade accepted with governance warnings.", {
          description: renderGovernanceMessages(response.governance) || undefined,
        })
      } else if (response.governance) {
        onGovernanceEvaluated?.(response.governance)
      }
      if (response.risk_snapshot) {
        onRiskSnapshotUpdate?.(response.risk_snapshot)
      }
      if (response.risk_scorecard) {
        onRiskScorecardUpdate?.(response.risk_scorecard)
      }
      if (response.recommendations) {
        onRecommendationsUpdate?.(response.recommendations)
      }

      await notifyTrade({
        side,
        symbol: selectedSymbol,
        volume: vol,
        price: response.trade?.price ? Number(response.trade.price) : selectedCurrentPrice,
      })
      resetSizingConfirmation()
      setPreviewOpen(false)
      setPreviewData(null)
    } catch (error) {
      const governance = extractGovernanceFromError(error)
      if (governance) {
        onTradeAttemptResult?.({ accepted: false, kind: "market" })
        onGovernanceEvaluated?.(governance)
        toast.error(governance.reason || "Trade rejected by governance.", {
          description: renderGovernanceMessages(governance) || undefined,
        })
        return
      }
      toast.error("Trade failed", {
        description: getErrorMessage(error),
      })
    } finally {
      setSubmitting(false)
    }
  }

  const handleTrade = async (side: "buy" | "sell") => {
    if (!sessionId) {
      toast.error("Start a simulation session first.")
      return
    }

    const vol = Number(volume.replace(",", "."))
    if (!vol || Number.isNaN(vol)) {
      toast.error("Enter a valid lot size.")
      return
    }

    const entryPrice = selectedCurrentPrice
    if (sizingMode !== "fixed_lot") {
      if (!entryPrice || Number.isNaN(entryPrice)) {
        toast.error("Current price is unavailable for position sizing.")
        return
      }
      const sizingKey = buildSizingKey(entryPrice)
      if (confirmedSizingKey !== sizingKey) {
        try {
          setSubmitting(true)
          await calculateSuggestedSize(entryPrice, side)
        } catch (error) {
          toast.error("Failed to calculate position size", {
            description: getErrorMessage(error),
          })
        } finally {
          setSubmitting(false)
        }
        return
      }
    }

    if (mode === "manual") {
      try {
        setSubmitting(true)
        await onPauseForManualReview?.()
        const preview = await simulatorApi.previewTrade(sessionId, {
          symbol: selectedSymbol,
          side,
          volume: vol,
          sl: sl ? Number(sl) : undefined,
          tp: tp ? Number(tp) : undefined,
        })
        setPreviewSide(side)
        setPreviewData(preview)
        setPreviewOpen(true)
        if (preview.governance) {
          onGovernanceEvaluated?.(preview.governance)
        }
      } catch (error) {
        toast.error("Failed to preview trade", {
          description: getErrorMessage(error),
        })
      } finally {
        setSubmitting(false)
      }
      return
    }
    await executeApprovedTrade(side, false)
  }

  const handlePending = async () => {
    if (!sessionId) {
      toast.error("Start a simulation session first.")
      return
    }

    const vol = Number(volume.replace(",", "."))
    if (!vol || Number.isNaN(vol)) {
      toast.error("Enter a valid lot size.")
      return
    }

    const price = Number(pendingPrice.replace(",", "."))
    if (!price || Number.isNaN(price)) {
      toast.error("Enter a valid pending price.")
      return
    }

    const slValue = sl ? Number(sl.replace(",", ".")) : null
    if (sl && (slValue === null || Number.isNaN(slValue))) {
      toast.error("Enter a valid Stop Loss.")
      return
    }

    const tpValue = tp ? Number(tp.replace(",", ".")) : null
    if (tp && (tpValue === null || Number.isNaN(tpValue))) {
      toast.error("Enter a valid Take Profit.")
      return
    }

    const validationError = validatePendingOrder({
      type: pendingType,
      volume: vol,
      price,
      sl: slValue,
      tp: tpValue,
      currentPrice: selectedCurrentPrice ?? null,
    })
    if (validationError) {
      toast.error(validationError)
      return
    }

    if (sizingMode !== "fixed_lot") {
      const signalType = pendingType.startsWith("sell") ? "sell" : "buy"
      const sizingKey = buildSizingKey(price)
      if (confirmedSizingKey !== sizingKey) {
        try {
          setSubmitting(true)
          await calculateSuggestedSize(price, signalType)
        } catch (error) {
          toast.error("Failed to calculate position size", {
            description: getErrorMessage(error),
          })
        } finally {
          setSubmitting(false)
        }
        return
      }
    }

    try {
      setSubmitting(true)
      const response = await simulatorApi.placePendingOrder(sessionId, {
        symbol: selectedSymbol,
        type: pendingType,
        volume: vol,
        price,
        sl: slValue ?? undefined,
        tp: tpValue ?? undefined,
      })

      onTradeAttemptResult?.({ accepted: true, kind: "pending" })
      toast.success(`Pending order placed (${pendingType.replace("_", " ").toUpperCase()})`)
      if (onTradeExecuted && response.positions) {
        onTradeExecuted(response.positions, response.orders || [])
      }
      if (response.governance?.warnings?.length) {
        onGovernanceEvaluated?.(response.governance)
        toast.warning(response.governance.reason || "Order accepted with governance warnings.", {
          description: renderGovernanceMessages(response.governance) || undefined,
        })
      } else if (response.governance) {
        onGovernanceEvaluated?.(response.governance)
      }
      if (response.risk_snapshot) {
        onRiskSnapshotUpdate?.(response.risk_snapshot)
      }
      if (response.risk_scorecard) {
        onRiskScorecardUpdate?.(response.risk_scorecard)
      }
      if (response.recommendations) {
        onRecommendationsUpdate?.(response.recommendations)
      }
      resetSizingConfirmation()
    } catch (error) {
      const governance = extractGovernanceFromError(error)
      if (governance) {
        onTradeAttemptResult?.({ accepted: false, kind: "pending" })
        onGovernanceEvaluated?.(governance)
        toast.error(governance.reason || "Pending order rejected by governance.", {
          description: renderGovernanceMessages(governance) || undefined,
        })
        return
      }
      toast.error("Pending order failed", {
        description: getErrorMessage(error),
      })
    } finally {
      setSubmitting(false)
    }
  }


  return (
    <Card className="h-fit">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">Trading Panel</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap items-end gap-4">
          <div className="min-w-[100px] space-y-1 text-xs text-muted-foreground">
            <div>Symbol</div>
            {availableSymbols.length > 1 ? (
              <Select value={selectedSymbol} onValueChange={setSelectedSymbol}>
                <SelectTrigger className="h-9 min-w-[140px] bg-background text-foreground">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {availableSymbols.map((item) => (
                    <SelectItem key={item} value={item}>
                      {item}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ) : (
              <div className="font-medium text-foreground">{selectedSymbol}</div>
            )}
          </div>

          <div className="min-w-[120px] space-y-1 text-xs text-muted-foreground">
            <div>Current Price</div>
            <div className="font-medium text-foreground">
              {selectedCurrentPrice ? selectedCurrentPrice.toFixed(5) : "--"}
            </div>
          </div>

          <div className="w-[120px] space-y-2">
            <Label>Sizing Mode</Label>
            <Select
              value={sizingMode}
              onValueChange={(value) => {
                setSizingMode(value as PositionSizingMethod)
                resetSizingConfirmation()
              }}
            >
              <SelectTrigger>
                <SelectValue />
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
          </div>

          {(sizingMode === "fixed_risk" || sizingMode === "volatility") && (
            <div className="w-[120px] space-y-2">
              <Label htmlFor="riskPercent">Risk %</Label>
              <Input
                id="riskPercent"
                type="number"
                step="0.1"
                min="0.1"
                value={riskPercent}
                onChange={(e) => {
                  setRiskPercent(e.target.value)
                  resetSizingConfirmation()
                }}
              />
            </div>
          )}

          {sizingMode === "milestone" && (
            <>
              <div className="w-[120px] space-y-2">
                <Label htmlFor="initialBalance">Initial Balance</Label>
                <Input
                  id="initialBalance"
                  type="number"
                  value={initialBalance}
                  onChange={(e) => {
                    setInitialBalance(e.target.value)
                    resetSizingConfirmation()
                  }}
                />
              </div>
              <div className="w-[120px] space-y-2">
                <Label htmlFor="baseLotSize">Base Lot</Label>
                <Input
                  id="baseLotSize"
                  type="number"
                  value={baseLotSize}
                  onChange={(e) => {
                    setBaseLotSize(e.target.value)
                    resetSizingConfirmation()
                  }}
                />
              </div>
              <div className="w-[120px] space-y-2">
                <Label htmlFor="milestoneAmount">Milestone</Label>
                <Input
                  id="milestoneAmount"
                  type="number"
                  value={milestoneAmount}
                  onChange={(e) => {
                    setMilestoneAmount(e.target.value)
                    resetSizingConfirmation()
                  }}
                />
              </div>
              <div className="w-[120px] space-y-2">
                <Label htmlFor="lotIncrement">Increment</Label>
                <Input
                  id="lotIncrement"
                  type="number"
                  value={lotIncrement}
                  onChange={(e) => {
                    setLotIncrement(e.target.value)
                    resetSizingConfirmation()
                  }}
                />
              </div>
            </>
          )}

          {sizingMode === "kelly" && (
            <>
              <div className="w-[120px] space-y-2">
                <Label htmlFor="kellyLimit">Kelly Limit</Label>
                <Input
                  id="kellyLimit"
                  type="number"
                  value={kellyLimit}
                  onChange={(e) => {
                    setKellyLimit(e.target.value)
                    resetSizingConfirmation()
                  }}
                />
              </div>
              <div className="w-[120px] space-y-2">
                <Label htmlFor="winRate">Win Rate</Label>
                <Input
                  id="winRate"
                  type="number"
                  value={winRate}
                  onChange={(e) => {
                    setWinRate(e.target.value)
                    resetSizingConfirmation()
                  }}
                />
              </div>
              <div className="w-[120px] space-y-2">
                <Label htmlFor="avgWin">Avg Win</Label>
                <Input
                  id="avgWin"
                  type="number"
                  value={avgWin}
                  onChange={(e) => {
                    setAvgWin(e.target.value)
                    resetSizingConfirmation()
                  }}
                />
              </div>
              <div className="w-[120px] space-y-2">
                <Label htmlFor="avgLoss">Avg Loss</Label>
                <Input
                  id="avgLoss"
                  type="number"
                  value={avgLoss}
                  onChange={(e) => {
                    setAvgLoss(e.target.value)
                    resetSizingConfirmation()
                  }}
                />
              </div>
            </>
          )}

          {sizingMode === "volatility" && (
            <>
              <div className="w-[120px] space-y-2">
                <Label htmlFor="atrValue">ATR</Label>
                <Input
                  id="atrValue"
                  type="number"
                  value={atr}
                  onChange={(e) => {
                    setAtr(e.target.value)
                    resetSizingConfirmation()
                  }}
                />
              </div>
              <div className="w-[120px] space-y-2">
                <Label htmlFor="atrMultiplier">ATR Mult</Label>
                <Input
                  id="atrMultiplier"
                  type="number"
                  value={atrMultiplier}
                  onChange={(e) => {
                    setAtrMultiplier(e.target.value)
                    resetSizingConfirmation()
                  }}
                />
              </div>
            </>
          )}

          {sizingMode === "fixed_fractional" && (
            <div className="w-[120px] space-y-2">
              <Label htmlFor="fractionValue">Fraction %</Label>
              <Input
                id="fractionValue"
                type="number"
                value={fraction}
                onChange={(e) => {
                  setFraction(e.target.value)
                  resetSizingConfirmation()
                }}
              />
            </div>
          )}

          <div className="w-[120px] space-y-2">
            <Label htmlFor="lotSize">Lot Size</Label>
            <Input
              id="lotSize"
              type="number"
              step="0.01"
              min="0.01"
              value={volume}
              onChange={(e) => {
                setVolume(e.target.value)
                resetSizingConfirmation()
              }}
            />
          </div>

          <div className="w-[140px] space-y-2">
            <Label htmlFor="slInput">Stop Loss</Label>
            <Input
              id="slInput"
              type="number"
              value={sl}
              onChange={(e) => {
                setSl(e.target.value)
                resetSizingConfirmation()
              }}
              placeholder={requiresStopLossForSizing ? "Required" : "Optional"}
            />
          </div>

          <div className="w-[140px] space-y-2">
            <Label htmlFor="tpInput">Take Profit</Label>
            <Input
              id="tpInput"
              type="number"
              value={tp}
              onChange={(e) => setTp(e.target.value)}
              placeholder="Optional"
            />
          </div>

          <div className="w-[160px] space-y-2">
            <Label>Order Type</Label>
            <Select
              value={tradeMode}
              onValueChange={(val) => setTradeMode(val as "market" | "pending")}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="market">Market</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {tradeMode === "pending" && (
            <div className="w-[170px] space-y-2">
              <Label>Pending Type</Label>
              <Select
                value={pendingType}
                onValueChange={(val) =>
                  {
                    setPendingType(
                      val as
                        | "buy_limit"
                        | "sell_limit"
                        | "buy_stop"
                        | "sell_stop"
                        | "buy_stop_limit"
                        | "sell_stop_limit"
                    )
                    resetSizingConfirmation()
                  }
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="buy_limit">Buy Limit</SelectItem>
                  <SelectItem value="sell_limit">Sell Limit</SelectItem>
                  <SelectItem value="buy_stop">Buy Stop</SelectItem>
                  <SelectItem value="sell_stop">Sell Stop</SelectItem>
                  <SelectItem value="buy_stop_limit">Buy Stop Limit</SelectItem>
                  <SelectItem value="sell_stop_limit">Sell Stop Limit</SelectItem>
                </SelectContent>
              </Select>
            </div>
          )}

          {tradeMode === "pending" && (
            <div className="w-[150px] space-y-2">
              <Label htmlFor="pendingPrice">Pending Price</Label>
              <Input
                id="pendingPrice"
                type="number"
                value={pendingPrice}
                onChange={(e) => {
                  setPendingPrice(e.target.value)
                  resetSizingConfirmation()
                }}
                placeholder="Entry price"
              />
            </div>
          )}

          {tradeMode === "market" ? (
            <div className="flex min-w-[220px] gap-2">
              <Button
                variant="outline"
                className="flex-1 text-red-500 hover:text-red-600 border-red-200 hover:bg-red-50 dark:border-red-900/30 dark:hover:bg-red-900/20"
                onClick={() => handleTrade("sell")}
                disabled={submitting}
              >
                SELL
              </Button>
              <Button
                variant="outline"
                className="flex-1 text-emerald-500 hover:text-emerald-600 border-emerald-200 hover:bg-emerald-50 dark:border-emerald-900/30 dark:hover:bg-emerald-900/20"
                onClick={() => handleTrade("buy")}
                disabled={submitting}
              >
                BUY
              </Button>
            </div>
          ) : (
            <div className="min-w-[180px]">
              <Button
                variant="outline"
                className="w-full border-slate-200 hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-900/30"
                onClick={handlePending}
                disabled={submitting}
              >
                Place Pending Order
              </Button>
            </div>
          )}

        </div>
      </CardContent>
      <Dialog open={previewOpen} onOpenChange={setPreviewOpen}>
        <DialogContent className="max-w-5xl">
          <DialogHeader>
            <DialogTitle>Manual Trade Review</DialogTitle>
            <DialogDescription>
              Review the proposed trade before it is placed. Green proposed values are within threshold; red ones exceed it.
            </DialogDescription>
          </DialogHeader>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b text-left">
                  <th className="px-3 py-2">Item</th>
                  <th className="px-3 py-2">Current Value</th>
                  <th className="px-3 py-2">Proposed Value</th>
                  <th className="px-3 py-2">Reference / Limit / Threshold</th>
                </tr>
              </thead>
              <tbody>
                {(previewData?.rows || []).map((row) => (
                  <tr key={row.key} className="border-b">
                    <td className="px-3 py-2">{row.item}</td>
                    <td className="px-3 py-2 text-muted-foreground">{row.current_value}</td>
                    <td className={`px-3 py-2 font-medium ${row.acceptable ? "text-emerald-500" : "text-red-500"}`}>
                      {row.proposed_value}
                    </td>
                    <td className="px-3 py-2 text-muted-foreground">{row.reference_value}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              onClick={() => {
                setPreviewOpen(false)
                setPreviewData(null)
                onTradeAttemptResult?.({ accepted: false, kind: "market" })
              }}
              disabled={submitting}
            >
              Reject
            </Button>
            <Button onClick={() => void executeApprovedTrade(previewSide, true)} disabled={submitting}>
              {submitting ? "Placing..." : "Accept"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  )
}
