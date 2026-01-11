/**
 * Trade Stats Sidebar Component
 *
 * Displays comprehensive trade statistics organized in tabs.
 * Shows all 60+ fields from the backtest_trades table with proper formatting.
 *
 * Tabs:
 * 1. Overview - Basic info (symbol, side, P&L, commission, swap, R-multiple)
 * 2. Execution - Timing (open/close times, bars in trade, slippage)
 * 3. Risk - Risk management (stop loss, profit target, position sizing)
 * 4. Excursion - MAE/MFE analysis (Maximum Adverse/Favorable Excursion)
 * 5. Account - Account state at entry (balance, equity, margin)
 *
 * @module components/performance/trade-stats-sidebar
 */

"use client"

import * as React from "react"
import { format } from "date-fns"
import { Trade } from "@/lib/api/trades"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { cn } from "@/lib/utils"

/**
 * Props for TradeStatsSidebar component
 */
interface TradeStatsSidebarProps {
  /** The trade object containing all statistics to display */
  trade: Trade
  /** Callback function when back button is clicked */
  onBack: () => void
}

// Formatting utilities
const formatCurrency = (value: number | null): string => {
  if (value === null || value === undefined) return "N/A"
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)
}

const formatPercentage = (value: number | null): string => {
  if (value === null || value === undefined) return "N/A"
  return `${value.toFixed(2)}%`
}

const formatDateTime = (value: string | null): string => {
  if (!value) return "N/A"
  try {
    return format(new Date(value), "MMM dd, yyyy HH:mm:ss")
  } catch {
    return "Invalid date"
  }
}

const formatDuration = (seconds: number | null): string => {
  if (seconds === null || seconds === undefined) return "N/A"

  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = Math.floor(seconds % 60)

  if (hours > 0) {
    return `${hours}h ${minutes}m ${secs}s`
  } else if (minutes > 0) {
    return `${minutes}m ${secs}s`
  } else {
    return `${secs}s`
  }
}

const formatNumber = (value: number | null, decimals: number = 2): string => {
  if (value === null || value === undefined) return "N/A"
  return value.toFixed(decimals)
}

// Stat display component
interface StatItemProps {
  label: string
  value: string | number | null
  colorCode?: boolean
  isPercentage?: boolean
  isCurrency?: boolean
}

function StatItem({ label, value, colorCode = false, isPercentage = false, isCurrency = false }: StatItemProps) {
  let displayValue = "N/A"
  let colorClass = "text-foreground"

  if (value !== null && value !== undefined) {
    if (isCurrency) {
      displayValue = formatCurrency(Number(value))
    } else if (isPercentage) {
      displayValue = formatPercentage(Number(value))
    } else {
      displayValue = String(value)
    }

    if (colorCode && typeof value === "number") {
      colorClass = value > 0 ? "text-green-500" : value < 0 ? "text-red-500" : "text-foreground"
    }
  }

  return (
    <div className="flex flex-col gap-1 py-2">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className={cn("text-sm font-medium", colorClass)}>{displayValue}</span>
    </div>
  )
}

