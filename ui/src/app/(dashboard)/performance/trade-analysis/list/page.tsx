"use client"

import { useEffect, useState } from "react"
import { PerformancePageHeader } from "@/components/performance/performance-page-header"
import { useSelectedBacktest } from "@/contexts/selected-backtest-context"
import { strategyApi } from "@/lib/api/strategies"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Loader2, Download } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

interface TradeData {
  trade_number?: number
  order_number?: number
  symbol?: string
  type?: string
  signal?: string
  open_time?: string
  close_time?: string
  open_price?: number
  close_price?: number
  entry_price?: number
  exit_price?: number
  volume?: number
  profit_loss?: number
  profit_loss_pips?: number
  commission?: number
  swap?: number
  mae_pips?: number
  mfe_pips?: number
  cumulative_profit_usd?: number
  cumulative_profit_percent?: number
  runup_usd?: number
  runup_percent?: number
  drawdown_usd?: number
  drawdown_percent?: number
  time_in_trade?: number
}

export default function TradeListPage() {
    const { selectedBacktest } = useSelectedBacktest()
    const [trades, setTrades] = useState<TradeData[]>([])
    const [loading, setLoading] = useState(false)
    const [selectedTrade, setSelectedTrade] = useState<string>("")
    const [highlightedTrade, setHighlightedTrade] = useState<number | null>(null)

    useEffect(() => {
        const fetchData = async () => {
            if (!selectedBacktest) return

            setLoading(true)
            try {
                let tradesData = selectedBacktest.trades || []

                // If trades are missing but we have an ID, fetch them
                if (tradesData.length === 0 && selectedBacktest.backtest_id) {
                     try {
                        const fullBacktest = await strategyApi.getBacktestById(selectedBacktest.backtest_id)
                        tradesData = fullBacktest.trades || []
                     } catch (err) {
                        console.error("Failed to fetch full backtest details", err)
                     }
                }

                const response = await strategyApi.getTradeList(tradesData, selectedBacktest.initial_balance || 10000)
                setTrades(response)
            } catch (error) {
                console.error("Failed to fetch trade list:", error)
            } finally {
                setLoading(false)
            }
        }

        fetchData()
    }, [selectedBacktest])

    const formatCurrency = (value: number | undefined) => {
        if (value === undefined || value === null) return "$0.00"
        return `$${value.toFixed(2)}`
    }

    const formatPercent = (value: number | undefined) => {
        if (value === undefined || value === null) return "0%"
        return `${value.toFixed(2)}%`
    }

    const formatDateTime = (dateStr: string | undefined) => {
        if (!dateStr) return "n/a"
        const date = new Date(dateStr)
        return date.toLocaleString("en-US", {
            month: "2-digit",
            day: "2-digit",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
            hour12: false
        }).replace(",", "")
    }

    const getValueColor = (value: number | undefined) => {
        if (value === undefined || value === null || value === 0) return ""
        return value > 0 ? "text-green-500" : "text-red-500"
    }

    const getSpecialTrade = (category: string): number | null => {
        if (trades.length === 0 || !selectedBacktest) return null

        const initialBalance = selectedBacktest.initial_balance || 10000

        switch (category) {
            case "first":
                return trades[0].trade_number || 1
            case "last":
                return trades[trades.length - 1].trade_number || trades.length
            case "largest_winning_usd":
                const maxWinTrade = trades.reduce((max, trade) =>
                    (trade.profit_loss || 0) > (max.profit_loss || 0) ? trade : max
                )
                return maxWinTrade.trade_number || trades.indexOf(maxWinTrade) + 1
            case "largest_losing_usd":
                const maxLossTrade = trades.reduce((min, trade) =>
                    (trade.profit_loss || 0) < (min.profit_loss || 0) ? trade : min
                )
                return maxLossTrade.trade_number || trades.indexOf(maxLossTrade) + 1
            case "largest_winning_percent":
                const maxWinPercentTrade = trades.reduce((max, trade) => {
                    const maxPercent = ((max.profit_loss || 0) / initialBalance) * 100
                    const tradePercent = ((trade.profit_loss || 0) / initialBalance) * 100
                    return tradePercent > maxPercent ? trade : max
                })
                return maxWinPercentTrade.trade_number || trades.indexOf(maxWinPercentTrade) + 1
            case "largest_losing_percent":
                const maxLossPercentTrade = trades.reduce((min, trade) => {
                    const minPercent = ((min.profit_loss || 0) / initialBalance) * 100
                    const tradePercent = ((trade.profit_loss || 0) / initialBalance) * 100
                    return tradePercent < minPercent ? trade : min
                })
                return maxLossPercentTrade.trade_number || trades.indexOf(maxLossPercentTrade) + 1
            case "longest":
                const longestTrade = trades.reduce((max, trade) => {
                    const maxDuration = max.time_in_trade || 0
                    const tradeDuration = trade.time_in_trade || 0
                    return tradeDuration > maxDuration ? trade : max
                })
                return longestTrade.trade_number || trades.indexOf(longestTrade) + 1
            case "shortest":
                const shortestTrade = trades.reduce((min, trade) => {
                    const minDuration = min.time_in_trade || Infinity
                    const tradeDuration = trade.time_in_trade || Infinity
                    return tradeDuration < minDuration ? trade : min
                })
                return shortestTrade.trade_number || trades.indexOf(shortestTrade) + 1
            case "max_runup_usd":
                const maxRUTrade = trades.reduce((max, trade) =>
                    (trade.runup_usd || 0) > (max.runup_usd || 0) ? trade : max
                )
                return maxRUTrade.trade_number || trades.indexOf(maxRUTrade) + 1
            case "max_runup_percent":
                const maxRUPercentTrade = trades.reduce((max, trade) =>
                    (trade.runup_percent || 0) > (max.runup_percent || 0) ? trade : max
                )
                return maxRUPercentTrade.trade_number || trades.indexOf(maxRUPercentTrade) + 1
            default:
                return null
        }
    }

    const handleTradeSelect = (value: string) => {
        let tradeNumber: number | null = null

        // Check if it's a special category
        if (value.startsWith("special_")) {
            const category = value.replace("special_", "")
            tradeNumber = getSpecialTrade(category)
        } else {
            tradeNumber = parseInt(value)
        }

        if (tradeNumber) {
            setSelectedTrade(String(tradeNumber))
            setHighlightedTrade(tradeNumber)

            // Scroll to the trade row
            const element = document.getElementById(`trade-${tradeNumber}`)
            if (element) {
                element.scrollIntoView({ behavior: "smooth", block: "center" })
            }

            // Remove highlight after 30 seconds
            setTimeout(() => {
                setHighlightedTrade(null)
            }, 30000)
        }
    }

    const handleExportCSV = () => {
        if (trades.length === 0) return

        const headers = [
            "Trade #",
            "Symbol",
            "Type",
            "Entry Time",
            "Exit Time",
            "Entry Price",
            "Exit Price",
            "Size",
            "Profit ($)",
            "Profit (Pips)",
            "Commission",
            "Swap",
            "MAE (Pips)",
            "MFE (Pips)",
            "Balance ($)"
        ]

        const initialBalance = selectedBacktest?.initial_balance || 10000
        const rows = trades.map((trade, index) => {
            const currentBalance = initialBalance + (trade.cumulative_profit_usd || 0)
            return [
                trade.trade_number || index + 1,
                trade.symbol || selectedBacktest?.symbol || '-',
                trade.type || '-',
                formatDateTime(trade.open_time),
                formatDateTime(trade.close_time),
                trade.open_price || 0,
                trade.close_price || 0,
                trade.volume || 0,
                trade.profit_loss || 0,
                trade.profit_loss_pips || 0,
                trade.commission || 0,
                trade.swap || 0,
                trade.mae_pips || 0,
                trade.mfe_pips || 0,
                currentBalance.toFixed(2)
            ]
        })

        const csvContent = [
            headers.join(","),
            ...rows.map(row => row.map(cell => `"${cell}"`).join(","))
        ].join("\n")

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
        const url = URL.createObjectURL(blob)
        const link = document.createElement("a")
        link.setAttribute("href", url)
        const filename = `trades_${selectedBacktest?.alias || selectedBacktest?.strategy_name || 'backtest'}_${new Date().toISOString().slice(0, 10)}.csv`
        link.setAttribute("download", filename)
        link.style.visibility = 'hidden'
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
    }

    if (!selectedBacktest) {
         return (
            <div className="flex flex-col h-full w-full">
                <PerformancePageHeader title="List of Trades" />
                <div className="flex-1 flex items-center justify-center p-6">
                    <div className="text-center text-muted-foreground ml-4">
                        Please select a backtest to view the trade list.
                    </div>
                </div>
            </div>
         )
    }

    return (
        <div className="flex flex-col h-full w-full">
            <PerformancePageHeader title="List of Trades" />
            <div className="flex-1 p-6 overflow-auto">
                 {loading ? (
                    <div className="flex justify-center p-12">
                        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                    </div>
                 ) : trades.length > 0 ? (
                    <Card>
                        <CardHeader className="py-3 bg-muted/50 border-b">
                            <div className="flex items-center gap-4">
                                <CardTitle className="text-sm font-medium">Trade History</CardTitle>
                                <div className="flex items-center gap-2">
                                    <span className="text-sm text-muted-foreground">Go to:</span>
                                    <Select value={selectedTrade} onValueChange={handleTradeSelect}>
                                        <SelectTrigger className="w-[240px] h-8">
                                            <SelectValue placeholder="Select Trade to Find" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="special_first">First Trade</SelectItem>
                                            <SelectItem value="special_last">Last Trade</SelectItem>
                                            <SelectItem value="special_largest_winning_usd">Largest Winning Trade</SelectItem>
                                            <SelectItem value="special_largest_losing_usd">Largest Losing Trade</SelectItem>
                                            <SelectItem value="special_largest_winning_percent">Largest Winning Trade %</SelectItem>
                                            <SelectItem value="special_largest_losing_percent">Largest Losing Trade %</SelectItem>
                                            <SelectItem value="special_longest">Longest Trade</SelectItem>
                                            <SelectItem value="special_shortest">Shortest Trade</SelectItem>
                                            <SelectItem value="special_max_runup_usd">Max Run-up Trade</SelectItem>
                                            <SelectItem value="special_max_runup_percent">Max Run-up Trade %</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="ml-auto">
                                    <Button 
                                        variant="outline" 
                                        size="sm" 
                                        className="h-8 gap-2"
                                        onClick={handleExportCSV}
                                        disabled={trades.length === 0}
                                    >
                                        <Download className="h-4 w-4" />
                                        Export CSV
                                    </Button>
                                </div>
                            </div>
                        </CardHeader>
                        <CardContent className="p-0">
                            <div className="overflow-auto max-h-[calc(100vh-200px)]">
                                <Table>
                                    <TableHeader className="sticky top-0 bg-muted/80 backdrop-blur-sm z-10">
                                        <TableRow>
                                            <TableHead className="text-center">
                                                <TooltipProvider>
                                                    <Tooltip>
                                                        <TooltipTrigger className="cursor-help">Trade #</TooltipTrigger>
                                                        <TooltipContent>Sequential trade number in the backtest</TooltipContent>
                                                    </Tooltip>
                                                </TooltipProvider>
                                            </TableHead>
                                            <TableHead className="text-center">
                                                <TooltipProvider>
                                                    <Tooltip>
                                                        <TooltipTrigger className="cursor-help">Symbol</TooltipTrigger>
                                                        <TooltipContent>Trading instrument symbol</TooltipContent>
                                                    </Tooltip>
                                                </TooltipProvider>
                                            </TableHead>
                                            <TableHead className="text-center">
                                                <TooltipProvider>
                                                    <Tooltip>
                                                        <TooltipTrigger className="cursor-help">Type</TooltipTrigger>
                                                        <TooltipContent>Trade direction: Long (Buy) or Short (Sell)</TooltipContent>
                                                    </Tooltip>
                                                </TooltipProvider>
                                            </TableHead>
                                            <TableHead className="text-center">
                                                <TooltipProvider>
                                                    <Tooltip>
                                                        <TooltipTrigger className="cursor-help">Entry Time</TooltipTrigger>
                                                        <TooltipContent>Trade entry timestamp</TooltipContent>
                                                    </Tooltip>
                                                </TooltipProvider>
                                            </TableHead>
                                            <TableHead className="text-center">
                                                <TooltipProvider>
                                                    <Tooltip>
                                                        <TooltipTrigger className="cursor-help">Exit Time</TooltipTrigger>
                                                        <TooltipContent>Trade exit timestamp</TooltipContent>
                                                    </Tooltip>
                                                </TooltipProvider>
                                            </TableHead>
                                            <TableHead className="text-center">
                                                <TooltipProvider>
                                                    <Tooltip>
                                                        <TooltipTrigger className="cursor-help">Entry Price</TooltipTrigger>
                                                        <TooltipContent>Execution price for entry</TooltipContent>
                                                    </Tooltip>
                                                </TooltipProvider>
                                            </TableHead>
                                            <TableHead className="text-center">
                                                <TooltipProvider>
                                                    <Tooltip>
                                                        <TooltipTrigger className="cursor-help">Exit Price</TooltipTrigger>
                                                        <TooltipContent>Execution price for exit</TooltipContent>
                                                    </Tooltip>
                                                </TooltipProvider>
                                            </TableHead>
                                            <TableHead className="text-center">
                                                <TooltipProvider>
                                                    <Tooltip>
                                                        <TooltipTrigger className="cursor-help">Size</TooltipTrigger>
                                                        <TooltipContent>Position size or number of contracts</TooltipContent>
                                                    </Tooltip>
                                                </TooltipProvider>
                                            </TableHead>
                                            <TableHead className="text-center" colSpan={2}>
                                                <TooltipProvider>
                                                    <Tooltip>
                                                        <TooltipTrigger className="cursor-help">Profit</TooltipTrigger>
                                                        <TooltipContent>Trade profit or loss</TooltipContent>
                                                    </Tooltip>
                                                </TooltipProvider>
                                            </TableHead>
                                            <TableHead className="text-center" colSpan={2}>
                                                <TooltipProvider>
                                                    <Tooltip>
                                                        <TooltipTrigger className="cursor-help">Costs</TooltipTrigger>
                                                        <TooltipContent>Commission and Swap fees</TooltipContent>
                                                    </Tooltip>
                                                </TooltipProvider>
                                            </TableHead>
                                            <TableHead className="text-center" colSpan={2}>
                                                <TooltipProvider>
                                                    <Tooltip>
                                                        <TooltipTrigger className="cursor-help">Running</TooltipTrigger>
                                                        <TooltipContent>Maximum Adverse (MAE) and Favorable (MFE) Excursion</TooltipContent>
                                                    </Tooltip>
                                                </TooltipProvider>
                                            </TableHead>
                                            <TableHead className="text-center">
                                                <TooltipProvider>
                                                    <Tooltip>
                                                        <TooltipTrigger className="cursor-help">Balance</TooltipTrigger>
                                                        <TooltipContent>Running account balance</TooltipContent>
                                                    </Tooltip>
                                                </TooltipProvider>
                                            </TableHead>
                                        </TableRow>
                                        <TableRow>
                                            <TableHead className="h-8"></TableHead>
                                            <TableHead className="h-8"></TableHead>
                                            <TableHead className="h-8"></TableHead>
                                            <TableHead className="h-8"></TableHead>
                                            <TableHead className="h-8"></TableHead>
                                            <TableHead className="h-8"></TableHead>
                                            <TableHead className="h-8"></TableHead>
                                            <TableHead className="h-8"></TableHead>
                                            <TableHead className="text-center text-xs h-8">$</TableHead>
                                            <TableHead className="text-center text-xs h-8">Pips</TableHead>
                                            <TableHead className="text-center text-xs h-8">Comm.</TableHead>
                                            <TableHead className="text-center text-xs h-8">Swap</TableHead>
                                            <TableHead className="text-center text-xs h-8">MAE</TableHead>
                                            <TableHead className="text-center text-xs h-8">MFE</TableHead>
                                            <TableHead className="text-center text-xs h-8">$</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {trades.map((trade, index) => {
                                            const tradeNum = trade.trade_number || index + 1
                                            const isHighlighted = highlightedTrade === tradeNum
                                            const initialBalance = selectedBacktest?.initial_balance || 10000
                                            const currentBalance = initialBalance + (trade.cumulative_profit_usd || 0)
                                            
                                            return (
                                            <TableRow
                                                key={index}
                                                id={`trade-${tradeNum}`}
                                                className={`${
                                                    isHighlighted
                                                        ? 'bg-primary/20 border-l-4 border-primary'
                                                        : index % 2 === 0 ? 'bg-card' : 'bg-muted/20'
                                                } hover:bg-muted/50 transition-all duration-300`}
                                            >
                                                <TableCell className="text-center text-sm">{trade.trade_number || index + 1}</TableCell>
                                                <TableCell className="text-center text-sm">{trade.symbol || selectedBacktest?.symbol || '-'}</TableCell>
                                                <TableCell className="text-center text-sm capitalize">{trade.type || '-'}</TableCell>
                                                <TableCell className="text-center text-sm">{formatDateTime(trade.open_time)}</TableCell>
                                                <TableCell className="text-center text-sm">{formatDateTime(trade.close_time)}</TableCell>
                                                <TableCell className="text-center text-sm">{trade.open_price?.toFixed(5) || '-'}</TableCell>
                                                <TableCell className="text-center text-sm">{trade.close_price?.toFixed(5) || '-'}</TableCell>
                                            <TableCell className="text-center text-sm">{trade.volume || '-'}</TableCell>
                                            <TableCell className={`text-center text-sm ${getValueColor(trade.profit_loss)}`}>
                                                {formatCurrency(trade.profit_loss)}
                                            </TableCell>
                                            <TableCell className={`text-center text-sm ${getValueColor(trade.profit_loss_pips)}`}>
                                                {trade.profit_loss_pips?.toFixed(1) || '-'}
                                            </TableCell>
                                            <TableCell className="text-center text-sm text-muted-foreground">
                                                {formatCurrency(trade.commission)}
                                            </TableCell>
                                            <TableCell className="text-center text-sm text-muted-foreground">
                                                {formatCurrency(trade.swap)}
                                            </TableCell>
                                            <TableCell className="text-center text-sm text-muted-foreground">
                                                {trade.mae_pips?.toFixed(1) || '-'}
                                            </TableCell>
                                            <TableCell className="text-center text-sm text-muted-foreground">
                                                {trade.mfe_pips?.toFixed(1) || '-'}
                                            </TableCell>
                                            <TableCell className="text-center text-sm font-medium">
                                                {formatCurrency(currentBalance)}
                                            </TableCell>
                                        </TableRow>

                                            )
                                        })}
                                    </TableBody>
                                </Table>
                            </div>
                        </CardContent>
                    </Card>
                 ) : (
                    <div className="text-center text-muted-foreground p-12 bg-muted/10 rounded-lg border border-dashed">
                        No trades available for this backtest.
                    </div>
                 )}
            </div>
        </div>
    )
}
