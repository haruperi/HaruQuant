"use client"

import * as React from "react"
import { ChevronsLeftRight, NotebookPen, MoreVertical, Search } from "lucide-react"

import { ChatHeader } from "@/components/ai-chat/ChatHeader"
import { ChatInput } from "@/components/ai-chat/ChatInput"
import { MessageList } from "@/components/ai-chat/MessageList"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"
import type { ChatMessage } from "@/stores/chatWidgetStore"
import type { AiChatToolDefinition } from "@/lib/ai-chat/contracts"

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
  showArchivedThreads: boolean
  activeResponseStatus: string | null
  error: string | null
  draft: string
  availableTools: AiChatToolDefinition[]
  selectedToolIds: string[]
  autoApprovePageActions: boolean
  threads: {
    threadId: string
    title: string
    updatedAt: string
    pageType?: string | null
    status: "active" | "archived" | "deleted" | "purged"
    retentionClass: "standard" | "ephemeral" | "regulated" | "legal_hold"
  }[]
  messages: ChatMessage[]
  onCancel: () => void
  onArchiveThread: (threadId?: string) => void
  onRestoreThread: (threadId?: string) => void
  onClose: () => void
  onCreateThread: () => void
  onDeleteThread: (threadId?: string) => void
  onPurgeThread: (threadId?: string) => void
  onDraftChange: (value: string) => void
  onExportThread: (threadId?: string) => void
  onShowRetentionDetails: (threadId?: string) => void
  onMarkThreadEphemeral: (threadId?: string) => void
  onMarkThreadLegalHold: (threadId?: string) => void
  onQueueSignalProposalForReview: (proposalId: string) => void
  onRequestActionDraftApproval: (draftId: string) => void
  onExecutePaperActionDraft: (draftId: string) => void
  onExecutePageAction: (actionId: string, params: Record<string, unknown>) => void | Promise<void>
  onEnablePageActionAutoApproval: () => void
  onRegenerate: () => void
  onRenameThread: (value: string, threadId?: string) => void
  onSaveSignalProposalToWatchlist: (proposalId: string) => void
  onSelectThread: (value: string) => void
  onThreadSearchChange: (value: string) => void
  onToggleArchivedThreads: () => void
  onToggleTool: (toolId: string) => void
  onSubmit: () => void
}

const BASE_PANEL_WIDTH = 928
const BASE_PANEL_HEIGHT = 672
const MIN_PANEL_SCALE = 0.72
const MAX_PANEL_SCALE = 1.35
const PANEL_VIEWPORT_MARGIN = 48

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max)
}

