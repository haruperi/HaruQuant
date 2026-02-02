"use client"

import { useState } from "react"
import { toast } from "sonner"
import { SimulationConfigForm } from "@/components/simulation/config-form"
import { SimulationExecutionView } from "@/components/simulation/execution-view"
import { SimulationResultsView } from "@/components/simulation/results-view"
import type { AccountMetrics } from "@/components/simulation/account-metrics"
import type { SimulationConfig, SimulationStartResponse } from "@/lib/api/simulator"

type ViewState = "config" | "execution" | "results"

export default function SimulationPage() {
  const [view, setView] = useState<ViewState>("config")
  const [sessionId, setSessionId] = useState<number | null>(null)
  const [sessionConfig, setSessionConfig] = useState<SimulationConfig | null>(null)
  const [totalBars, setTotalBars] = useState<number>(0)
  const [symbolDigits, setSymbolDigits] = useState<number>(5)
  const [trades, setTrades] = useState<any[]>([])
  const [finalAccount, setFinalAccount] = useState<AccountMetrics | null>(null)

  const handleStart = (id: number, config: SimulationConfig, response?: SimulationStartResponse) => {
    setSessionId(id)
    setSessionConfig(config)
    setTotalBars(response?.total_bars || config.number_of_bars || 500)
    setSymbolDigits(response?.symbol_digits || 5)
    setTrades([])
    setFinalAccount(null)
    setView("execution")
  }

  const handleResume = (id: number) => {
    setSessionId(id)
    setSessionConfig(null)
    setTotalBars(0)
    setTrades([])
    setFinalAccount(null)
    setView("execution")
  }

  const handleBackToConfig = () => {
    setView("config")
    setSessionId(null)
    setSessionConfig(null)
    setTotalBars(0)
    setTrades([])
    setFinalAccount(null)
  }

  const handleComplete = () => {
    if (sessionId) {
      toast.success("Simulation completed.")
      setView("results")
    }
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Simulator</h1>
        <p className="text-muted-foreground">
          Configure and replay historical sessions with manual, strategy, or trade replay modes.
        </p>
      </div>

      {view === "config" && (
        <SimulationConfigForm onStart={handleStart} onResume={handleResume} />
      )}

      {view === "execution" && sessionId && (
        <SimulationExecutionView
          sessionId={sessionId}
          config={sessionConfig}
          totalBars={totalBars}
          symbolDigits={symbolDigits}
          onComplete={handleComplete}
          onStop={handleBackToConfig}
          onTradesUpdate={setTrades}
          onFinalAccount={setFinalAccount}
        />
      )}

      {view === "results" && sessionId && (
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
