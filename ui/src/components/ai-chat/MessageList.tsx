"use client"

import * as React from "react"
import { AlertTriangle, Loader2, Scale, Sparkles, TrendingUp, TriangleAlert, User2 } from "lucide-react"

import { ScrollArea } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"
import type { ChatMessage } from "@/stores/chatWidgetStore"

interface MessageListProps {
  messages: ChatMessage[]
  isInitializing: boolean
  isOnline: boolean
  error: string | null
  onQueueSignalProposalForReview?: (proposalId: string) => void
  onRequestActionDraftApproval?: (draftId: string) => void
  onExecutePaperActionDraft?: (draftId: string) => void
  onSaveSignalProposalToWatchlist?: (proposalId: string) => void
  showDebug?: boolean
}

function formatTimestamp(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleTimeString()
}

function formatGenerationMeta(message: ChatMessage): string | null {
  if (message.role !== "assistant") {
    return null
  }
  const source = message.generationSource === "llm_runtime"
    ? "live"
    : message.generationSource === "fallback"
      ? "fallback"
      : message.generationSource === "clarification_policy"
        ? "policy"
        : null
  if (!source && !message.providerName && !message.model) {
    return null
  }
  const parts = [source, message.providerName, message.model].filter(Boolean)
  return parts.length > 0 ? parts.join(" | ") : null
}

function getResponseStyleConfig(responseStyle?: string) {
  switch (responseStyle) {
    case "clarification":
      return {
        label: "Clarification",
        icon: Sparkles,
        bubbleClassName: "border-orange-500/40 bg-orange-500/5",
        badgeClassName: "border border-orange-500/40 bg-orange-500/10 text-orange-700 dark:text-orange-300",
      }
    case "diagnostic":
      return {
        label: "Diagnostic",
        icon: AlertTriangle,
        bubbleClassName: "border-amber-500/40 bg-amber-500/5",
        badgeClassName: "border border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-300",
      }
    case "compare":
      return {
        label: "Compare",
        icon: Scale,
        bubbleClassName: "border-sky-500/40 bg-sky-500/5",
        badgeClassName: "border border-sky-500/40 bg-sky-500/10 text-sky-700 dark:text-sky-300",
      }
    case "warning":
      return {
        label: "Risk Warning",
        icon: TriangleAlert,
        bubbleClassName: "border-rose-500/40 bg-rose-500/5",
        badgeClassName: "border border-rose-500/40 bg-rose-500/10 text-rose-700 dark:text-rose-300",
      }
    case "recommendation":
      return {
        label: "Recommendation",
        icon: TrendingUp,
        bubbleClassName: "border-emerald-500/40 bg-emerald-500/5",
        badgeClassName: "border border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
      }
    default:
      return {
        label: "Answer",
        icon: Sparkles,
        bubbleClassName: "border-violet-500/30 bg-violet-500/5",
        badgeClassName: "border border-violet-500/30 bg-violet-500/10 text-violet-700 dark:text-violet-300",
      }
  }
}

function renderMessageContent(content: string) {
  return content.split("\n").map((line, index) => {
    const trimmed = line.trim()
    if (!trimmed) {
      return <div key={`empty_${index}`} className="h-2" />
    }
    const isSectionHeader = /^[A-Z][A-Za-z ]+:$/.test(trimmed)
    return (
      <p
        key={`${trimmed}_${index}`}
        className={cn(
          "whitespace-pre-wrap break-words",
          isSectionHeader && "mt-2 font-semibold text-foreground",
        )}
      >
        {trimmed}
      </p>
    )
  })
}

function renderListItems(items: string[]) {
  return (
    <ul className="space-y-1">
      {items.map((item, index) => (
        <li key={`${item}_${index}`} className="break-words">
          - {item}
        </li>
      ))}
    </ul>
  )
}

