"use client"

import { useEffect } from "react"
import { usePathname, useRouter, useSearchParams } from "next/navigation"
import { HistoricalRunShell } from "@/components/historical-run/historical-run-shell"

type SimulationRouteTab = "visual_auto" | "batch_auto" | "manual" | "replay"

interface SimulationPageProps {
  initialTab?: SimulationRouteTab
  replayBacktestId?: string
  replayTradeId?: string
  replayTradeTime?: string
  autoStartReplay?: boolean
}

export function SimulationPage({
  initialTab,
  replayBacktestId: routeReplayBacktestId = "",
  replayTradeId: routeReplayTradeId = "",
  replayTradeTime: routeReplayTradeTime = "",
  autoStartReplay: routeAutoStartReplay = false,
}: SimulationPageProps) {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const execution = searchParams.get("execution")
  const source = searchParams.get("source")
  const strategyId = searchParams.get("strategyId") || ""
  const replayBacktestId = routeReplayBacktestId || searchParams.get("replayBacktestId") || ""
  const replayTradeId = routeReplayTradeId || searchParams.get("replayTradeId") || ""
  const replayTradeTime = routeReplayTradeTime || searchParams.get("replayTradeTime") || ""
  const replaySource = searchParams.get("replaySource") === "csv" ? "csv" : "backtest"
  const autoStartReplay = routeAutoStartReplay || searchParams.get("autoStartReplay") === "1"

  useEffect(() => {
    if (pathname !== "/simulation" || !searchParams.toString()) {
      return
    }

    const params = new URLSearchParams()
    const selectedStrategyId = searchParams.get("strategyId")
    if (selectedStrategyId) {
      params.set("strategyId", selectedStrategyId)
    }

    let targetPath = "/simulation/visual-auto"
    if (source === "manual") {
      targetPath = "/simulation/manual"
    } else if (execution === "batch") {
      targetPath = "/simulation/batch-auto"
    } else if (source === "replay") {
      targetPath = replayBacktestId
        ? `/simulation/replay/backtest/${replayBacktestId}`
        : "/simulation/replay"
      if (replayBacktestId && replayTradeId) {
        targetPath = `${targetPath}/trade/${encodeURIComponent(replayTradeId)}`
      }
      if (replayTradeTime) {
        params.set("replayTradeTime", replayTradeTime)
      }
      if (searchParams.get("replaySource") === "csv") {
        params.set("replaySource", "csv")
      }
    }

    const query = params.toString()
    router.replace(query ? `${targetPath}?${query}` : targetPath)
  }, [
    execution,
    pathname,
    replayBacktestId,
    replayTradeId,
    replayTradeTime,
    router,
    searchParams,
    source,
  ])

  const initialExecutionMode =
    initialTab === "batch_auto" || execution === "batch" ? "batch" : "visualized"
  const initialSource =
    initialTab === "manual"
      ? "manual"
      : initialTab === "visual_auto" || initialTab === "batch_auto"
        ? "strategy"
        : initialTab === "replay" || source === "replay"
          ? "replay"
          : source === "strategy"
            ? "strategy"
            : source === "manual"
              ? "manual"
              : "manual"

  return (
    <HistoricalRunShell
      title="Simulation"
      description="Run manual, strategy, replay, and batch simulation workflows from one page."
      initialExecutionMode={initialExecutionMode}
      initialSource={initialSource}
      initialStrategyId={strategyId}
      initialReplayBacktestId={replayBacktestId}
      initialReplayTradeId={replayTradeId}
      initialReplayTradeTime={replayTradeTime}
      initialReplaySource={replaySource}
      initialAutoStartReplay={autoStartReplay}
    />
  )
}