export function TradeStatsSidebar({ trade, onBack }: TradeStatsSidebarProps) {
  return (
    <div className="flex h-full flex-col">
      <Tabs defaultValue="overview" className="flex h-full flex-col">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="overview" className="text-xs">
            Overview
          </TabsTrigger>
          <TabsTrigger value="execution" className="text-xs">
            Execution
          </TabsTrigger>
          <TabsTrigger value="risk" className="text-xs">
            Risk
          </TabsTrigger>
          <TabsTrigger value="excursion" className="text-xs">
            Excursion
          </TabsTrigger>
          <TabsTrigger value="account" className="text-xs">
            Account
          </TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="flex-1 overflow-y-auto p-4">
          <div className="space-y-4">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">Trade Information</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground">Symbol:</span>
                  <Badge variant="outline">{trade.symbol || "N/A"}</Badge>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground">Side:</span>
                  <Badge
                    variant={trade.side?.toUpperCase() === "BUY" ? "default" : "destructive"}
                    className={
                      trade.side?.toUpperCase() === "BUY"
                        ? "bg-green-500 hover:bg-green-600"
                        : "bg-red-500 hover:bg-red-600"
                    }
                  >
                    {trade.side?.toUpperCase() || "N/A"}
                  </Badge>
                </div>
                <StatItem label="Strategy" value={trade.strategy_name} />
                <StatItem label="Setup ID" value={trade.setup_id} />
                <StatItem label="Ticket" value={trade.ticket} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">Performance</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <StatItem label="Net P&L" value={trade.pnl} isCurrency colorCode />
                <StatItem label="P&L (Pips)" value={formatNumber(trade.pnl_pips, 1)} colorCode />
                <StatItem label="R-Multiple" value={formatNumber(trade.r_multiple, 2)} colorCode />
                <StatItem label="Commission" value={trade.commission} isCurrency />
                <StatItem label="Swap" value={trade.swap} isCurrency />
                <StatItem label="Buy & Hold" value={trade.buy_hold} isCurrency />
                <StatItem label="Buy & Hold (Pips)" value={formatNumber(trade.buy_hold_pips, 1)} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">Context</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <StatItem label="Signal Timeframe" value={trade.signal_timeframe} />
                <StatItem label="Execution Timeframe" value={trade.execution_timeframe} />
                <StatItem label="Session" value={trade.session} />
                <StatItem label="Day of Week" value={trade.day_of_week} />
                <StatItem label="Hour of Day" value={trade.hour_of_day} />
                <StatItem label="Sample Type" value={trade.sample_type} />
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Execution Tab */}
        <TabsContent value="execution" className="flex-1 overflow-y-auto p-4">
          <div className="space-y-4">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">Timing</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex flex-col gap-1 py-2">
                  <span className="text-xs text-muted-foreground">Open Time</span>
                  <span className="text-sm font-medium">{formatDateTime(trade.open_time)}</span>
                </div>
                <div className="flex flex-col gap-1 py-2">
                  <span className="text-xs text-muted-foreground">Close Time</span>
                  <span className="text-sm font-medium">{formatDateTime(trade.close_time)}</span>
                </div>
                <div className="flex flex-col gap-1 py-2">
                  <span className="text-xs text-muted-foreground">Time in Trade</span>
                  <span className="text-sm font-medium">
                    {(() => {
                      // Calculate duration from open_time to close_time
                      if (trade.open_time && trade.close_time) {
                        const openDate = new Date(trade.open_time)
                        const closeDate = new Date(trade.close_time)
                        const durationSeconds = (closeDate.getTime() - openDate.getTime()) / 1000
                        return formatDuration(durationSeconds)
                      }
                      return formatDuration(trade.time_in_trade_seconds)
                    })()}
                  </span>
                </div>
                <StatItem label="Bars in Trade" value={trade.bars_in_trade} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">Prices</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <StatItem label="Open Price" value={formatNumber(trade.open_price, 5)} />
                <StatItem label="Close Price" value={formatNumber(trade.close_price, 5)} />
                <StatItem label="Original Open Price" value={formatNumber(trade.orig_open_price, 5)} />
                <StatItem label="Requested Entry Price" value={formatNumber(trade.requested_entry_price, 5)} />
                <StatItem label="Requested Exit Price" value={formatNumber(trade.requested_exit_price, 5)} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">Execution Quality</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <StatItem label="Slippage (USD)" value={trade.slippage_usd} isCurrency />
                <StatItem label="Fill Price Deviation" value={formatNumber(trade.fill_price_deviation, 5)} />
                <StatItem label="Execution Latency (ms)" value={trade.execution_latency_ms} />
                <StatItem label="Spread at Entry" value={formatNumber(trade.spread_at_entry, 5)} />
                <StatItem label="ATR at Entry" value={formatNumber(trade.atr_at_entry, 5)} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">Exit Details</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <StatItem label="Close Type" value={trade.close_type} />
                <StatItem label="Exit Reason" value={trade.exit_reason} />
                <StatItem label="Partial Close Count" value={trade.partial_close_count} />
                <div className="flex items-center gap-2 py-2">
                  <span className="text-xs text-muted-foreground">Trailing Stop Used:</span>
                  <Badge variant={trade.trailing_stop_used ? "default" : "outline"}>
                    {trade.trailing_stop_used ? "Yes" : "No"}
                  </Badge>
                </div>
                <div className="flex items-center gap-2 py-2">
                  <span className="text-xs text-muted-foreground">Breakeven Triggered:</span>
                  <Badge variant={trade.breakeven_triggered ? "default" : "outline"}>
                    {trade.breakeven_triggered ? "Yes" : "No"}
                  </Badge>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Risk Tab */}
        <TabsContent value="risk" className="flex-1 overflow-y-auto p-4">
          <div className="space-y-4">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">Risk Parameters</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <StatItem label="Stop Loss Price" value={formatNumber(trade.stop_loss_price, 5)} />
                <StatItem label="Profit Target Price" value={formatNumber(trade.profit_target_price, 5)} />
                <StatItem label="Initial Risk (Pips)" value={formatNumber(trade.initial_risk_pips, 1)} />
                <StatItem label="Initial Risk (USD)" value={trade.initial_risk_usd} isCurrency />
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">Position Sizing</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <StatItem label="Position Size" value={formatNumber(trade.position_size, 2)} />
                <StatItem label="Max Position Size" value={formatNumber(trade.max_position_size, 2)} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">Risk Management</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex items-center gap-2 py-2">
                  <span className="text-xs text-muted-foreground">Rule Violation:</span>
                  <Badge variant={trade.rule_violation ? "destructive" : "outline"}>
                    {trade.rule_violation ? "Yes" : "No"}
                  </Badge>
                </div>
                <div className="flex items-center gap-2 py-2">
                  <span className="text-xs text-muted-foreground">Manual Intervention:</span>
                  <Badge variant={trade.manual_intervention ? "default" : "outline"}>
                    {trade.manual_intervention ? "Yes" : "No"}
                  </Badge>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">Market Context</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <StatItem label="Market Regime" value={trade.market_regime} />
                <StatItem label="Volatility Bucket" value={trade.volatility_bucket} />
                <StatItem label="Correlation Cluster" value={trade.correlation_cluster} />
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Excursion Tab */}
        <TabsContent value="excursion" className="flex-1 overflow-y-auto p-4">
          <div className="space-y-4">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">Maximum Adverse Excursion (MAE)</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <StatItem label="MAE (USD)" value={trade.mae_usd} isCurrency colorCode />
                <StatItem label="MAE (Pips)" value={formatNumber(trade.mae_pips, 1)} colorCode />
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">Maximum Favorable Excursion (MFE)</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <StatItem label="MFE (USD)" value={trade.mfe_usd} isCurrency colorCode />
                <StatItem label="MFE (Pips)" value={formatNumber(trade.mfe_pips, 1)} colorCode />
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">Excursion Analysis</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex flex-col gap-1 py-2">
                  <span className="text-xs text-muted-foreground">MAE/MFE Ratio</span>
                  <span className="text-sm font-medium">
                    {trade.mae_usd && trade.mfe_usd && trade.mfe_usd !== 0
                      ? formatNumber(Math.abs(trade.mae_usd) / trade.mfe_usd, 2)
                      : "N/A"}
                  </span>
                </div>
                <StatItem label="Drawdown" value={trade.drawdown} colorCode />
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">Performance Metrics</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <StatItem label="Net P&L" value={trade.pnl} isCurrency colorCode />
                <StatItem label="P&L (Pips)" value={formatNumber(trade.pnl_pips, 1)} colorCode />
                <StatItem label="R-Multiple" value={formatNumber(trade.r_multiple, 2)} colorCode />
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Account Tab */}
        <TabsContent value="account" className="flex-1 overflow-y-auto p-4">
          <div className="space-y-4">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">Account State at Entry</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <StatItem label="Balance" value={trade.balance_at_entry} isCurrency />
                <StatItem label="Equity" value={trade.equity_at_entry} isCurrency />
                <StatItem label="Margin Used" value={trade.margin_used} isCurrency />
                <StatItem label="Free Margin" value={trade.free_margin} isCurrency />
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">Account Growth</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex flex-col gap-1 py-2">
                  <span className="text-xs text-muted-foreground">Account Growth (%)</span>
                  <span
                    className={cn(
                      "text-sm font-medium",
                      trade.pnl && trade.balance_at_entry
                        ? trade.pnl > 0
                          ? "text-green-500"
                          : "text-red-500"
                        : "text-foreground"
                    )}
                  >
                    {trade.pnl && trade.balance_at_entry
                      ? formatPercentage((trade.pnl / trade.balance_at_entry) * 100)
                      : "N/A"}
                  </span>
                </div>
                <StatItem label="Net P&L" value={trade.pnl} isCurrency colorCode />
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">Trade Details</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <StatItem label="Position Size" value={formatNumber(trade.position_size, 2)} />
                <StatItem label="Commission" value={trade.commission} isCurrency />
                <StatItem label="Swap" value={trade.swap} isCurrency />
                <StatItem label="Total Costs" value={
                  trade.commission && trade.swap
                    ? trade.commission + trade.swap
                    : trade.commission || trade.swap
                } isCurrency />
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">Additional Info</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <StatItem label="Magic Number" value={trade.magic_number} />
                <StatItem label="Comment" value={trade.comment} />
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
