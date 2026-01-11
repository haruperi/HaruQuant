"use client"

import * as React from "react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Loader2 } from "lucide-react"
import { Backtest } from "@/lib/api/strategies"

interface EditBacktestDialogProps {
  backtest: Backtest | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onSave: (backtestId: number, data: { alias?: string; description?: string }) => Promise<void>
}

export function EditBacktestDialog({
  backtest,
  open,
  onOpenChange,
  onSave,
}: EditBacktestDialogProps) {
  const [alias, setAlias] = React.useState("")
  const [description, setDescription] = React.useState("")
  const [saving, setSaving] = React.useState(false)

  React.useEffect(() => {
    if (backtest && open) {
      setAlias(backtest.alias || "")
      setDescription(backtest.description || "")
    }
  }, [backtest, open])

  const handleSave = async () => {
    if (!backtest) return

    try {
      setSaving(true)
      await onSave(backtest.backtest_id, {
        alias: alias || undefined,
        description: description || undefined,
      })
      onOpenChange(false)
    } catch (error) {
      // Error handling is done in parent component
    } finally {
      setSaving(false)
    }
  }

  if (!backtest) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Edit Backtest</DialogTitle>
          <DialogDescription>
            Update the alias and description for this backtest run.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <Label htmlFor="alias">Alias</Label>
            <Input
              id="alias"
              placeholder="e.g., 'Q4 2024 Test' or 'EUR/USD Optimization'"
              value={alias}
              onChange={(e) => setAlias(e.target.value)}
              disabled={saving}
            />
            <p className="text-xs text-muted-foreground">
              Give this backtest a memorable name for easy identification
            </p>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              placeholder="e.g., 'Testing strategy with adjusted parameters for better risk management'"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              disabled={saving}
              rows={4}
            />
            <p className="text-xs text-muted-foreground">
              Add notes about this backtest run
            </p>
          </div>
          <div className="grid gap-2 rounded-lg border p-3 bg-muted/50">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Strategy:</span>
              <span className="font-medium">{backtest.strategy_name}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Symbol:</span>
              <span className="font-medium">{backtest.symbol || "N/A"}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Timeframe:</span>
              <span className="font-medium">{backtest.timeframe || "N/A"}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Date Range:</span>
              <span className="font-medium">
                {backtest.start_date && backtest.end_date
                  ? `${backtest.start_date} to ${backtest.end_date}`
                  : "N/A"}
              </span>
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={saving}
          >
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Save Changes
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
