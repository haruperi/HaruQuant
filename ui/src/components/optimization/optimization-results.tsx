"use client"

import { useState, useMemo } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ArrowLeft, Check } from "lucide-react"

import type { OptimizationRunDetails, OptimizationResultItem } from "@/lib/api/optimization"

interface OptimizationResultsProps {
    run: OptimizationRunDetails | null
    results: OptimizationResultItem[]
    onBack: () => void
}

export function OptimizationResults({ run, results, onBack }: OptimizationResultsProps) {
    // Transform API results to match component format
    const RESULTS = useMemo(() => {
        return results.map(r => ({
            id: r.result_id,
            parameters: r.parameters,
            metrics: {
                sharpe_ratio: r.sharpe_ratio,
                total_return: r.total_return,
                max_drawdown: r.max_drawdown,
                win_rate: r.win_rate,
                profit_factor: r.profit_factor,
                total_trades: r.total_trades,
            }
        }))
    }, [results])
    // Get parameter names dynamically from results
    const paramNames = useMemo(() => {
        if (RESULTS.length === 0) return []
        return Object.keys(RESULTS[0].parameters)
    }, [RESULTS])

    const [xAxis, setXAxis] = useState<string>(paramNames[0] || "")
    const [yAxis, setYAxis] = useState<string>(paramNames[1] || "")
    const [metric, setMetric] = useState<string>("sharpe_ratio")

    const metricNames = ["sharpe_ratio", "total_return", "max_drawdown", "win_rate", "profit_factor"]

    // Prepare Heatmap Data
    const heatmapData = useMemo(() => {
        // Extract unique values for axes
        const xValues = Array.from(new Set(RESULTS.map(r => r.parameters[xAxis as keyof typeof r.parameters]))).sort((a, b) => a - b)
        const yValues = Array.from(new Set(RESULTS.map(r => r.parameters[yAxis as keyof typeof r.parameters]))).sort((a, b) => a - b)

        // Create Grid
        const grid = yValues.map(y => {
            return xValues.map(x => {
                const match = RESULTS.find(r => r.parameters[xAxis as keyof typeof r.parameters] === x && r.parameters[yAxis as keyof typeof r.parameters] === y)
                return match ? match.metrics[metric as keyof typeof match.metrics] : null
            })
        })

        // Find min/max for color scale
        const values = grid.flat().filter(v => v !== null) as number[]
        const min = Math.min(...values)
        const max = Math.max(...values)

        return { xValues, yValues, grid, min, max }
    }, [xAxis, yAxis, metric])

    const getColor = (value: number | null) => {
        if (value === null) return "bg-muted"
        const { min, max } = heatmapData
        const ratio = (value - min) / (max - min)

        // Simple distinct blue/emerald ramp
        // Low = Red/Gray, High = Green
        // Using HSL for gradients might be better, but simple opacity works for now
        // Let's use opacity of emerald
        return `rgba(16, 185, 129, ${0.1 + ratio * 0.9})`
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center gap-4">
                <Button variant="ghost" onClick={onBack} size="sm">
                    <ArrowLeft className="mr-2 h-4 w-4" />
                    Back
                </Button>
                <h2 className="text-2xl font-bold tracking-tight">Optimization Results</h2>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Heatmap Section */}
                <Card className="lg:col-span-2">
                    <CardHeader>
                        <div className="flex justify-between items-center">
                            <CardTitle>Parameter Heatmap</CardTitle>
                            <div className="flex gap-2">
                                <Select value={metric} onValueChange={setMetric}>
                                    <SelectTrigger className="w-[140px] h-8 text-xs">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="sharpe_ratio">Sharpe Ratio</SelectItem>
                                        <SelectItem value="total_return">Total Return</SelectItem>
                                        <SelectItem value="max_drawdown">Max Drawdown</SelectItem>
                                        <SelectItem value="win_rate">Win Rate</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>
                        <div className="flex gap-4 pt-2">
                            <div className="space-y-1">
                                <span className="text-xs text-muted-foreground uppercase">X-Axis</span>
                                <Select value={xAxis} onValueChange={setXAxis}>
                                    <SelectTrigger className="w-[120px] h-8 text-xs">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {paramNames.map(p => <SelectItem key={p} value={p}>{p}</SelectItem>)}
                                    </SelectContent>
                                </Select>
                            </div>
                            <div className="space-y-1">
                                <span className="text-xs text-muted-foreground uppercase">Y-Axis</span>
                                <Select value={yAxis} onValueChange={setYAxis}>
                                    <SelectTrigger className="w-[120px] h-8 text-xs">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {paramNames.map(p => <SelectItem key={p} value={p}>{p}</SelectItem>)}
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>
                    </CardHeader>
                    <CardContent>
                        <div className="w-full overflow-auto">
                            <div className="min-w-[400px]">
                                {/* Heatmap Visualization */}
                                <div
                                    className="grid gap-1"
                                    style={{
                                        gridTemplateColumns: `auto repeat(${heatmapData.xValues.length}, minmax(40px, 1fr))`
                                    }}
                                >
                                    {/* Header Row (X-Axis) */}
                                    <div className="h-8"></div> {/* Corner */}
                                    {heatmapData.xValues.map(x => (
                                        <div key={x} className="flex items-center justify-center text-xs text-muted-foreground font-mono">
                                            {x}
                                        </div>
                                    ))}

                                    {/* Rows */}
                                    {heatmapData.yValues.map((y, yIdx) => (
                                        <>
                                            {/* Y-Axis Label */}
                                            <div key={`label-${y}`} className="flex items-center justify-end pr-2 text-xs text-muted-foreground font-mono">
                                                {y}
                                            </div>
                                            {/* Cells */}
                                            {heatmapData.grid[yIdx].map((val, xIdx) => (
                                                <div
                                                    key={`${y}-${xIdx}`}
                                                    className="h-10 w-full rounded-sm flex items-center justify-center text-[10px] font-medium transition-all hover:scale-110 hover:shadow-md cursor-pointer relative group"
                                                    style={{ backgroundColor: getColor(val) }}
                                                >
                                                    {val?.toFixed(2)}
                                                    {/* Tooltip */}
                                                    <div className="hidden group-hover:block absolute bottom-full mb-1 bg-popover text-popover-foreground text-xs p-2 rounded border shadow-lg z-10 whitespace-nowrap">
                                                        {xAxis}: {heatmapData.xValues[xIdx]}<br/>
                                                        {yAxis}: {y}<br/>
                                                        {metric}: {val?.toFixed(3)}
                                                    </div>
                                                </div>
                                            ))}
                                        </>
                                    ))}
                                </div>
                                <div className="text-center mt-2 text-xs text-muted-foreground">
                                    {yAxis} (Y) vs {xAxis} (X)
                                </div>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* Top Candidates List */}
                <Card>
                    <CardHeader>
                        <CardTitle>Top Candidates</CardTitle>
                        <CardDescription>Ranked by Objective</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead className="w-[50px]">Rank</TableHead>
                                    <TableHead>Params</TableHead>
                                    <TableHead className="text-right">Sharpe</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {RESULTS.slice(0, 8).map((r, i) => (
                                    <TableRow key={r.id} className="text-xs">
                                        <TableCell className="font-medium text-muted-foreground">#{i + 1}</TableCell>
                                        <TableCell>
                                            <div className="flex flex-col gap-1">
                                                <span className="font-mono">F:{r.parameters.fast_period} S:{r.parameters.slow_period}</span>
                                            </div>
                                        </TableCell>
                                        <TableCell className="text-right font-bold text-emerald-500">
                                            {r.metrics.sharpe_ratio.toFixed(2)}
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                         <div className="mt-4">
                            <Button className="w-full">
                                <Check className="mr-2 h-4 w-4" />
                                Apply Best Parameters
                            </Button>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}
