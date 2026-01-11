"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { AlertTriangle, Play, Square, XCircle } from "lucide-react"

export function QuickActions() {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">Quick Actions</CardTitle>
        <Play className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-2 mt-2">
        <Button variant="outline" size="sm" className="w-full justify-start">
            <Play className="mr-2 h-4 w-4 text-emerald-500" />
            New Backtest
        </Button>
        <Button variant="outline" size="sm" className="w-full justify-start">
            <Square className="mr-2 h-4 w-4 text-blue-500" />
            Flatten All
        </Button>
         <Button variant="outline" size="sm" className="w-full justify-start">
            <XCircle className="mr-2 h-4 w-4 text-orange-500" />
            Cancel Orders
        </Button>
        <Button variant="destructive" size="sm" className="w-full justify-start">
            <AlertTriangle className="mr-2 h-4 w-4" />
            Panic Close
        </Button>
      </CardContent>
    </Card>
  )
}