function getMaxPanelScale(): number {
  if (typeof window === "undefined") {
    return 1
  }

  return Math.max(
    MIN_PANEL_SCALE,
    Math.min(
      MAX_PANEL_SCALE,
      (window.innerWidth - PANEL_VIEWPORT_MARGIN) / BASE_PANEL_WIDTH,
      (window.innerHeight - PANEL_VIEWPORT_MARGIN) / BASE_PANEL_HEIGHT,
    ),
  )
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

function retentionBadgeLabel(retentionClass: string): string | null {
  if (retentionClass === "legal_hold") {
    return "legal hold"
  }
  if (retentionClass === "regulated") {
    return "regulated"
  }
  if (retentionClass === "ephemeral") {
    return "30 days"
  }
  return null
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
  showArchivedThreads,
  activeResponseStatus,
  error,
  draft,
  availableTools,
  selectedToolIds,
  autoApprovePageActions,
  threads,
  messages,
  onCancel,
  onArchiveThread,
  onRestoreThread,
  onClose,
  onCreateThread,
  onDeleteThread,
  onPurgeThread,
  onDraftChange,
  onExportThread,
  onShowRetentionDetails,
  onMarkThreadEphemeral,
  onMarkThreadLegalHold,
  onQueueSignalProposalForReview,
  onRequestActionDraftApproval,
  onExecutePaperActionDraft,
  onExecutePageAction,
  onEnablePageActionAutoApproval,
  onRegenerate,
  onRenameThread,
  onSaveSignalProposalToWatchlist,
  onSelectThread,
  onThreadSearchChange,
  onToggleArchivedThreads,
  onToggleTool,
  onSubmit,
}: ChatPanelProps) {
  const panelRef = React.useRef<HTMLDivElement | null>(null)
  const searchInputRef = React.useRef<HTMLInputElement | null>(null)
  const textareaRef = React.useRef<HTMLTextAreaElement | null>(null)
  const [showDebug, setShowDebug] = React.useState(false)
  const [panelScale, setPanelScale] = React.useState(1)
  const [isResizing, setIsResizing] = React.useState(false)
  const resizeStartRef = React.useRef<{ x: number; scale: number } | null>(null)

  React.useEffect(() => {
    setPanelScale((current) => clamp(current, MIN_PANEL_SCALE, getMaxPanelScale()))

    const handleResize = () => {
      setPanelScale((current) => clamp(current, MIN_PANEL_SCALE, getMaxPanelScale()))
    }

    window.addEventListener("resize", handleResize)
    return () => window.removeEventListener("resize", handleResize)
  }, [])

  React.useEffect(() => {
    if (!isResizing) {
      return
    }

    const handlePointerMove = (event: PointerEvent) => {
      const start = resizeStartRef.current
      if (!start) {
        return
      }

      const widthDelta = start.x - event.clientX
      const nextWidth = BASE_PANEL_WIDTH * start.scale + widthDelta
      setPanelScale(clamp(nextWidth / BASE_PANEL_WIDTH, MIN_PANEL_SCALE, getMaxPanelScale()))
    }

    const handlePointerUp = () => {
      resizeStartRef.current = null
      setIsResizing(false)
      document.body.style.cursor = ""
      document.body.style.userSelect = ""
    }

    document.body.style.cursor = "ew-resize"
    document.body.style.userSelect = "none"
    window.addEventListener("pointermove", handlePointerMove)
    window.addEventListener("pointerup", handlePointerUp)
    return () => {
      window.removeEventListener("pointermove", handlePointerMove)
      window.removeEventListener("pointerup", handlePointerUp)
      document.body.style.cursor = ""
      document.body.style.userSelect = ""
    }
  }, [isResizing])

  const handleResizeStart = React.useCallback((event: React.PointerEvent<HTMLButtonElement>) => {
    event.preventDefault()
    event.currentTarget.setPointerCapture(event.pointerId)
    resizeStartRef.current = { x: event.clientX, scale: panelScale }
    setIsResizing(true)
  }, [panelScale])

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
      const target = event.target
      const isTextEntry =
        target instanceof HTMLInputElement
        || target instanceof HTMLTextAreaElement
        || target instanceof HTMLSelectElement
        || (target instanceof HTMLElement && target.isContentEditable)

      if (event.key === "Escape") {
        event.preventDefault()
        onClose()
        return
      }

      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "n") {
        event.preventDefault()
        onCreateThread()
        return
      }

      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "e") {
        event.preventDefault()
        onExportThread(threadId ?? undefined)
        return
      }

      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "r") {
        event.preventDefault()
        onRegenerate()
        return
      }

      if (event.key === "/" && !isTextEntry) {
        event.preventDefault()
        searchInputRef.current?.focus()
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
  }, [isOpen, onClose, onCreateThread, onExportThread, onRegenerate, threadId])

  const handleRename = React.useCallback((targetThreadId: string, currentTitle: string) => {
    const nextTitle = window.prompt("Rename conversation", currentTitle)
    if (nextTitle && nextTitle.trim()) {
      onRenameThread(nextTitle.trim(), targetThreadId)
    }
  }, [onRenameThread])

  const latestAssistantMessage = React.useMemo(
    () => [...messages].reverse().find((message) => message.role === "assistant"),
    [messages],
  )
  const runtimeMeta = React.useMemo(
    () => formatRuntimeMeta(latestAssistantMessage),
    [latestAssistantMessage],
  )
  const isRetentionStatus = activeResponseStatus?.startsWith("Retention:")

  return (
    <aside
      aria-hidden={!isOpen}
      aria-label="HaruQuant AI chat panel"
      role="dialog"
      ref={panelRef}
      style={{
        "--chat-panel-width": `${BASE_PANEL_WIDTH * panelScale}px`,
        "--chat-panel-height": `${BASE_PANEL_HEIGHT * panelScale}px`,
        "--chat-content-scale": String(panelScale),
      } as React.CSSProperties}
      className={cn(
        "fixed inset-x-0 bottom-0 z-40 flex h-[78vh] max-h-[78vh] flex-col overflow-hidden border bg-background shadow-xl transition-all duration-200 md:inset-x-auto md:bottom-6 md:right-6 md:h-[var(--chat-panel-height)] md:max-h-[calc(100vh-3rem)] md:w-[var(--chat-panel-width)] md:rounded-md",
        isOpen
          ? "translate-y-0 opacity-100"
          : "pointer-events-none translate-y-4 opacity-0 md:translate-y-2",
        isResizing && "transition-none",
      )}
    >
      <button
        type="button"
        aria-label="Resize AI chat"
        onPointerDown={handleResizeStart}
        className={cn(
          "group absolute inset-y-0 left-0 z-10 hidden w-4 cursor-ew-resize items-center justify-center border-l border-transparent bg-background/0 text-muted-foreground transition-colors hover:bg-muted/50 hover:text-foreground md:flex",
          isResizing && "bg-muted/60 text-foreground",
        )}
      >
        <span className={cn("rounded-sm border bg-background px-1 py-2 opacity-0 shadow-sm transition-opacity", isResizing && "opacity-100", "group-hover:opacity-100")} aria-hidden="true">
          <ChevronsLeftRight className="h-4 w-4" />
        </span>
      </button>
      <div className="flex h-full min-h-0 flex-col md:h-[calc(100%/var(--chat-content-scale))] md:w-[calc(100%/var(--chat-content-scale))] md:origin-top-left md:scale-[var(--chat-content-scale)]">
        <ChatHeader
          isOnline={isOnline}
          isRestoring={isRestoring}
          threadTitle={threadTitle}
          activeResponseStatus={activeResponseStatus}
          runtimeMeta={runtimeMeta}
          onClose={onClose}
        />
        <div className="grid min-h-0 flex-1 gap-0 md:grid-cols-[16rem_minmax(0,1fr)]">
          <div className="min-w-0 overflow-hidden flex flex-col border-b md:border-b-0 md:border-r">
            <div className="space-y-2 p-3">
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  ref={searchInputRef}
                  value={threadSearch}
                  onChange={(event) => onThreadSearchChange(event.target.value)}
                  placeholder="Search chats..."
                  aria-label="Search chats"
                  aria-keyshortcuts="/"
                  className="rounded-md pl-9"
                />
              </div>
              <div>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={onCreateThread}
                  disabled={isManagingThreads || isStreaming}
                  aria-keyshortcuts="Control+N Meta+N"
                  className="w-full justify-start gap-2 border-transparent bg-transparent shadow-none hover:border-border hover:bg-background focus-visible:border-ring"
                >
                  <NotebookPen className="h-4 w-4" />
                  New chat
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={onToggleArchivedThreads}
                  disabled={isManagingThreads || isStreaming}
                  className="mt-1 w-full justify-start text-xs"
                >
                  {showArchivedThreads ? "Hide archived" : "Show archived"}
                </Button>
              </div>
            </div>
            <ScrollArea className="h-40 min-w-0 border-t md:h-[calc(100%-5.5rem)]">
              <div className="min-w-0 space-y-1 p-2">
                {threads.map((thread) => (
                  <div
                    key={thread.threadId}
                    className={cn(
                      "group grid min-w-0 grid-cols-[minmax(0,1fr)_2rem] items-center overflow-hidden rounded-md border",
                      thread.threadId === threadId ? "border-primary bg-muted/40" : "hover:bg-muted/30",
                    )}
                  >
                    <button
                      type="button"
                      onClick={() => onSelectThread(thread.threadId)}
                      className="block min-w-0 overflow-hidden rounded-l-md px-3 py-2 text-left text-sm"
                    >
                      <div className="min-w-0 truncate font-medium">{thread.title}</div>
                      <div className="mt-1 flex min-w-0 items-center gap-1.5 text-[11px] text-muted-foreground">
                        {thread.status === "archived" ? (
                          <span className="shrink-0 rounded-sm border px-1 py-0.5">archived</span>
                        ) : null}
                        {retentionBadgeLabel(thread.retentionClass) ? (
                          <span
                            className={cn(
                              "shrink-0 rounded-sm border px-1 py-0.5",
                              thread.retentionClass === "legal_hold" && "border-amber-500/50 bg-amber-500/10 text-amber-700 dark:text-amber-300",
                              thread.retentionClass === "regulated" && "border-sky-500/50 bg-sky-500/10 text-sky-700 dark:text-sky-300",
                              thread.retentionClass === "ephemeral" && "border-emerald-500/50 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
                            )}
                          >
                            {retentionBadgeLabel(thread.retentionClass)}
                          </span>
                        ) : null}
                        <span className="min-w-0 truncate">
                          {thread.pageType ?? "generic"} | {formatUpdatedAt(thread.updatedAt)}
                        </span>
                      </div>
                    </button>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          aria-label={`Conversation actions for ${thread.title}`}
                          disabled={isManagingThreads || isStreaming}
                          className={cn(
                            "h-7 w-7 bg-background/80 transition-opacity hover:bg-muted",
                            thread.threadId === threadId
                              ? "opacity-100"
                              : "opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 data-[state=open]:opacity-100"
                          )}
                        >
                          <MoreVertical className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => handleRename(thread.threadId, thread.title)}>
                          Rename
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => onExportThread(thread.threadId)}>
                          Export
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => onShowRetentionDetails(thread.threadId)}>
                          Retention
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => onMarkThreadEphemeral(thread.threadId)}>
                          Keep 30 days
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => onMarkThreadLegalHold(thread.threadId)}>
                          Legal hold
                        </DropdownMenuItem>
                        {thread.status === "archived" ? (
                          <DropdownMenuItem onClick={() => onRestoreThread(thread.threadId)}>
                            Restore
                          </DropdownMenuItem>
                        ) : (
                          <DropdownMenuItem onClick={() => onArchiveThread(thread.threadId)}>
                            Archive
                          </DropdownMenuItem>
                        )}
                        <DropdownMenuItem onClick={() => onPurgeThread(thread.threadId)}>
                          Purge
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onClick={() => onDeleteThread(thread.threadId)}
                          className="text-destructive focus:text-destructive"
                        >
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
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
                <Button type="button" variant="ghost" size="sm" onClick={onRegenerate} disabled={!threadId || isStreaming || messages.length === 0} aria-keyshortcuts="Control+R Meta+R">
                  Regenerate
                </Button>
              </div>
            </div>
            {isRetentionStatus ? (
              <div className="border-b bg-muted/40 px-4 py-2 text-xs text-foreground">
                {activeResponseStatus}
              </div>
            ) : null}
            <div className="min-h-0 flex-1">
              <MessageList
                messages={messages}
                isInitializing={!isHydrated || isInitializing || isRestoring}
                isOnline={isOnline}
                error={error}
                onQueueSignalProposalForReview={onQueueSignalProposalForReview}
                onRequestActionDraftApproval={onRequestActionDraftApproval}
                onExecutePaperActionDraft={onExecutePaperActionDraft}
                onExecutePageAction={onExecutePageAction}
                onEnablePageActionAutoApproval={onEnablePageActionAutoApproval}
                onSaveSignalProposalToWatchlist={onSaveSignalProposalToWatchlist}
                autoApprovePageActions={autoApprovePageActions}
                showDebug={showDebug}
              />
            </div>
            <ChatInput
              draft={draft}
              disabled={!isOnline || !isHydrated}
              isStreaming={isStreaming}
              textareaRef={textareaRef}
              availableTools={availableTools}
              selectedToolIds={selectedToolIds}
              onCancel={onCancel}
              onDraftChange={onDraftChange}
              onToggleTool={onToggleTool}
              onSubmit={onSubmit}
            />
          </div>
        </div>
      </div>
    </aside>
  )
}
