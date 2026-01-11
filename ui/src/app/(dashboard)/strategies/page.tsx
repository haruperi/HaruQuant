import { StrategyList } from "@/components/strategies/strategy-list"

export default function StrategiesPage() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Strategy Library</h2>
        <p className="text-muted-foreground">
          Manage and monitor your algorithmic trading strategies.
        </p>
      </div>
      <StrategyList />
    </div>
  )
}
