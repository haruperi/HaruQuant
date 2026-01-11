"use client"

import React from "react"
import { Separator } from "@/components/ui/separator"
import { MetricGrid3Way, MetricConfig, MetricData } from "./metric-grid-3way"
import { SeriesChart3Way } from "./series-chart-3way"
import { DistributionPanel3Way } from "./distribution-panel-3way"
import { ScatterChart3Way } from "./scatter-chart-3way"

export type ChartConfig = {
  id: string
  type: "series" | "distribution" | "scatter"
  title: string
  dataKey?: string // Key in the data object for series data
  valueFormatter?: (value: number) => string
  unit?: string // For distributions
}

export type PageConfig = {
  title: string
  description?: string
  metrics?: MetricConfig[]
  charts?: ChartConfig[]
}

interface PerformancePageLayoutProps {
  config: PageConfig
  data: {
    metrics: MetricData
    charts?: Record<string, any> // map of id -> data
  }
}

export function PerformancePageLayout({
  config,
  data,
}: PerformancePageLayoutProps) {
  return (
    <div className="space-y-6 container mx-auto p-6 max-w-[1600px]">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">{config.title}</h1>
        {config.description && (
          <p className="text-muted-foreground mt-2">{config.description}</p>
        )}
      </div>

      <Separator />

      {/* Metrics Section */}
      {config.metrics && config.metrics.length > 0 && (
        <section className="space-y-4">
          <MetricGrid3Way
            metrics={config.metrics}
            data={data.metrics}
            className="border shadow-sm"
          />
        </section>
      )}

      {/* Charts Section */}
      {config.charts && config.charts.length > 0 && (
        <div className="grid grid-cols-1 gap-6">
          {config.charts.map((chartConfig) => {
            const chartData = data.charts?.[chartConfig.id]

            if (!chartData) {
              return (
                <div key={chartConfig.id} className="p-8 border border-dashed rounded-lg text-center text-muted-foreground">
                    No data for chart: {chartConfig.title}
                </div>
              )
            }

            if (chartConfig.type === "series") {
              return (
                <SeriesChart3Way
                  key={chartConfig.id}
                  title={chartConfig.title}
                  data={chartData}
                  valueFormatter={chartConfig.valueFormatter}
                />
              )
            }

            if (chartConfig.type === "distribution") {
              return (
                <DistributionPanel3Way
                  key={chartConfig.id}
                  title={chartConfig.title}
                  data={chartData}
                  unit={chartConfig.unit}
                />
              )
            }

            if (chartConfig.type === "scatter") {
                return (
                    <ScatterChart3Way
                        key={chartConfig.id}
                        title={chartConfig.title}
                        data={chartData}
                        valueFormatter={chartConfig.valueFormatter}
                    />
                )
            }

            return null
          })}
        </div>
      )}
    </div>
  )
}
