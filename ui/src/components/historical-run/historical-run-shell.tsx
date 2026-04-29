"use client"
import { usePathname, useRouter } from "next/navigation"
import { useEffect, useState } from "react"
import { toast } from "sonner"
import { BacktestExecutionView } from "@/components/backtest/execution-view"
import { HistoricalRunForm } from "@/components/historical-run/historical-run-form"
import type { AccountMetrics } from "@/components/simulation/account-metrics"
import { SimulationExecutionView } from "@/components/simulation/execution-view"
import { SimulationResultsView } from "@/components/simulation/results-view"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  historicalRunConfigToSimulationPayload,
  type HistoricalRunConfig,
} from "@/lib/historical-run"
import simulatorApi, { type SimulationStartResponse } from "@/lib/api/simulator"

type ViewState = "config" | "execution" | "results"

type SimulationTrade = {
  time?: string
  symbol?: string
  side?: string
  price?: number
  volume?: number
  pnl?: number
}

export type SimulationTab = "visual_auto" | "batch_auto" | "manual" | "replay"

const simulationTabPaths: Record<SimulationTab, string> = {
  visual_auto: "/simulation/visual-auto",
  batch_auto: "/simulation/batch-auto",
  manual: "/simulation/manual",
  replay: "/simulation/replay",
}

interface HistoricalRunShellProps {
  title: string
  description: string
  initialExecutionMode?: "visualized" | "batch"
  initialSource?: "manual" | "strategy" | "replay"
  initialStrategyId?: string
  initialReplayBacktestId?: string
  initialReplayTradeId?: string
  initialReplayTradeTime?: string
  initialReplaySource?: "backtest" | "csv"
  initialAutoStartReplay?: boolean
}

