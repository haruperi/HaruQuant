"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Activity, Wifi, Server, Wallet } from "lucide-react"

export function LiveStatusCard() {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">System Status</CardTitle>
        <Activity className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Server className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium">Broker Connection</span>
            </div>
            <Badge variant="outline" className="bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/20 border-emerald-500/20">
              Connected
            </Badge>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Wifi className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium">Latency</span>
            </div>
            <span className="text-sm font-bold font-mono">24ms</span>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Wallet className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium">Equity</span>
            </div>
            <div className="flex flex-col items-end">
               <span className="text-lg font-bold text-emerald-500">$52,430.50</span>
               <span className="text-xs text-muted-foreground">Balance: $50,000.00</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
