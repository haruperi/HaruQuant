import { BacktestRunsTable } from "@/components/performance/backtest-runs-table"

export default function PerformancePage() {
    return (
        <div className="flex-1 p-6">
            <div className="space-y-6">
                <div>
                    <h2 className="text-2xl font-bold tracking-tight">Backtest Performance</h2>
                    <p className="text-muted-foreground">
                        View and manage all your backtest runs. Select a category from the navigation above for detailed performance metrics and analysis.
                    </p>
                </div>
                <BacktestRunsTable />
            </div>
        </div>
    )
}
