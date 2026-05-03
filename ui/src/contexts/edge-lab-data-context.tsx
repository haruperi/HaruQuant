"use client"

import React, { createContext, useContext, useEffect, useMemo, useState } from "react"

import {
  edgeLabApi,
  type EdgeCoreMetricProfile,
  type EdgeLabDatasetPayload,
  type EdgeLabPreparedDataset,
  type EdgeLabSeasonalityResponse,
  type EdgeMarketStructureProfile,
  type EdgeMarketStructureRobustnessReport,
  type EdgeMarketStructureStabilityReport,
  type EdgeUnsupervisedResult,
} from "@/lib/api/edge"

interface EdgeLabDataContextValue {
  dataset: EdgeLabPreparedDataset | null
  coreMetricProfile: EdgeCoreMetricProfile | null
  seasonalityResult: EdgeLabSeasonalityResponse | null
  marketStructureProfile: EdgeMarketStructureProfile | null
  unsupervisedResult: EdgeUnsupervisedResult | null
  marketStructureStability: EdgeMarketStructureStabilityReport | null
  marketStructureRobustness: EdgeMarketStructureRobustnessReport | null
  loading: boolean
  error: string | null
  loadDataset: (payload: EdgeLabDatasetPayload) => Promise<EdgeLabPreparedDataset | null>
  setCoreMetricProfile: (profile: EdgeCoreMetricProfile | null) => void
  setSeasonalityResult: (result: EdgeLabSeasonalityResponse | null) => void
  setMarketStructureProfile: (profile: EdgeMarketStructureProfile | null) => void
  setUnsupervisedResult: (result: EdgeUnsupervisedResult | null) => void
  setMarketStructureStability: (report: EdgeMarketStructureStabilityReport | null) => void
  setMarketStructureRobustness: (report: EdgeMarketStructureRobustnessReport | null) => void
  clearAnalysis: () => void
  clearDataset: () => void
}

const STORAGE_KEY = "edge_lab_prepared_dataset"
const CORE_METRIC_STORAGE_KEY = "edge_lab_core_metric_profile"
const SEASONALITY_STORAGE_KEY = "edge_lab_seasonality_result"
const MARKET_STRUCTURE_STORAGE_KEY = "edge_lab_market_structure_profile"
const UNSUPERVISED_STORAGE_KEY = "edge_lab_unsupervised_result"
const MARKET_STRUCTURE_STABILITY_STORAGE_KEY = "edge_lab_market_structure_stability"
const MARKET_STRUCTURE_ROBUSTNESS_STORAGE_KEY = "edge_lab_market_structure_robustness"

const EdgeLabDataContext = createContext<EdgeLabDataContextValue | undefined>(undefined)

function compactMarketStructureProfile(
  profile: EdgeMarketStructureProfile | null
): EdgeMarketStructureProfile | null {
  if (!profile) return null
  return {
    ...profile,
    values: [],
    swing_points: profile.swing_points.slice(0, 120),
    trend_legs: profile.trend_legs.slice(0, 120),
    summary: {
      ...profile.summary,
      regime_map: [],
      calibration_metadata: profile.summary.calibration_metadata,
    },
  }
}

function compactSeasonalityResult(
  result: EdgeLabSeasonalityResponse | null
): EdgeLabSeasonalityResponse | null {
  if (!result) return null
  return {
    ...result,
    data_rows: [],
  }
}

