"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { CreditCard } from "lucide-react"
import { useDashboardSummary } from "@/components/dashboard/use-dashboard-summary"

export function WinRateCard() {
  const { data, loading } = useDashboardSummary()

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">Win Rate</CardTitle>
        <CreditCard className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">
          {loading ? "..." : `${data.win_rate.toFixed(1)}%`}
        </div>
        <p className="text-xs text-muted-foreground">
          {loading
            ? "Loading closed trades"
            : `${data.winning_trade_count} winners out of ${data.closed_trade_count} closed trades`}
        </p>
      </CardContent>
    </Card>
  )
}
