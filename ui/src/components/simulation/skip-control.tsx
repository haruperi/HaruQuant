"use client"

import { useState } from "react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import simulatorApi from "@/lib/api/simulator"

interface SkipControlProps {
  sessionId?: number
  getBarIndexForTime?: (isoTime: string) => number | null
  onSeek?: (barIndex: number) => void
}

export function SkipControl({ sessionId, getBarIndexForTime, onSeek }: SkipControlProps) {
  const [dateTime, setDateTime] = useState("")
  const [seeking, setSeeking] = useState(false)

  const handleSeek = async () => {
    if (!sessionId) {
      toast.error("Start a simulation session first.")
      return
    }

    if (!dateTime) {
      toast.error("Select a date/time to jump to.")
      return
    }

    if (!getBarIndexForTime) {
      toast.error("Bar index lookup not available yet.")
      return
    }

    const isoTime = new Date(dateTime).toISOString()
    const barIndex = getBarIndexForTime(isoTime)
    if (barIndex === null || Number.isNaN(barIndex)) {
      toast.error("Unable to calculate bar index for that time.")
      return
    }

    try {
      setSeeking(true)
      await simulatorApi.seekToBar(sessionId, { bar_index: barIndex })
      toast.success("Jumped to selected date")
      onSeek?.(barIndex)
    } catch (error) {
      toast.error("Failed to jump to date")
    } finally {
      setSeeking(false)
    }
  }

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-border/60 bg-muted/10 p-4">
      <div className="text-sm font-medium">Jump to Date</div>
      <div className="grid grid-cols-1 md:grid-cols-[1fr_auto] gap-3">
        <div className="space-y-2">
          <Label htmlFor="jumpDate">Date / Time</Label>
          <Input
            id="jumpDate"
            type="datetime-local"
            value={dateTime}
            onChange={(e) => setDateTime(e.target.value)}
          />
        </div>
        <div className="flex items-end">
          <Button onClick={handleSeek} disabled={seeking}>
            {seeking ? "Jumping..." : "Jump to Date"}
          </Button>
        </div>
      </div>
    </div>
  )
}