export function HistoricalRunShell({
  title,
  description,
  initialExecutionMode = "visualized",
  initialSource = "manual",
  initialStrategyId = "",
  initialReplayBacktestId = "",
  initialReplayTradeId = "",
  initialReplayTradeTime = "",
  initialReplaySource = "backtest",
  initialAutoStartReplay = false,
}: HistoricalRunShellProps) {
  const router = useRouter()
  const [view, setView] = useState<ViewState>("config")
  const [sessionId, setSessionId] = useState<number | null>(null)
  const [sessionConfig, setSessionConfig] = useState<HistoricalRunConfig | null>(null)
  const [sessionResponse, setSessionResponse] = useState<SimulationStartResponse | null>(null)
  const [totalBars, setTotalBars] = useState<number>(0)
  const [symbolDigits, setSymbolDigits] = useState<number>(5)
  const [trades, setTrades] = useState<SimulationTrade[]>([])
  const [finalAccount, setFinalAccount] = useState<AccountMetrics | null>(null)
  const [backtestId, setBacktestId] = useState<number | null>(null)
  const [strategyId, setStrategyId] = useState<number | null>(null)
  const [activeExecutionMode, setActiveExecutionMode] = useState<"visualized" | "batch">(
    initialExecutionMode
  )

  const [activeTab, setActiveTab] = useState<SimulationTab>(() => {
    if (initialSource === "manual") return "manual"
    if (initialSource === "replay") return "replay"
    if (initialSource === "strategy") {
      return initialExecutionMode === "batch" ? "batch_auto" : "visual_auto"
    }
    return "visual_auto"
  })

  const pathname = usePathname()

  const resetVisualizedState = () => {
    setSessionId(null)
    setSessionConfig(null)
    setSessionResponse(null)
    setTotalBars(0)
    setSymbolDigits(5)
    setTrades([])
    setFinalAccount(null)
  }

  const resetBatchState = () => {
    setBacktestId(null)
    setStrategyId(null)
  }

  const handleSimulationStart = async (
    id: number,
    config: HistoricalRunConfig,
    response?: SimulationStartResponse
  ) => {
    let effectiveResponse = response || null
    try {
      const persistedSession = await simulatorApi.getSession(id)
      if (persistedSession.config) {
        effectiveResponse = {
          ...(response || {
            session_id: id,
            status: persistedSession.status,
            total_bars: persistedSession.total_bars,
            symbol_digits: symbolDigits,
          }),
          config: persistedSession.config,
        }
      }
    } catch {
      effectiveResponse = response || null
    }

    setActiveExecutionMode("visualized")
    setSessionId(id)
    setSessionConfig(config)
    setSessionResponse(effectiveResponse)
    setTotalBars(effectiveResponse?.total_bars || config.range.numberOfBars || 500)
    setSymbolDigits(effectiveResponse?.symbol_digits || 5)
    setTrades([])
    setFinalAccount(null)
    setView("execution")
  }

  const handleSimulationResume = (id: number) => {
    setActiveExecutionMode("visualized")
    setSessionId(id)
    setSessionConfig(null)
    setSessionResponse(null)
    setTotalBars(0)
    setTrades([])
    setFinalAccount(null)
    setView("execution")
  }

  const handleSimulationComplete = () => {
    toast.success("Simulation completed.")
    setView("results")
  }

  const handleBacktestStart = (btId: number, stId: number) => {
    setActiveExecutionMode("batch")
    setBacktestId(btId)
    setStrategyId(stId)
    setView("execution")
  }

  const handleBacktestCancel = () => {
    setView("config")
    resetBatchState()
    toast.info("Backtest aborted.")
  }

  const handleBacktestComplete = () => {
    if (backtestId) {
      toast.success("Backtest execution finished.")
      router.push(`/performance?selected=${backtestId}`)
    }
  }

  const handleBackToConfig = () => {
    const targetPath = simulationTabPaths[activeTab]
    
    // If we are on a specific sub-route (like a specific backtest replay), 
    // just redirect to the base tab. The remount will handle starting in config view.
    if (pathname !== targetPath) {
      router.push(targetPath)
      return
    }

    // Otherwise we are on the base page, just switch the view back to config.
    setView("config")
    resetVisualizedState()
    resetBatchState()
    // Ensure URL is clean
    router.replace(targetPath)
  }

  const handleTabChange = (value: string) => {
    const nextTab = value as SimulationTab
    setActiveTab(nextTab)
    router.push(simulationTabPaths[nextTab])
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{title}</h1>
          <p className="text-muted-foreground">{description}</p>
        </div>
        <Button variant="outline" onClick={() => router.push("/simulation/visual-auto")}>
          New Run
        </Button>
      </div>

      {view === "config" && (
        <Tabs value={activeTab} onValueChange={handleTabChange} className="w-full">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="visual_auto">Visual Auto</TabsTrigger>
            <TabsTrigger value="batch_auto">Batch Auto</TabsTrigger>
            <TabsTrigger value="manual">Manual</TabsTrigger>
            <TabsTrigger value="replay">Replay</TabsTrigger>
          </TabsList>

          <div className="mt-6">
            <HistoricalRunForm
              variant={activeTab}
              initialStrategyId={initialStrategyId}
              initialReplayBacktestId={initialReplayBacktestId}
              initialReplaySource={initialReplaySource}
              initialAutoStartReplay={initialAutoStartReplay}
              onSimulationStart={handleSimulationStart}
              onSimulationResume={handleSimulationResume}
              onBacktestStart={(backtestIdValue, strategyIdValue, _config) =>
                handleBacktestStart(backtestIdValue, strategyIdValue)
              }
            />
          </div>
        </Tabs>
      )}

      {view === "execution" && activeExecutionMode === "visualized" && sessionId && (
        <SimulationExecutionView
          sessionId={sessionId}
          config={
            sessionResponse?.config ??
            (sessionConfig ? historicalRunConfigToSimulationPayload(sessionConfig) : null)
          }
          sessionResponse={sessionResponse}
          totalBars={totalBars}
          symbolDigits={symbolDigits}
          initialReplayTradeId={initialReplayTradeId}
          initialReplayTradeTime={initialReplayTradeTime}
          onComplete={handleSimulationComplete}
          onStop={handleBackToConfig}
          onTradesUpdate={setTrades}
          onFinalAccount={setFinalAccount}
        />
      )}

      {view === "execution" && activeExecutionMode === "batch" && backtestId && strategyId && (
        <BacktestExecutionView
          backtestId={backtestId}
          strategyId={strategyId}
          onCancel={handleBacktestCancel}
          onComplete={handleBacktestComplete}
        />
      )}

      {view === "results" && activeExecutionMode === "visualized" && sessionId && (
        <SimulationResultsView
          sessionId={sessionId}
          trades={trades}
          finalAccount={finalAccount}
          onBack={handleBackToConfig}
        />
      )}
    </div>
  )
}
