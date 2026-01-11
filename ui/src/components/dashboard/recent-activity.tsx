import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { CheckCircle2, AlertTriangle, Info } from "lucide-react"

const activities = [
    {
        id: 1,
        type: "trade",
        title: "Order #3201 Executed",
        desc: "Bought 0.1 BTC @ 42,000",
        time: "2m ago",
        value: "+$0.00",
        icon: CheckCircle2,
        color: "text-emerald-500"
    },
    {
        id: 2,
        type: "warning",
        title: "Strategy Warning",
        desc: "High slippage detected on EURUSD",
        time: "15m ago",
        value: "Warn",
        icon: AlertTriangle,
        color: "text-amber-500"
    },
     {
        id: 3,
        type: "info",
        title: "Daily Backup",
        desc: "Database backup completed successfully",
        time: "1h ago",
        value: "Info",
        icon: Info,
        color: "text-blue-500"
    }
]

export function RecentActivity() {
  return (
    <Card className="col-span-3">
      <CardHeader>
        <CardTitle>Recent Activity</CardTitle>
        <CardDescription>
          Latest trades and events
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
            {activities.map((activity) => (
                <div key={activity.id} className="flex items-center">
                    <activity.icon className={`h-4 w-4 ${activity.color}`} />
                    <div className="ml-4 space-y-1">
                        <p className="text-sm font-medium leading-none">{activity.title}</p>
                        <p className="text-sm text-muted-foreground">
                            {activity.desc}
                        </p>
                    </div>
                    <div className="ml-auto text-sm text-muted-foreground tabular-nums">
                        {activity.time}
                    </div>
                </div>
            ))}
        </div>
      </CardContent>
    </Card>
  )
}
