"use client"

import React, { createContext, useContext, useState, useCallback } from "react"
import { Backtest } from "@/lib/api/strategies"

interface SelectedBacktestContextType {
  selectedBacktest: Backtest | null
  selectBacktest: (backtest: Backtest | null) => void
  isSelected: (backtestId: number) => boolean
  clearSelection: () => void
}

const SelectedBacktestContext = createContext<SelectedBacktestContextType | undefined>(undefined)

export function SelectedBacktestProvider({ children }: { children: React.ReactNode }) {
  const [selectedBacktest, setSelectedBacktest] = useState<Backtest | null>(null)

  const selectBacktest = useCallback((backtest: Backtest | null) => {
    setSelectedBacktest(backtest)
  }, [])

  const isSelected = useCallback((backtestId: number) => {
    return selectedBacktest?.backtest_id === backtestId
  }, [selectedBacktest])

  const clearSelection = useCallback(() => {
    setSelectedBacktest(null)
  }, [])

  return (
    <SelectedBacktestContext.Provider
      value={{
        selectedBacktest,
        selectBacktest,
        isSelected,
        clearSelection
      }}
    >
      {children}
    </SelectedBacktestContext.Provider>
  )
}

export function useSelectedBacktest() {
  const context = useContext(SelectedBacktestContext)
  if (context === undefined) {
    throw new Error("useSelectedBacktest must be used within a SelectedBacktestProvider")
  }
  return context
}
