"use client"

import type { EdgeLabPreparedDataset } from "@/lib/api/edge"

export function EdgeLabDatasetSummary({
  dataset,
  emptyMessage,
}: {
  dataset: EdgeLabPreparedDataset | null
  emptyMessage: string
}) {
  if (!dataset) {
    return <div className="text-sm text-muted-foreground">{emptyMessage}</div>
  }

  return (
    <div className="grid gap-4 md:grid-cols-4 text-sm">
      <div>
        <div className="text-muted-foreground">Symbol</div>
        <div>{dataset.request.symbol}</div>
      </div>
      <div>
        <div className="text-muted-foreground">Timeframe</div>
        <div>{dataset.request.timeframe}</div>
      </div>
      <div>
        <div className="text-muted-foreground">Rows</div>
        <div>{dataset.meta.n_rows}</div>
      </div>
      <div>
        <div className="text-muted-foreground">Warnings</div>
        <div>{dataset.report.warnings.length}</div>
      </div>
    </div>
  )
}
