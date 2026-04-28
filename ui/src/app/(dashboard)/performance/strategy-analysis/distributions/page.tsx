"use client"

import React from "react"
import { usePerformanceData } from "@/components/performance/use-performance-data"
import { Loader2 } from "lucide-react"
import { MetricConfig } from "@/components/performance/shared/metric-grid-3way"
import { PerformancePageLayout } from "@/components/performance/shared/performance-page-layout"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"

const distributionsMetrics: MetricConfig[] = [
  // --- Core Summary Statistics (Returns) ---
  { label: "Core Summary Statistics (Returns)", accessor: "", type: "group" as const },
  {
    label: "Mean Return",
    accessor: "returns.mean",
    format: (val: any) => val != null ? `${val.toFixed(4)}%` : "-",
    unit: "%",
    description: "Average return per period."
  },
  {
    label: "Median Return",
    accessor: "returns.median",
    format: (val: any) => val != null ? `${val.toFixed(4)}%` : "-",
    unit: "%",
    description: "Middle value of returns."
  },
  {
    label: "Return StdDev",
    accessor: "returns.std",
    format: (val: any) => val != null ? `${val.toFixed(4)}%` : "-",
    unit: "%",
    description: "Standard deviation of returns."
  },
  {
    label: "Min Return",
    accessor: "returns.min",
    format: (val: any) => val != null ? `${val.toFixed(2)}%` : "-",
    unit: "%",
    description: "Worst single period return."
  },
  {
    label: "Max Return",
    accessor: "returns.max",
    format: (val: any) => val != null ? `${val.toFixed(2)}%` : "-",
    unit: "%",
    description: "Best single period return."
  },

  // --- Core Summary Statistics (Trade PnL) ---
  { label: "Core Summary Statistics (Trade PnL)", accessor: "", type: "group" as const },
  {
    label: "Mean PnL",
    accessor: "trades.mean",
    format: (val: any) => val != null ? `$${val.toFixed(2)}` : "-",
    unit: "USD",
    description: "Average trade PnL."
  },
  {
    label: "Median PnL",
    accessor: "trades.median",
    format: (val: any) => val != null ? `$${val.toFixed(2)}` : "-",
    unit: "USD",
    description: "Middle value of trade PnL."
  },
  {
    label: "PnL StdDev",
    accessor: "trades.std",
    format: (val: any) => val != null ? `$${val.toFixed(2)}` : "-",
    unit: "USD",
    description: "Standard deviation of trade PnL."
  },
  {
    label: "Min PnL",
    accessor: "trades.min",
    format: (val: any) => val != null ? `$${val.toFixed(2)}` : "-",
    unit: "USD",
    description: "Worst single trade PnL."
  },
  {
    label: "Max PnL",
    accessor: "trades.max",
    format: (val: any) => val != null ? `$${val.toFixed(2)}` : "-",
    unit: "USD",
    description: "Best single trade PnL."
  },

  // --- Core Summary Statistics (R-Multiples) ---
  { label: "Core Summary Statistics (R-Multiples)", accessor: "", type: "group" as const },
  {
    label: "Mean R-Multiple",
    accessor: "r_multiples.mean",
    format: (val: any) => val != null ? `${val.toFixed(2)}R` : "-",
    description: "Average R-multiple."
  },
  {
    label: "Median R-Multiple",
    accessor: "r_multiples.median",
    format: (val: any) => val != null ? `${val.toFixed(2)}R` : "-",
    description: "Middle value of R-multiples."
  },
  {
    label: "R-Multiple StdDev",
    accessor: "r_multiples.std",
    format: (val: any) => val != null ? val.toFixed(2) : "-",
    description: "Standard deviation of R-multiples."
  },

  // --- Higher Moments ---
  { label: "Higher Moments", accessor: "", type: "group" as const },
  {
    label: "Skewness",
    accessor: "skewness",
    format: (val: any) => val != null ? val.toFixed(2) : "-",
    description: "Measure of return distribution asymmetry."
  },
  {
    label: "Excess Kurtosis",
    accessor: "kurtosis",
    format: (val: any) => val != null ? val.toFixed(2) : "-",
    description: "Measure of extreme tail thickness (kurtosis - 3)."
  },
  {
    label: "Total Kurtosis",
    accessor: "higher_moments.kurtosis",
    format: (val: any) => val != null ? val.toFixed(2) : "-",
    description: "Total kurtosis. Normal distribution ≈ 3."
  },
  {
    label: "Fat Tail Score",
    accessor: "fat_tail_score",
    format: (val: any) => val != null ? val.toFixed(2) : "-",
    description: "Kurtosis-based measure compared to a normal distribution."
  },

  // --- Normality & Statistical Tests ---
  { label: "Normality & Statistical Tests", accessor: "", type: "group" as const },
  {
    label: "Jarque-Bera Statistic",
    accessor: "jarque_bera.statistic",
    format: (val: any) => val != null ? val.toFixed(2) : "-",
    description: "Test statistic for JB normality test."
  },
  {
    label: "Jarque-Bera p-value",
    accessor: "jarque_bera_p_value",
    format: (val: any) => val != null ? val.toFixed(4) : "-",
    description: "p-value of JB test. < 0.05 indicates non-normal distribution."
  },
  {
    label: "Is Normal (JB)",
    accessor: "is_normal_jb",
    format: (val: any) => val === true ? "Yes" : val === false ? "No" : "-",
    description: "Based on Jarque-Bera test (p > 0.05)."
  },
  {
    label: "Shapiro-Wilk Statistic",
    accessor: "shapiro_wilk.statistic",
    format: (val: any) => val != null ? val.toFixed(2) : "-",
    description: "Test statistic for SW normality test."
  },
  {
    label: "Shapiro-Wilk p-value",
    accessor: "shapiro_wilk_p_value",
    format: (val: any) => val != null ? val.toFixed(4) : "-",
    description: "p-value of SW test. < 0.05 indicates non-normal distribution."
  },
  {
    label: "Is Normal (SW)",
    accessor: "is_normal_sw",
    format: (val: any) => val === true ? "Yes" : val === false ? "No" : "-",
    description: "Based on Shapiro-Wilk test (p > 0.05)."
  },

  // --- Outlier Detection ---
  { label: "Outlier Detection", accessor: "", type: "group" as const },
  {
    label: "Outlier Ratio",
    accessor: "outlier_ratio",
    format: (val: any) => val != null ? `${val.toFixed(2)}%` : "-",
    unit: "%",
    description: "Percentage of the data set flagged as outliers."
  },
  {
    label: "Tail Ratio (95/5)",
    accessor: "tail_ratio",
    format: (val: any) => val != null ? val.toFixed(2) : "-",
    description: "Ratio of absolute value of 95th percentile to 5th percentile. > 1 implies positive skew."
  },

  // --- Asymmetry & Percentiles ---
  { label: "Asymmetry & Percentiles", accessor: "", type: "group" as const },
  { label: "P99 (Extreme Gain)", accessor: "percentiles.p99", format: (v: any) => v != null ? `${(v * 100).toFixed(2)}%` : "-", description: "99th percentile return." },
  { label: "P95 (Tail Gain)", accessor: "percentiles.p95", format: (v: any) => v != null ? `${(v * 100).toFixed(2)}%` : "-", description: "95th percentile return." },
  { label: "P75 (Upper Quartile)", accessor: "percentiles.p75", format: (v: any) => v != null ? `${(v * 100).toFixed(2)}%` : "-", description: "75th percentile return." },
  { label: "P25 (Lower Quartile)", accessor: "percentiles.p25", format: (v: any) => v != null ? `${(v * 100).toFixed(2)}%` : "-", description: "25th percentile return." },
  { label: "P05 (Tail Loss)", accessor: "percentiles.p5", format: (v: any) => v != null ? `${(v * 100).toFixed(2)}%` : "-", description: "5th percentile return." },
  { label: "P01 (Extreme Loss)", accessor: "percentiles.p1", format: (v: any) => v != null ? `${(v * 100).toFixed(2)}%` : "-", description: "1st percentile return." },
  
  { label: "Mean Gain", accessor: "upside_downside.upside_mean", format: (v: any) => v != null ? `${(v * 100).toFixed(2)}%` : "-", description: "Average positive return." },
  { label: "Mean Loss", accessor: "upside_downside.downside_mean", format: (v: any) => v != null ? `${(v * 100).toFixed(2)}%` : "-", description: "Average negative return." },
  { label: "Upside/Downside Ratio", accessor: "tail_ratio", format: (v: any) => v != null ? v.toFixed(2) : "-", description: "Ratio of right-tail to left-tail returns." },

  // --- Distribution Fit Quality ---
  { label: "Distribution Fit Quality (AIC/BIC)", accessor: "", type: "group" as const },
  { label: "Normal Fit (AIC)", accessor: "fit_quality.norm.aic", format: (v: any) => v != null ? v.toFixed(0) : "-", description: "Akaike Information Criterion for Normal fit." },
  { label: "T-Dist Fit (AIC)", accessor: "fit_quality.t.aic", format: (v: any) => v != null ? v.toFixed(0) : "-", description: "Akaike Information Criterion for T-distribution fit." },
  { label: "Best Fit Model", accessor: "fit_quality.best_model", description: "The statistical model that best describes the data (lower AIC)." },
]

const distributionsConfig = {
  title: "Statistical Distributions",
  description: "Analysis of return distributions, higher moments, normality tests, and outliers.",
  metrics: distributionsMetrics,
  charts: []
}

export default function DistributionsPage() {
  const { analytics, loading, error, selectedBacktest } = usePerformanceData()

  if (!selectedBacktest) {
      return <div className="p-12 text-center text-slate-500">Please select a backtest based strategy.</div>
  }

  if (loading) {
     return (
       <div className="flex h-[400px] items-center justify-center">
         <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
       </div>
     )
  }

  if (error) {
    return <div className="p-8 text-red-500">Error: {error}</div>
  }

  if (!analytics?.distributions) {
      return null
  }

  return (
    <div className="space-y-6">
        <PerformancePageLayout
            config={distributionsConfig}
            data={{ metrics: analytics.distributions as any }}
        />
    </div>
  )
}
