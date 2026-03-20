"use client"

import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableRow,
} from "@/components/ui/table"
import { Pencil } from "lucide-react"

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
  onModifyOrderField?: (
    orderId: OrderRow["id"],
    field: "sl" | "tp",
    currentValue?: number | null
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

export function OrdersPanel({
  orders,
  digits = 5,
  onModifyOrderField,
}: OrdersPanelProps) {
  const handleModify = async (
    orderId: OrderRow["id"],
    field: "sl" | "tp",
    currentValue?: number | null
  ) => {
    if (!onModifyOrderField) {
      toast.info("Modify order action is not wired yet.")
      return
    }
    try {
      await onModifyOrderField(orderId, field, currentValue)
    } catch {
      toast.error("Failed to modify order")
    }
  }

  return (
    <Card className="h-fit">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">Pending Orders</CardTitle>
      </CardHeader>
      <CardContent className="overflow-x-auto">
        <Table className="min-w-[1440px]">
          <colgroup>
            {COLUMN_WIDTHS.split(" ").map((width, index) => (
              <col key={index} style={{ width }} />
            ))}
          </colgroup>
          <TableBody>
            {orders.length === 0 ? (
              <TableRow>
                <TableCell colSpan={13} className="text-center text-muted-foreground">
                  No pending orders.
                </TableCell>
              </TableRow>
            ) : (
              orders.map((order) => (
                <TableRow key={order.id}>
                  <TableCell>{order.symbol}</TableCell>
                  <TableCell>{order.ticket}</TableCell>
                  <TableCell>{formatTime(order.time)}</TableCell>
                  <TableCell>{order.type}</TableCell>
                  <TableCell>{order.volume.toFixed(2)}</TableCell>
                  <TableCell>{formatPrice(order.price, digits)}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <span>{formatPrice(order.sl, digits)}</span>
                      <Button
                        size="icon"
                        variant="ghost"
                        className="h-6 w-6"
                        onClick={() => handleModify(order.id, "sl", order.sl)}
                      >
                        <Pencil className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <span>{formatPrice(order.tp, digits)}</span>
                      <Button
                        size="icon"
                        variant="ghost"
                        className="h-6 w-6"
                        onClick={() => handleModify(order.id, "tp", order.tp)}
                      >
                        <Pencil className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </TableCell>
                  <TableCell>--</TableCell>
                  <TableCell>--</TableCell>
                  <TableCell>--</TableCell>
                  <TableCell>--</TableCell>
                  <TableCell>--</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
