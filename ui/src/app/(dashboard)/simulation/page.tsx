"use client"

import { useSearchParams } from "next/navigation"
import { HistoricalRunShell } from "@/components/historical-run/historical-run-shell"

export default function SimulationPage() {
  const searchParams = useSearchParams()
  const execution = searchParams.get("execution")
  const source = searchParams.get("source")
  const strategyId = searchParams.get("strategyId") || ""
  const replayBacktestId = searchParams.get("replayBacktestId") || ""
  const replaySource = (searchParams.get("replaySource") as any) || "backtest"

  const initialExecutionMode = execution === "batch" ? "batch" : "visualized"
  const initialSource =
    source === "strategy" || source === "replay" ? source : "manual"

  return (
    <HistoricalRunShell
      title="Simulation"
      description="Run manual, strategy, replay, and batch simulation workflows from one page."
      initialExecutionMode={initialExecutionMode}
      initialSource={initialSource}
      initialStrategyId={strategyId}
      initialReplayBacktestId={replayBacktestId}
      initialReplaySource={replaySource}
    />
  )
}
