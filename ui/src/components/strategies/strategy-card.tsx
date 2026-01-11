"use client"

import { useState } from "react"
import Link from "next/link"
import { Card, CardContent, CardFooter, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { MoreVertical, Play, Pause, Edit, Activity, Trash2 } from "lucide-react"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
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
import { AreaChart, Area, ResponsiveContainer } from "recharts"
import { useStrategyMutations } from "@/lib/use-strategies"
import { toast } from "sonner"

interface StrategyCardProps {
    strategy: {
        id: string
        name: string
        description: string
        status: "active" | "inactive" | "testing"
        type: string
        winRate: number
        profitFactor: number
        dailyPnL: { value: number }[]
    }
    onDelete?: () => void
}

export function StrategyCard({ strategy, onDelete }: StrategyCardProps) {
    const isPositive = strategy.dailyPnL[strategy.dailyPnL.length - 1].value >= strategy.dailyPnL[0].value
    const [showDeleteDialog, setShowDeleteDialog] = useState(false)
    const { deleteStrategy, updateStrategy, loading } = useStrategyMutations()
    const [toggling, setToggling] = useState(false)

    const handleDelete = async () => {
        try {
            await deleteStrategy(parseInt(strategy.id))
            toast.success("Strategy deleted", {
                description: `${strategy.name} has been deleted successfully.`
            })
            setShowDeleteDialog(false)
            // Call the onDelete callback to refresh the list
            if (onDelete) {
                onDelete()
            }
        } catch (error) {
            toast.error("Failed to delete strategy", {
                description: "An error occurred while deleting the strategy."
            })
        }
    }

    const handleToggleStatus = async () => {
        try {
            setToggling(true)
            const newStatus = strategy.status === "active" ? "inactive" : "active"
            await updateStrategy(parseInt(strategy.id), { status: newStatus })

            toast.success(`Strategy ${newStatus === "active" ? "Started" : "Stopped"}`, {
                description: `${strategy.name} is now ${newStatus}.`
            })

            // Call onDelete (which is actually refetch) to update list
            if (onDelete) {
                onDelete()
            }
        } catch (error) {
            toast.error("Failed to update status", {
                description: "An error occurred while updating the strategy status."
            })
        } finally {
            setToggling(false)
        }
    }

  return (
    <>
      <Card className="flex flex-col h-full hover:border-primary/50 transition-colors">
        <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
          <div className="space-y-1">
              <CardTitle className="text-base font-semibold">{strategy.name}</CardTitle>
              <CardDescription className="line-clamp-1">{strategy.description}</CardDescription>
          </div>
          <div className="flex items-center space-x-2">
              <Badge variant={strategy.status === "active" ? "default" : "secondary"}>
                  {strategy.status}
              </Badge>
              <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon" className="h-8 w-8">
                          <MoreVertical className="h-4 w-4" />
                      </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                      <DropdownMenuItem asChild>
                          <Link href={`/strategies/${strategy.id}`}>
                              <Edit className="mr-2 h-4 w-4" />
                              Edit Configuration
                          </Link>
                      </DropdownMenuItem>
                      <DropdownMenuItem>
                          <Activity className="mr-2 h-4 w-4" />
                          View Backtests
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem
                          className="text-destructive focus:text-destructive"
                          onClick={() => setShowDeleteDialog(true)}
                      >
                          <Trash2 className="mr-2 h-4 w-4" />
                          Delete Strategy
                      </DropdownMenuItem>
                  </DropdownMenuContent>
              </DropdownMenu>
          </div>
        </CardHeader>
        <CardContent className="flex-1 pb-2">
          <div className="h-[60px] w-full mt-2">
              <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={strategy.dailyPnL}>
                      <Area
                          type="monotone"
                          dataKey="value"
                          stroke={isPositive ? "#10b981" : "#ef4444"}
                          fill={isPositive ? "#10b981" : "#ef4444"}
                          fillOpacity={0.1}
                          strokeWidth={2}
                      />
                  </AreaChart>
              </ResponsiveContainer>
          </div>
          <div className="grid grid-cols-2 gap-4 mt-4">
              <div>
                  <p className="text-xs text-muted-foreground">Win Rate</p>
                  <p className="text-lg font-bold">{strategy.winRate}%</p>
              </div>
              <div>
                   <p className="text-xs text-muted-foreground">Profit Factor</p>
                  <p className="text-lg font-bold">{strategy.profitFactor}</p>
              </div>
          </div>
        </CardContent>
        <CardFooter className="pt-2">
          <div className="flex w-full items-center justify-between">
              <Badge variant="outline" className="text-xs">{strategy.type}</Badge>
              {strategy.status === "active" ? (
                   <Button
                    variant="outline"
                    size="sm"
                    className="text-destructive hover:text-destructive"
                    onClick={handleToggleStatus}
                    disabled={toggling || loading}
                   >
                      <Pause className="mr-2 h-3 w-3" />
                      Stop
                   </Button>
              ) : (
                  <Button
                    variant="default"
                    size="sm"
                    onClick={handleToggleStatus}
                    disabled={toggling || loading}
                  >
                      <Play className="mr-2 h-3 w-3" />
                      Start
                  </Button>
              )}
          </div>
        </CardFooter>
      </Card>

      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Strategy</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete <span className="font-semibold">{strategy.name}</span>?
              This will permanently delete the strategy, all its versions, and associated files.
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={loading}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {loading ? "Deleting..." : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