export function MessageList({
  messages,
  isInitializing,
  isOnline,
  error,
  onQueueSignalProposalForReview,
  onRequestActionDraftApproval,
  onExecutePaperActionDraft,
  onSaveSignalProposalToWatchlist,
  showDebug = false,
}: MessageListProps) {
  const endRef = React.useRef<HTMLDivElement | null>(null)

  React.useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" })
  }, [isInitializing, messages.length])

  return (
    <ScrollArea className="h-full">
      <div className="flex min-h-full flex-col gap-3 p-4">
        {isInitializing ? (
          <>
            <div className="space-y-2">
              <Skeleton className="h-4 w-24 rounded-sm" />
              <Skeleton className="h-16 w-full rounded-sm" />
            </div>
            <div className="space-y-2 self-end">
              <Skeleton className="ml-auto h-4 w-20 rounded-sm" />
              <Skeleton className="ml-auto h-12 w-48 rounded-sm" />
            </div>
          </>
        ) : messages.length === 0 ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-3 text-center">
            <div className="rounded-md border bg-muted/30 p-3">
              <Sparkles className="h-5 w-5" />
            </div>
            <div className="space-y-1">
              <p className="text-sm font-medium">
                {isOnline ? "Start a conversation" : "You are offline"}
              </p>
              <p className="max-w-xs text-xs text-muted-foreground">
                {isOnline
                  ? "Persistent threads, page-aware grounding, and conversational specialist support are ready."
                  : "Draft text is still preserved locally, but replies are disabled until connectivity returns."}
              </p>
              {error ? (
                <p className="max-w-xs text-xs text-destructive">
                  {error}
                </p>
              ) : null}
            </div>
          </div>
        ) : (
          <div aria-live="polite" className="space-y-3">
            {messages.map((message) => {
              const styleConfig = getResponseStyleConfig(message.responseStyle)
              const StyleIcon = styleConfig.icon
              const generationMeta = formatGenerationMeta(message)
              const isClarification = message.role === "assistant" && message.responseStyle === "clarification"
              const toolItems = message.toolCalls ?? []
              const sourceItems = (message.specialistArtifacts ?? [])
                .flatMap((artifact) => artifact.sources ?? [])
                .filter((value, index, values) => values.indexOf(value) === index)
              const specialistItems = (message.specialistArtifacts ?? []).map(
                (artifact) => `${artifact.agent_name}: ${artifact.summary}`,
              )

              return (
                <div
                  key={message.id}
                  className={cn(
                    "flex gap-2",
                    message.role === "user" ? "justify-end" : "justify-start",
                  )}
                >
                  {message.role === "assistant" && (
                    <div className="mt-1 rounded-sm border bg-muted/40 p-1.5">
                      <StyleIcon className="h-3.5 w-3.5" />
                    </div>
                  )}
                  <div
                    className={cn(
                      "max-w-[85%] rounded-md border px-3 py-2 text-sm shadow-xs",
                      message.role === "user"
                        ? "bg-primary text-primary-foreground"
                        : cn("bg-background", styleConfig.bubbleClassName),
                    )}
                  >
                    <div className="mb-1 flex flex-wrap items-center gap-2 text-[11px] opacity-80">
                      {message.role === "user" ? (
                        <>
                          <User2 className="h-3 w-3" />
                          You
                        </>
                      ) : (
                        <>
                          <Sparkles className="h-3 w-3" />
                          HaruQuant AI
                        </>
                      )}
                      <span>{formatTimestamp(message.createdAt)}</span>
                      {generationMeta ? (
                        <span className="rounded-sm border px-1.5 py-0.5 text-[10px] text-muted-foreground">
                          {generationMeta}
                        </span>
                      ) : null}
                      {message.role === "assistant" ? (
                        <span className={cn("inline-flex items-center rounded-sm px-1.5 py-0.5 text-[10px] font-medium", styleConfig.badgeClassName)}>
                          {styleConfig.label}
                        </span>
                      ) : null}
                      {message.status === "pending" ? (
                        <>
                          <Loader2 className="h-3 w-3 animate-spin" />
                          Responding
                        </>
                      ) : null}
                    </div>
                    {isClarification ? (
                      <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                        I need one detail before I answer.
                      </p>
                    ) : null}
                    <div className="space-y-1">{renderMessageContent(message.content || "...")}</div>
                    {message.role === "assistant" && (toolItems.length > 0 || sourceItems.length > 0 || specialistItems.length > 0) ? (
                      <div className="mt-3 space-y-2">
                        {toolItems.length > 0 ? (
                          <details className="rounded-md border bg-muted/30 px-2 py-1.5 text-[11px] text-muted-foreground">
                            <summary className="cursor-pointer font-medium text-foreground">Tools used</summary>
                            <div className="mt-2">{renderListItems(toolItems)}</div>
                          </details>
                        ) : null}
                        {sourceItems.length > 0 ? (
                          <details className="rounded-md border bg-muted/30 px-2 py-1.5 text-[11px] text-muted-foreground">
                            <summary className="cursor-pointer font-medium text-foreground">Sources used</summary>
                            <div className="mt-2">{renderListItems(sourceItems)}</div>
                          </details>
                        ) : null}
                        {specialistItems.length > 0 ? (
                          <details className="rounded-md border bg-muted/30 px-2 py-1.5 text-[11px] text-muted-foreground">
                            <summary className="cursor-pointer font-medium text-foreground">Specialists consulted</summary>
                            <div className="mt-2">{renderListItems(specialistItems)}</div>
                          </details>
                        ) : null}
                      </div>
                    ) : null}
                    {message.role === "assistant" && showDebug ? (
                      <details className="mt-3 rounded-md border bg-muted/30 px-2 py-1.5 text-[11px] text-muted-foreground">
                        <summary className="cursor-pointer font-medium text-foreground">Debug</summary>
                        <div className="mt-2 space-y-2">
                          {renderListItems(
                            [
                              message.responseMode ? `response mode: ${message.responseMode}` : null,
                              message.answerMode ? `answer mode: ${message.answerMode}` : null,
                              message.taskClass ? `task class: ${message.taskClass}` : null,
                              message.domainFocus ? `domain focus: ${message.domainFocus}` : null,
                              message.activeTopic ? `active topic: ${message.activeTopic}` : null,
                              message.conversationPlanId ? `plan id: ${message.conversationPlanId}` : null,
                              typeof message.clarificationRequired === "boolean"
                                ? `clarification required: ${message.clarificationRequired}`
                                : null,
                              message.telemetry?.latency_ms != null ? `latency: ${message.telemetry.latency_ms} ms` : null,
                              message.telemetry?.total_tokens != null ? `tokens: ${message.telemetry.total_tokens}` : null,
                              message.costPolicy?.budget_downgraded ? "cost policy downgraded model for budget" : null,
                              message.costPolicy?.within_workflow_budget === false ? "workflow budget exceeded" : null,
                            ].filter((value): value is string => Boolean(value)),
                          )}
                        </div>
                      </details>
                    ) : null}
                    {message.signalProposal ? (
                      <div className="mt-3 rounded-md border bg-muted/40 p-2 text-[11px] text-muted-foreground">
                        <p className="font-medium text-foreground">{message.signalProposal.symbol} {message.signalProposal.direction} {message.signalProposal.timeframe}</p>
                        <p className="mt-1">Confidence: {message.signalProposal.confidence}</p>
                        <p>Status: {message.signalProposal.status}</p>
                        <p className="mt-1">{message.signalProposal.non_executed_label}</p>
                        <div className="mt-2 flex flex-wrap gap-2">
                          <button
                            type="button"
                            className="rounded-md border px-2 py-1 text-[11px] text-foreground disabled:opacity-50"
                            disabled={message.signalProposal.watchlist_saved}
                            onClick={() => onSaveSignalProposalToWatchlist?.(message.signalProposal!.proposal_id)}
                          >
                            {message.signalProposal.watchlist_saved ? "Saved to watchlist" : "Save to watchlist"}
                          </button>
                          <button
                            type="button"
                            className="rounded-md border px-2 py-1 text-[11px] text-foreground disabled:opacity-50"
                            disabled={message.signalProposal.review_queue_saved}
                            onClick={() => onQueueSignalProposalForReview?.(message.signalProposal!.proposal_id)}
                          >
                            {message.signalProposal.review_queue_saved ? "Queued for review" : "Queue for review"}
                          </button>
                        </div>
                      </div>
                    ) : null}
                    {message.actionDraft ? (
                      <div className="mt-3 rounded-md border bg-muted/40 p-2 text-[11px] text-muted-foreground">
                        <p className="font-medium text-foreground">{message.actionDraft.title}</p>
                        <p className="mt-1">Type: {message.actionDraft.draft_type}</p>
                        <p>Status: {message.actionDraft.status}</p>
                        <p>Risk precheck: {message.actionDraft.risk_precheck_status}</p>
                        <p className="mt-1">{message.actionDraft.risk_precheck_notes}</p>
                        <p className="mt-1">Execution: {message.actionDraft.side_effect_status}</p>
                        <div className="mt-2 flex flex-wrap gap-2">
                          <button
                            type="button"
                            className="rounded-md border px-2 py-1 text-[11px] text-foreground disabled:opacity-50"
                            disabled={
                              !!message.actionDraft.approval_id
                              || message.actionDraft.status !== "draft"
                              || !message.actionDraft.requires_human_approval
                            }
                            onClick={() => onRequestActionDraftApproval?.(message.actionDraft!.draft_id)}
                          >
                            {message.actionDraft.approval_id ? "Approval requested" : "Request approval"}
                          </button>
                          <button
                            type="button"
                            className="rounded-md border px-2 py-1 text-[11px] text-foreground disabled:opacity-50"
                            disabled={
                              message.actionDraft.draft_type !== "order_draft"
                              || message.actionDraft.status !== "approved"
                              || message.actionDraft.side_effect_status !== "not_executed"
                            }
                            onClick={() => onExecutePaperActionDraft?.(message.actionDraft!.draft_id)}
                          >
                            {message.actionDraft.execution_receipt_id ? "Paper executed" : "Run paper execution"}
                          </button>
                        </div>
                      </div>
                    ) : null}
                  </div>
                </div>
              )
            })}
            <div ref={endRef} />
          </div>
        )}
      </div>
    </ScrollArea>
  )
}
