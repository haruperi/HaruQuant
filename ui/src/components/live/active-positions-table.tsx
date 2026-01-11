"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { XCircle, Edit2 } from "lucide-react"

export function ActivePositionsTable() {
    const positions = [
        { id: 1, symbol: "EURUSD", type: "BUY", volume: 1.0, openPrice: 1.0500, currentPrice: 1.0520, pnl: 200.00, profit: true },
        { id: 2, symbol: "XAUUSD", type: "SELL", volume: 0.5, openPrice: 2040.50, currentPrice: 2035.00, pnl: 275.00, profit: true },
        { id: 3, symbol: "GBPUSD", type: "BUY", volume: 0.8, openPrice: 1.2700, currentPrice: 1.2680, pnl: -160.00, profit: false },
    ]

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <div className="flex items-center space-x-2">
            <CardTitle className="text-sm font-medium">Active Positions</CardTitle>
            <Badge variant="secondary" className="text-xs">{positions.length}</Badge>
        </div>
      </CardHeader>
      <CardContent>
        <Table>
            <TableHeader>
                <TableRow>
                    <TableHead className="w-[80px]">Symbol</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Vol</TableHead>
                    <TableHead>Open</TableHead>
                    <TableHead>Current</TableHead>
                    <TableHead className="text-right">PnL</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                </TableRow>
            </TableHeader>
            <TableBody>
                {positions.map((pos) => (
                    <TableRow key={pos.id}>
                        <TableCell className="font-medium">{pos.symbol}</TableCell>
                        <TableCell>
                            <span className={pos.type === 'BUY' ? 'text-emerald-500 font-bold' : 'text-red-500 font-bold'}>
                                {pos.type}
                            </span>
                        </TableCell>
                        <TableCell>{pos.volume}</TableCell>
                        <TableCell>{pos.openPrice.toFixed(pos.symbol.includes('JPY') || pos.symbol.includes('XAU') ? 2 : 5)}</TableCell>
                        <TableCell>{pos.currentPrice.toFixed(pos.symbol.includes('JPY') || pos.symbol.includes('XAU') ? 2 : 5)}</TableCell>
                        <TableCell className={`text-right font-mono ${pos.profit ? 'text-emerald-500' : 'text-red-500'}`}>
                            {pos.pnl > 0 ? '+' : ''}{pos.pnl.toFixed(2)}
                        </TableCell>
                        <TableCell className="text-right">
                             <div className="flex justify-end space-x-1">
                                <Button size="icon" variant="ghost" className="h-8 w-8">
                                    <Edit2 className="h-4 w-4" />
                                </Button>
                                <Button size="icon" variant="ghost" className="h-8 w-8 text-destructive hover:text-destructive hover:bg-destructive/10">
                                    <XCircle className="h-4 w-4" />
                                </Button>
                             </div>
                        </TableCell>
                    </TableRow>
                ))}
            </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
