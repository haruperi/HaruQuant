"use client"

import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"

export type HistoricalRangeMode = "dates" | "bars"

interface RangeModeSelectorProps {
  value: HistoricalRangeMode
  onValueChange: (value: HistoricalRangeMode) => void
  label?: string
  variant?: "select" | "toggle"
}

export function RangeModeSelector({
  value,
  onValueChange,
  label = "Range By",
  variant = "select",
}: RangeModeSelectorProps) {
  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      {variant === "toggle" ? (
        <ToggleGroup
          type="single"
          value={value}
          onValueChange={(next) => {
            if (next) {
              onValueChange(next as HistoricalRangeMode)
            }
          }}
        >
          <ToggleGroupItem value="dates">Dates</ToggleGroupItem>
          <ToggleGroupItem value="bars">Bars</ToggleGroupItem>
        </ToggleGroup>
      ) : (
        <Select value={value} onValueChange={(next) => onValueChange(next as HistoricalRangeMode)}>
          <SelectTrigger id="rangeBy">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="dates">Dates</SelectItem>
            <SelectItem value="bars">Bars</SelectItem>
          </SelectContent>
        </Select>
      )}
    </div>
  )
}
