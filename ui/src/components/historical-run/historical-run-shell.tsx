"use client"
import { useRouter } from "next/navigation"
import { useState } from "react"
import { toast } from "sonner"
import { BacktestExecutionView } from "@/components/backtest/execution-view"
import { HistoricalRunForm } from "@/components/historical-run/historical-run-form"
import type { AccountMetrics } from "@/components/simulation/account-metrics"
import { SimulationExecutionView } from "@/components/simulation/execution-view"
import { SimulationResultsView } from "@/components/simulation/results-view"
import { Button } from "@/components/ui/button"
import {
  historicalRunConfigToSimulationPayload,
  type HistoricalRunConfig,
} from "@/lib/historical-run"
import type { SimulationStartResponse } from "@/lib/api/simulator"

type ViewState = "config" | "execution" | "results"

type SimulationTrade = {
  time?: string
  symbol?: string
  side?: string
  price?: number
  volume?: number
  pnl?: number
}

interface HistoricalRunShellProps {
  title: string
  description: string
  initialExecutionMode?: "visualized" | "batch"
  initialSource?: "manual" | "strategy" | "replay"
  initialStrategyId?: string
}

export function HistoricalRunShell({
  title,
  description,
  initialExecutionMode = "visualized",
  initialSource = "manual",
  initialStrategyId = "",
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

  const handleSimulationStart = (
    id: number,
    config: HistoricalRunConfig,
    response?: SimulationStartResponse
  ) => {
    setActiveExecutionMode("visualized")
    setSessionId(id)
    setSessionConfig(config)
    setSessionResponse(response || null)
    setTotalBars(response?.total_bars || config.range.numberOfBars || 500)
    setSymbolDigits(response?.symbol_digits || 5)
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
    setView("config")
    resetVisualizedState()
    resetBatchState()
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{title}</h1>
          <p className="text-muted-foreground">{description}</p>
        </div>
        <Button variant="outline" onClick={() => router.push("/simulation")}>
          New Run
        </Button>
      </div>

      {view === "config" && (
        <HistoricalRunForm
          initialExecutionMode={initialExecutionMode}
          initialSource={initialSource}
          initialStrategyId={initialStrategyId}
          onSimulationStart={handleSimulationStart}
          onSimulationResume={handleSimulationResume}
          onBacktestStart={(backtestIdValue, strategyIdValue, _config) =>
            handleBacktestStart(backtestIdValue, strategyIdValue)
          }
        />
      )}

      {view === "execution" && activeExecutionMode === "visualized" && sessionId && (
        <SimulationExecutionView
          sessionId={sessionId}
          config={sessionConfig ? historicalRunConfigToSimulationPayload(sessionConfig) : null}
          sessionResponse={sessionResponse}
          totalBars={totalBars}
          symbolDigits={symbolDigits}
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
