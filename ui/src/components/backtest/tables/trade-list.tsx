"use client"

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"

export interface Trade {
  id: number;
  time: string;
  type: string;
  symbol: string;
  price: number;
  volume: number;
  profit: number;
}

interface TradeListProps {
    trades: Trade[]
}

export function TradeList({ trades }: TradeListProps) {
    return (
        <div className="rounded-md border">
            <Table>
                <TableHeader>
                    <TableRow>
                        <TableHead>ID</TableHead>
                        <TableHead>Time</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead>Symbol</TableHead>
                        <TableHead className="text-right">Price</TableHead>
                        <TableHead className="text-right">Volume</TableHead>
                        <TableHead className="text-right">Profit ($)</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {trades.map((trade) => (
                        <TableRow key={trade.id}>
                            <TableCell>{trade.id}</TableCell>
                            <TableCell>{trade.time}</TableCell>
                            <TableCell>
                                <Badge variant={trade.type === 'BUY' ? 'default' : 'destructive'} className={trade.type === 'BUY' ? 'bg-emerald-600' : 'bg-red-600'}>
                                    {trade.type}
                                </Badge>
                            </TableCell>
                            <TableCell>{trade.symbol}</TableCell>
                            <TableCell className="text-right">{trade.price.toFixed(2)}</TableCell>
                            <TableCell className="text-right">{trade.volume.toFixed(2)}</TableCell>
                            <TableCell className={`text-right font-medium ${trade.profit > 0 ? 'text-emerald-500' : (trade.profit < 0 ? 'text-red-500' : '')}`}>
                                {trade.profit !== 0 ? trade.profit.toFixed(2) : '-'}
                            </TableCell>
                        </TableRow>
                    ))}
                </TableBody>
            </Table>
        </div>
    )
}
