"use client"

import React, { createContext, useContext, useEffect, useMemo, useState } from "react"
import { marketDataApi, type MarketDatasetPayload, type MarketPreparedDataset } from "@/lib/api/data"

interface MarketDataContextValue {
  dataset: MarketPreparedDataset | null
  loading: boolean
  error: string | null
  loadDataset: (payload: MarketDatasetPayload) => Promise<MarketPreparedDataset | null>
  clearDataset: () => void
}

const STORAGE_KEY = "market_data_prepared_dataset"

const MarketDataContext = createContext<MarketDataContextValue | undefined>(undefined)

export function MarketDataProvider({ children }: { children: React.ReactNode }) {
  const [dataset, setStoredDataset] = useState<MarketPreparedDataset | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (typeof window === "undefined") return
    const raw = window.sessionStorage.getItem(STORAGE_KEY)
    if (raw) {
      try {
        setStoredDataset(JSON.parse(raw) as MarketPreparedDataset)
      } catch {
        window.sessionStorage.removeItem(STORAGE_KEY)
      }
    }
  }, [])

  useEffect(() => {
    if (typeof window === "undefined") return
    if (dataset) {
      try {
        window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(dataset))
      } catch (error) {
        if (error instanceof DOMException && error.name === "QuotaExceededError") {
          window.sessionStorage.removeItem(STORAGE_KEY)
        }
      }
    } else {
      window.sessionStorage.removeItem(STORAGE_KEY)
    }
  }, [dataset])

  const value = useMemo<MarketDataContextValue>(
    () => ({
      dataset,
      loading,
      error,
      async loadDataset(payload) {
        setLoading(true)
        setError(null)
        try {
          const response = await marketDataApi.prepareDataset(payload)
          setStoredDataset(response)
          return response
        } catch (err) {
          const message = err instanceof Error ? err.message : "Failed to prepare dataset."
          setError(message)
          return null
        } finally {
          setLoading(false)
        }
      },
      clearDataset() {
        setStoredDataset(null)
        setError(null)
      },
    }),
    [dataset, loading, error]
  )

  return <MarketDataContext.Provider value={value}>{children}</MarketDataContext.Provider>
}

export function useMarketData() {
  const context = useContext(MarketDataContext)
  if (!context) {
    throw new Error("useMarketData must be used within a MarketDataProvider")
  }
  return context
}
