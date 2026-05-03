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

export type Trade = Record<string, unknown>

interface TradeListProps {
    trades: Trade[]
}

export function TradeList({ trades }: TradeListProps) {
    const normalizedTrades = trades.map((trade, index) => {
        const numberValue = (value: unknown): number => {
            if (typeof value === "number" && Number.isFinite(value)) return value
            if (typeof value === "string" && value.trim() !== "") {
                const parsed = Number(value)
                return Number.isFinite(parsed) ? parsed : 0
            }
            return 0
        }
        const stringValue = (value: unknown, fallback = "N/A"): string =>
            typeof value === "string" && value.trim() !== "" ? value : fallback

        return {
            id: numberValue(trade.id ?? trade.trade_id ?? trade.ticket) || index + 1,
            time: stringValue(trade.time ?? trade.close_time ?? trade.exit_time ?? trade.open_time),
            type: stringValue(trade.type ?? trade.side ?? trade.direction),
            symbol: stringValue(trade.symbol),
            price: numberValue(trade.price ?? trade.close_price ?? trade.exit_price ?? trade.open_price),
            volume: numberValue(trade.volume ?? trade.position_size ?? trade.size),
            profit: numberValue(trade.profit ?? trade.pnl ?? trade.profit_loss ?? trade.net_profit),
        }
    })

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
                    {normalizedTrades.map((trade) => (
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
