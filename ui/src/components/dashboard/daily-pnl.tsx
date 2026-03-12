"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useDashboardSummary } from "@/components/dashboard/use-dashboard-summary"
import { formatCurrency } from "@/lib/utils"
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, Cell } from "recharts"

export function DailyPnlChart() {
  const { data, loading } = useDashboardSummary()

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">Daily PnL</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[80px]">
          {loading ? (
            <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
              Loading...
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.daily_pnl}>
                <Tooltip
                  cursor={{ fill: "transparent" }}
                  contentStyle={{ backgroundColor: "hsl(var(--card))", borderColor: "hsl(var(--border))", borderRadius: "var(--radius)" }}
                  itemStyle={{ color: "hsl(var(--foreground))" }}
                  formatter={(value: number) => [formatCurrency(value), "PnL"]}
                  labelStyle={{ display: "none" }}
                />
                <XAxis dataKey="day" hide />
                <Bar dataKey="pnl">
                  {data.daily_pnl.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.pnl >= 0 ? "#10b981" : "#ef4444"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
        <div className="mt-4 flex items-center justify-between">
            <div>
                 <div className={`text-2xl font-bold ${data.weekly_pnl_total >= 0 ? "text-emerald-500" : "text-red-500"}`}>
                  {formatCurrency(data.weekly_pnl_total)}
                 </div>
                 <p className="text-xs text-muted-foreground">This Week</p>
            </div>
             <div className="text-right">
                <div className="text-xs font-medium">Best: {formatCurrency(data.weekly_best_day)}</div>
                <div className="text-xs text-muted-foreground">Worst: {formatCurrency(data.weekly_worst_day)}</div>
            </div>
        </div>
      </CardContent>
    </Card>
  )
}
