"use client"

import { useState } from "react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import simulatorApi, { type Position, type Order } from "@/lib/api/simulator"
import { useSimulatorTradeNotifications } from "@/lib/hooks/use-simulator-trade-notifications"

interface TradingPanelProps {
  sessionId?: number
  symbol?: string
  currentPrice?: number
  chartClickEnabled?: boolean
  onToggleChartClick?: (enabled: boolean) => void
  onTradeExecuted?: (positions: Position[], orders: Order[]) => void
}

export function TradingPanel({
  sessionId,
  symbol = "EURUSD",
  currentPrice,
  chartClickEnabled = false,
  onToggleChartClick,
  onTradeExecuted,
}: TradingPanelProps) {
  const [volume, setVolume] = useState("0.1")
  const [sl, setSl] = useState("")
  const [tp, setTp] = useState("")
  const [tradeMode, setTradeMode] = useState<"market" | "pending">("market")
  const [pendingType, setPendingType] = useState<
    "buy_limit" | "sell_limit" | "buy_stop" | "sell_stop" | "buy_stop_limit" | "sell_stop_limit"
  >("buy_limit")
  const [pendingPrice, setPendingPrice] = useState("")
  const [submitting, setSubmitting] = useState(false)
  const { notifyTrade } = useSimulatorTradeNotifications()

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

    try {
      setSubmitting(true)
      const response = await simulatorApi.executeTrade(sessionId, {
        side,
        volume: vol,
        price: currentPrice,
        sl: sl ? Number(sl) : undefined,
        tp: tp ? Number(tp) : undefined,
      })

      toast.success(`Trade executed (${side.toUpperCase()})`)

      // Notify parent of updated positions
      if (onTradeExecuted && response.positions) {
        onTradeExecuted(response.positions, response.orders || [])
      }

      await notifyTrade({
        side,
        symbol,
        volume: vol,
        price: response.trade?.price ? Number(response.trade.price) : currentPrice,
      })
    } catch (error) {
      toast.error("Trade failed")
    } finally {
      setSubmitting(false)
    }
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

    try {
      setSubmitting(true)
      const response = await simulatorApi.placePendingOrder(sessionId, {
        type: pendingType,
        volume: vol,
        price,
        sl: sl ? Number(sl) : undefined,
        tp: tp ? Number(tp) : undefined,
      })

      toast.success(`Pending order placed (${pendingType.replace("_", " ").toUpperCase()})`)
      if (onTradeExecuted && response.positions) {
        onTradeExecuted(response.positions, response.orders || [])
      }
    } catch (error) {
      toast.error("Pending order failed")
    } finally {
      setSubmitting(false)
    }
  }


  return (
    <Card className="h-fit">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">Trading Panel</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>Symbol</span>
          <span className="font-medium text-foreground">{symbol}</span>
        </div>
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>Current Price</span>
          <span className="font-medium text-foreground">
            {currentPrice ? currentPrice.toFixed(5) : "--"}
          </span>
        </div>

        <div className="space-y-2">
          <Label htmlFor="lotSize">Lot Size</Label>
          <Input
            id="lotSize"
            type="number"
            step="0.01"
            min="0.01"
            value={volume}
            onChange={(e) => setVolume(e.target.value)}
          />
        </div>

        <div className="grid grid-cols-2 gap-2">
          <div className="space-y-2">
            <Label htmlFor="slInput">Stop Loss</Label>
            <Input
              id="slInput"
              type="number"
              value={sl}
              onChange={(e) => setSl(e.target.value)}
              placeholder="Optional"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="tpInput">Take Profit</Label>
            <Input
              id="tpInput"
              type="number"
              value={tp}
              onChange={(e) => setTp(e.target.value)}
              placeholder="Optional"
            />
          </div>
        </div>

        <div className="space-y-2">
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
          <div className="space-y-2">
            <Label>Pending Type</Label>
            <Select
              value={pendingType}
              onValueChange={(val) =>
                setPendingType(
                  val as
                    | "buy_limit"
                    | "sell_limit"
                    | "buy_stop"
                    | "sell_stop"
                    | "buy_stop_limit"
                    | "sell_stop_limit"
                )
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
          <div className="space-y-2">
            <Label htmlFor="pendingPrice">Pending Price</Label>
            <Input
              id="pendingPrice"
              type="number"
              value={pendingPrice}
              onChange={(e) => setPendingPrice(e.target.value)}
              placeholder="Entry price"
            />
          </div>
        )}

        {tradeMode === "market" ? (
          <div className="grid grid-cols-2 gap-2 pt-2">
            <Button
              variant="outline"
              className="text-red-500 hover:text-red-600 border-red-200 hover:bg-red-50 dark:border-red-900/30 dark:hover:bg-red-900/20"
              onClick={() => handleTrade("sell")}
              disabled={submitting || chartClickEnabled}
            >
              SELL
            </Button>
            <Button
              variant="outline"
              className="text-emerald-500 hover:text-emerald-600 border-emerald-200 hover:bg-emerald-50 dark:border-emerald-900/30 dark:hover:bg-emerald-900/20"
              onClick={() => handleTrade("buy")}
              disabled={submitting || chartClickEnabled}
            >
              BUY
            </Button>
          </div>
        ) : (
          <div className="pt-2">
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

        <div className="flex items-center justify-between rounded-md border border-border/60 px-3 py-2 text-xs text-muted-foreground">
          <span>Chart Click Trading</span>
          <Switch
            checked={chartClickEnabled}
            onCheckedChange={(checked) => onToggleChartClick?.(checked)}
          />
        </div>
      </CardContent>
    </Card>
  )
}
