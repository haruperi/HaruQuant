"use client"

import { useMemo, useState } from "react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { AlertCircle, Activity, TrendingUp } from "lucide-react"

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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useRegisterPageContext } from "@/hooks/usePageContext"
import { useRegisterPageActions } from "@/hooks/useRegisterPageActions"
import type { SessionStatusInfo } from "@/types/live"

export default function LivePage() {
  const [sessionId, setSessionId] = useState<number | undefined>(undefined)
  const [sessionStatus, setSessionStatus] = useState<string>("stopped")
  const [liveStatus, setLiveStatus] = useState<SessionStatusInfo | null>(null)
  const [refreshTrigger, setRefreshTrigger] = useState(0)

  // Chart state
  const [selectedSymbol, setSelectedSymbol] = useState<string>("XAUUSD")
  const [selectedTimeframe, setSelectedTimeframe] = useState<string>("M15")

  useRegisterPageActions(
    useMemo(() => [
      {
        id: "live_trading.change_symbol",
        label: "Change Symbol",
        description: "Change the symbol displayed on the live chart",
        riskLevel: "local_ui",
        inputSchema: { symbol: "string" },
      },
      {
        id: "live_trading.change_timeframe",
        label: "Change Timeframe",
        description: "Change the timeframe displayed on the live chart",
        riskLevel: "local_ui",
        inputSchema: { timeframe: "string" },
      }
    ], []),
    useMemo(() => ({
      "live_trading.change_symbol": (params) => {
        if (typeof params.symbol === "string") setSelectedSymbol(params.symbol.toUpperCase())
      },
      "live_trading.change_timeframe": (params) => {
        if (typeof params.timeframe === "string") setSelectedTimeframe(params.timeframe.toUpperCase())
      }
    }), [])
  )

  const handleSessionCreated = (newSessionId: number) => {
    setSessionId(newSessionId)
    setRefreshTrigger(prev => prev + 1)
  }

  useRegisterPageContext(useMemo(
    () => ({
      pageTitle: "Live Command Center",
      sessionId: sessionId ?? null,
      symbol: selectedSymbol,
      timeframe: selectedTimeframe,
      activeTab: "live",
      entityRefs: sessionId ? [{ type: "live_session", id: String(sessionId), label: `Session ${sessionId}` }] : [],
      pageIntelligence: {
        visibleMetrics: [
          liveStatus?.account_login != null
            ? {
                id: "live.account_login",
                label: "Account Login",
                value: liveStatus.account_login,
                source: "live_status",
              }
            : null,
          liveStatus?.account_server
            ? {
                id: "live.account_server",
                label: "Account Server",
                value: liveStatus.account_server,
                source: "live_status",
              }
            : null,
          liveStatus?.account_name
            ? {
                id: "live.account_name",
                label: "Account Name",
                value: liveStatus.account_name,
                source: "live_status",
              }
            : null,
          liveStatus?.current_equity != null
            ? {
                id: "live.current_equity",
                label: "Current Equity",
                value: liveStatus.current_equity,
                unit: "USD",
                source: "live_status",
              }
            : null,
          liveStatus?.current_balance != null
            ? {
                id: "live.current_balance",
                label: "Current Balance",
                value: liveStatus.current_balance,
                unit: "USD",
                source: "live_status",
              }
            : null,
        ].filter((metric): metric is NonNullable<typeof metric> => metric !== null),
        freshness: {
          observedAt: new Date().toISOString(),
          stalenessSeconds: 0,
          source: "live_status",
        },
      },
    }),
    [liveStatus, selectedSymbol, selectedTimeframe, sessionId],
  ))

  return (
    <div className="space-y-6 p-1 h-full flex flex-col">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Live Command Center</h1>
          <p className="text-muted-foreground">Monitor and control your algorithmic trading strategies in real-time.</p>
        </div>
        <SessionCreateDialog onSessionCreated={handleSessionCreated} />
      </div>

      <div className="grid gap-4 md:grid-cols-12 lg:grid-cols-12">
        {/* Status Section - Spans top row */}
        <div className="col-span-12 lg:col-span-4">
           {sessionId ? (
            <LiveStatusCardEnhanced sessionId={sessionId} onStatusUpdate={setLiveStatus} />
          ) : (
            <Card className="h-full flex flex-col justify-center items-center text-center p-6 border-dashed">
              <Activity className="h-10 w-10 text-muted-foreground mb-4 opacity-50" />
              <h3 className="text-lg font-medium">No Session Selected</h3>
              <p className="text-sm text-muted-foreground mt-2">Select a session from the control panel to view status.</p>
            </Card>
          )}
        </div>

        <div className="col-span-12 md:col-span-6 lg:col-span-4">
           <StrategyRunnerEnhanced
            onSessionChange={setSessionId}
            onStatusChange={setSessionStatus}
            refreshTrigger={refreshTrigger}
          />
        </div>

        <div className="col-span-12 md:col-span-6 lg:col-span-4">
           <RiskMonitor sessionId={sessionId} />
        </div>
      </div>

      {!sessionId && (
        <Alert variant="default" className="bg-primary/5 border-primary/20">
          <AlertCircle className="h-4 w-4 text-primary" />
          <AlertTitle className="text-primary font-medium">Getting Started</AlertTitle>
          <AlertDescription className="text-muted-foreground">
            Select an existing session from the <strong>Strategy Control</strong> panel above, or create a new session to begin.
          </AlertDescription>
        </Alert>
      )}

      {sessionId && (
        <div className="grid gap-6 grid-cols-12 flex-1">
          {/* Main Chart Column - Left */}
          <div className="col-span-12 lg:col-span-8 flex flex-col gap-6">
            <Card className="flex-1 flex flex-col min-h-[500px]">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 border-b">
                <div className="flex items-center gap-2">
                    <TrendingUp className="h-5 w-5 text-emerald-500" />
                    <CardTitle>Market Overview</CardTitle>
                </div>
                <div className="flex items-center gap-2">
                   <Select value={selectedSymbol} onValueChange={setSelectedSymbol}>
                    <SelectTrigger className="w-[120px] h-8 text-xs">
                      <SelectValue placeholder="Symbol" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="XAUUSD">XAUUSD</SelectItem>
                      <SelectItem value="EURUSD">EURUSD</SelectItem>
                      <SelectItem value="GBPUSD">GBPUSD</SelectItem>
                      <SelectItem value="USDJPY">USDJPY</SelectItem>
                      <SelectItem value="BTCUSD">BTCUSD</SelectItem>
                      <SelectItem value="ETHUSD">ETHUSD</SelectItem>
                      <SelectItem value="US30">US30</SelectItem>
                      <SelectItem value="NAS100">NAS100</SelectItem>
                    </SelectContent>
                  </Select>

                  <Select value={selectedTimeframe} onValueChange={setSelectedTimeframe}>
                    <SelectTrigger className="w-[80px] h-8 text-xs">
                      <SelectValue placeholder="TF" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="M1">M1</SelectItem>
                      <SelectItem value="M5">M5</SelectItem>
                      <SelectItem value="M15">M15</SelectItem>
                      <SelectItem value="M30">M30</SelectItem>
                      <SelectItem value="H1">H1</SelectItem>
                      <SelectItem value="H4">H4</SelectItem>
                      <SelectItem value="D1">D1</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </CardHeader>
              <CardContent className="flex-1 p-0 relative">
                 <LiveCandleChart
                    sessionId={sessionId}
                    symbol={selectedSymbol}
                    timeframe={selectedTimeframe}
                  />
              </CardContent>
            </Card>

            {/* Logs Viewer */}
             <LiveLogViewer sessionId={sessionId} />
          </div>

          {/* Right Column - Tabs for Management */}
          <div className="col-span-12 lg:col-span-4 flex flex-col gap-6">
            <Tabs defaultValue="positions" className="w-full flex-1 flex flex-col">
              <TabsList className="w-full grid grid-cols-3 mb-2">
                <TabsTrigger value="positions">Positions</TabsTrigger>
                <TabsTrigger value="orders">Orders</TabsTrigger>
                <TabsTrigger value="strategies">Strategies</TabsTrigger>
              </TabsList>

              <TabsContent value="positions" className="flex-1 mt-0">
                 <ActivePositionsTableEnhanced sessionId={sessionId} />
                 <div className="mt-4">
                     <ManualOrderControls sessionId={sessionId} defaultSymbol={selectedSymbol} />
                 </div>
              </TabsContent>

              <TabsContent value="orders" className="flex-1 mt-0 space-y-4">
                 <OpenOrdersTable sessionId={sessionId} />
                 <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm">Quick Trade</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <ManualOrderControls sessionId={sessionId} defaultSymbol={selectedSymbol} />
                    </CardContent>
                 </Card>
              </TabsContent>

              <TabsContent value="strategies" className="flex-1 mt-0">
                 <SessionStrategyManager
                    sessionId={sessionId}
                    sessionStatus={sessionStatus}
                  />
              </TabsContent>
            </Tabs>
          </div>
        </div>
      )}
    </div>
  )
}
