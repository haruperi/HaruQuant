"use client"


import * as React from "react"
import { useSearchParams } from "next/navigation"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { MoreVertical, Loader2, CheckCircle2, Edit, Trash2 } from "lucide-react"
import { useAllBacktests } from "@/lib/use-strategies"
import { useSelectedBacktest } from "@/contexts/selected-backtest-context"
import { EditBacktestDialog } from "./edit-backtest-dialog"
import backtestApi, { Backtest } from "@/lib/api/backtest"
import { toast } from "sonner"
import { format } from "date-fns"
import { cn } from "@/lib/utils"
import { SemanticSnapshotScript } from "@/components/ai-chat/SemanticSnapshotScript"
import { useRegisterPageActions } from "@/hooks/useRegisterPageActions"

export function BacktestRunsTable() {
  const { backtests, loading, error, refetch } = useAllBacktests(100, true)
  const { selectedBacktest, selectBacktest, isSelected } = useSelectedBacktest()
  const [editDialogOpen, setEditDialogOpen] = React.useState(false)
  const [backtestToEdit, setBacktestToEdit] = React.useState<Backtest | null>(null)
  const [deleteDialogOpen, setDeleteDialogOpen] = React.useState(false)
  const [backtestToDelete, setBacktestToDelete] = React.useState<Backtest | null>(null)
  const [deleting, setDeleting] = React.useState(false)
  const searchParams = useSearchParams()
  const initialSelectionMade = React.useRef(false)

  const handleSelect = React.useCallback((backtest: Backtest) => {
    if (isSelected(backtest.backtest_id)) {
      // Deselect if already selected
      selectBacktest(null)
      toast.info("Backtest deselected")
    } else {
      // Select the backtest
      selectBacktest(backtest)
      toast.success("Backtest selected", {
        description: `${backtest.alias || backtest.strategy_name} is now active for analysis`,
      })
    }
  }, [isSelected, selectBacktest])

  useRegisterPageActions(
    React.useMemo(() => [
      {
        id: "backtests.select_first",
        label: "Select First Backtest",
        description: "Select the first visible backtest run in the backtest list.",
        riskLevel: "local_ui" as const,
        parameters: [],
      },
      {
        id: "backtests.select_by_index",
        label: "Select Backtest By Index",
        description: "Select a visible backtest run by 1-based row number from the current backtest list.",
        riskLevel: "local_ui" as const,
        parameters: [
          {
            name: "index",
            type: "number",
            description: "1-based row number in the visible backtest list.",
            required: true,
          },
        ],
      },
      {
        id: "backtests.clear_selection",
        label: "Clear Selected Backtest",
        description: "Clear the currently selected backtest.",
        riskLevel: "local_ui" as const,
        parameters: [],
      },
      {
        id: "backtests.refresh",
        label: "Refresh Backtests",
        description: "Refresh the backtest runs table.",
        riskLevel: "view_only" as const,
        parameters: [],
      },
    ], []),
    React.useMemo(() => ({
      "backtests.select_first": () => {
        const first = backtests[0]
        if (first) {
          handleSelect(first)
        }
      },
      "backtests.select_by_index": ({ index }) => {
        const numericIndex = typeof index === "number" ? index : Number(index)
        const target = Number.isFinite(numericIndex) ? backtests[Math.max(0, numericIndex - 1)] : null
        if (target) {
          handleSelect(target)
        }
      },
      "backtests.clear_selection": () => {
        selectBacktest(null)
        toast.info("Backtest selection cleared")
      },
      "backtests.refresh": () => {
        refetch()
      },
    }), [backtests, handleSelect, refetch, selectBacktest])
  )

  // Auto-select backtest from URL query param
  React.useEffect(() => {
    const selectedIdParam = searchParams.get("selected")
    if (selectedIdParam && backtests.length > 0 && !initialSelectionMade.current) {
      const backtestId = parseInt(selectedIdParam, 10)
      if (!isNaN(backtestId)) {
        const backtestToSelect = backtests.find(b => b.backtest_id === backtestId)
        if (backtestToSelect) {
          selectBacktest(backtestToSelect)
          // Optional: Scroll to the row or just let the user see it selected
          initialSelectionMade.current = true
        }
      }
    }
  }, [backtests, searchParams, selectBacktest])

  const handleEdit = (backtest: Backtest) => {
    setBacktestToEdit(backtest)
    setEditDialogOpen(true)
  }

  const handleSaveEdit = async (
    backtestId: number,
    data: { alias?: string; description?: string }
  ) => {
    try {
      await backtestApi.update(backtestId, data)
      toast.success("Backtest updated successfully")
      refetch()
    } catch (error) {
      toast.error("Failed to update backtest", {
        description: error instanceof Error ? error.message : "Please try again",
      })
      throw error
    }
  }

  const handleDeleteClick = (backtest: Backtest) => {
    setBacktestToDelete(backtest)
    setDeleteDialogOpen(true)
  }

  const handleDeleteConfirm = async () => {
    if (!backtestToDelete) return

    try {
      setDeleting(true)
      await backtestApi.delete(backtestToDelete.backtest_id)

      // If the deleted backtest was selected, deselect it
      if (isSelected(backtestToDelete.backtest_id)) {
        selectBacktest(null)
      }

      toast.success("Backtest deleted successfully", {
        description: "All associated data has been removed",
      })
      refetch()
      setDeleteDialogOpen(false)
      setBacktestToDelete(null)
    } catch (error) {
      toast.error("Failed to delete backtest", {
        description: error instanceof Error ? error.message : "Please try again",
      })
    } finally {
      setDeleting(false)
    }
  }

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-10">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-10">
          <div className="text-center">
            <p className="text-sm text-destructive">Error loading backtests</p>
            <p className="text-xs text-muted-foreground mt-1">{error}</p>
            <Button onClick={refetch} variant="outline" size="sm" className="mt-4">
              Retry
            </Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "N/A"
    try {
      return format(new Date(dateStr), "MMM dd, yyyy")
    } catch {
      return dateStr
    }
  }

  const formatDateTime = (dateStr: string | null) => {
    if (!dateStr) return "N/A"
    try {
      return format(new Date(dateStr), "MMM dd, yyyy HH:mm")
    } catch {
      return dateStr
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "completed":
        return <Badge variant="default" className="bg-emerald-500 hover:bg-emerald-600">Completed</Badge>
      case "running":
        return <Badge variant="default" className="bg-blue-500 hover:bg-blue-600">Running</Badge>
      case "pending":
        return <Badge variant="secondary">Pending</Badge>
      case "failed":
        return <Badge variant="destructive">Failed</Badge>
      default:
        return <Badge variant="outline">{status}</Badge>
    }
  }

  return (
    <>
      <Card>
        <SemanticSnapshotScript
          block={{
            id: "backtest-runs-table",
            blockType: "table",
            title: "Backtest Runs",
            summary: "Backtest run inventory with strategy, market, engine, and status columns.",
            keywords: ["backtests", "runs", "strategy", "symbol", "timeframe", "status"],
            metrics: [
              { label: "Backtest Count", value: String(backtests.length) },
              { label: "Selected Backtests", value: selectedBacktest ? "1" : "0" },
            ],
            headers: ["Alias", "Strategy", "Symbol", "Timeframe", "Date Range", "Engine", "Resolution", "# of Trades", "Created", "Status"],
            rows: backtests.slice(0, 24).map((backtest) => [
              backtest.alias || "-",
              backtest.strategy_name || "-",
              backtest.symbol || "N/A",
              backtest.timeframe || "N/A",
              backtest.start_date && backtest.end_date
                ? `${formatDate(backtest.start_date)} to ${formatDate(backtest.end_date)}`
                : "N/A",
              backtest.engine_type || "N/A",
              backtest.data_resolution || "N/A",
              backtest.total_trades !== null && backtest.total_trades !== undefined
                ? backtest.total_trades.toLocaleString()
                : "-",
              formatDateTime(backtest.created_at),
              backtest.status,
            ]),
          }}
        />
        <CardHeader className="flex flex-row items-center justify-between pb-4">
          <div className="flex flex-col space-y-1">
            <div className="flex items-center space-x-2">
              <CardTitle className="text-lg font-medium">Backtest Runs</CardTitle>
              <Badge variant="secondary" className="text-xs">{backtests.length}</Badge>
              {selectedBacktest && (
                <Badge variant="default" className="text-xs bg-emerald-500">
                  <CheckCircle2 className="h-3 w-3 mr-1" />
                  1 Selected
                </Badge>
              )}
            </div>
          </div>
          <Button onClick={refetch} variant="outline" size="sm">
            Refresh
          </Button>
        </CardHeader>
        <CardContent>
          {backtests.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-10 text-center">
              <p className="text-sm text-muted-foreground">No backtest runs found</p>
              <p className="text-xs text-muted-foreground mt-1">
                Run a backtest or import trades to see them here
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[120px]">Alias</TableHead>
                    <TableHead>Strategy</TableHead>
                    <TableHead>Symbol</TableHead>
                    <TableHead>Timeframe</TableHead>
                    <TableHead>Date Range</TableHead>
                    <TableHead>Engine</TableHead>
                    <TableHead>Resolution</TableHead>
                    <TableHead className="text-right"># of Trades</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="w-[50px]"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {backtests.map((backtest) => {
                    const selected = isSelected(backtest.backtest_id)
                    return (
                      <TableRow
                        key={backtest.backtest_id}
                        className={cn(
                          selected && "bg-emerald-50 hover:bg-emerald-100 dark:bg-emerald-950/50 dark:hover:bg-emerald-950/70"
                        )}
                      >
                        <TableCell className="font-medium">
                          <div className="flex items-center gap-2">
                            {selected && (
                              <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                            )}
                            {backtest.alias}
                          </div>
                        </TableCell>
                        <TableCell>{backtest.strategy_name}</TableCell>
                        <TableCell>{backtest.symbol || "N/A"}</TableCell>
                        <TableCell>{backtest.timeframe || "N/A"}</TableCell>
                        <TableCell className="text-xs">
                          {backtest.start_date && backtest.end_date ? (
                            <div>
                              <div>{formatDate(backtest.start_date)}</div>
                              <div className="text-muted-foreground">
                                to {formatDate(backtest.end_date)}
                              </div>
                            </div>
                          ) : (
                            "N/A"
                          )}
                        </TableCell>
                        <TableCell>
                          {backtest.engine_type ? (
                            <Badge variant="outline" className="text-xs">
                              {backtest.engine_type}
                            </Badge>
                          ) : (
                            "N/A"
                          )}
                        </TableCell>
                        <TableCell>
                          {backtest.data_resolution ? (
                            <Badge variant="outline" className="text-xs">
                              {backtest.data_resolution}
                            </Badge>
                          ) : (
                            "N/A"
                          )}
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {backtest.total_trades !== null && backtest.total_trades !== undefined
                            ? backtest.total_trades.toLocaleString()
                            : "-"}
                        </TableCell>
                        <TableCell className="text-xs">
                          {formatDateTime(backtest.created_at)}
                        </TableCell>
                        <TableCell>{getStatusBadge(backtest.status)}</TableCell>
                        <TableCell>
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" className="h-8 w-8 p-0">
                                <span className="sr-only">Open menu</span>
                                <MoreVertical className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuItem onClick={() => handleSelect(backtest)}>
                                <CheckCircle2 className="mr-2 h-4 w-4" />
                                {selected ? "Deselect" : "Select"}
                              </DropdownMenuItem>
                              <DropdownMenuItem onClick={() => handleEdit(backtest)}>
                                <Edit className="mr-2 h-4 w-4" />
                                Edit
                              </DropdownMenuItem>
                              <DropdownMenuItem
                                onClick={() => handleDeleteClick(backtest)}
                                className="text-destructive focus:text-destructive"
                              >
                                <Trash2 className="mr-2 h-4 w-4" />
                                Delete
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      <EditBacktestDialog
        backtest={backtestToEdit}
        open={editDialogOpen}
        onOpenChange={setEditDialogOpen}
        onSave={handleSaveEdit}
      />

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Are you sure?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete the backtest run for{" "}
              <span className="font-semibold">
                {backtestToDelete?.alias || backtestToDelete?.strategy_name}
              </span>{" "}
              and all associated data including trades, performance metrics, and equity curve.
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteConfirm}
              disabled={deleting}
              className="bg-destructive hover:bg-destructive/90"
            >
              {deleting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
