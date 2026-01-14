"use client"

import { useState, useEffect } from "react"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Plus, Loader2 } from "lucide-react"
import { LiveTradingAPI } from "@/lib/api/live"
import { useSettings } from "@/lib/use-settings"
import type { SessionCreateRequest, TradingMode, SessionStopMode } from "@/types/live"
import { toast } from "sonner"

interface SessionCreateDialogProps {
  onSessionCreated?: (sessionId: number) => void
}

export function SessionCreateDialog({ onSessionCreated }: SessionCreateDialogProps) {
  const { settings, isLoading: isLoadingSettings } = useSettings()
  const [isOpen, setIsOpen] = useState(false)
  const [isCreating, setIsCreating] = useState(false)

  // Form state
  const [sessionName, setSessionName] = useState("")
  const [mode, setMode] = useState<TradingMode>("paper")
  const [stopMode, setStopMode] = useState<SessionStopMode>("manual")
  const [stopAt, setStopAt] = useState("")
  const [maxTotalRiskPct, setMaxTotalRiskPct] = useState(2.0)
  const [maxPositions, setMaxPositions] = useState(5)
  const [maxCorrelation, setMaxCorrelation] = useState(0.7)
  const [maxDrawdownPct, setMaxDrawdownPct] = useState(10.0)

  // Load defaults from user trading preferences
  useEffect(() => {
    if (settings?.trading_preferences && isOpen) {
      try {
        let tradingPrefs
        if (typeof settings.trading_preferences === "string") {
          tradingPrefs = JSON.parse(settings.trading_preferences)
        } else {
          tradingPrefs = settings.trading_preferences
        }

        // Map trading preferences to session defaults
        if (tradingPrefs.riskPerTrade) {
          setMaxTotalRiskPct(parseFloat(tradingPrefs.riskPerTrade))
        }
        if (tradingPrefs.maxPositions) {
          setMaxPositions(parseInt(tradingPrefs.maxPositions))
        }
        if (tradingPrefs.maxDrawdown) {
          setMaxDrawdownPct(parseFloat(tradingPrefs.maxDrawdown))
        }
      } catch (e) {
        console.error("Error loading trading preferences:", e)
      }
    }
  }, [settings, isOpen])

  const handleCreate = async () => {
    if (!sessionName.trim()) {
      toast.error("Session name is required")
      return
    }

    if (stopMode === "auto" && !stopAt) {
      toast.error("Stop time is required for auto stop")
      return
    }

    try {
      setIsCreating(true)

      const request: SessionCreateRequest = {
        session_name: sessionName,
        mode,
        stop_mode: stopMode,
        stop_at: stopMode === "auto" ? stopAt : undefined,
        max_total_risk_pct: maxTotalRiskPct,
        max_positions: maxPositions,
        max_correlation: maxCorrelation,
        max_drawdown_pct: maxDrawdownPct,
      }

      const session = await LiveTradingAPI.createSession(request)

      toast.success("Session Created", {
        description: `${sessionName} has been created successfully`,
      })

      // Reset form
      setSessionName("")
      setMode("paper")
      setStopMode("manual")
      setStopAt("")
      setIsOpen(false)

      // Notify parent
      onSessionCreated?.(session.session_id)
    } catch (err) {
      console.error("Error creating session:", err)
      toast.error("Failed to create session", {
        description: err instanceof Error ? err.message : "Unknown error",
      })
    } finally {
      setIsCreating(false)
    }
  }

  const generateSessionName = () => {
    const now = new Date()
    const dateStr = now.toISOString().split("T")[0]
    const timeStr = now.toTimeString().split(" ")[0].replace(/:/g, "")
    return `Session_${dateStr}_${timeStr}`
  }

  const handleOpen = (open: boolean) => {
    setIsOpen(open)
    if (open && !sessionName) {
      setSessionName(generateSessionName())
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={handleOpen}>
      <DialogTrigger asChild>
        <Button size="sm" variant="default">
          <Plus className="mr-2 h-4 w-4" />
          New Session
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Create Live Trading Session</DialogTitle>
          <DialogDescription>
            Configure a new trading session
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-4">
          {/* Session Name */}
          <div className="grid gap-2">
            <Label htmlFor="sessionName">Session Name</Label>
            <Input
              id="sessionName"
              placeholder="e.g., Morning Session"
              value={sessionName}
              onChange={(e) => setSessionName(e.target.value)}
            />
          </div>

          {/* Trading Mode */}
          <div className="grid gap-2">
            <Label htmlFor="mode">Trading Mode</Label>
            <Select value={mode} onValueChange={(value: TradingMode) => setMode(value)}>
              <SelectTrigger id="mode">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="paper">
                  <div className="flex flex-col items-start">
                    <span className="font-medium">Paper Trading</span>
                    <span className="text-xs text-muted-foreground">Safe mode - no real orders</span>
                  </div>
                </SelectItem>
                <SelectItem value="live">
                  <div className="flex flex-col items-start">
                    <span className="font-medium text-red-500">Live Trading</span>
                    <span className="text-xs text-muted-foreground">Real money - use with caution</span>
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="stopMode">Session Stop</Label>
            <Select value={stopMode} onValueChange={(value: SessionStopMode) => setStopMode(value)}>
              <SelectTrigger id="stopMode">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="manual">Manual stop</SelectItem>
                <SelectItem value="auto">Auto stop</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {stopMode === "auto" && (
            <div className="grid gap-2">
              <Label htmlFor="stopAt">Stop At</Label>
              <Input
                id="stopAt"
                type="datetime-local"
                value={stopAt}
                onChange={(e) => setStopAt(e.target.value)}
              />
            </div>
          )}

          {isLoadingSettings && (
            <div className="text-xs text-muted-foreground flex items-center gap-2">
              <Loader2 className="h-3 w-3 animate-spin" />
              Loading your trading preferences...
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => setIsOpen(false)}
            disabled={isCreating}
          >
            Cancel
          </Button>
          <Button onClick={handleCreate} disabled={isCreating}>
            {isCreating ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Creating...
              </>
            ) : (
              <>
                <Plus className="mr-2 h-4 w-4" />
                Create Session
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
