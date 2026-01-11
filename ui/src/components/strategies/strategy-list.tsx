"use client"

import { useState, useMemo } from "react"
import { Input } from "@/components/ui/input"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { Search, Loader2, AlertCircle } from "lucide-react"
import { StrategyCard } from "./strategy-card"
import { CreateStrategyDialog } from "./create-strategy-dialog"
import { useStrategies } from "@/lib/use-strategies"
import { Alert, AlertDescription } from "@/components/ui/alert"

export function StrategyList() {
    const [filter, setFilter] = useState("all")
    const [search, setSearch] = useState("")

    // Fetch strategies from backend
    const { strategies, loading, error, refetch } = useStrategies()

    // Transform backend data to match UI expectations
    const transformedStrategies = useMemo(() => {
        return strategies.map(s => ({
            id: s.id.toString(),
            name: s.name,
            description: s.description || "",
            status: s.status,
            type: s.category || "Uncategorized",
            winRate: 0, // Will be populated from latest backtest
            profitFactor: 0, // Will be populated from latest backtest
            dailyPnL: Array.from({length: 20}, (_, i) => ({
                value: 100 + i * 5 + Math.random() * 20
            })) // Placeholder equity curve
        }))
    }, [strategies])

    const filteredStrategies = useMemo(() => {
        return transformedStrategies.filter(s => {
            const matchesSearch = s.name.toLowerCase().includes(search.toLowerCase())
            const matchesFilter = filter === "all" || s.status === filter
            return matchesSearch && matchesFilter
        })
    }, [transformedStrategies, search, filter])

    return (
        <div className="space-y-6">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div className="flex w-full md:w-auto items-center space-x-2">
                    <div className="relative w-full md:w-[300px]">
                        <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                        <Input
                            placeholder="Search strategies..."
                            className="pl-8"
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                        />
                    </div>
                     <ToggleGroup type="single" value={filter} onValueChange={(val) => val && setFilter(val)}>
                        <ToggleGroupItem value="all">All</ToggleGroupItem>
                        <ToggleGroupItem value="active">Active</ToggleGroupItem>
                        <ToggleGroupItem value="inactive">Inactive</ToggleGroupItem>
                        <ToggleGroupItem value="testing">Testing</ToggleGroupItem>
                    </ToggleGroup>
                </div>
                <CreateStrategyDialog onSuccess={refetch} />
            </div>

            {error && (
                <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>
                        {error}
                    </AlertDescription>
                </Alert>
            )}

            {loading ? (
                <div className="flex items-center justify-center py-12">
                    <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                </div>
            ) : filteredStrategies.length === 0 ? (
                <div className="text-center py-12">
                    <p className="text-muted-foreground">
                        {search || filter !== "all"
                            ? "No strategies found matching your criteria."
                            : "No strategies yet. Create your first strategy to get started!"
                        }
                    </p>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                    {filteredStrategies.map(strategy => (
                        <StrategyCard key={strategy.id} strategy={strategy} onDelete={refetch} />
                    ))}
                </div>
            )}
        </div>
    )
}
