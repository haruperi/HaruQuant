"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, Cell } from "recharts"

const data = [
  { day: "Mon", pnl: 120 },
  { day: "Tue", pnl: -40 },
  { day: "Wed", pnl: 250 },
  { day: "Thu", pnl: 180 },
  { day: "Fri", pnl: -90 },
  { day: "Sat", pnl: 0 },
  { day: "Sun", pnl: 0 },
]

export function DailyPnlChart() {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">Daily PnL</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[80px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data}>
              <Tooltip
                cursor={{fill: 'transparent'}}
                contentStyle={{ backgroundColor: 'hsl(var(--card))', borderColor: 'hsl(var(--border))', borderRadius: 'var(--radius)' }}
                itemStyle={{ color: 'hsl(var(--foreground))' }}
                formatter={(value: number) => [`$${value}`, "PnL"]}
                labelStyle={{ display: 'none' }}
              />
              <Bar dataKey="pnl">
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.pnl >= 0 ? '#10b981' : '#ef4444'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="mt-4 flex items-center justify-between">
            <div>
                 <div className="text-2xl font-bold text-emerald-500">+$420.00</div>
                 <p className="text-xs text-muted-foreground">This Week</p>
            </div>
             <div className="text-right">
                <div className="text-xs font-medium">Best: +$250</div>
                <div className="text-xs text-muted-foreground">Worst: -$90</div>
            </div>
        </div>
      </CardContent>
    </Card>
  )
}
