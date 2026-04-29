"use client"

import { useState, useRef, useEffect } from "react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { Pencil, X, TrendingUp, TrendingDown } from "lucide-react"

export interface PositionRow {
  id: string | number
  symbol: string
  ticket: string | number
  time?: string | number | null
  type: "buy" | "sell"
  volume: number
  openPrice: number
  sl?: number | null
  tp?: number | null
  currentPrice: number
  swap?: number
  pnl: number
  pnlPct?: number
  marginRequired?: number
  exposure?: number
  weight?: number
}

interface PositionsPanelProps {
  positions: PositionRow[]
  digits?: number
  onModifyPositionField?: (
    positionId: PositionRow["id"],
    field: "sl" | "tp",
    newValue: number | null
  ) => Promise<void> | void
  onClosePosition?: (
    positionId: PositionRow["id"],
    volume: number
  ) => Promise<void> | void
}

const COLUMN_WIDTHS = [
  "minmax(88px, 1fr)",
  "minmax(82px, 0.9fr)",
  "minmax(150px, 1.2fr)",
  "minmax(72px, 0.75fr)",
  "minmax(70px, 0.7fr)",
  "minmax(94px, 0.9fr)",
  "minmax(104px, 1fr)",
  "minmax(104px, 1fr)",
  "minmax(94px, 0.9fr)",
  "minmax(82px, 0.8fr)",
  "minmax(96px, 0.95fr)",
  "minmax(100px, 1fr)",
  "minmax(100px, 1fr)",
  "minmax(80px, 0.8fr)",
  "minmax(60px, 0.6fr)",
].join(" ")

function formatPrice(value?: number | null, digits = 5) {
  if (!value) return "--"
  return value.toFixed(digits)
}

function formatTime(value?: string | number | null) {
  if (value === null || value === undefined || value === "") return "--"
  const date =
    typeof value === "number"
      ? new Date(value * 1000)
      : new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleString([], {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  })
}

function inferPipSize(openPrice: number, digits = 5) {
  if (digits === 3 || digits === 5) return 10 ** (-(digits - 1))
  if (digits > 0) return 10 ** (-digits)
  return openPrice >= 100 ? 0.01 : 0.0001
}

function InlineEditableNumber({
  value,
  digits,
  onSave,
}: {
  value?: number | null
  digits: number
  onSave: (newVal: number | null) => void
}) {
  const [isEditing, setIsEditing] = useState(false)
  const [editValue, setEditValue] = useState("")
  const inputRef = useRef<HTMLInputElement>(null)

  const handleStartEdit = () => {
    setIsEditing(true)
    setEditValue(value ? String(value) : "")
  }

  const handleSave = () => {
    setIsEditing(false)
    const trimmed = editValue.trim()
    if (trimmed === "") {
      onSave(null)
      return
    }
    const numericValue = Number(trimmed)
    if (!Number.isNaN(numericValue)) {
      onSave(numericValue)
    } else {
      toast.error("Invalid number format")
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleSave()
    if (e.key === "Escape") setIsEditing(false)
  }

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus()
    }
  }, [isEditing])

  if (isEditing) {
    return (
      <Input
        ref={inputRef}
        value={editValue}
        onChange={(e) => setEditValue(e.target.value)}
        onBlur={handleSave}
        onKeyDown={handleKeyDown}
        className="h-7 w-20 text-xs px-2"
      />
    )
  }

  return (
    <div className="flex items-center gap-1 group">
      <span>{formatPrice(value, digits)}</span>
      <Button
        size="icon"
        variant="ghost"
        className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
        onClick={handleStartEdit}
      >
        <Pencil className="h-3.5 w-3.5" />
      </Button>
    </div>
  )
}

interface CloseDialogState {
  open: boolean
  position: PositionRow | null
  volumeInput: string
  isSubmitting: boolean
}

function PriceCell({ value, digits, className }: { value: number, digits: number, className?: string }) {
  const [flash, setFlash] = useState<"up" | "down" | null>(null)
  const prevValue = useRef(value)

  useEffect(() => {
    if (value !== prevValue.current) {
      setFlash(value > prevValue.current ? "up" : "down")
      const timer = setTimeout(() => setFlash(null), 400)
      prevValue.current = value
      return () => clearTimeout(timer)
    }
  }, [value])

  return (
    <TableCell className={`${className} transition-colors duration-500 ${
      flash === "up" ? "bg-emerald-500/20" : flash === "down" ? "bg-red-500/20" : ""
    }`}>
      {formatPrice(value, digits)}
    </TableCell>
  )
}

