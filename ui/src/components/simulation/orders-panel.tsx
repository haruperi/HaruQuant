"use client"

import { useEffect, useRef, useState } from "react"
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
import { validatePendingOrder } from "@/components/simulation/order-validation"

export interface OrderRow {
  id: string | number
  symbol: string
  ticket: string | number
  time?: string | number | null
  type: string
  volume: number
  price: number
  sl?: number | null
  tp?: number | null
}

interface OrdersPanelProps {
  orders: OrderRow[]
  digits?: number
  currentPrice?: number
  onModifyOrder?: (
    orderId: OrderRow["id"],
    payload: { volume?: number; price?: number; sl?: number; tp?: number }
  ) => Promise<void> | void
  onDeleteOrder?: (orderId: OrderRow["id"]) => Promise<void> | void
}

const COLUMN_WIDTHS = [
  "minmax(88px, 1fr)",
  "minmax(82px, 0.9fr)",
  "minmax(150px, 1.2fr)",
  "minmax(96px, 0.9fr)",
  "minmax(82px, 0.8fr)",
  "minmax(104px, 1fr)",
  "minmax(104px, 1fr)",
  "minmax(104px, 1fr)",
  "minmax(94px, 0.9fr)",
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

function formatOrderType(type: string) {
  return type.replaceAll("_", " ").toUpperCase()
}

function parseOptionalNumber(value: string) {
  const trimmed = value.trim()
  if (trimmed === "") return null
  const parsed = Number(trimmed)
  if (Number.isNaN(parsed)) return Number.NaN
  return parsed
}

function InlineEditableNumber({
  value,
  digits,
  allowEmpty = false,
  onSave,
}: {
  value?: number | null
  digits: number
  allowEmpty?: boolean
  onSave: (newVal: number | null) => Promise<void> | void
}) {
  const [isEditing, setIsEditing] = useState(false)
  const [editValue, setEditValue] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleStartEdit = () => {
    setIsEditing(true)
    setEditValue(value ? String(value) : "")
  }

  const handleSave = async () => {
    if (isSubmitting) return

    const parsedValue = parseOptionalNumber(editValue)
    if (Number.isNaN(parsedValue)) {
      toast.error("Invalid number format")
      return
    }
    if (!allowEmpty && parsedValue === null) {
      toast.error("Value is required")
      return
    }

    setIsSubmitting(true)
    try {
      await onSave(parsedValue)
      setIsEditing(false)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") void handleSave()
    if (e.key === "Escape" && !isSubmitting) setIsEditing(false)
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
        onBlur={() => void handleSave()}
        onKeyDown={handleKeyDown}
        className="h-7 w-24 px-2 text-xs"
        disabled={isSubmitting}
      />
    )
  }

  return (
    <div className="group flex items-center gap-1">
      <span>{formatPrice(value, digits)}</span>
      <Button
        size="icon"
        variant="ghost"
        className="h-6 w-6 opacity-0 transition-opacity group-hover:opacity-100"
        onClick={handleStartEdit}
      >
        <Pencil className="h-3.5 w-3.5" />
      </Button>
    </div>
  )
}

interface OrderDialogState {
  open: boolean
  order: OrderRow | null
  volumeInput: string
  priceInput: string
  slInput: string
  tpInput: string
  isSubmitting: boolean
}

export function OrdersPanel({
  orders,
  digits = 5,
  currentPrice,
  onModifyOrder,
  onDeleteOrder,
}: OrdersPanelProps) {
  const [orderDialog, setOrderDialog] = useState<OrderDialogState>({
    open: false,
    order: null,
    volumeInput: "",
    priceInput: "",
    slInput: "",
    tpInput: "",
    isSubmitting: false,
  })

  const runModify = async (
    order: OrderRow,
    payload: { volume?: number; price?: number; sl?: number; tp?: number }
  ) => {
    if (!onModifyOrder) {
      toast.info("Modify order action is not wired yet.")
      return
    }
    await onModifyOrder(order.id, payload)
  }

  const handleInlineSave = async (
    order: OrderRow,
    field: "price" | "sl" | "tp",
    newValue: number | null
  ) => {
    const nextPrice = field === "price" ? newValue : order.price
    const nextSl = field === "sl" ? newValue : order.sl
    const nextTp = field === "tp" ? newValue : order.tp

    const validationError = validatePendingOrder({
      type: order.type,
      volume: order.volume,
      price: nextPrice,
      sl: nextSl,
      tp: nextTp,
      currentPrice: currentPrice ?? null,
      maxVolume: order.volume,
    })
    if (validationError) {
      toast.error(validationError)
      return
    }

    await runModify(order, {
      [field]: field === "price" ? (newValue ?? undefined) : (newValue ?? 0),
    })
  }

  const openOrderDialog = (order: OrderRow) => {
    setOrderDialog({
      open: true,
      order,
      volumeInput: order.volume.toFixed(2),
      priceInput: String(order.price),
      slInput: order.sl ? String(order.sl) : "",
      tpInput: order.tp ? String(order.tp) : "",
      isSubmitting: false,
    })
  }

  const closeDialog = () => {
    setOrderDialog({
      open: false,
      order: null,
      volumeInput: "",
      priceInput: "",
      slInput: "",
      tpInput: "",
      isSubmitting: false,
    })
  }

  const handleDialogSave = async () => {
    if (!orderDialog.order) return
    if (!onModifyOrder) {
      toast.info("Modify order action is not wired yet.")
      return
    }

    const volume = parseOptionalNumber(orderDialog.volumeInput)
    const price = parseOptionalNumber(orderDialog.priceInput)
    const sl = parseOptionalNumber(orderDialog.slInput)
    const tp = parseOptionalNumber(orderDialog.tpInput)

    if (
      Number.isNaN(volume) ||
      Number.isNaN(price) ||
      Number.isNaN(sl) ||
      Number.isNaN(tp)
    ) {
      toast.error("Enter valid numeric values.")
      return
    }

    if (volume === null) {
      toast.error("Volume is required.")
      return
    }

    if (price === null) {
      toast.error("Open price is required.")
      return
    }

    const validationError = validatePendingOrder({
      type: orderDialog.order.type,
      volume,
      price,
      sl,
      tp,
      currentPrice: currentPrice ?? null,
      maxVolume: orderDialog.order.volume,
    })
    if (validationError) {
      toast.error(validationError)
      return
    }

    setOrderDialog((prev) => ({ ...prev, isSubmitting: true }))
    try {
      await onModifyOrder(orderDialog.order.id, {
        volume: volume ?? undefined,
        price: price ?? undefined,
        sl: sl ?? 0,
        tp: tp ?? 0,
      })
      closeDialog()
    } finally {
      setOrderDialog((prev) => ({ ...prev, isSubmitting: false }))
    }
  }

  const handleDeleteOrder = async () => {
    if (!orderDialog.order || !onDeleteOrder) {
      if (!onDeleteOrder) {
        toast.info("Delete order action is not wired yet.")
      }
      return
    }

    setOrderDialog((prev) => ({ ...prev, isSubmitting: true }))
    try {
      await onDeleteOrder(orderDialog.order.id)
      closeDialog()
    } finally {
      setOrderDialog((prev) => ({ ...prev, isSubmitting: false }))
    }
  }

  const isVolumeReduced =
    orderDialog.order !== null &&
    Number(orderDialog.volumeInput || "0") < orderDialog.order.volume

  return (
    <>
      <Card className="h-fit">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Pending Orders</CardTitle>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <Table className="min-w-[1180px]">
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
                <TableHead></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {orders.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={10} className="text-center text-muted-foreground">
                    No pending orders.
                  </TableCell>
                </TableRow>
              ) : (
                orders.map((order) => (
                  <TableRow key={order.id}>
                    <TableCell>{order.symbol}</TableCell>
                    <TableCell>{order.ticket}</TableCell>
                    <TableCell>{formatTime(order.time)}</TableCell>
                    <TableCell>{formatOrderType(order.type)}</TableCell>
                    <TableCell>{order.volume.toFixed(2)}</TableCell>
                    <TableCell>
                      <InlineEditableNumber
                        value={order.price}
                        digits={digits}
                        onSave={(newVal) => handleInlineSave(order, "price", newVal)}
                      />
                    </TableCell>
                    <TableCell>
                      <InlineEditableNumber
                        value={order.sl}
                        digits={digits}
                        allowEmpty
                        onSave={(newVal) => handleInlineSave(order, "sl", newVal)}
                      />
                    </TableCell>
                    <TableCell>
                      <InlineEditableNumber
                        value={order.tp}
                        digits={digits}
                        allowEmpty
                        onSave={(newVal) => handleInlineSave(order, "tp", newVal)}
                      />
                    </TableCell>
                    <TableCell>{formatPrice(currentPrice, digits)}</TableCell>
                    <TableCell>
                      <Button
                        size="icon"
                        variant="ghost"
                        className="h-6 w-6 text-red-500 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950/30"
                        title="Manage order"
                        onClick={() => openOrderDialog(order)}
                      >
                        <X className="h-3.5 w-3.5" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog
        open={orderDialog.open}
        onOpenChange={(open) => {
          if (!open && !orderDialog.isSubmitting) {
            closeDialog()
          }
        }}
      >
        <DialogContent className="sm:max-w-[420px]">
          <DialogHeader>
            <DialogTitle>Manage Pending Order</DialogTitle>
            <DialogDescription>
              {orderDialog.order && (
                <>
                  {orderDialog.order.symbol} · {formatOrderType(orderDialog.order.type)} · Ticket #
                  {orderDialog.order.ticket}
                </>
              )}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 py-2">
            <div className="space-y-1">
              <Label htmlFor="pending-order-volume">
                Volume
                <span className="ml-1 text-xs text-muted-foreground">
                  (max {orderDialog.order?.volume.toFixed(2)})
                </span>
              </Label>
              <Input
                id="pending-order-volume"
                type="number"
                step="0.01"
                min="0.01"
                max={orderDialog.order?.volume ?? undefined}
                value={orderDialog.volumeInput}
                onChange={(e) =>
                  setOrderDialog((prev) => ({ ...prev, volumeInput: e.target.value }))
                }
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="pending-order-price">Open</Label>
              <Input
                id="pending-order-price"
                type="number"
                value={orderDialog.priceInput}
                onChange={(e) =>
                  setOrderDialog((prev) => ({ ...prev, priceInput: e.target.value }))
                }
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label htmlFor="pending-order-sl">SL</Label>
                <Input
                  id="pending-order-sl"
                  type="number"
                  value={orderDialog.slInput}
                  placeholder="Optional"
                  onChange={(e) =>
                    setOrderDialog((prev) => ({ ...prev, slInput: e.target.value }))
                  }
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="pending-order-tp">TP</Label>
                <Input
                  id="pending-order-tp"
                  type="number"
                  value={orderDialog.tpInput}
                  placeholder="Optional"
                  onChange={(e) =>
                    setOrderDialog((prev) => ({ ...prev, tpInput: e.target.value }))
                  }
                />
              </div>
            </div>
            {isVolumeReduced && (
              <p className="text-xs text-amber-500">
                Partial volume reduction. Remaining order volume will be{" "}
                <strong>{Number(orderDialog.volumeInput || "0").toFixed(2)}</strong>.
              </p>
            )}
          </div>

          <DialogFooter className="gap-2 sm:justify-between">
            <Button
              variant="destructive"
              onClick={() => void handleDeleteOrder()}
              disabled={orderDialog.isSubmitting}
            >
              Delete Order
            </Button>
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={closeDialog}
                disabled={orderDialog.isSubmitting}
              >
                Cancel
              </Button>
              <Button onClick={() => void handleDialogSave()} disabled={orderDialog.isSubmitting}>
                {orderDialog.isSubmitting ? "Saving..." : "Save Changes"}
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
