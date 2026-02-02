"use client"

import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Pencil, X } from "lucide-react"

export interface PositionRow {
  id: string | number
  symbol: string
  type: "buy" | "sell"
  volume: number
  openPrice: number
  currentPrice: number
  pnl: number
}

interface PositionsPanelProps {
  positions: PositionRow[]
  onModifyPosition?: (positionId: PositionRow["id"]) => Promise<void> | void
  onClosePosition?: (positionId: PositionRow["id"]) => Promise<void> | void
}

export function PositionsPanel({
  positions,
  onModifyPosition,
  onClosePosition,
}: PositionsPanelProps) {
  const handleModify = async (positionId: PositionRow["id"]) => {
    if (!onModifyPosition) {
      toast.info("Modify position action is not wired yet.")
      return
    }
    try {
      await onModifyPosition(positionId)
    } catch (error) {
      toast.error("Failed to modify position")
    }
  }

  const handleClose = async (positionId: PositionRow["id"]) => {
    if (!onClosePosition) {
      toast.info("Close position action is not wired yet.")
      return
    }
    try {
      await onClosePosition(positionId)
    } catch (error) {
      toast.error("Failed to close position")
    }
  }

  return (
    <Card className="h-fit">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">Open Positions</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Symbol</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Volume</TableHead>
              <TableHead>Open</TableHead>
              <TableHead>Current</TableHead>
              <TableHead>P&amp;L</TableHead>
              <TableHead className="text-right">Action</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {positions.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center text-muted-foreground">
                  No open positions.
                </TableCell>
              </TableRow>
            ) : (
              positions.map((position) => (
                <TableRow key={position.id}>
                  <TableCell>{position.symbol}</TableCell>
                  <TableCell className={position.type === "buy" ? "text-emerald-500" : "text-red-500"}>
                    {position.type.toUpperCase()}
                  </TableCell>
                  <TableCell>{position.volume}</TableCell>
                  <TableCell>{position.openPrice.toFixed(5)}</TableCell>
                  <TableCell>{position.currentPrice.toFixed(5)}</TableCell>
                <TableCell className={position.pnl >= 0 ? "text-emerald-500" : "text-red-500"}>
                  {position.pnl.toFixed(2)}
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex justify-end gap-2">
                    <Button
                      size="icon"
                      variant="ghost"
                      onClick={() => handleModify(position.id)}
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button
                      size="icon"
                      variant="ghost"
                      onClick={() => handleClose(position.id)}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))
            )}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
