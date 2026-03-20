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
import { Pencil } from "lucide-react"

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
}

interface PositionsPanelProps {
  positions: PositionRow[]
  digits?: number
  onModifyPositionField?: (
    positionId: PositionRow["id"],
    field: "sl" | "tp",
    newValue: number | null
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
  "minmax(96px, 0.95fr)",
  "minmax(100px, 1fr)",
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

export function PositionsPanel({
  positions,
  digits = 5,
  onModifyPositionField,
}: PositionsPanelProps) {
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

  return (
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
            </TableRow>
          </TableHeader>
          <TableBody>
            {positions.length === 0 ? (
              <TableRow>
                <TableCell colSpan={13} className="text-center text-muted-foreground">
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
                  </TableRow>
                )
              })
            )}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
