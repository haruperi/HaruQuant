"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export interface AccountMetrics {
  balance: number
  equity: number
  margin: number
  margin_free?: number
  profit: number
}

interface AccountMetricsProps {
  metrics: AccountMetrics
}

export function AccountMetricsBar({ metrics }: AccountMetricsProps) {
  const profitClass = metrics.profit >= 0 ? "text-emerald-500" : "text-red-500"

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">Account Metrics</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-sm">
          <div className="space-y-1">
            <div className="text-muted-foreground">Balance</div>
            <div className="font-medium">{metrics.balance.toFixed(2)}</div>
          </div>
          <div className="space-y-1">
            <div className="text-muted-foreground">Equity</div>
            <div className="font-medium">{metrics.equity.toFixed(2)}</div>
          </div>
          <div className="space-y-1">
            <div className="text-muted-foreground">Margin</div>
            <div className="font-medium">{metrics.margin.toFixed(2)}</div>
          </div>
          <div className="space-y-1">
            <div className="text-muted-foreground">Free Margin</div>
            <div className="font-medium">
              {Number(metrics.margin_free ?? 0).toFixed(2)}
            </div>
          </div>
          <div className="space-y-1">
            <div className="text-muted-foreground">Profit</div>
            <div className={`font-medium ${profitClass}`}>{metrics.profit.toFixed(2)}</div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
