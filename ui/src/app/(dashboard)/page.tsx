import { BrokerStatus } from "@/components/dashboard/broker-status"
import { SystemStatus } from "@/components/dashboard/system-status"
import { ResourceUsage } from "@/components/dashboard/resource-usage"
import { MarketHours } from "@/components/dashboard/market-hours"
import { QuickActions } from "@/components/dashboard/quick-actions"
import { EquityCurve } from "@/components/dashboard/equity-curve"
import { DailyPnlChart } from "@/components/dashboard/daily-pnl"
import { ActiveStrategies } from "@/components/dashboard/active-strategies"
import { RecentActivity } from "@/components/dashboard/recent-activity"
import { WinRateCard } from "@/components/dashboard/win-rate-card"
import { ActiveStrategiesCard } from "@/components/dashboard/active-strategies-card"

export default function Home() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <BrokerStatus />
        <SystemStatus />
        <ResourceUsage />
        <MarketHours />
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <QuickActions />
        <DailyPnlChart />
        <WinRateCard />
        <ActiveStrategiesCard />
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
        <EquityCurve />
        <ActiveStrategies />
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
        <div className="col-span-4" />
        <RecentActivity />
      </div>
    </div>
  )
}
