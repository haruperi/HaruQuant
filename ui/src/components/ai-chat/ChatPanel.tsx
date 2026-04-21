"use client"

import * as React from "react"

import { ChatHeader } from "@/components/ai-chat/ChatHeader"
import { ChatInput } from "@/components/ai-chat/ChatInput"
import { MessageList } from "@/components/ai-chat/MessageList"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"
import type { ChatMessage } from "@/stores/chatWidgetStore"

interface ChatPanelProps {
  isOpen: boolean
  isHydrated: boolean
  isInitializing: boolean
  isOnline: boolean
  isRestoring: boolean
  isStreaming: boolean
  isManagingThreads: boolean
  threadTitle: string
  threadId: string | null
  threadSearch: string
  activeResponseStatus: string | null
  error: string | null
  draft: string
  threads: {
    threadId: string
    title: string
    updatedAt: string
    pageType?: string | null
  }[]
  messages: ChatMessage[]
  onCancel: () => void
  onClose: () => void
  onCreateThread: () => void
  onDeleteThread: () => void
  onDraftChange: (value: string) => void
  onExportThread: () => void
  onQueueSignalProposalForReview: (proposalId: string) => void
  onRequestActionDraftApproval: (draftId: string) => void
  onExecutePaperActionDraft: (draftId: string) => void
  onRegenerate: () => void
  onRenameThread: (value: string) => void
  onSaveSignalProposalToWatchlist: (proposalId: string) => void
  onSelectThread: (value: string) => void
  onThreadSearchChange: (value: string) => void
  onSubmit: () => void
}

function getFocusableElements(container: HTMLElement | null): HTMLElement[] {
  if (!container) {
    return []
  }

  return Array.from(
    container.querySelectorAll<HTMLElement>(
      'button, [href], textarea, input, select, [tabindex]:not([tabindex="-1"])',
    ),
  ).filter((element) => !element.hasAttribute("disabled") && !element.getAttribute("aria-hidden"))
}

