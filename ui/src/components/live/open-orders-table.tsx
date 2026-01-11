"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { XCircle } from "lucide-react"

export function OpenOrdersTable() {
    const orders = [
        { id: 1, symbol: "USDJPY", type: "BUY LIMIT", volume: 1.0, price: 142.00, current: 142.50 },
        { id: 2, symbol: "EURUSD", type: "SELL STOP", volume: 0.5, price: 1.0450, current: 1.0520 },
    ]

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <div className="flex items-center space-x-2">
            <CardTitle className="text-sm font-medium">Open Orders</CardTitle>
            <Badge variant="outline" className="text-xs">{orders.length}</Badge>
        </div>
      </CardHeader>
      <CardContent>
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
                {orders.map((order) => (
                    <TableRow key={order.id}>
                        <TableCell className="font-medium">{order.symbol}</TableCell>
                        <TableCell>
                            <Badge variant="secondary" className="font-normal text-xs">{order.type}</Badge>
                        </TableCell>
                        <TableCell>{order.volume}</TableCell>
                        <TableCell>{order.price.toFixed(order.symbol.includes('JPY') ? 2 : 5)}</TableCell>
                        <TableCell className="text-muted-foreground">
                            {Math.abs(order.current - order.price).toFixed(order.symbol.includes('JPY') ? 2 : 4)}
                        </TableCell>
                        <TableCell className="text-right">
                             <Button size="icon" variant="ghost" className="h-8 w-8 text-muted-foreground hover:text-destructive">
                                <XCircle className="h-4 w-4" />
                            </Button>
                        </TableCell>
                    </TableRow>
                ))}
            </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
