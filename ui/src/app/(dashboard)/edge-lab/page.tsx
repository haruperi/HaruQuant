"use client"

import { EdgeLabIndicatorChart } from "@/components/edge-lab/edge-lab-indicator-chart"
import { useEdgeLabData } from "@/contexts/edge-lab-data-context"

export default function EdgeLabDataPage() {
  const { dataset } = useEdgeLabData()

  return (
    <div className="h-full min-h-0">
      {dataset ? (
        <EdgeLabIndicatorChart
          className="h-full w-full"
          symbol={dataset.request.symbol}
          timeframe={dataset.request.timeframe}
          rows={dataset.rows}
          schema={dataset.schema}
        />
      ) : (
        <div className="flex h-full items-center justify-center rounded-2xl border border-dashed border-border/60 bg-muted/10 text-sm text-muted-foreground">
          No prepared dataset is available for this page.
        </div>
      )}
    </div>
  )
}
