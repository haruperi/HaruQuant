"use client"

import * as React from "react"

import { SemanticSnapshotScript } from "@/components/ai-chat/SemanticSnapshotScript"
import type {
  AiChatSemanticBlock,
  AiChatSemanticMetricValue,
  AiChatSemanticSeries,
} from "@/lib/ai-chat/contracts"

interface CustomChartSemanticSnapshotProps {
  id: string
  title: string
  summary: string
  keywords?: string[]
  metrics?: AiChatSemanticMetricValue[]
  series?: AiChatSemanticSeries[]
}

export function CustomChartSemanticSnapshot({
  id,
  title,
  summary,
  keywords = [],
  metrics = [],
  series = [],
}: CustomChartSemanticSnapshotProps) {
  const block = React.useMemo<AiChatSemanticBlock>(
    () => ({
      id,
      blockType: "chart",
      title,
      summary,
      keywords,
      metrics,
      series,
    }),
    [id, keywords, metrics, series, summary, title],
  )

  return <SemanticSnapshotScript block={block} />
}
