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

export interface OrderRow {
  id: string | number
  symbol: string
  type: string
  volume: number
  price: number
  sl?: number | null
  tp?: number | null
}

interface OrdersPanelProps {
  orders: OrderRow[]
  onModifyOrder?: (orderId: OrderRow["id"]) => Promise<void> | void
  onCancelOrder?: (orderId: OrderRow["id"]) => Promise<void> | void
}

export function OrdersPanel({
  orders,
  onModifyOrder,
  onCancelOrder,
}: OrdersPanelProps) {
  const handleModify = async (orderId: OrderRow["id"]) => {
    if (!onModifyOrder) {
      toast.info("Modify order action is not wired yet.")
      return
    }
    try {
      await onModifyOrder(orderId)
    } catch (error) {
      toast.error("Failed to modify order")
    }
  }

  const handleCancel = async (orderId: OrderRow["id"]) => {
    if (!onCancelOrder) {
      toast.info("Cancel order action is not wired yet.")
      return
    }
    try {
      await onCancelOrder(orderId)
    } catch (error) {
      toast.error("Failed to cancel order")
    }
  }

  return (
    <Card className="h-fit">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">Pending Orders</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Symbol</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Volume</TableHead>
              <TableHead>Price</TableHead>
              <TableHead>SL</TableHead>
              <TableHead>TP</TableHead>
              <TableHead className="text-right">Action</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {orders.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center text-muted-foreground">
                  No pending orders.
                </TableCell>
              </TableRow>
            ) : (
              orders.map((order) => (
                <TableRow key={order.id}>
                  <TableCell>{order.symbol}</TableCell>
                  <TableCell>{order.type}</TableCell>
                  <TableCell>{order.volume}</TableCell>
                  <TableCell>{order.price.toFixed(5)}</TableCell>
                  <TableCell>{order.sl ? order.sl.toFixed(5) : "--"}</TableCell>
                <TableCell>{order.tp ? order.tp.toFixed(5) : "--"}</TableCell>
                <TableCell className="text-right">
                  <div className="flex justify-end gap-2">
                    <Button
                      size="icon"
                      variant="ghost"
                      onClick={() => handleModify(order.id)}
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button
                      size="icon"
                      variant="ghost"
                      onClick={() => handleCancel(order.id)}
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
