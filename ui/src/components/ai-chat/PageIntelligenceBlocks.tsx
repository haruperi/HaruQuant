"use client"

import * as React from "react"

import { SemanticSnapshotScript } from "@/components/ai-chat/SemanticSnapshotScript"
import type {
  AiChatPageActionAffordance,
  AiChatPageChart,
  AiChatPageMetric,
  AiChatPageTable,
  AiChatSemanticBlock,
} from "@/lib/ai-chat/contracts"

interface AiMetricBlockProps {
  id: string
  title?: string
  metrics: AiChatPageMetric[]
}

interface AiTableBlockProps {
  table: AiChatPageTable
}

interface AiChartBlockProps {
  chart: AiChatPageChart
}

interface AiActionAffordanceBlockProps {
  id?: string
  title?: string
  actions: AiChatPageActionAffordance[]
}

function formatMetric(metric: AiChatPageMetric): string {
  const unit = metric.unit ? ` ${metric.unit}` : ""
  const window = metric.window ? ` (${metric.window})` : ""
  return `${metric.value}${unit}${window}`
}

export function AiMetricBlock({ id, title = "Page metrics", metrics }: AiMetricBlockProps) {
  const block = React.useMemo<AiChatSemanticBlock>(
    () => ({
      id,
      blockType: "metric_table",
      title,
      summary: "Canonical metric values exposed for AI page grounding.",
      keywords: metrics.flatMap((metric) => [metric.id, metric.label]).slice(0, 24),
      metrics: metrics.map((metric) => ({
        label: metric.label,
        value: formatMetric(metric),
      })),
      rows: metrics.map((metric) => [
        metric.label,
        formatMetric(metric),
        metric.source ?? "",
        metric.timestamp ?? "",
      ]),
    }),
    [id, metrics, title],
  )

  return <SemanticSnapshotScript block={block} />
}

export function AiTableBlock({ table }: AiTableBlockProps) {
  const block = React.useMemo<AiChatSemanticBlock>(
    () => ({
      id: table.id,
      blockType: "table",
      title: table.title,
      summary: table.source ? `Canonical table from ${table.source}.` : "Canonical page table.",
      keywords: [table.id, table.title, ...table.headers].slice(0, 24),
      headers: table.headers,
      rows: table.rows,
    }),
    [table],
  )

  return <SemanticSnapshotScript block={block} />
}

export function AiChartBlock({ chart }: AiChartBlockProps) {
  const block = React.useMemo<AiChatSemanticBlock>(
    () => ({
      id: chart.id,
      blockType: "chart",
      title: chart.title,
      summary: chart.summary ?? "Canonical page chart.",
      keywords: [chart.id, chart.title],
      series: chart.series,
    }),
    [chart],
  )

  return <SemanticSnapshotScript block={block} />
}

export function AiActionAffordanceBlock({
  id = "page_actions",
  title = "Page actions",
  actions,
}: AiActionAffordanceBlockProps) {
  const block = React.useMemo<AiChatSemanticBlock>(
    () => ({
      id,
      blockType: "control",
      title,
      summary: actions
        .map((action) => `${action.label}: ${action.riskLevel}`)
        .join(" | "),
      keywords: actions.flatMap((action) => [action.id, action.label, action.riskLevel]).slice(0, 24),
      rows: actions.map((action) => [
        action.label,
        action.riskLevel,
        action.requiresConfirmation ? "confirmation_required" : "no_confirmation_required",
        action.description ?? "",
      ]),
    }),
    [actions, id, title],
  )

  return <SemanticSnapshotScript block={block} />
}
