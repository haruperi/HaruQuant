"use client"

import { useState } from "react"
import { toast } from "sonner"
import { ChevronDown } from "lucide-react"
import { SimulationConfigForm } from "@/components/simulation/config-form"
import { RiskAllocationPanel } from "@/components/simulation/risk-allocation"
import { SimulationExecutionView } from "@/components/simulation/execution-view"
import { RiskGovernorPanel } from "@/components/simulation/risk-governor"
import { RiskRegimeDetectionPanel } from "@/components/simulation/risk-regime-detection"
import { RiskPositionSizingPanel } from "@/components/simulation/risk-position-sizing"
import { SimulationResultsView } from "@/components/simulation/results-view"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import type { AccountMetrics } from "@/components/simulation/account-metrics"
import type { SimulationConfig, SimulationStartResponse } from "@/lib/api/simulator"

type ViewState = "config" | "execution" | "results"
type ToolView =
  | "simulator"
  | "risk-position-sizing"
  | "risk-regime-detection"
  | "risk-allocation"
  | "risk-governor"
type SimulationTrade = {
  time?: string
  symbol?: string
  side?: string
  price?: number
  volume?: number
  pnl?: number
}

export default function SimulationPage() {
  const [view, setView] = useState<ViewState>("config")
  const [toolView, setToolView] = useState<ToolView>("simulator")
  const [sessionId, setSessionId] = useState<number | null>(null)
  const [sessionConfig, setSessionConfig] = useState<SimulationConfig | null>(null)
  const [totalBars, setTotalBars] = useState<number>(0)
  const [symbolDigits, setSymbolDigits] = useState<number>(5)
  const [trades, setTrades] = useState<SimulationTrade[]>([])
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

      <div className="flex items-center gap-3">
        <Button
          variant={toolView === "simulator" ? "default" : "outline"}
          onClick={() => setToolView("simulator")}
        >
          Simulator
        </Button>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant={toolView === "risk-position-sizing" ? "default" : "outline"}>
              Risk
              <ChevronDown className="size-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start">
            <DropdownMenuItem onSelect={() => setToolView("risk-position-sizing")}>
              Position Sizing
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={() => setToolView("risk-regime-detection")}>
              Regime Detection
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={() => setToolView("risk-allocation")}>
              Risk Allocation
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={() => setToolView("risk-governor")}>
              Risk Governor
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {toolView === "simulator" && view === "config" && (
        <SimulationConfigForm onStart={handleStart} onResume={handleResume} />
      )}

      {toolView === "simulator" && view === "execution" && sessionId && (
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

      {toolView === "simulator" && view === "results" && sessionId && (
        <SimulationResultsView
          sessionId={sessionId}
          trades={trades}
          finalAccount={finalAccount}
          onBack={handleBackToConfig}
        />
      )}

      {toolView === "risk-position-sizing" && <RiskPositionSizingPanel />}
      {toolView === "risk-regime-detection" && <RiskRegimeDetectionPanel />}
      {toolView === "risk-allocation" && <RiskAllocationPanel />}
      {toolView === "risk-governor" && <RiskGovernorPanel />}
    </div>
  )
}
