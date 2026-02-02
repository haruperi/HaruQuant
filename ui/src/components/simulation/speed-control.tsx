"use client"

import { useState } from "react"
import { toast } from "sonner"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import simulatorApi from "@/lib/api/simulator"

interface SpeedControlProps {
  sessionId?: number
  initialSpeed?: number
  onSpeedChange?: (speed: number) => void
}

const speedOptions = [
  1, 5, 15, 30, 60, 120, 240, 720, 1440,
]

export function SpeedControl({
  sessionId,
  initialSpeed = 1,
  onSpeedChange,
}: SpeedControlProps) {
  const [speed, setSpeed] = useState(initialSpeed)
  const [updating, setUpdating] = useState(false)

  const handleSpeedChange = async (value: string) => {
    const nextSpeed = Number(value)
    if (!sessionId || Number.isNaN(nextSpeed)) return
    try {
      setUpdating(true)
      await simulatorApi.updateSession(sessionId, { speed_multiplier: nextSpeed })
      setSpeed(nextSpeed)
      onSpeedChange?.(nextSpeed)
    } catch (error) {
      toast.error("Failed to update speed")
    } finally {
      setUpdating(false)
    }
  }

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-border/60 bg-muted/10 p-4">
      <div className="flex items-center justify-between">
        <div className="text-sm font-medium">Speed Control</div>
        <div className="text-xs text-muted-foreground">X{speed}</div>
      </div>

      <ToggleGroup
        type="single"
        value={speed.toString()}
        onValueChange={(val) => val && handleSpeedChange(val)}
        className="flex flex-wrap gap-2"
      >
        {speedOptions.map((option) => (
          <ToggleGroupItem key={option} value={option.toString()} disabled={updating}>
            X{option}
          </ToggleGroupItem>
        ))}
      </ToggleGroup>
    </div>
  )
}
