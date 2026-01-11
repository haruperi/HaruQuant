"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid } from "recharts"

const data = [
  { name: "Jan", total: 40000 },
  { name: "Feb", total: 41500 },
  { name: "Mar", total: 42200 },
  { name: "Apr", total: 41800 },
  { name: "May", total: 43500 },
  { name: "Jun", total: 45231 },
]

export function EquityCurve() {
  return (
    <Card className="col-span-4">
      <CardHeader>
        <CardTitle>Equity Curve</CardTitle>
        <CardDescription>
          Your total account value over the last 6 months
        </CardDescription>
      </CardHeader>
      <CardContent className="pl-2">
        <ResponsiveContainer width="100%" height={350}>
          <AreaChart data={data}>
            <defs>
                <linearGradient id="colorTotal" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                </linearGradient>
            </defs>
            <XAxis
              dataKey="name"
              stroke="#888888"
              fontSize={12}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              stroke="#888888"
              fontSize={12}
              tickLine={false}
              axisLine={false}
              tickFormatter={(value) => `$${value}`}
              domain={['auto', 'auto']}
            />
             <Tooltip
                contentStyle={{ backgroundColor: 'hsl(var(--card))', borderColor: 'hsl(var(--border))', borderRadius: 'var(--radius)' }}
                itemStyle={{ color: 'hsl(var(--foreground))' }}
                formatter={(value: number) => [`$${value.toLocaleString()}`, "Equity"]}
            />
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
            <Area
              type="monotone"
              dataKey="total"
              stroke="#10b981"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#colorTotal)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
