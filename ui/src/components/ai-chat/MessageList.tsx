"use client"

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
}

function formatTimestamp(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleTimeString()
}

function getResponseStyleConfig(responseStyle?: string) {
  switch (responseStyle) {
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
        label: "Summary",
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

export function MessageList({ messages, isInitializing, isOnline, error }: MessageListProps) {
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
                  ? "Persistent threads, styled copilot responses, and page-aware grounding are ready."
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
                      {message.role === "assistant" ? (
                        <span className={cn("inline-flex items-center rounded-sm px-1.5 py-0.5 text-[10px] font-medium", styleConfig.badgeClassName)}>
                          {styleConfig.label}
                        </span>
                      ) : null}
                      {message.status === "pending" && (
                        <>
                          <Loader2 className="h-3 w-3 animate-spin" />
                          Thinking
                        </>
                      )}
                    </div>
                    <div className="space-y-1">{renderMessageContent(message.content || "...")}</div>
                    {message.role === "assistant" && message.toolCalls && message.toolCalls.length > 0 ? (
                      <p className="mt-2 text-[11px] text-muted-foreground">
                        Tools used: {message.toolCalls.join(", ")}
                      </p>
                    ) : null}
                    {message.taskClass ? (
                      <p className="mt-1 text-[10px] text-muted-foreground">
                        Task: {message.taskClass}{message.domainFocus ? ` · ${message.domainFocus}` : ""}
                      </p>
                    ) : null}
                    {message.requestId ? (
                      <p className="mt-1 text-[10px] text-muted-foreground">
                        Request ID: {message.requestId}
                      </p>
                    ) : null}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </ScrollArea>
  )
}