function formatUpdatedAt(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

function formatRuntimeMeta(message: ChatMessage | undefined): string | null {
  if (!message || message.role !== "assistant") {
    return null
  }

  const source = message.generationSource === "llm_runtime"
    ? "Runtime"
    : message.generationSource === "fallback"
      ? "Fallback"
      : message.generationSource === "clarification_policy"
        ? "Clarification policy"
        : message.generationSource

  const parts = [
    source ? `source: ${source}` : null,
    message.providerName ? `provider: ${message.providerName}` : null,
    message.model ? `model: ${message.model}` : null,
  ].filter((value): value is string => Boolean(value))

  return parts.length > 0 ? parts.join(" | ") : null
}

export function ChatPanel({
  isOpen,
  isHydrated,
  isInitializing,
  isOnline,
  isRestoring,
  isStreaming,
  isManagingThreads,
  threadTitle,
  threadId,
  threadSearch,
  activeResponseStatus,
  error,
  draft,
  threads,
  messages,
  onCancel,
  onClose,
  onCreateThread,
  onDeleteThread,
  onDraftChange,
  onExportThread,
  onQueueSignalProposalForReview,
  onRequestActionDraftApproval,
  onExecutePaperActionDraft,
  onRegenerate,
  onRenameThread,
  onSaveSignalProposalToWatchlist,
  onSelectThread,
  onThreadSearchChange,
  onSubmit,
}: ChatPanelProps) {
  const panelRef = React.useRef<HTMLDivElement | null>(null)
  const textareaRef = React.useRef<HTMLTextAreaElement | null>(null)
  const [showDebug, setShowDebug] = React.useState(false)

  React.useEffect(() => {
    if (!isOpen || !isHydrated) {
      return
    }
    const timeoutId = window.setTimeout(() => {
      textareaRef.current?.focus()
    }, isInitializing ? 360 : 0)
    return () => window.clearTimeout(timeoutId)
  }, [isHydrated, isInitializing, isOpen])

  React.useEffect(() => {
    if (!isOpen) {
      return
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault()
        onClose()
        return
      }

      if (event.key !== "Tab") {
        return
      }

      const focusable = getFocusableElements(panelRef.current)
      if (focusable.length === 0) {
        return
      }

      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      const active = document.activeElement

      if (event.shiftKey && active === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && active === last) {
        event.preventDefault()
        first.focus()
      }
    }

    document.addEventListener("keydown", handleKeyDown)
    return () => document.removeEventListener("keydown", handleKeyDown)
  }, [isOpen, onClose])

  const handleRename = React.useCallback(() => {
    const nextTitle = window.prompt("Rename conversation", threadTitle)
    if (nextTitle && nextTitle.trim()) {
      onRenameThread(nextTitle.trim())
    }
  }, [onRenameThread, threadTitle])

  const latestAssistantMessage = React.useMemo(
    () => [...messages].reverse().find((message) => message.role === "assistant"),
    [messages],
  )
  const runtimeMeta = React.useMemo(
    () => formatRuntimeMeta(latestAssistantMessage),
    [latestAssistantMessage],
  )

  return (
    <aside
      aria-hidden={!isOpen}
      aria-label="HaruQuant AI chat panel"
      role="dialog"
      ref={panelRef}
      className={cn(
        "fixed inset-x-0 bottom-0 z-40 flex h-[78vh] max-h-[78vh] flex-col border bg-background shadow-xl transition-all duration-200 md:inset-x-auto md:bottom-6 md:right-6 md:h-[42rem] md:max-h-[calc(100vh-4rem)] md:w-[58rem] md:rounded-md",
        isOpen
          ? "translate-y-0 opacity-100"
          : "pointer-events-none translate-y-4 opacity-0 md:translate-y-2",
      )}
    >
      <ChatHeader
        isOnline={isOnline}
        isRestoring={isRestoring}
        threadTitle={threadTitle}
        runtimeMeta={runtimeMeta}
        onClose={onClose}
      />
      <div className="grid min-h-0 flex-1 gap-0 md:grid-cols-[16rem_minmax(0,1fr)]">
        <div className="border-b md:border-b-0 md:border-r">
          <div className="space-y-2 p-3">
            <Input
              value={threadSearch}
              onChange={(event) => onThreadSearchChange(event.target.value)}
              placeholder="Search conversations"
              aria-label="Search conversations"
              className="rounded-md"
            />
            <div className="grid grid-cols-2 gap-2">
              <Button type="button" variant="outline" size="sm" onClick={onCreateThread} disabled={isManagingThreads || isStreaming}>
                New
              </Button>
              <Button type="button" variant="outline" size="sm" onClick={handleRename} disabled={!threadId || isManagingThreads}>
                Rename
              </Button>
              <Button type="button" variant="outline" size="sm" onClick={onExportThread} disabled={!threadId}>
                Export
              </Button>
              <Button type="button" variant="outline" size="sm" onClick={onDeleteThread} disabled={!threadId || isManagingThreads || isStreaming}>
                Delete
              </Button>
            </div>
          </div>
          <ScrollArea className="h-40 border-t md:h-[calc(100%-5.5rem)]">
            <div className="space-y-1 p-2">
              {threads.map((thread) => (
                <button
                  key={thread.threadId}
                  type="button"
                  onClick={() => onSelectThread(thread.threadId)}
                  className={cn(
                    "w-full rounded-md border px-3 py-2 text-left text-sm",
                    thread.threadId === threadId ? "border-primary bg-muted/40" : "hover:bg-muted/30",
                  )}
                >
                  <div className="truncate font-medium">{thread.title}</div>
                  <div className="mt-1 text-[11px] text-muted-foreground">
                    {thread.pageType ?? "generic"} | {formatUpdatedAt(thread.updatedAt)}
                  </div>
                </button>
              ))}
              {threads.length === 0 ? (
                <p className="px-2 py-4 text-xs text-muted-foreground">No conversations found.</p>
              ) : null}
            </div>
          </ScrollArea>
        </div>
        <div className="flex min-h-0 flex-col">
          <div className="flex items-center justify-between gap-3 border-b px-4 py-2 text-[11px] text-muted-foreground">
            <span>{activeResponseStatus ?? "Durable thread memory active."}</span>
            <div className="flex items-center gap-1">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setShowDebug((current) => !current)}
                disabled={messages.length === 0}
              >
                {showDebug ? "Hide debug" : "Show debug"}
              </Button>
              <Button type="button" variant="ghost" size="sm" onClick={onRegenerate} disabled={!threadId || isStreaming || messages.length === 0}>
                Regenerate
              </Button>
            </div>
          </div>
          <div className="min-h-0 flex-1">
            <MessageList
              messages={messages}
              isInitializing={!isHydrated || isInitializing || isRestoring}
              isOnline={isOnline}
              error={error}
              onQueueSignalProposalForReview={onQueueSignalProposalForReview}
              onRequestActionDraftApproval={onRequestActionDraftApproval}
              onExecutePaperActionDraft={onExecutePaperActionDraft}
              onSaveSignalProposalToWatchlist={onSaveSignalProposalToWatchlist}
              showDebug={showDebug}
            />
          </div>
          <ChatInput
            draft={draft}
            disabled={!isOnline || !isHydrated}
            isStreaming={isStreaming}
            textareaRef={textareaRef}
            onCancel={onCancel}
            onDraftChange={onDraftChange}
            onSubmit={onSubmit}
          />
        </div>
      </div>
    </aside>
  )
}