function PnlCell({ pnl, pnlPct, className }: { pnl: number, pnlPct: number, className?: string }) {
  const [flash, setFlash] = useState<"up" | "down" | null>(null)
  const prevValue = useRef(pnl)
  const isProfit = pnl >= 0

  useEffect(() => {
    if (pnl !== prevValue.current) {
      setFlash(pnl > prevValue.current ? "up" : "down")
      const timer = setTimeout(() => setFlash(null), 400)
      prevValue.current = pnl
      return () => clearTimeout(timer)
    }
  }, [pnl])

  return (
    <TableCell className={`${className} transition-colors duration-500 ${
      flash === "up" ? "bg-emerald-500/20" : flash === "down" ? "bg-red-500/20" : ""
    }`}>
      <div className="flex flex-col">
        <span className={`font-mono font-bold text-sm ${isProfit ? "text-emerald-500" : "text-red-500"}`}>
          {isProfit ? "+" : ""}{pnl.toFixed(2)}
        </span>
        <span className={`font-mono text-[10px] ${isProfit ? "text-emerald-400/80" : "text-red-400/80"}`}>
          ({isProfit ? "+" : ""}{pnlPct.toFixed(2)}%)
        </span>
      </div>
    </TableCell>
  )
}

export function PositionsPanel({
  positions,
  digits = 5,
  onModifyPositionField,
  onClosePosition,
}: PositionsPanelProps) {
  const [closeDialog, setCloseDialog] = useState<CloseDialogState>({
    open: false,
    position: null,
    volumeInput: "",
    isSubmitting: false,
  })

  const handleModifyField = async (
    positionId: PositionRow["id"],
    field: "sl" | "tp",
    newValue: number | null
  ) => {
    if (!onModifyPositionField) {
      toast.info("Modify position action is not wired yet.")
      return
    }
    try {
      await onModifyPositionField(positionId, field, newValue)
    } catch {
      toast.error("Failed to modify position")
    }
  }

  const openCloseDialog = (position: PositionRow) => {
    setCloseDialog({
      open: true,
      position,
      volumeInput: position.volume.toFixed(2),
      isSubmitting: false,
    })
  }

  const handleCloseDialogConfirm = async () => {
    if (!closeDialog.position || !onClosePosition) return

    const volume = parseFloat(closeDialog.volumeInput)
    if (isNaN(volume) || volume <= 0) {
      toast.error("Invalid volume")
      return
    }
    if (volume > closeDialog.position.volume) {
      toast.error(`Volume cannot exceed position size (${closeDialog.position.volume.toFixed(2)})`)
      return
    }

    setCloseDialog((prev) => ({ ...prev, isSubmitting: true }))
    try {
      await onClosePosition(closeDialog.position.id, volume)
      setCloseDialog({ open: false, position: null, volumeInput: "", isSubmitting: false })
    } catch {
      toast.error("Failed to close position")
      setCloseDialog((prev) => ({ ...prev, isSubmitting: false }))
    }
  }

  const isPartial =
    closeDialog.position !== null &&
    parseFloat(closeDialog.volumeInput) < closeDialog.position.volume

  return (
    <>
      <Card className="h-fit">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Open Positions</CardTitle>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <Table className="min-w-[1440px]">
            <colgroup>
              {COLUMN_WIDTHS.split(" ").map((width, index) => (
                <col key={index} style={{ width }} />
              ))}
            </colgroup>
            <TableHeader>
              <TableRow>
                <TableHead>Symbol</TableHead>
                <TableHead>Ticket</TableHead>
                <TableHead>Time</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Volume</TableHead>
                <TableHead>Open</TableHead>
                <TableHead>SL</TableHead>
                <TableHead>TP</TableHead>
                <TableHead>Current</TableHead>
                <TableHead>Swap</TableHead>
                <TableHead>PnL ($/%)</TableHead>
                <TableHead>PnL (Pips)</TableHead>
                <TableHead>Margin Req</TableHead>
                <TableHead>Exposure</TableHead>
                <TableHead>Weight</TableHead>
                <TableHead></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {positions.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={16} className="text-center text-muted-foreground py-8">
                    No open positions.
                  </TableCell>
                </TableRow>
              ) : (
                positions.map((position) => {
                  const pipSize = inferPipSize(position.openPrice, digits)
                  const pipDelta =
                    position.type === "buy"
                      ? (position.currentPrice - position.openPrice) / pipSize
                      : (position.openPrice - position.currentPrice) / pipSize
                  
                  const isProfit = position.pnl >= 0
                  const pnlPct = position.pnlPct ?? (
                    position.type === "buy" 
                      ? ((position.currentPrice / position.openPrice) - 1) * 100 
                      : ((position.openPrice / position.currentPrice) - 1) * 100
                  )

                  return (
                    <TableRow key={position.id} className="hover:bg-muted/50 transition-colors">
                      <TableCell className="font-medium">{position.symbol}</TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground">#{position.ticket}</TableCell>
                      <TableCell className="text-xs">{formatTime(position.time)}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1.5">
                          {position.type === "buy" ? (
                            <TrendingUp className="h-3.5 w-3.5 text-emerald-500" />
                          ) : (
                            <TrendingDown className="h-3.5 w-3.5 text-red-500" />
                          )}
                          <span className={`text-xs font-bold ${position.type === "buy" ? "text-emerald-500" : "text-red-500"}`}>
                            {position.type.toUpperCase()}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell className="font-mono text-xs">{position.volume.toFixed(2)}</TableCell>
                      <TableCell className="font-mono text-xs">{formatPrice(position.openPrice, digits)}</TableCell>
                      <TableCell>
                        <InlineEditableNumber
                          value={position.sl}
                          digits={digits}
                          onSave={(newVal) => handleModifyField(position.id, "sl", newVal)}
                        />
                      </TableCell>
                      <TableCell>
                        <InlineEditableNumber
                          value={position.tp}
                          digits={digits}
                          onSave={(newVal) => handleModifyField(position.id, "tp", newVal)}
                        />
                      </TableCell>
                      <PriceCell 
                        value={position.currentPrice} 
                        digits={digits} 
                        className="font-mono text-xs font-semibold" 
                      />
                      <TableCell className="font-mono text-xs text-muted-foreground">{(position.swap ?? 0).toFixed(2)}</TableCell>
                      <PnlCell pnl={position.pnl} pnlPct={pnlPct} />
                      <TableCell className={`font-mono text-xs ${pipDelta >= 0 ? "text-emerald-500" : "text-red-500"}`}>
                        {pipDelta.toFixed(1)}
                      </TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground">{(position.marginRequired ?? 0).toFixed(2)}</TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground">{position.exposure !== undefined ? position.exposure.toFixed(2) : "--"}</TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground">{position.weight !== undefined ? (position.weight * 100).toFixed(2) + "%" : "--"}</TableCell>
                      <TableCell>
                        <Button
                          size="icon"
                          variant="ghost"
                          className="h-7 w-7 text-muted-foreground hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors"
                          title="Close position"
                          onClick={() => openCloseDialog(position)}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  )
                })
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Close Position Dialog */}
      <Dialog
        open={closeDialog.open}
        onOpenChange={(open) => {
          if (!open && !closeDialog.isSubmitting) {
            setCloseDialog({ open: false, position: null, volumeInput: "", isSubmitting: false })
          }
        }}
      >
        <DialogContent className="sm:max-w-[380px]">
          <DialogHeader>
            <DialogTitle>Close Position</DialogTitle>
            <DialogDescription>
              {closeDialog.position && (
                <>
                  {closeDialog.position.symbol} &nbsp;
                  <span className={closeDialog.position.type === "buy" ? "text-emerald-500 font-semibold" : "text-red-500 font-semibold"}>
                    {closeDialog.position.type.toUpperCase()}
                  </span>
                  &nbsp;· Ticket #{closeDialog.position.ticket}
                  &nbsp;· Current P&L:{" "}
                  <span className={closeDialog.position.pnl >= 0 ? "text-emerald-500" : "text-red-500"}>
                    ${closeDialog.position.pnl.toFixed(2)}
                  </span>
                </>
              )}
            </DialogDescription>
          </DialogHeader>

          <div className="py-2 space-y-3">
            <div className="space-y-1">
              <Label htmlFor="close-volume">
                Volume to close{" "}
                <span className="text-muted-foreground text-xs">
                  (max {closeDialog.position?.volume.toFixed(2)})
                </span>
              </Label>
              <Input
                id="close-volume"
                type="number"
                step="0.01"
                min="0.01"
                max={closeDialog.position?.volume ?? undefined}
                value={closeDialog.volumeInput}
                onChange={(e) =>
                  setCloseDialog((prev) => ({ ...prev, volumeInput: e.target.value }))
                }
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleCloseDialogConfirm()
                  if (e.key === "Escape")
                    setCloseDialog({ open: false, position: null, volumeInput: "", isSubmitting: false })
                }}
                autoFocus
              />
            </div>
            {isPartial && (
              <p className="text-xs text-amber-500">
                ⚠ Partial close — remaining volume:{" "}
                <strong>
                  {(
                    (closeDialog.position?.volume ?? 0) - parseFloat(closeDialog.volumeInput || "0")
                  ).toFixed(2)}
                </strong>
              </p>
            )}
          </div>

          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              onClick={() =>
                setCloseDialog({ open: false, position: null, volumeInput: "", isSubmitting: false })
              }
              disabled={closeDialog.isSubmitting}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleCloseDialogConfirm}
              disabled={closeDialog.isSubmitting}
            >
              {closeDialog.isSubmitting
                ? "Closing…"
                : isPartial
                ? "Partial Close"
                : "Close Position"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
