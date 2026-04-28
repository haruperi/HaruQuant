"use client"

import React from "react"
import { Separator } from "@/components/ui/separator"
import { MetricGrid3Way, MetricConfig, MetricData } from "./metric-grid-3way"
import { SeriesChart3Way } from "./series-chart-3way"
import { DistributionPanel3Way } from "./distribution-panel-3way"
import { ScatterChart3Way } from "./scatter-chart-3way"
import { PerformanceActions } from "./performance-actions"
import { 
  TrendingUp, 
  ShieldCheck, 
  Activity, 
  BarChart3, 
  Clock, 
  Target, 
  Zap, 
  Search,
  Scale,
  FileSearch,
  ChevronRight,
  LayoutGrid
} from "lucide-react"

const GROUP_ICONS: Record<string, any> = {
  "Profitability": TrendingUp,
  "Returns": TrendingUp,
  "Risk": ShieldCheck,
  "Preservation": ShieldCheck,
  "Quality": Activity,
  "Robustness": BarChart3,
  "Validation": BarChart3,
  "Trade Analysis": Search,
  "Core Trade Counts": Target,
  "Trade P&L": Zap,
  "R-Multiple": Scale,
  "Time-in-Trade": Clock,
  "Sequence Quality": Activity,
  "Efficiency": Zap,
  "Benchmark": FileSearch,
  "Relative Performance": TrendingUp,
  "Market Statistics": BarChart3,
  "Equity Drawdowns": ShieldCheck,
  "Duration & Recovery": Clock,
  "Trade-Level Drawdowns": Search,
  "Periodic & Time-Based": Clock,
  "Pain & Volatility": Zap,
  "Core Statistics": Activity,
  "Advanced Analysis": Search,
  "VAMI": LayoutGrid,
  "Management": Target,
  "Tail": ShieldCheck
}

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
  /** Optional skeleton UI to show while charts are loading */
  chartSkeletons?: React.ReactNode
  /** Optional action elements to show in the header */
  actions?: React.ReactNode
}

export function PerformancePageLayout({
  config,
  data,
  chartSkeletons,
  actions,
}: PerformancePageLayoutProps) {
  const containerId = `report-${config.title.toLowerCase().replace(/\s+/g, '-')}`

  // Group metrics into sections
  const groupedMetrics = React.useMemo(() => {
    if (!config.metrics || config.metrics.length === 0) return []
    
    const sections: { label: string, icon: any, metrics: MetricConfig[] }[] = []
    let currentSection: { label: string, icon: any, metrics: MetricConfig[] } | null = null

    config.metrics.forEach(m => {
      if (m.type === "group") {
        let Icon = ChevronRight
        const labelLower = m.label.toLowerCase()
        for (const [key, IconComp] of Object.entries(GROUP_ICONS)) {
          if (labelLower.includes(key.toLowerCase())) {
            Icon = IconComp
            break
          }
        }
        currentSection = { label: m.label, icon: Icon, metrics: [] }
        sections.push(currentSection)
      } else {
        if (!currentSection) {
          currentSection = { label: "Statistics", icon: Activity, metrics: [] }
          sections.push(currentSection)
        }
        currentSection.metrics.push(m)
      }
    })
    return sections
  }, [config.metrics])

  return (
    <div id={containerId} className="space-y-12 container mx-auto p-6 max-w-[1600px] bg-background pb-32">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight uppercase">{config.title}</h1>
          {config.description && (
            <p className="text-muted-foreground mt-2">{config.description}</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {actions}
          <PerformanceActions 
            data={data} 
            filename={config.title.toLowerCase().replace(/\s+/g, '-')}
            containerId={containerId}
          />
        </div>
      </div>

      <Separator className="opacity-50" />

      {/* Metrics Section */}
      {groupedMetrics.length > 0 && (
        <div className="grid grid-cols-1 gap-16">
          {groupedMetrics.map((section, idx) => (
            <section key={idx} className="space-y-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-primary/10 rounded-xl border border-primary/20">
                  <section.icon className="h-5 w-5 text-primary" />
                </div>
                <h2 className="text-xl font-black tracking-tight uppercase text-primary/90">{section.label}</h2>
              </div>
              <MetricGrid3Way 
                metrics={section.metrics} 
                data={data.metrics} 
                className="border shadow-lg bg-card/40 backdrop-blur-sm hover:border-primary/30 transition-colors" 
              />
            </section>
          ))}
        </div>
      )}

      {/* Charts Section - show skeletons while loading */}
      {chartSkeletons && !data.charts && (
        <section className="space-y-4">
          {chartSkeletons}
        </section>
      )}

      {/* Charts Section - render actual charts when data is available */}
      {config.charts && config.charts.length > 0 && data.charts && (
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
