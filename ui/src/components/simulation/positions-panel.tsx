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
import { Pencil, X } from "lucide-react"

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
                <TableHead>P&amp;L ($)</TableHead>
                <TableHead>P&amp;L (Pips)</TableHead>
                <TableHead>Margin Req</TableHead>
                <TableHead>Exposure</TableHead>
                <TableHead>Weight</TableHead>
                <TableHead></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {positions.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={16} className="text-center text-muted-foreground">
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

                  return (
                    <TableRow key={position.id}>
                      <TableCell>{position.symbol}</TableCell>
                      <TableCell>{position.ticket}</TableCell>
                      <TableCell>{formatTime(position.time)}</TableCell>
                      <TableCell className={position.type === "buy" ? "text-emerald-500" : "text-red-500"}>
                        {position.type.toUpperCase()}
                      </TableCell>
                      <TableCell>{position.volume.toFixed(2)}</TableCell>
                      <TableCell>{formatPrice(position.openPrice, digits)}</TableCell>
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
                      <TableCell>{formatPrice(position.currentPrice, digits)}</TableCell>
                      <TableCell>{(position.swap ?? 0).toFixed(2)}</TableCell>
                      <TableCell className={position.pnl >= 0 ? "text-emerald-500" : "text-red-500"}>
                        {position.pnl.toFixed(2)}
                      </TableCell>
                      <TableCell className={pipDelta >= 0 ? "text-emerald-500" : "text-red-500"}>
                        {pipDelta.toFixed(1)}
                      </TableCell>
                      <TableCell>{(position.marginRequired ?? 0).toFixed(2)}</TableCell>
                      <TableCell>{position.exposure !== undefined ? position.exposure.toFixed(2) : "--"}</TableCell>
                      <TableCell>{position.weight !== undefined ? (position.weight * 100).toFixed(2) + "%" : "--"}</TableCell>
                      <TableCell>
                        <Button
                          size="icon"
                          variant="ghost"
                          className="h-6 w-6 text-red-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30"
                          title="Close position"
                          onClick={() => openCloseDialog(position)}
                        >
                          <X className="h-3.5 w-3.5" />
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
