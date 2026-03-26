"use client"

import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

interface StrategyOption {
  id: number
  name: string
}

interface StrategySelectorProps {
  id?: string
  label?: string
  value: string
  onValueChange: (value: string) => void
  strategies: StrategyOption[]
  loading?: boolean
  placeholder?: string
}

export function StrategySelector({
  id = "strategyId",
  label = "Strategy",
  value,
  onValueChange,
  strategies,
  loading = false,
  placeholder = "Select strategy",
}: StrategySelectorProps) {
  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      <Select value={value} onValueChange={onValueChange} disabled={loading}>
        <SelectTrigger id={id}>
          <SelectValue placeholder={loading ? "Loading..." : placeholder} />
        </SelectTrigger>
        <SelectContent>
          {strategies.map((strategy) => (
            <SelectItem key={strategy.id} value={strategy.id.toString()}>
              {strategy.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}
