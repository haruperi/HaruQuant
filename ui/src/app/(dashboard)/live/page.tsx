"use client"

import { useState } from "react"
import { LiveStatusCardEnhanced } from "@/components/live/live-status-card-enhanced"
import { StrategyRunnerEnhanced } from "@/components/live/strategy-runner-enhanced"
import { SessionStrategyManager } from "@/components/live/session-strategy-manager"
import { SessionCreateDialog } from "@/components/live/session-create-dialog"
import { RiskMonitor } from "@/components/live/risk-monitor"
import { LiveCandleChart } from "@/components/live/live-candle-chart"
import { ActivePositionsTableEnhanced } from "@/components/live/active-positions-table-enhanced"
import { OpenOrdersTable } from "@/components/live/open-orders-table"
import { ManualOrderControls } from "@/components/live/manual-order-controls"
import { LiveLogViewer } from "@/components/live/live-log-viewer"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { AlertCircle } from "lucide-react"

export default function LivePage() {
  const [sessionId, setSessionId] = useState<number | undefined>(undefined)
  const [sessionStatus, setSessionStatus] = useState<string>("stopped")
  const [refreshTrigger, setRefreshTrigger] = useState(0)
  const [selectedSymbol, setSelectedSymbol] = useState<string>("XAUUSD")
  const [selectedTimeframe, setSelectedTimeframe] = useState<string>("M15")

  const handleSessionCreated = (newSessionId: number) => {
    setSessionId(newSessionId)
    setRefreshTrigger(prev => prev + 1)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Live Command Center</h1>
        <SessionCreateDialog onSessionCreated={handleSessionCreated} />
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {sessionId ? (
          <LiveStatusCardEnhanced sessionId={sessionId} />
        ) : (
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">System Status</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-sm text-muted-foreground">Select a session to start</div>
            </CardContent>
          </Card>
        )}
        <StrategyRunnerEnhanced
          onSessionChange={setSessionId}
          onStatusChange={setSessionStatus}
          refreshTrigger={refreshTrigger}
        />
        <RiskMonitor sessionId={sessionId} />
      </div>

      {!sessionId && (
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>No Active Session</AlertTitle>
          <AlertDescription>
            Select or create a trading session using the Strategy Control panel to begin live trading.
          </AlertDescription>
        </Alert>
      )}

      {sessionId && (
        <div className="grid gap-4 grid-cols-1">
          {/* Strategy Management */}
          <SessionStrategyManager
            sessionId={sessionId}
            sessionStatus={sessionStatus}
          />

          {/* Main Chart */}
          <Card className="h-[500px] flex flex-col">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
              <CardTitle>Live Chart</CardTitle>
              <div className="flex items-center gap-2">
                <select
                  value={selectedSymbol}
                  onChange={(e) => setSelectedSymbol(e.target.value)}
                  className="h-8 rounded-md border border-input bg-background px-3 py-1 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <option value="XAUUSD">XAUUSD</option>
                  <option value="EURUSD">EURUSD</option>
                  <option value="GBPUSD">GBPUSD</option>
                  <option value="USDJPY">USDJPY</option>
                  <option value="BTCUSD">BTCUSD</option>
                </select>
                <select
                  value={selectedTimeframe}
                  onChange={(e) => setSelectedTimeframe(e.target.value)}
                  className="h-8 rounded-md border border-input bg-background px-3 py-1 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <option value="M1">M1</option>
                  <option value="M5">M5</option>
                  <option value="M15">M15</option>
                  <option value="M30">M30</option>
                  <option value="H1">H1</option>
                  <option value="H4">H4</option>
                  <option value="D1">D1</option>
                </select>
              </div>
            </CardHeader>
            <CardContent className="flex-1 p-0 overflow-hidden">
              <LiveCandleChart
                sessionId={sessionId}
                symbol={selectedSymbol}
                timeframe={selectedTimeframe}
              />
            </CardContent>
          </Card>

          {/* Bottom Section: Positions & Orders */}
          <div className="grid gap-4 grid-cols-1 lg:grid-cols-3">
            <div className="lg:col-span-2 flex flex-col gap-4">
              <ActivePositionsTableEnhanced sessionId={sessionId} />
              <OpenOrdersTable />
            </div>
            <div className="lg:col-span-1">
              {/* Right Column - Execution & Tables */}
              <div className="space-y-4">
                <div className="grid gap-4 grid-cols-1">
                   <ManualOrderControls sessionId={sessionId} />
                </div>
              </div>
            </div>
          </div>

          {/* Live Log */}
          <div>
            <LiveLogViewer />
          </div>
        </div>
      )}
    </div>
  )
}
