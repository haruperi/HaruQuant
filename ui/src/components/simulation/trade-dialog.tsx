"use client"

import { useState } from "react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import simulatorApi from "@/lib/api/simulator"
import { useSimulatorTradeNotifications } from "@/lib/hooks/use-simulator-trade-notifications"

interface TradeDialogProps {
  open: boolean
  sessionId?: number
  price?: number
  symbol?: string
  onOpenChange: (open: boolean) => void
}

export function TradeDialog({
  open,
  sessionId,
  price,
  symbol = "EURUSD",
  onOpenChange,
}: TradeDialogProps) {
  const [side, setSide] = useState<"buy" | "sell">("buy")
  const [volume, setVolume] = useState("0.1")
  const [sl, setSl] = useState("")
  const [tp, setTp] = useState("")
  const [submitting, setSubmitting] = useState(false)
  const { notifyTrade } = useSimulatorTradeNotifications()

  const handleSubmit = async () => {
    if (!sessionId) {
      toast.error("Start a simulation session first.")
      return
    }

    const vol = Number(volume)
    if (!vol || Number.isNaN(vol)) {
      toast.error("Enter a valid lot size.")
      return
    }

    try {
      setSubmitting(true)
      const response = await simulatorApi.executeTrade(sessionId, {
        side,
        volume: vol,
        price,
        sl: sl ? Number(sl) : undefined,
        tp: tp ? Number(tp) : undefined,
      })
      toast.success("Trade executed")
      await notifyTrade({
        side,
        symbol,
        volume: vol,
        price: response.trade?.price ? Number(response.trade.price) : price,
      })
      onOpenChange(false)
    } catch (error) {
      toast.error("Trade failed")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Execute Trade</DialogTitle>
          <DialogDescription>Place a chart-click trade.</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Side</Label>
            <ToggleGroup
              type="single"
              value={side}
              onValueChange={(val) => val && setSide(val as "buy" | "sell")}
            >
              <ToggleGroupItem value="buy">Buy</ToggleGroupItem>
              <ToggleGroupItem value="sell">Sell</ToggleGroupItem>
            </ToggleGroup>
          </div>

          <div className="space-y-2">
            <Label>Price</Label>
            <Input value={price ? price.toFixed(5) : ""} disabled />
          </div>

          <div className="space-y-2">
            <Label>Lot Size</Label>
            <Input
              type="number"
              step="0.01"
              value={volume}
              onChange={(e) => setVolume(e.target.value)}
            />
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div className="space-y-2">
              <Label>Stop Loss</Label>
              <Input
                type="number"
                value={sl}
                onChange={(e) => setSl(e.target.value)}
                placeholder="Optional"
              />
            </div>
            <div className="space-y-2">
              <Label>Take Profit</Label>
              <Input
                type="number"
                value={tp}
                onChange={(e) => setTp(e.target.value)}
                placeholder="Optional"
              />
            </div>
          </div>

          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button onClick={handleSubmit} disabled={submitting}>
              {submitting ? "Placing..." : "Place Trade"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
