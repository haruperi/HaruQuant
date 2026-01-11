import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { CreditCard, Users } from "lucide-react"
import { BrokerStatus } from "@/components/dashboard/broker-status"
import { SystemStatus } from "@/components/dashboard/system-status"
import { ResourceUsage } from "@/components/dashboard/resource-usage"
import { MarketHours } from "@/components/dashboard/market-hours"
import { QuickActions } from "@/components/dashboard/quick-actions"
import { EquityCurve } from "@/components/dashboard/equity-curve"
import { DailyPnlChart } from "@/components/dashboard/daily-pnl"
import { ActiveStrategies } from "@/components/dashboard/active-strategies"
import { RecentActivity } from "@/components/dashboard/recent-activity"

export default function Home() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
      </div>

      {/* Infrastructure & Status Row */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <BrokerStatus />
        <SystemStatus />
        <ResourceUsage />
        <MarketHours />
      </div>

      {/* Actions & KPI Row */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <QuickActions />

        <DailyPnlChart />

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
                Win Rate
            </CardTitle>
            <CreditCard className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">64.2%</div>
            <p className="text-xs text-muted-foreground">
              -2% from last week
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Active Strategies
            </CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">+3</div>
            <p className="text-xs text-muted-foreground">
              Running on MT5 & Binance
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Charts Row */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
        <EquityCurve />
        <ActiveStrategies />
      </div>

      {/* Activity Row */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
         <div className="col-span-4">
              {/* Future: Maybe a trade log or news feed here? For now leaving empty or putting something else */}
         </div>
         <RecentActivity />
      </div>
    </div>
  )
}
