"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Users } from "lucide-react"
import { useDashboardSummary } from "@/components/dashboard/use-dashboard-summary"

export function ActiveStrategiesCard() {
  const { data, loading } = useDashboardSummary()

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">Active Strategies</CardTitle>
        <Users className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">
          {loading ? "..." : data.active_strategy_count}
        </div>
        <p className="text-xs text-muted-foreground">
          {loading
            ? "Loading active sessions"
            : data.active_strategy_count > 0
              ? "Configured in running or paused live sessions"
              : "No active live-session strategies"}
        </p>
      </CardContent>
    </Card>
  )
}
