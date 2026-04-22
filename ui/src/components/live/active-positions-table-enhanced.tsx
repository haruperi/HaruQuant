"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
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
import { SemanticSnapshotScript } from "@/components/ai-chat/SemanticSnapshotScript"
import { XCircle, Edit2, Loader2, AlertCircle, TrendingUp, TrendingDown } from "lucide-react"
import { LiveTradingAPI } from "@/lib/api/live"
import { useLiveWebSocket } from "@/lib/hooks/use-live-websocket"
import type { Position } from "@/types/live"
import { toast } from "sonner"

interface ActivePositionsTableEnhancedProps {
  sessionId: number
}

export function ActivePositionsTableEnhanced({ sessionId }: ActivePositionsTableEnhancedProps) {
  const [positions, setPositions] = useState<Position[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [modifyDialogOpen, setModifyDialogOpen] = useState(false)
  const [closeDialogOpen, setCloseDialogOpen] = useState(false)
  const [selectedPosition, setSelectedPosition] = useState<Position | null>(null)
  const [modifyStopLoss, setModifyStopLoss] = useState("")
  const [modifyTakeProfit, setModifyTakeProfit] = useState("")
  const [isModifying, setIsModifying] = useState(false)
  const [isClosing, setIsClosing] = useState(false)

  // WebSocket for real-time position updates
  const { isConnected } = useLiveWebSocket({
    sessionId,
    channels: ["positions"],
    onPositionOpened: (position) => {
      setPositions((prev) => {
        // Check if position already exists
        const exists = prev.find((p) => p.position_id === position.position_id)
        if (exists) return prev
        return [...prev, position]
      })
    },
    onPositionUpdated: (position) => {
      setPositions((prev) =>
        prev.map((p) => (p.position_id === position.position_id ? position : p))
      )
    },
    onPositionClosed: (position, reason) => {
      setPositions((prev) =>
        prev.filter((p) => p.position_id !== position.position_id)
      )
      toast.success("Position Closed", {
        description: `${position.symbol} closed: ${reason}`,
      })
    },
    autoConnect: true,
  })

  // Fetch initial positions
  useEffect(() => {
    const fetchPositions = async () => {
      try {
        setIsLoading(true)
        setError(null)
        const data = await LiveTradingAPI.getPositions(sessionId, "open")
        setPositions(data)
      } catch (err) {
        console.error("Error fetching positions:", err)
        setError(err instanceof Error ? err.message : "Failed to load positions")
      } finally {
        setIsLoading(false)
      }
    }

    fetchPositions()

    // Poll every 30 seconds as backup
    const interval = setInterval(fetchPositions, 30000)
    return () => clearInterval(interval)
  }, [sessionId])

  const handleModifyClick = (position: Position) => {
    setSelectedPosition(position)
    setModifyStopLoss(position.current_stop_loss?.toString() || "")
    setModifyTakeProfit(position.current_take_profit?.toString() || "")
    setModifyDialogOpen(true)
  }

  const handleCloseClick = (position: Position) => {
    setSelectedPosition(position)
    setCloseDialogOpen(true)
  }

  const handleModifySubmit = async () => {
    if (!selectedPosition) return

    try {
      setIsModifying(true)
      const data: { stop_loss?: number; take_profit?: number } = {}

      if (modifyStopLoss) {
        data.stop_loss = parseFloat(modifyStopLoss)
      }
      if (modifyTakeProfit) {
        data.take_profit = parseFloat(modifyTakeProfit)
      }

      await LiveTradingAPI.modifyPosition(sessionId, selectedPosition.position_id, data)

      toast.success("Position Modified", {
        description: `SL/TP updated for ${selectedPosition.symbol}`,
      })

      // Refresh positions
      const updatedPositions = await LiveTradingAPI.getPositions(sessionId, "open")
      setPositions(updatedPositions)

      setModifyDialogOpen(false)
      setSelectedPosition(null)
    } catch (err) {
      console.error("Error modifying position:", err)
      toast.error("Modification Failed", {
        description: err instanceof Error ? err.message : "Unknown error",
      })
    } finally {
      setIsModifying(false)
    }
  }

  const handleCloseSubmit = async () => {
    if (!selectedPosition) return

    try {
      setIsClosing(true)
      await LiveTradingAPI.closePosition(sessionId, selectedPosition.position_id)

      toast.success("Position Closed", {
        description: `${selectedPosition.symbol} position closed successfully`,
      })

      // Refresh positions
      const updatedPositions = await LiveTradingAPI.getPositions(sessionId, "open")
      setPositions(updatedPositions)

      setCloseDialogOpen(false)
      setSelectedPosition(null)
    } catch (err) {
      console.error("Error closing position:", err)
      toast.error("Close Failed", {
        description: err instanceof Error ? err.message : "Unknown error",
      })
    } finally {
      setIsClosing(false)
    }
  }

  const getPrecision = (symbol: string): number => {
    if (symbol.includes("JPY")) return 3
    if (symbol.includes("XAU") || symbol.includes("GOLD")) return 2
    return 5
  }

  const formatPrice = (price: number | null, symbol: string): string => {
    if (price === null) return "-"
    return price.toFixed(getPrecision(symbol))
  }

  if (isLoading) {
    return (
      <Card>
        <SemanticSnapshotScript
          block={{
            id: `live-positions:${sessionId}`,
            blockType: "table",
            title: "Active Positions",
            summary: `Open positions for live session ${sessionId}.`,
            keywords: ["positions", "open positions", "pnl", "stop loss", "take profit"],
            metrics: [
              { label: "Open Position Count", value: String(positions.length) },
              {
                label: "Aggregate Floating PnL",
                value: positions.reduce((sum, position) => sum + (position.current_profit || 0), 0).toFixed(2),
              },
            ],
            headers: ["Symbol", "Type", "Size", "Open", "Current", "SL", "TP", "PnL"],
            rows: positions.slice(0, 24).map((pos) => [
              pos.symbol,
              pos.type.toUpperCase(),
              pos.position_size.toFixed(2),
              formatPrice(pos.open_price, pos.symbol),
              formatPrice(pos.current_price, pos.symbol),
              formatPrice(pos.current_stop_loss, pos.symbol),
              formatPrice(pos.current_take_profit, pos.symbol),
              `${(pos.current_profit || 0).toFixed(2)} (${(pos.current_profit_pct || 0).toFixed(2)}%)`,
            ]),
          }}
        />
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <div className="flex items-center space-x-2">
            <CardTitle className="text-sm font-medium">Active Positions</CardTitle>
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          </div>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground">Loading positions...</div>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <div className="flex items-center space-x-2">
            <CardTitle className="text-sm font-medium">Active Positions</CardTitle>
            <AlertCircle className="h-4 w-4 text-destructive" />
          </div>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-destructive">{error}</div>
        </CardContent>
      </Card>
    )
  }

  return (
    <>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <div className="flex items-center space-x-2">
            <CardTitle className="text-sm font-medium">Active Positions</CardTitle>
            <Badge variant="secondary" className="text-xs">
              {positions.length}
            </Badge>
            <div className={`h-2 w-2 rounded-full ${isConnected ? 'bg-emerald-500' : 'bg-amber-500'}`} />
          </div>
        </CardHeader>
        <CardContent>
          {positions.length === 0 ? (
            <div className="text-sm text-muted-foreground text-center py-8">
              No active positions
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[100px]">Symbol</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Size</TableHead>
                  <TableHead>Open</TableHead>
                  <TableHead>Current</TableHead>
                  <TableHead>SL</TableHead>
                  <TableHead>TP</TableHead>
                  <TableHead className="text-right">PnL</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {positions.map((pos) => {
                  const isProfit = (pos.current_profit || 0) > 0
                  const profitPct = pos.current_profit_pct || 0

                  return (
                    <TableRow key={pos.position_id}>
                      <TableCell className="font-medium">{pos.symbol}</TableCell>
                      <TableCell>
                        <div className="flex items-center space-x-1">
                          {pos.type === "buy" ? (
                            <TrendingUp className="h-3 w-3 text-emerald-500" />
                          ) : (
                            <TrendingDown className="h-3 w-3 text-red-500" />
                          )}
                          <span
                            className={
                              pos.type === "buy"
                                ? "text-emerald-500 font-bold text-xs"
                                : "text-red-500 font-bold text-xs"
                            }
                          >
                            {pos.type.toUpperCase()}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell className="font-mono text-xs">{pos.position_size.toFixed(2)}</TableCell>
                      <TableCell className="font-mono text-xs">
                        {formatPrice(pos.open_price, pos.symbol)}
                      </TableCell>
                      <TableCell className="font-mono text-xs">
                        {formatPrice(pos.current_price, pos.symbol)}
                      </TableCell>
                      <TableCell className="font-mono text-xs">
                        {formatPrice(pos.current_stop_loss, pos.symbol)}
                      </TableCell>
                      <TableCell className="font-mono text-xs">
                        {formatPrice(pos.current_take_profit, pos.symbol)}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex flex-col items-end">
                          <span
                            className={`font-mono font-bold text-sm ${
                              isProfit ? "text-emerald-500" : "text-red-500"
                            }`}
                          >
                            {isProfit ? "+" : ""}
                            {(pos.current_profit || 0).toFixed(2)}
                          </span>
                          <span
                            className={`font-mono text-xs ${
                              isProfit ? "text-emerald-500/70" : "text-red-500/70"
                            }`}
                          >
                            ({isProfit ? "+" : ""}
                            {profitPct.toFixed(2)}%)
                          </span>
                        </div>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end space-x-1">
                          <Button
                            size="icon"
                            variant="ghost"
                            className="h-8 w-8"
                            onClick={() => handleModifyClick(pos)}
                          >
                            <Edit2 className="h-4 w-4" />
                          </Button>
                          <Button
                            size="icon"
                            variant="ghost"
                            className="h-8 w-8 text-destructive hover:text-destructive hover:bg-destructive/10"
                            onClick={() => handleCloseClick(pos)}
                          >
                            <XCircle className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Modify SL/TP Dialog */}
      <Dialog open={modifyDialogOpen} onOpenChange={setModifyDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Modify Position</DialogTitle>
            <DialogDescription>
              Update Stop Loss and Take Profit for {selectedPosition?.symbol}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="stopLoss">Stop Loss</Label>
              <Input
                id="stopLoss"
                type="number"
                step="0.00001"
                placeholder="Enter stop loss price"
                value={modifyStopLoss}
                onChange={(e) => setModifyStopLoss(e.target.value)}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="takeProfit">Take Profit</Label>
              <Input
                id="takeProfit"
                type="number"
                step="0.00001"
                placeholder="Enter take profit price"
                value={modifyTakeProfit}
                onChange={(e) => setModifyTakeProfit(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setModifyDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleModifySubmit} disabled={isModifying}>
              {isModifying ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Updating...
                </>
              ) : (
                "Update"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Close Position Dialog */}
      <Dialog open={closeDialogOpen} onOpenChange={setCloseDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Close Position</DialogTitle>
            <DialogDescription>
              Are you sure you want to close this position?
            </DialogDescription>
          </DialogHeader>
          {selectedPosition && (
            <div className="py-4 space-y-2">
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Symbol:</span>
                <span className="text-sm font-medium">{selectedPosition.symbol}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Type:</span>
                <span
                  className={`text-sm font-bold ${
                    selectedPosition.type === "buy" ? "text-emerald-500" : "text-red-500"
                  }`}
                >
                  {selectedPosition.type.toUpperCase()}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Size:</span>
                <span className="text-sm font-medium">{selectedPosition.position_size.toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Current P&L:</span>
                <span
                  className={`text-sm font-bold ${
                    (selectedPosition.current_profit || 0) > 0 ? "text-emerald-500" : "text-red-500"
                  }`}
                >
                  {(selectedPosition.current_profit || 0) > 0 ? "+" : ""}
                  {(selectedPosition.current_profit || 0).toFixed(2)}
                </span>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setCloseDialogOpen(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleCloseSubmit} disabled={isClosing}>
              {isClosing ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Closing...
                </>
              ) : (
                "Close Position"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
