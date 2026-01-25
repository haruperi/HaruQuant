"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Checkbox } from "@/components/ui/checkbox"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { toast } from "sonner"
import { Loader2, Upload, Activity } from "lucide-react"

export default function SQXImportPage() {
  const [file, setFile] = useState<File | null>(null)
  const [stage, setStage] = useState("CORE")
  const [importName, setImportName] = useState("")
  const [purgeMissing, setPurgeMissing] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [isLoadingScores, setIsLoadingScores] = useState(false)
  const [scoreRows, setScoreRows] = useState<any[]>([])
  const [page, setPage] = useState(1)
  const [pageSize] = useState(50)
  const [totalRows, setTotalRows] = useState(0)
  const [sortBy, setSortBy] = useState("final_score")
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc")

  const loadScores = async (nextPage: number = page, nextSortBy: string = sortBy, nextSortDir: "asc" | "desc" = sortDir) => {
    setIsLoadingScores(true)
    try {
      const offset = (nextPage - 1) * pageSize
      const params = new URLSearchParams({
        limit: String(pageSize),
        offset: String(offset),
        sort_by: nextSortBy,
        sort_dir: nextSortDir,
      })
      const response = await fetch(`http://localhost:8000/api/sqx/strategies?${params.toString()}`)
      if (!response.ok) {
        const err = await response.json()
        throw new Error(err.detail || "Failed to load scores")
      }
      const data = await response.json()
      setScoreRows(Array.isArray(data.rows) ? data.rows : [])
      setTotalRows(Number.isFinite(Number(data.total)) ? Number(data.total) : 0)
      setPage(nextPage)
      setSortBy(nextSortBy)
      setSortDir(nextSortDir)
    } catch (e: any) {
      toast.error(e.message || "Failed to load scores")
    } finally {
      setIsLoadingScores(false)
    }
  }

  const formatNum = (value: any, digits: number = 2) => {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
      return "-"
    }
    return Number(value).toFixed(digits)
  }

  const stagePrefix = (stageValue: any) => {
    if (stageValue === "A1_OOS2") return "a1"
    if (stageValue === "A2_OOS3") return "a2"
    if (stageValue === "E1_WFM") return "e1"
    return ""
  }

  const stageValue = (row: any, key: string) => {
    const prefix = stagePrefix(row.stage)
    if (prefix) {
      const prefixed = row[`${prefix}_${key}`]
      if (prefixed !== null && prefixed !== undefined) {
        return prefixed
      }
    }
    return row[key]
  }

  const toggleSort = (col: string) => {
    if (sortBy === col) {
      const nextDir = sortDir === "asc" ? "desc" : "asc"
      loadScores(1, col, nextDir)
    } else {
      loadScores(1, col, "desc")
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
      if (!importName) {
        setImportName(e.target.files[0].name)
      }
    }
  }

  const handleUpload = async () => {
    if (!file) {
      toast.error("Please select a file")
      return
    }

    setIsLoading(true)
    const formData = new FormData()
    formData.append("file", file)
    formData.append("stage", stage)
    formData.append("import_name", importName)
    formData.append("purge_missing", String(purgeMissing))

    try {
      // Assuming API client is configured to proxy /api to backend
      // But here we use fetch directly or use a properly configured api client
      // Let's us fetch for simplicity, adjusting URL if needed (usually /api/...)
      const response = await fetch("http://localhost:8000/api/sqx/import", {
        method: "POST",
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || "Upload failed")
      }

      const data = await response.json()
      toast.success(data.message)
      if (Array.isArray(data.missing_columns) && data.missing_columns.length > 0) {
        toast.warning(`Missing required columns: ${data.missing_columns.join(", ")}`)
      }

      // Reset logic if needed
    } catch (error: any) {
        console.error(error)
      toast.error(error.message || "Failed to upload")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="container py-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">SQX Import</h1>
          <p className="text-muted-foreground">Import strategies from StrategyQuant X CSV exports.</p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Import Configuration</CardTitle>
          <CardDescription>Upload CSV and configure import settings.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">

          <div className="grid w-full max-w-sm items-center gap-1.5">
            <Label htmlFor="file">CSV File</Label>
            <Input id="file" type="file" accept=".csv" onChange={handleFileChange} />
          </div>

          <div className="grid w-full max-w-sm items-center gap-1.5">
            <Label htmlFor="importName">Import Name (Label)</Label>
            <Input
                id="importName"
                value={importName}
                onChange={(e) => setImportName(e.target.value)}
                placeholder="My Import 1"
            />
          </div>

          <div className="grid w-full max-w-sm items-center gap-1.5">
            <Label htmlFor="stage">Stage</Label>
             <Select value={stage} onValueChange={setStage}>
              <SelectTrigger>
                <SelectValue placeholder="Select stage" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="0_DEV">0 Development</SelectItem>
                <SelectItem value="A1_OOS2">A1 Second OOS</SelectItem>
                <SelectItem value="A2_OOS3">A2 Third OOS</SelectItem>
                <SelectItem value="B1_SPREAD">B1 Spread</SelectItem>
                <SelectItem value="B2_SPREAD_MAX">B2 Spread (Max)</SelectItem>
                <SelectItem value="B3_SLIP">B3 Slippage</SelectItem>
                <SelectItem value="B4_DELAY">B4 Delay</SelectItem>
                <SelectItem value="C1_MC_EXACT">C1 MC Exact</SelectItem>
                <SelectItem value="C2_MC_RESAMP">C2 MC Resampling</SelectItem>
                <SelectItem value="C3_MC_SKIP">C3 MC Skip</SelectItem>
                <SelectItem value="C4_MC_PARAM">C4 MC Params</SelectItem>
                <SelectItem value="C5_MC_HIST">C5 MC History</SelectItem>
                <SelectItem value="C6_MC_ALL">C6 MC Overall</SelectItem>
                <SelectItem value="C7_MAE_MFE">C7 MAE/MFE</SelectItem>
                <SelectItem value="D1_MARKET">D1 Market</SelectItem>
                <SelectItem value="D2_TF">D2 Timeframe</SelectItem>
                <SelectItem value="E1_WFM">E1 WFM</SelectItem>
                <SelectItem value="E2_WFO">E2 WFO</SelectItem>
                <SelectItem value="E3_WFM_WFO">E3 WFM-on-WFO</SelectItem>
                <SelectItem value="F1_FINAL">F1 Final Test</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center space-x-2">
            <Checkbox
                id="purge"
                checked={purgeMissing}
                onCheckedChange={(c) => setPurgeMissing(!!c)}
            />
            <Label htmlFor="purge">Purge Missing (Delete strategies not in this file for these symbols)</Label>
          </div>

          <Button onClick={handleUpload} disabled={isLoading} className="w-full max-w-sm">
            {isLoading ? (
                <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Importing...
                </>
            ) : (
                <>
                    <Upload className="mr-2 h-4 w-4" />
                    Import Strategies
                </>
            )}
          </Button>

        </CardContent>
      </Card>

      <Card>
        <CardHeader>
            <CardTitle>Strategy Scorecard</CardTitle>
            <CardDescription>Compute final scores (0-100) for all imported strategies.</CardDescription>
        </CardHeader>
        <CardContent>
             <Button onClick={async () => {
                setIsLoading(true)
                try {
                    const formData = new FormData()
                    // Optional: append symbol if we want filtering
                    const response = await fetch("http://localhost:8000/api/sqx/calculate-scores", {
                        method: "POST",
                        body: formData
                    })
                    if (!response.ok) {
                        const err = await response.json()
                        throw new Error(err.detail || "Scoring failed")
                    }
                    const data = await response.json()
                    toast.success(data.message)
                    await loadScores()
                } catch(e: any) {
                    toast.error(e.message || "Scoring failed")
                } finally {
                    setIsLoading(false)
                }
             }} disabled={isLoading} variant="secondary" className="w-full max-w-sm">
                {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Activity className="mr-2 h-4 w-4" />}
                Run Scorecard
            </Button>
            <div className="mt-4">
              <Button
                onClick={() => loadScores(1)}
                disabled={isLoadingScores}
                variant="outline"
                className="w-full max-w-sm"
              >
                {isLoadingScores ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Activity className="mr-2 h-4 w-4" />}
                Load Scores
              </Button>
            </div>
            <div className="mt-4 overflow-x-auto rounded-md border">
              <table className="w-full text-sm">
                <thead className="bg-muted/50">
                  <tr className="text-left">
                    <th className="px-3 py-2">
                      <button className="underline-offset-2 hover:underline" onClick={() => toggleSort("stage")}>Test Name</button>
                    </th>
                    <th className="px-3 py-2">
                      <button className="underline-offset-2 hover:underline" onClick={() => toggleSort("strategy_name")}>Strategy Name</button>
                    </th>
                    <th className="px-3 py-2">
                      <button className="underline-offset-2 hover:underline" onClick={() => toggleSort("symbol")}>Symbol</button>
                    </th>
                    <th className="px-3 py-2">
                      <button className="underline-offset-2 hover:underline" onClick={() => toggleSort("profit_factor")}>PF</button>
                    </th>
                    <th className="px-3 py-2">
                      <button className="underline-offset-2 hover:underline" onClick={() => toggleSort("ret_dd_ratio")}>Ret/DD</button>
                    </th>
                    <th className="px-3 py-2">
                      <button className="underline-offset-2 hover:underline" onClick={() => toggleSort("annual_return_pct")}>Ann %</button>
                    </th>
                    <th className="px-3 py-2">
                      <button className="underline-offset-2 hover:underline" onClick={() => toggleSort("trades")}>Trades</button>
                    </th>
                    <th className="px-3 py-2">
                      <button className="underline-offset-2 hover:underline" onClick={() => toggleSort("net_profit")}>Net Profit</button>
                    </th>
                    <th className="px-3 py-2">
                      <button className="underline-offset-2 hover:underline" onClick={() => toggleSort("max_drawdown_pct")}>DD</button>
                    </th>
                    <th className="px-3 py-2">
                      <button className="underline-offset-2 hover:underline" onClick={() => toggleSort("edge_score")}>Edge</button>
                    </th>
                    <th className="px-3 py-2">
                      <button className="underline-offset-2 hover:underline" onClick={() => toggleSort("robust_score")}>Robust</button>
                    </th>
                    <th className="px-3 py-2">
                      <button className="underline-offset-2 hover:underline" onClick={() => toggleSort("stability_score")}>Stability</button>
                    </th>
                    <th className="px-3 py-2">
                      <button className="underline-offset-2 hover:underline" onClick={() => toggleSort("risk_score")}>Risk</button>
                    </th>
                    <th className="px-3 py-2">
                      <button className="underline-offset-2 hover:underline" onClick={() => toggleSort("simple_score")}>Simplicity</button>
                    </th>
                    <th className="px-3 py-2">
                      <button className="underline-offset-2 hover:underline" onClick={() => toggleSort("final_score")}>Final</button>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {scoreRows.length === 0 ? (
                    <tr>
                      <td colSpan={15} className="px-3 py-4 text-muted-foreground">
                        No scores loaded yet.
                      </td>
                    </tr>
                  ) : (
                    scoreRows.map((row, idx) => (
                      <tr key={`${row.strategy_name || "row"}-${row.stage || "stage"}-${idx}`} className="border-t">
                        <td className="px-3 py-2">{row.stage || "-"}</td>
                        <td className="px-3 py-2">{row.strategy_name || "-"}</td>
                        <td className="px-3 py-2">{row.symbol || "-"}</td>
                        <td className="px-3 py-2">{formatNum(stageValue(row, "profit_factor"))}</td>
                        <td className="px-3 py-2">{formatNum(stageValue(row, "ret_dd_ratio") ?? row.ret_dd)}</td>
                        <td className="px-3 py-2">{formatNum(stageValue(row, "annual_return_pct"))}</td>
                        <td className="px-3 py-2">{Number.isFinite(Number(stageValue(row, "trades"))) ? Number(stageValue(row, "trades")) : "-"}</td>
                        <td className="px-3 py-2">{formatNum(stageValue(row, "net_profit"))}</td>
                        <td className="px-3 py-2">{formatNum(stageValue(row, "max_drawdown_pct") ?? row.drawdown)}</td>
                        <td className="px-3 py-2">{formatNum(row.edge_score)}</td>
                        <td className="px-3 py-2">{formatNum(row.robust_score)}</td>
                        <td className="px-3 py-2">{formatNum(row.stability_score)}</td>
                        <td className="px-3 py-2">{formatNum(row.risk_score)}</td>
                        <td className="px-3 py-2">{formatNum(row.simple_score)}</td>
                        <td className="px-3 py-2">{formatNum(row.final_score)}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
            <div className="mt-3 flex items-center gap-2">
              <Button
                variant="outline"
                disabled={isLoadingScores || page <= 1}
                onClick={() => loadScores(page - 1)}
              >
                Prev
              </Button>
              <Button
                variant="outline"
                disabled={isLoadingScores || page * pageSize >= totalRows}
                onClick={() => loadScores(page + 1)}
              >
                Next
              </Button>
              <span className="text-xs text-muted-foreground">
                Page {page} of {Math.max(1, Math.ceil(totalRows / pageSize))}
              </span>
            </div>
        </CardContent>
      </Card>
    </div>
  )
}
