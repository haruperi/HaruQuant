"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { ChatLauncher } from "@/components/ai-chat/ChatLauncher"
import { ChatPanel } from "@/components/ai-chat/ChatPanel"
import { Sidebar } from "@/components/layout/sidebar"
import { Navbar } from "@/components/layout/navbar"
import { ChatWidgetStoreProvider, useChatWidgetStore } from "@/stores/chatWidgetStore"
import { PageContextProvider } from "@/providers/PageContextProvider"
import { useRegisterPageActions } from "@/hooks/useRegisterPageActions"

function GlobalPageActions() {
  const router = useRouter()

  useRegisterPageActions(
    React.useMemo(() => [
      {
        id: "navigate_app_page",
        label: "Navigate App Page",
        description: "Navigate to a top-level HaruQuant app page such as Simulation, Strategies, Optimization, Performance, Live, Operator, Settings, Documentation, Tools, or Edge Lab.",
        riskLevel: "view_only" as const,
        parameters: [
          {
            name: "path",
            type: "string",
            description: "Absolute app route, for example /simulation, /strategies, /optimization, /performance/trades-calender, or /live.",
            required: true,
          },
        ],
      },
      {
        id: "generic_dom_click",
        label: "Click Visible UI Element",
        description: "Click a visible low-risk button, link, tab, menu item, or other local UI control from the current page snapshot.",
        riskLevel: "local_ui" as const,
        parameters: [
          {
            name: "selector",
            type: "string",
            description: "Generated selector for the visible UI element from the current DOM snapshot.",
            required: true,
          },
          {
            name: "label",
            type: "string",
            description: "Human-readable label of the target element.",
            required: false,
          },
        ],
      },
    ], []),
    React.useMemo(() => ({
      navigate_app_page: ({ path }) => {
        if (typeof path !== "string" || !path.startsWith("/")) {
          return
        }
        router.push(path)
      },
      generic_dom_click: ({ selector, label }) => {
        if (typeof selector !== "string" || !selector.startsWith("[data-ai-chat-actionable=")) {
          return
        }
        const element = document.querySelector(selector)
        if (!(element instanceof HTMLElement)) {
          return
        }
        const text = `${label ?? ""} ${element.getAttribute("aria-label") ?? ""} ${element.textContent ?? ""}`.toLowerCase()
        const blocked = ["delete", "remove", "place order", "buy ", "sell ", "execute", "start live", "stop live"]
        if (blocked.some((term) => text.includes(term))) {
          throw new Error("Generic DOM click refused a high-risk target.")
        }
        if (element.hasAttribute("disabled") || element.getAttribute("aria-disabled") === "true") {
          return
        }
        element.click()
      },
    }), [router]),
  )

  return null
}

function GlobalChatWidget() {
  const {
    close,
    createNewThread,
    deleteThread,
    draft,
    error,
    exportThread,
    activeResponseStatus,
    availableTools,
    isHydrated,
    isInitializing,
    isManagingThreads,
    isOnline,
    isOpen,
    isRestoring,
    isStreaming,
    messages,
    autoApprovePageActions,
    enablePageActionAutoApproval,
    regenerateLastResponse,
    queueSignalProposalForReview,
    requestActionDraftApproval,
    executePaperActionDraft,
    executePageAction,
    cancelStream,
    open,
    renameThread,
    saveSignalProposalToWatchlist,
    setDraft,
    setThreadSearch,
    selectedToolIds,
    selectThread,
    submitDraft,
    toggleTool,
    threadId,
    threadSearch,
    threadTitle,
    threads,
  } = useChatWidgetStore()

  return (
    <>
      <ChatLauncher onOpen={open} hidden={isOpen} />
      <ChatPanel
        isOpen={isOpen}
        isHydrated={isHydrated}
        isInitializing={isInitializing}
        isOnline={isOnline}
        isRestoring={isRestoring}
        isStreaming={isStreaming}
        isManagingThreads={isManagingThreads}
        threadTitle={threadTitle}
        threadId={threadId}
        threadSearch={threadSearch}
        activeResponseStatus={activeResponseStatus}
        error={error}
        draft={draft}
        availableTools={availableTools}
        selectedToolIds={selectedToolIds}
        threads={threads}
        messages={messages}
        autoApprovePageActions={autoApprovePageActions}
        onCancel={cancelStream}
        onClose={close}
        onCreateThread={createNewThread}
        onDeleteThread={deleteThread}
        onDraftChange={setDraft}
        onExportThread={exportThread}
        onQueueSignalProposalForReview={queueSignalProposalForReview}
        onRequestActionDraftApproval={requestActionDraftApproval}
        onExecutePaperActionDraft={executePaperActionDraft}
        onExecutePageAction={executePageAction}
        onEnablePageActionAutoApproval={enablePageActionAutoApproval}
        onRegenerate={regenerateLastResponse}
        onRenameThread={renameThread}
        onSaveSignalProposalToWatchlist={saveSignalProposalToWatchlist}
        onSelectThread={selectThread}
        onThreadSearchChange={setThreadSearch}
        onToggleTool={toggleTool}
        onSubmit={submitDraft}
      />
    </>
  )
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const [isCollapsed, setIsCollapsed] = React.useState(true)

  return (
    <PageContextProvider>
      <GlobalPageActions />
      <ChatWidgetStoreProvider>
        <div className="flex h-screen w-full overflow-hidden bg-background font-sans antialiased text-foreground">
          <Sidebar isCollapsed={isCollapsed} setIsCollapsed={setIsCollapsed} />
          <div className="flex flex-col flex-1 w-0 overflow-hidden">
            <Navbar onMenuClick={() => setIsCollapsed(!isCollapsed)} />
            <main className="flex-1 overflow-y-auto p-4 md:p-6 bg-muted/20">
                {children}
            </main>
          </div>
          <GlobalChatWidget />
        </div>
      </ChatWidgetStoreProvider>
    </PageContextProvider>
  )
}
