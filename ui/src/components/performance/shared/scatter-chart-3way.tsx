"use client"

import * as React from "react"
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ZAxis,
  Cell,
} from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"

interface ScatterChart3WayProps {
    title: string
    data: any[]
    className?: string
    xAxisLabel?: string
    yAxisLabel?: string
    valueFormatter?: (value: number) => string
}

export function ScatterChart3Way({
    title,
    data,
    className,
    valueFormatter = (val) => val.toFixed(2),
}: ScatterChart3WayProps) {

    // Simple tooltip
    const CustomTooltip = ({ active, payload }: any) => {
        if (active && payload && payload.length) {
            const data = payload[0].payload;
            return (
                <div className="rounded-lg border bg-background p-2 shadow-sm">
                    <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
                        <div className="text-muted-foreground">X (Size):</div>
                        <div className="font-medium text-right">{data.x}</div>

                        <div className="text-muted-foreground">Y (P/L):</div>
                        <div className={`font-medium text-right ${data.y >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                            {valueFormatter(data.y)}
                        </div>

                        {data.r_multiple !== undefined && (
                             <>
                                <div className="text-muted-foreground">R-Mult:</div>
                                <div className="font-medium text-right">{data.r_multiple.toFixed(2)}</div>
                             </>
                        )}
                    </div>
                </div>
            );
        }
        return null;
    };

    return (
        <Card className={cn("w-full flex flex-col", className)}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-lg font-medium">{title}</CardTitle>
            </CardHeader>
            <CardContent>
                 <div className="h-[400px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                        <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
                            <XAxis
                                type="number"
                                dataKey="x"
                                name="Size"
                                stroke="#888888"
                                fontSize={12}
                                tickLine={false}
                                axisLine={false}
                            />
                            <YAxis
                                type="number"
                                dataKey="y"
                                name="P/L"
                                stroke="#888888"
                                fontSize={12}
                                tickLine={false}
                                axisLine={false}
                                tickFormatter={(val) => valueFormatter(val)}
                            />
                            <ZAxis type="number" dataKey="z" range={[60, 400]} />
                            <Tooltip content={<CustomTooltip />} />
                            <Scatter name={title} data={data} fill="#8884d8">
                                {data.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={entry.y >= 0 ? '#10b981' : '#ef4444'} />
                                ))}
                            </Scatter>
                        </ScatterChart>
                    </ResponsiveContainer>
                 </div>
            </CardContent>
        </Card>
    )
}
