"use client"

import * as React from "react"
import { ChatLauncher } from "@/components/ai-chat/ChatLauncher"
import { ChatPanel } from "@/components/ai-chat/ChatPanel"
import { Sidebar } from "@/components/layout/sidebar"
import { Navbar } from "@/components/layout/navbar"
import { ChatWidgetStoreProvider, useChatWidgetStore } from "@/stores/chatWidgetStore"
import { PageContextProvider } from "@/providers/PageContextProvider"

function GlobalChatWidget() {
  const {
    close,
    createNewThread,
    deleteThread,
    draft,
    error,
    exportThread,
    activeResponseStatus,
    isHydrated,
    isInitializing,
    isManagingThreads,
    isOnline,
    isOpen,
    isRestoring,
    isStreaming,
    messages,
    regenerateLastResponse,
    queueSignalProposalForReview,
    requestActionDraftApproval,
    executePaperActionDraft,
    cancelStream,
    open,
    renameThread,
    saveSignalProposalToWatchlist,
    setDraft,
    setThreadSearch,
    selectThread,
    submitDraft,
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
        threads={threads}
        messages={messages}
        onCancel={cancelStream}
        onClose={close}
        onCreateThread={createNewThread}
        onDeleteThread={deleteThread}
        onDraftChange={setDraft}
        onExportThread={exportThread}
        onQueueSignalProposalForReview={queueSignalProposalForReview}
        onRequestActionDraftApproval={requestActionDraftApproval}
        onExecutePaperActionDraft={executePaperActionDraft}
        onRegenerate={regenerateLastResponse}
        onRenameThread={renameThread}
        onSaveSignalProposalToWatchlist={saveSignalProposalToWatchlist}
        onSelectThread={selectThread}
        onThreadSearchChange={setThreadSearch}
        onSubmit={submitDraft}
      />
    </>
  )
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const [isCollapsed, setIsCollapsed] = React.useState(true)

  return (
    <PageContextProvider>
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