export function EdgeLabDataProvider({ children }: { children: React.ReactNode }) {
  const [dataset, setStoredDataset] = useState<EdgeLabPreparedDataset | null>(null)
  const [coreMetricProfile, setStoredCoreMetricProfile] = useState<EdgeCoreMetricProfile | null>(null)
  const [seasonalityResult, setStoredSeasonalityResult] = useState<EdgeLabSeasonalityResponse | null>(null)
  const [marketStructureProfile, setStoredMarketStructureProfile] = useState<EdgeMarketStructureProfile | null>(null)
  const [unsupervisedResult, setStoredUnsupervisedResult] = useState<EdgeUnsupervisedResult | null>(null)
  const [marketStructureStability, setStoredMarketStructureStability] = useState<EdgeMarketStructureStabilityReport | null>(null)
  const [marketStructureRobustness, setStoredMarketStructureRobustness] = useState<EdgeMarketStructureRobustnessReport | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (typeof window === "undefined") return
    const hydrate = <T,>(key: string, setter: (value: T | null) => void) => {
      const raw = window.sessionStorage.getItem(key)
      if (!raw) return
      try {
        setter(JSON.parse(raw) as T)
      } catch {
        window.sessionStorage.removeItem(key)
      }
    }
    hydrate<EdgeLabPreparedDataset>(STORAGE_KEY, setStoredDataset)
    hydrate<EdgeCoreMetricProfile>(CORE_METRIC_STORAGE_KEY, setStoredCoreMetricProfile)
    hydrate<EdgeLabSeasonalityResponse>(SEASONALITY_STORAGE_KEY, setStoredSeasonalityResult)
    hydrate<EdgeMarketStructureProfile>(MARKET_STRUCTURE_STORAGE_KEY, setStoredMarketStructureProfile)
    hydrate<EdgeUnsupervisedResult>(UNSUPERVISED_STORAGE_KEY, setStoredUnsupervisedResult)
    hydrate<EdgeMarketStructureStabilityReport>(MARKET_STRUCTURE_STABILITY_STORAGE_KEY, setStoredMarketStructureStability)
    hydrate<EdgeMarketStructureRobustnessReport>(MARKET_STRUCTURE_ROBUSTNESS_STORAGE_KEY, setStoredMarketStructureRobustness)
  }, [])

  useEffect(() => {
    if (typeof window === "undefined") return
    const persist = (key: string, value: unknown) => {
      if (value === null || value === undefined) {
        window.sessionStorage.removeItem(key)
        return
      }
      try {
        window.sessionStorage.setItem(key, JSON.stringify(value))
      } catch (error) {
        if (error instanceof DOMException && error.name === "QuotaExceededError") {
          window.sessionStorage.removeItem(key)
          return
        }
        throw error
      }
    }
    persist(STORAGE_KEY, dataset)
    persist(CORE_METRIC_STORAGE_KEY, coreMetricProfile)
    persist(SEASONALITY_STORAGE_KEY, compactSeasonalityResult(seasonalityResult))
    persist(MARKET_STRUCTURE_STORAGE_KEY, compactMarketStructureProfile(marketStructureProfile))
    persist(UNSUPERVISED_STORAGE_KEY, unsupervisedResult)
    persist(MARKET_STRUCTURE_STABILITY_STORAGE_KEY, marketStructureStability)
    persist(MARKET_STRUCTURE_ROBUSTNESS_STORAGE_KEY, marketStructureRobustness)
  }, [
    dataset,
    coreMetricProfile,
    seasonalityResult,
    marketStructureProfile,
    unsupervisedResult,
    marketStructureStability,
    marketStructureRobustness,
  ])

  const value = useMemo<EdgeLabDataContextValue>(
    () => ({
      dataset,
      coreMetricProfile,
      seasonalityResult,
      marketStructureProfile,
      unsupervisedResult,
      marketStructureStability,
      marketStructureRobustness,
      loading,
      error,
      async loadDataset(payload) {
        setLoading(true)
        setError(null)
        try {
          const response = await edgeLabApi.prepareDataset(payload)
          setStoredDataset(response)
          setStoredCoreMetricProfile(null)
          setStoredSeasonalityResult(null)
          setStoredMarketStructureProfile(null)
          setStoredUnsupervisedResult(null)
          setStoredMarketStructureStability(null)
          setStoredMarketStructureRobustness(null)
          return response
        } catch (err) {
          const message = err instanceof Error ? err.message : "Failed to prepare dataset."
          setError(message)
          return null
        } finally {
          setLoading(false)
        }
      },
      setCoreMetricProfile: setStoredCoreMetricProfile,
      setSeasonalityResult: setStoredSeasonalityResult,
      setMarketStructureProfile(profile) {
        setStoredMarketStructureProfile(profile)
        setStoredMarketStructureStability(null)
        setStoredMarketStructureRobustness(null)
        setStoredUnsupervisedResult(null)
      },
      setUnsupervisedResult: setStoredUnsupervisedResult,
      setMarketStructureStability: setStoredMarketStructureStability,
      setMarketStructureRobustness: setStoredMarketStructureRobustness,
      clearAnalysis() {
        setStoredCoreMetricProfile(null)
        setStoredSeasonalityResult(null)
        setStoredMarketStructureProfile(null)
        setStoredUnsupervisedResult(null)
        setStoredMarketStructureStability(null)
        setStoredMarketStructureRobustness(null)
      },
      clearDataset() {
        setStoredDataset(null)
        setStoredCoreMetricProfile(null)
        setStoredSeasonalityResult(null)
        setStoredMarketStructureProfile(null)
        setStoredUnsupervisedResult(null)
        setStoredMarketStructureStability(null)
        setStoredMarketStructureRobustness(null)
        setError(null)
      },
    }),
    [
      dataset,
      coreMetricProfile,
      seasonalityResult,
      marketStructureProfile,
      unsupervisedResult,
      marketStructureStability,
      marketStructureRobustness,
      error,
      loading,
    ]
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
