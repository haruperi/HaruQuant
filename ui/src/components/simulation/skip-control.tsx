"use client"

import { useEffect, useState } from "react"
import { ChevronLeft, ChevronRight, Hash, Play, Calendar } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import simulatorApi from "@/lib/api/simulator"

interface SkipControlProps {
  sessionId?: number
  getBarIndexForTime?: (isoTime: string) => number | null
  onSeek?: (barIndex: number) => void
  currentBarIndex?: number
}

export function SkipControl({
  sessionId,
  getBarIndexForTime,
  onSeek,
  currentBarIndex = 0,
}: SkipControlProps) {
  const [dateTime, setDateTime] = useState("")
  const [seeking, setSeeking] = useState(false)
  const [trades, setTrades] = useState<any[]>([])
  const [tradeNumber, setTradeNumber] = useState<string>("")
  const [currentTradeIndex, setCurrentTradeIndex] = useState<number>(-1)

  useEffect(() => {
    if (sessionId) {
      simulatorApi
        .getTrades(sessionId)
        .then((data: any[]) => {
          setTrades(data || [])
        })
        .catch((err: any) => {
          console.error("Failed to fetch trades for skip control:", err)
        })
    }
  }, [sessionId])

  const handleSeek = async () => {
    if (!sessionId) {
      toast.error("Start a simulation session first.")
      return
    }

    if (!dateTime) {
      toast.error("Select a date/time to jump to.")
      return
    }

    const isoTime = new Date(dateTime).toISOString()
    const barIndex = getBarIndexForTime?.(isoTime)
    if (barIndex !== undefined && barIndex !== null && Number.isNaN(barIndex)) {
      toast.error("Unable to calculate bar index for that time.")
      return
    }

    try {
      setSeeking(true)
      const response = await simulatorApi.seekToBar(sessionId, {
        bar_index: barIndex ?? undefined,
        target_time: isoTime,
      })
      toast.success("Jumped to selected date")
      onSeek?.(response.bar_index)
    } catch {
      toast.error("Failed to jump to date")
    } finally {
      setSeeking(false)
    }
  }

  const handleTradeSeek = async (index: number) => {
    if (!sessionId || index < 0 || index >= trades.length) return

    try {
      setSeeking(true)
      const response = await simulatorApi.seekToTrade(sessionId, index)
      toast.success(`Jumped to trade #${index + 1}`)
      setCurrentTradeIndex(index)
      setTradeNumber((index + 1).toString())
      onSeek?.(response.bar_index)
    } catch {
      toast.error("Failed to jump to trade")
    } finally {
      setSeeking(false)
    }
  }

  const handleJumpToTrade = () => {
    const num = parseInt(tradeNumber, 10)
    if (Number.isNaN(num) || num < 1 || num > trades.length) {
      toast.error(`Please enter a valid trade number (1-${trades.length})`)
      return
    }
    handleTradeSeek(num - 1)
  }

  const hasTrades = trades.length > 0

  return (
    <Card className="overflow-hidden border-border/40 shadow-sm">
      <CardContent className="p-4">
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold flex items-center gap-2">
              <Play className="h-4 w-4 text-primary" />
              Simulation Navigation
            </h3>
            {hasTrades && (
              <span className="text-[10px] font-medium bg-primary/10 text-primary px-2 py-0.5 rounded-full">
                {trades.length} Replay Trades
              </span>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-[1fr_auto_1fr] gap-4 items-center">
            {/* Date Jump Section */}
            <div className="space-y-2">
              <Label htmlFor="jumpDate" className="text-[10px] uppercase tracking-wider text-muted-foreground font-bold">
                Jump to Date
              </Label>
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <Calendar className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
                  <Input
                    id="jumpDate"
                    type="datetime-local"
                    className="h-9 pl-8 text-xs bg-muted/30 border-border/60 focus-visible:ring-primary/30"
                    value={dateTime}
                    onChange={(e) => setDateTime(e.target.value)}
                  />
                </div>
                <Button 
                  size="sm" 
                  onClick={handleSeek} 
                  disabled={seeking}
                  className="h-9 px-4 font-semibold shadow-sm"
                >
                  Go
                </Button>
              </div>
            </div>

            {hasTrades && (
              <Separator orientation="vertical" className="hidden md:block h-12" />
            )}

            {/* Trade Navigation Section */}
            {hasTrades && (
              <div className="space-y-2">
                <Label className="text-[10px] uppercase tracking-wider text-muted-foreground font-bold">
                  Trade Navigation
                </Label>
                <div className="flex items-center gap-2">
                  <div className="flex items-center rounded-md border border-border/60 bg-muted/20 p-1 shadow-inner">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 hover:bg-background hover:shadow-sm"
                      disabled={seeking || currentTradeIndex <= 0}
                      onClick={() => handleTradeSeek(currentTradeIndex - 1)}
                      title="Previous Trade"
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </Button>
                    
                    <div className="flex items-center gap-1 px-2">
                      <Hash className="h-3 w-3 text-muted-foreground" />
                      <Input
                        type="text"
                        placeholder="--"
                        className="h-7 w-10 border-none bg-transparent p-0 text-center text-xs font-bold focus-visible:ring-0"
                        value={tradeNumber}
                        onChange={(e) => setTradeNumber(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && handleJumpToTrade()}
                      />
                    </div>

                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 hover:bg-background hover:shadow-sm"
                      disabled={seeking || currentTradeIndex >= trades.length - 1}
                      onClick={() => handleTradeSeek(currentTradeIndex + 1)}
                      title="Next Trade"
                    >
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>

                  <Button
                    variant="secondary"
                    size="sm"
                    className="h-9 px-4 text-xs font-bold shadow-sm"
                    onClick={handleJumpToTrade}
                    disabled={seeking}
                  >
                    Jump to Trade
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
