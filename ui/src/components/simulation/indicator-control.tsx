"use client"

import { toast } from "sonner"
import { ChevronDown } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import simulatorApi from "@/lib/api/simulator"

export interface IndicatorSelection {
  sma: boolean
  ema: boolean
  rsi: boolean
}

interface IndicatorControlProps {
  sessionId?: number
  value: IndicatorSelection
  onChange: (value: IndicatorSelection) => void
}

function formatSummary(value: IndicatorSelection) {
  const selected = [
    value.sma ? "SMA" : null,
    value.ema ? "EMA" : null,
    value.rsi ? "RSI" : null,
  ].filter(Boolean)

  if (!selected.length) return "None"
  return selected.join(", ")
}

export function IndicatorControl({
  sessionId,
  value,
  onChange,
}: IndicatorControlProps) {
  const updateIndicators = async (next: IndicatorSelection) => {
    if (!sessionId) {
      toast.error("Start a simulation session first.")
      return
    }

    try {
      await simulatorApi.updateSession(sessionId, {
        indicators_enabled: next.sma || next.ema || next.rsi,
        indicator_sma_enabled: next.sma,
        indicator_ema_enabled: next.ema,
        indicator_rsi_enabled: next.rsi,
      })
      onChange(next)
    } catch {
      toast.error("Failed to update indicators")
    }
  }

  const toggle = (key: keyof IndicatorSelection) => {
    void updateIndicators({
      ...value,
      [key]: !value[key],
    })
  }

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-border/60 bg-muted/10 p-4">
      <div className="flex items-center justify-between">
        <div className="text-sm font-medium">Indicators</div>
        <div className="text-xs text-muted-foreground">{formatSummary(value)}</div>
      </div>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" className="justify-between">
            Select Indicators
            <ChevronDown className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="min-w-[220px]">
          <DropdownMenuLabel>Chart Indicators</DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuCheckboxItem
            checked={value.sma}
            onCheckedChange={() => toggle("sma")}
          >
            SMA
          </DropdownMenuCheckboxItem>
          <DropdownMenuCheckboxItem
            checked={value.ema}
            onCheckedChange={() => toggle("ema")}
          >
            EMA
          </DropdownMenuCheckboxItem>
          <DropdownMenuCheckboxItem
            checked={value.rsi}
            onCheckedChange={() => toggle("rsi")}
          >
            RSI
          </DropdownMenuCheckboxItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  )
}
