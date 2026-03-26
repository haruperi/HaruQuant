"use client"

import { Label } from "@/components/ui/label"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import type { SimulationMode } from "@/lib/api/simulator"

interface RunSourceSelectorProps {
  value: SimulationMode
  onValueChange: (value: SimulationMode) => void
  label?: string
}

export function RunSourceSelector({
  value,
  onValueChange,
  label = "Mode",
}: RunSourceSelectorProps) {
  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      <ToggleGroup
        type="single"
        value={value}
        onValueChange={(next) => {
          if (next) {
            onValueChange(next as SimulationMode)
          }
        }}
      >
        <ToggleGroupItem value="manual">Manual</ToggleGroupItem>
        <ToggleGroupItem value="strategy">Strategy</ToggleGroupItem>
        <ToggleGroupItem value="replay">Replay</ToggleGroupItem>
      </ToggleGroup>
    </div>
  )
}
