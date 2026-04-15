"use client"

import * as React from "react"
import { RefreshCcw } from "lucide-react"
import { toast } from "sonner"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"

const lifecycleStates = [
  "RESEARCH",
  "BACKTEST_QUALIFIED",
  "ROBUSTNESS_QUALIFIED",
  "PAPER_APPROVED",
  "LIVE_LIMITED",
  "LIVE_PRODUCTION",
  "SUSPENDED",
  "RETIRED",
] as const

type LifecycleState = (typeof lifecycleStates)[number]

interface OperatorStrategy {
  strategy_id: number
  user_id: number
  name: string
  status: string
  category?: string | null
  active_version?: string | null
  governance_strategy_id: string
  lifecycle_state?: LifecycleState | string | null
  strategy_family?: string | null
  code_hash?: string | null
  parameter_hash?: string | null
  artifact_root?: string | null
  updated_at: string
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  })
  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || `Request failed with ${response.status}`)
  }
  return response.json() as Promise<T>
}

function shortHash(value?: string | null): string {
  return value ? value.slice(0, 10) : "missing"
}

export function OperatorStrategyLifecycleView() {
  const [strategies, setStrategies] = React.useState<OperatorStrategy[]>([])
  const [loading, setLoading] = React.useState(true)
  const [updating, setUpdating] = React.useState<string | null>(null)

  const loadStrategies = React.useCallback(async () => {
    setLoading(true)
    try {
      const result = await requestJson<OperatorStrategy[]>("/api/operator/strategies")
      setStrategies(result)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to load strategy lifecycle data")
    } finally {
      setLoading(false)
    }
  }, [])

  React.useEffect(() => {
    void loadStrategies()
  }, [loadStrategies])

  const updateLifecycle = async (strategy: OperatorStrategy, lifecycle_state: LifecycleState) => {
    setUpdating(strategy.governance_strategy_id)
    try {
      const updated = await requestJson<OperatorStrategy>(
        `/api/operator/strategies/${encodeURIComponent(strategy.governance_strategy_id)}/lifecycle`,
        {
          method: "POST",
          body: JSON.stringify({ lifecycle_state }),
        },
      )
      setStrategies((current) =>
        current.map((item) => (item.governance_strategy_id === updated.governance_strategy_id ? updated : item)),
      )
      toast.success("Lifecycle updated")
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Lifecycle transition failed")
    } finally {
      setUpdating(null)
    }
  }

  return (
    <div className="space-y-6">
      <Card className="border-slate-200/70 shadow-sm">
        <CardHeader className="flex flex-row items-start justify-between gap-4 space-y-0">
          <div>
            <CardTitle>Strategy Lifecycle Control</CardTitle>
            <CardDescription>
              Govern strategy promotion state separately from the operational active or inactive flag.
            </CardDescription>
          </div>
          <Button variant="outline" size="sm" onClick={() => void loadStrategies()} disabled={loading}>
            <RefreshCcw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Strategy</TableHead>
                <TableHead>Family</TableHead>
                <TableHead>Operational</TableHead>
                <TableHead>Lifecycle</TableHead>
                <TableHead>Hashes</TableHead>
                <TableHead>Promote</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {strategies.map((strategy) => (
                <TableRow key={strategy.governance_strategy_id}>
                  <TableCell>
                    <div className="font-medium text-slate-900">{strategy.name}</div>
                    <div className="text-xs text-muted-foreground">{strategy.governance_strategy_id}</div>
                  </TableCell>
                  <TableCell>{strategy.strategy_family || strategy.category || "custom"}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{strategy.status}</Badge>
                    <div className="mt-1 text-xs text-muted-foreground">v{strategy.active_version || "none"}</div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary">{strategy.lifecycle_state || "UNREGISTERED"}</Badge>
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    <div>code {shortHash(strategy.code_hash)}</div>
                    <div>params {shortHash(strategy.parameter_hash)}</div>
                  </TableCell>
                  <TableCell>
                    <Select
                      value={String(strategy.lifecycle_state || "")}
                      onValueChange={(value) => updateLifecycle(strategy, value as LifecycleState)}
                      disabled={!strategy.lifecycle_state || updating === strategy.governance_strategy_id}
                    >
                      <SelectTrigger className="w-[210px]">
                        <SelectValue placeholder="Select lifecycle" />
                      </SelectTrigger>
                      <SelectContent>
                        {lifecycleStates.map((state) => (
                          <SelectItem key={state} value={state}>
                            {state}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </TableCell>
                </TableRow>
              ))}
              {!loading && strategies.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="py-8 text-center text-sm text-muted-foreground">
                    No strategies are registered yet.
                  </TableCell>
                </TableRow>
              ) : null}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}

