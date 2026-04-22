"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { SemanticSnapshotScript } from "@/components/ai-chat/SemanticSnapshotScript"
import { XCircle, Loader2, AlertCircle } from "lucide-react"
import { LiveTradingAPI } from "@/lib/api/live"
import type { Order } from "@/types/live"
import { toast } from "sonner"

interface OpenOrdersTableProps {
  sessionId?: number
}

export function OpenOrdersTable({ sessionId }: OpenOrdersTableProps) {
  const [orders, setOrders] = useState<Order[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!sessionId) return

    const fetchOrders = async () => {
      try {
        setIsLoading(true)
        setError(null)
        const data = await LiveTradingAPI.getOrders(sessionId)
        setOrders(data)
      } catch (err) {
        console.error("Error fetching orders:", err)
        setError(err instanceof Error ? err.message : "Failed to load orders")
      } finally {
        setIsLoading(false)
      }
    }

    fetchOrders()
    const interval = setInterval(fetchOrders, 15000)
    return () => clearInterval(interval)
  }, [sessionId])

  const handleCancel = async (ticket: number) => {
    if (!sessionId) return
    try {
      await LiveTradingAPI.cancelOrder(sessionId, ticket)
      toast.success("Order Cancelled", {
        description: `Order ${ticket} cancelled`,
      })
      const updated = await LiveTradingAPI.getOrders(sessionId)
      setOrders(updated)
    } catch (err) {
      console.error("Error cancelling order:", err)
      toast.error("Cancel Failed", {
        description: err instanceof Error ? err.message : "Unknown error",
      })
    }
  }

  const getPrecision = (symbol: string): number => {
    if (symbol.includes("JPY")) return 3
    if (symbol.includes("XAU") || symbol.includes("GOLD")) return 2
    return 5
  }

  const formatPrice = (price: number | undefined, symbol: string): string => {
    if (price === undefined || price === null) return "-"
    return price.toFixed(getPrecision(symbol))
  }

  const orderTypeLabel = (type: number): string => {
    const map: Record<number, string> = {
      2: "BUY LIMIT",
      3: "SELL LIMIT",
      4: "BUY STOP",
      5: "SELL STOP",
      6: "BUY STOP LIMIT",
      7: "SELL STOP LIMIT",
    }
    return map[type] || `TYPE ${type}`
  }

  if (!sessionId) {
    return (
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-sm font-medium">Open Orders</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground">Select a session to view orders.</div>
        </CardContent>
      </Card>
    )
  }

  if (isLoading) {
    return (
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <div className="flex items-center space-x-2">
            <CardTitle className="text-sm font-medium">Open Orders</CardTitle>
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          </div>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground">Loading orders...</div>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <div className="flex items-center space-x-2">
            <CardTitle className="text-sm font-medium">Open Orders</CardTitle>
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
    <Card>
      <SemanticSnapshotScript
        block={{
          id: `live-open-orders:${sessionId}`,
          blockType: "table",
          title: "Open Orders",
          summary: sessionId ? `Pending orders for live session ${sessionId}.` : "Open orders table.",
          keywords: ["orders", "open orders", "pending orders", "price", "distance"],
          metrics: [
            { label: "Open Order Count", value: String(orders.length) },
          ],
          headers: ["Symbol", "Type", "Vol", "Price", "Distance"],
          rows: orders.slice(0, 24).map((order) => {
            const current = order.price_current ?? order.price_open
            const distance = current !== undefined ? Math.abs(current - order.price_open) : undefined
            return [
              order.symbol,
              orderTypeLabel(order.type),
              String(order.volume_current),
              formatPrice(order.price_open, order.symbol),
              distance !== undefined ? distance.toFixed(getPrecision(order.symbol)) : "-",
            ]
          }),
        }}
      />
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <div className="flex items-center space-x-2">
            <CardTitle className="text-sm font-medium">Open Orders</CardTitle>
            <Badge variant="outline" className="text-xs">{orders.length}</Badge>
        </div>
      </CardHeader>
      <CardContent>
        {orders.length === 0 ? (
          <div className="text-sm text-muted-foreground text-center py-8">
            No open orders
          </div>
        ) : (
          <Table>
              <TableHeader>
                  <TableRow>
                      <TableHead className="w-[80px]">Symbol</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Vol</TableHead>
                      <TableHead>Price</TableHead>
                      <TableHead>Distance</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
              </TableHeader>
              <TableBody>
                  {orders.map((order) => {
                      const current = order.price_current ?? order.price_open
                      const distance = current !== undefined ? Math.abs(current - order.price_open) : undefined
                      return (
                        <TableRow key={order.ticket}>
                            <TableCell className="font-medium">{order.symbol}</TableCell>
                            <TableCell>
                                <Badge variant="secondary" className="font-normal text-xs">
                                  {orderTypeLabel(order.type)}
                                </Badge>
                            </TableCell>
                            <TableCell>{order.volume_current}</TableCell>
                            <TableCell>{formatPrice(order.price_open, order.symbol)}</TableCell>
                            <TableCell className="text-muted-foreground">
                                {distance !== undefined ? distance.toFixed(getPrecision(order.symbol)) : "-"}
                            </TableCell>
                            <TableCell className="text-right">
                                 <Button
                                   size="icon"
                                   variant="ghost"
                                   className="h-8 w-8 text-muted-foreground hover:text-destructive"
                                   onClick={() => handleCancel(order.ticket)}
                                 >
                                    <XCircle className="h-4 w-4" />
                                </Button>
                            </TableCell>
                        </TableRow>
                      )
                  })}
              </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  )
}
