"use client"

import { useEffect, useMemo, useState } from "react"
import { useRouter } from "next/navigation"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import simulatorApi, { type SimulationSession } from "@/lib/api/simulator"
import type { AccountMetrics } from "@/components/simulation/account-metrics"

interface SimulationTrade {
  time?: string
  symbol?: string
  side?: string
  price?: number
  volume?: number
  pnl?: number
}

interface SimulationResultsViewProps {
  sessionId: number
  trades: SimulationTrade[]
  finalAccount?: AccountMetrics | null
  onBack: () => void
}

export function SimulationResultsView({
  sessionId,
  trades,
  finalAccount,
  onBack,
}: SimulationResultsViewProps) {
  const router = useRouter()
  const [session, setSession] = useState<SimulationSession | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [savedBacktestId, setSavedBacktestId] = useState<number | null>(null)

  useEffect(() => {
    const fetchSession = async () => {
      try {
        setLoading(true)
        const data = await simulatorApi.getSession(sessionId)
        setSession(data)
      } catch (error) {
        toast.error("Failed to load simulation results")
      } finally {
        setLoading(false)
      }
    }

    fetchSession()
  }, [sessionId])

  const handleSaveAsBacktest = async () => {
    try {
      setSaving(true)
      const result = await simulatorApi.stopAndSaveSession(sessionId)
      setSavedBacktestId(result.backtest_id)
      toast.success("Simulation saved as backtest", {
        description: `Backtest ${result.backtest_id}`,
      })
    } catch (error) {
      toast.error("Failed to save simulation", {
        description: error instanceof Error ? error.message : "An error occurred",
      })
    } finally {
      setSaving(false)
    }
  }

  const metrics = useMemo(() => {
    const totalTrades = trades.length
    const winningTrades = trades.filter((trade) => (trade.pnl ?? 0) > 0).length
    const losingTrades = trades.filter((trade) => (trade.pnl ?? 0) < 0).length
    const winRate =
      totalTrades > 0 ? (winningTrades / totalTrades) * 100 : null
    const grossProfit = trades.reduce((acc, trade) => {
      const pnl = trade.pnl ?? 0
      return pnl > 0 ? acc + pnl : acc
    }, 0)
    const grossLoss = trades.reduce((acc, trade) => {
      const pnl = trade.pnl ?? 0
      return pnl < 0 ? acc + Math.abs(pnl) : acc
    }, 0)
    const profitFactor =
      grossLoss > 0 ? grossProfit / grossLoss : null

    return {
      totalTrades,
      winRate,
      profitFactor,
    }
  }, [trades])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[300px] text-muted-foreground">
        Loading simulation results...
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold">Simulation Results</h2>
          <p className="text-sm text-muted-foreground">
            Session {sessionId} {session?.symbol ? `- ${session.symbol}` : ""}
          </p>
          <p className="text-xs text-muted-foreground">
            Visualized runs can be saved as completed backtests for the same downstream reporting flow used by batch runs.
          </p>
        </div>
        <div className="flex gap-2">
          {savedBacktestId ? (
            <Button
              variant="outline"
              onClick={() => router.push(`/performance?selected=${savedBacktestId}`)}
            >
              Open Saved Backtest Report
            </Button>
          ) : (
            <Button
              variant="outline"
              onClick={handleSaveAsBacktest}
              disabled={saving}
            >
              {saving ? "Saving..." : "Save As Backtest"}
            </Button>
          )}
          <Button onClick={onBack}>New Simulation</Button>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs text-muted-foreground">Final Balance</CardTitle>
          </CardHeader>
          <CardContent className="text-lg font-semibold">
            {finalAccount?.balance !== undefined
              ? finalAccount.balance.toFixed(2)
              : session?.initial_balance?.toFixed(2) || "--"}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs text-muted-foreground">Total Trades</CardTitle>
          </CardHeader>
          <CardContent className="text-lg font-semibold">
            {metrics.totalTrades}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs text-muted-foreground">Win Rate</CardTitle>
          </CardHeader>
          <CardContent className="text-lg font-semibold">
            {metrics.winRate === null ? "--" : `${metrics.winRate.toFixed(1)}%`}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs text-muted-foreground">Profit Factor</CardTitle>
          </CardHeader>
          <CardContent className="text-lg font-semibold">
            {metrics.profitFactor === null ? "--" : metrics.profitFactor.toFixed(2)}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Trades History</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Time</TableHead>
                <TableHead>Symbol</TableHead>
                <TableHead>Side</TableHead>
                <TableHead>Price</TableHead>
                <TableHead>Volume</TableHead>
                <TableHead>P&amp;L</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {trades.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-muted-foreground">
                    No trades recorded for this simulation.
                  </TableCell>
                </TableRow>
              ) : (
                trades.map((trade, index) => (
                  <TableRow key={`${trade.time || "trade"}-${index}`}>
                    <TableCell>{trade.time || "--"}</TableCell>
                    <TableCell>{trade.symbol || "--"}</TableCell>
                    <TableCell>{trade.side ? trade.side.toUpperCase() : "--"}</TableCell>
                    <TableCell>
                      {trade.price !== undefined ? trade.price.toFixed(5) : "--"}
                    </TableCell>
                    <TableCell>{trade.volume ?? "--"}</TableCell>
                    <TableCell className={(trade.pnl ?? 0) >= 0 ? "text-emerald-500" : "text-red-500"}>
                      {trade.pnl !== undefined ? trade.pnl.toFixed(2) : "--"}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
