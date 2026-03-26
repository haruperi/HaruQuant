"use client"

import { Label } from "@/components/ui/label"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"

export type HistoricalOutputMode = "visualized" | "batch"

interface OutputModeSelectorProps {
  value: HistoricalOutputMode
  onValueChange: (value: HistoricalOutputMode) => void
  label?: string
}

export function OutputModeSelector({
  value,
  onValueChange,
  label = "Execution Mode",
}: OutputModeSelectorProps) {
  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      <ToggleGroup
        type="single"
        value={value}
        onValueChange={(next) => {
          if (next) {
            onValueChange(next as HistoricalOutputMode)
          }
        }}
      >
        <ToggleGroupItem value="visualized">Visualized</ToggleGroupItem>
        <ToggleGroupItem value="batch">Batch</ToggleGroupItem>
      </ToggleGroup>
    </div>
  )
}
