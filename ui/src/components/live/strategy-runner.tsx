"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Play, Square, Pause } from "lucide-react"
import { useState } from "react"
import { Badge } from "@/components/ui/badge"

export function StrategyRunner() {
  const [isRunning, setIsRunning] = useState(false)
  const [mode, setMode] = useState("paper")

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">Strategy Control</CardTitle>
        <div className="flex items-center space-x-2">
            <Badge variant={mode === 'live' ? 'destructive' : 'secondary'}>
                {mode === 'live' ? 'LIVE TRADING' : 'PAPER TRADING'}
            </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="space-y-2">
            <label className="text-xs font-medium text-muted-foreground">Active Strategy</label>
            <div className="font-medium text-sm border rounded-md p-2 bg-muted/50">
                MACD Trend Follower v2.1
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-medium text-muted-foreground">Execution Mode</label>
            <Select value={mode} onValueChange={setMode} disabled={isRunning}>
              <SelectTrigger>
                <SelectValue placeholder="Select mode" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="paper">Paper Trading (Simulated)</SelectItem>
                <SelectItem value="live">Live Trading (Real Money)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="pt-2 flex space-x-2">
            {!isRunning ? (
                <Button
                    className="w-full bg-emerald-600 hover:bg-emerald-700"
                    onClick={() => setIsRunning(true)}
                >
                    <Play className="mr-2 h-4 w-4" /> Start Strategy
                </Button>
            ) : (
                <>
                    <Button
                        variant="outline"
                        className="flex-1"
                        onClick={() => setIsRunning(false)}
                    >
                        <Pause className="mr-2 h-4 w-4" /> Pause
                    </Button>
                    <Button
                        variant="destructive"
                        className="flex-1"
                        onClick={() => setIsRunning(false)}
                    >
                        <Square className="mr-2 h-4 w-4" /> Stop
                    </Button>
                </>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
