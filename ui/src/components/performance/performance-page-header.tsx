"use client"

import { useSelectedBacktest } from "@/contexts/selected-backtest-context"

interface PerformancePageHeaderProps {
  title: string
}

export function PerformancePageHeader({ title }: PerformancePageHeaderProps) {
  const { selectedBacktest } = useSelectedBacktest()

  const timeframe = selectedBacktest
    ? (selectedBacktest.signal_timeframe || selectedBacktest.timeframe)
    : null

  const displayTitle = selectedBacktest
    ? `${title} - ${selectedBacktest.alias || selectedBacktest.strategy_name}${timeframe ? ` (${timeframe})` : ''}`
    : title

  return (
    <div className="flex items-center justify-between p-6 border-b border-border/40">
      <h1 className="text-2xl font-semibold tracking-tight">{displayTitle}</h1>
    </div>
  )
}
