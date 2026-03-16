"use client"

import React, { createContext, useContext, useEffect, useMemo, useState } from "react"

import { edgeLabApi, type EdgeLabDatasetPayload, type EdgeLabPreparedDataset } from "@/lib/api/edge"

interface EdgeLabDataContextValue {
  dataset: EdgeLabPreparedDataset | null
  loading: boolean
  error: string | null
  loadDataset: (payload: EdgeLabDatasetPayload) => Promise<EdgeLabPreparedDataset | null>
  clearDataset: () => void
}

const STORAGE_KEY = "edge_lab_prepared_dataset"

const EdgeLabDataContext = createContext<EdgeLabDataContextValue | undefined>(undefined)

export function EdgeLabDataProvider({ children }: { children: React.ReactNode }) {
  const [dataset, setDataset] = useState<EdgeLabPreparedDataset | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (typeof window === "undefined") return
    const raw = window.sessionStorage.getItem(STORAGE_KEY)
    if (!raw) return
    try {
      setDataset(JSON.parse(raw) as EdgeLabPreparedDataset)
    } catch {
      window.sessionStorage.removeItem(STORAGE_KEY)
    }
  }, [])

  useEffect(() => {
    if (typeof window === "undefined") return
    if (!dataset) {
      window.sessionStorage.removeItem(STORAGE_KEY)
      return
    }
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(dataset))
  }, [dataset])

  const value = useMemo<EdgeLabDataContextValue>(
    () => ({
      dataset,
      loading,
      error,
      async loadDataset(payload) {
        setLoading(true)
        setError(null)
        try {
          const response = await edgeLabApi.prepareDataset(payload)
          setDataset(response)
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
        setDataset(null)
        setError(null)
      },
    }),
    [dataset, error, loading]
  )

  return <EdgeLabDataContext.Provider value={value}>{children}</EdgeLabDataContext.Provider>
}

export function useEdgeLabData() {
  const context = useContext(EdgeLabDataContext)
  if (!context) {
    throw new Error("useEdgeLabData must be used within an EdgeLabDataProvider")
  }
  return context
}
