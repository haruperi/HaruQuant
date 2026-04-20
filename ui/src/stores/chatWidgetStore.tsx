"use client"

import * as React from "react"

import {
  createAiChatThread,
  deleteAiChatThread,
  exportAiChatThread,
  getAiChatThread,
  listAiChatThreads,
  regenerateAiChatResponse,
  renameAiChatThread,
  searchAiChatThreads,
  streamAiChatResponse,
  updateAiChatThreadContext,
} from "@/lib/api/ai-chat"
import type {
  AiChatMessage,
  AiChatResponseMetadata,
  AiChatThreadDetail,
  AiChatThreadSummary,
} from "@/lib/ai-chat/contracts"
import { useAuth } from "@/lib/auth-context"
import { usePageContext } from "@/hooks/usePageContext"

type ChatRole = "user" | "assistant"

export interface ChatMessage {
  id: string
  role: ChatRole
  content: string
  createdAt: string
  toolCalls?: string[]
  requestId?: string | null
  responseStyle?: string
  taskClass?: string
  domainFocus?: string
  status?: "ready" | "pending"
}

export interface ChatThreadListItem {
  threadId: string
  title: string
  updatedAt: string
  pageType?: string | null
}

interface ChatWidgetStoreValue {
  isOpen: boolean
  isHydrated: boolean
  isInitializing: boolean
  isOnline: boolean
  isRestoring: boolean
  isStreaming: boolean
  isManagingThreads: boolean
  draft: string
  messages: ChatMessage[]
  threads: ChatThreadListItem[]
  threadSearch: string
  threadId: string | null
  threadTitle: string
  activeResponseStatus: string | null
  error: string | null
  open: () => void
  close: () => void
  toggle: () => void
  setDraft: (value: string) => void
  setThreadSearch: (value: string) => void
  createNewThread: () => Promise<void>
  selectThread: (value: string) => Promise<void>
  renameThread: (value: string) => Promise<void>
  deleteThread: () => Promise<void>
  exportThread: () => Promise<void>
  submitDraft: () => Promise<void>
  regenerateLastResponse: () => Promise<void>
  cancelStream: () => void
}

const STORAGE_KEYS = {
  open: "haruquant.ai_chat.open",
  draft: "haruquant.ai_chat.draft",
  activeThreadId: "haruquant.ai_chat.active_thread_id",
} as const

const DEFAULT_THREAD_TITLE = "New conversation"
const ChatWidgetStoreContext = React.createContext<ChatWidgetStoreValue | null>(null)

function mapApiMessage(
  message: AiChatMessage,
  metadataByRequestId: Record<string, AiChatResponseMetadata>,
): ChatMessage {
  const responseMetadata = message.request_id ? metadataByRequestId[message.request_id] : undefined
  return {
    id: message.message_id,
    role: message.role === "assistant" ? "assistant" : "user",
    content: message.content,
    createdAt: message.created_at,
    toolCalls: message.tool_calls,
    requestId: message.request_id,
    responseStyle: responseMetadata?.response_style,
    taskClass: responseMetadata?.task_class,
    domainFocus: responseMetadata?.domain_focus,
    status: "ready",
  }
}

function mapThreadSummary(thread: AiChatThreadSummary): ChatThreadListItem {
  return {
    threadId: thread.thread_id,
    title: thread.title,
    updatedAt: thread.last_message_at ?? thread.updated_at,
    pageType: thread.current_page_type,
  }
}

function makePendingAssistant(): ChatMessage {
  const idSuffix = typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}_${Math.random().toString(16).slice(2)}`
  return {
    id: `assistant_pending_${idSuffix}`,
    role: "assistant",
    content: "",
    createdAt: new Date().toISOString(),
    status: "pending",
  }
}

function extractResponseMetadata(payload: Record<string, unknown>): AiChatResponseMetadata | null {
  const requestId = typeof payload.request_id === "string" ? payload.request_id : undefined
  if (!requestId) {
    return null
  }
  return {
    request_id: requestId,
    response_mode: typeof payload.response_mode === "string" ? payload.response_mode as AiChatResponseMetadata["response_mode"] : undefined,
    response_style: typeof payload.response_style === "string" ? payload.response_style : undefined,
    task_class: typeof payload.task_class === "string" ? payload.task_class : undefined,
    domain_focus: typeof payload.domain_focus === "string" ? payload.domain_focus : undefined,
    tools_used: Array.isArray(payload.tools_used) ? payload.tools_used.filter((value): value is string => typeof value === "string") : undefined,
  }
}

export function ChatWidgetStoreProvider({ children }: { children: React.ReactNode }) {
  const { authenticatedFetch, isAuthenticated, isLoading } = useAuth()
  const { pageContext } = usePageContext()
  const [isOpen, setIsOpen] = React.useState(false)
  const [draft, setDraftState] = React.useState("")
  const [messages, setMessages] = React.useState<ChatMessage[]>([])
  const [threads, setThreads] = React.useState<ChatThreadListItem[]>([])
  const [isHydrated, setIsHydrated] = React.useState(false)
  const [isInitializing, setIsInitializing] = React.useState(false)
  const [hasOpenedOnce, setHasOpenedOnce] = React.useState(false)
  const [isOnline, setIsOnline] = React.useState(true)
  const [isRestoring, setIsRestoring] = React.useState(false)
  const [isStreaming, setIsStreaming] = React.useState(false)
  const [isManagingThreads, setIsManagingThreads] = React.useState(false)
  const [threadSearch, setThreadSearchState] = React.useState("")
  const [threadId, setThreadId] = React.useState<string | null>(null)
  const [threadTitle, setThreadTitle] = React.useState(DEFAULT_THREAD_TITLE)
  const [activeResponseStatus, setActiveResponseStatus] = React.useState<string | null>(null)
  const [error, setError] = React.useState<string | null>(null)
  const abortControllerRef = React.useRef<AbortController | null>(null)
  const responseMetadataRef = React.useRef<Record<string, AiChatResponseMetadata>>({})

  React.useEffect(() => {
    if (typeof window === "undefined") {
      return
    }

    setIsOpen(window.localStorage.getItem(STORAGE_KEYS.open) === "true")
    setDraftState(window.localStorage.getItem(STORAGE_KEYS.draft) ?? "")
    setThreadId(window.localStorage.getItem(STORAGE_KEYS.activeThreadId))
    setIsOnline(window.navigator.onLine)
    setIsHydrated(true)
  }, [])

  React.useEffect(() => {
    if (!isHydrated || typeof window === "undefined") {
      return
    }
    window.localStorage.setItem(STORAGE_KEYS.open, String(isOpen))
  }, [isHydrated, isOpen])

  React.useEffect(() => {
    if (!isHydrated || typeof window === "undefined") {
      return
    }
    window.localStorage.setItem(STORAGE_KEYS.draft, draft)
  }, [draft, isHydrated])

  React.useEffect(() => {
    if (!isHydrated || typeof window === "undefined") {
      return
    }
    if (threadId) {
      window.localStorage.setItem(STORAGE_KEYS.activeThreadId, threadId)
      return
    }
    window.localStorage.removeItem(STORAGE_KEYS.activeThreadId)
  }, [isHydrated, threadId])

  React.useEffect(() => {
    if (typeof window === "undefined") {
      return
    }

    const onOnline = () => setIsOnline(true)
    const onOffline = () => setIsOnline(false)

    window.addEventListener("online", onOnline)
    window.addEventListener("offline", onOffline)

    return () => {
      window.removeEventListener("online", onOnline)
      window.removeEventListener("offline", onOffline)
    }
  }, [])

  const syncThread = React.useCallback((thread: AiChatThreadDetail) => {
    setThreadId(thread.thread_id)
    setThreadTitle(thread.title)
    setMessages(
      thread.messages
        .filter((message) => message.role === "user" || message.role === "assistant")
        .map((message) => mapApiMessage(message, responseMetadataRef.current)),
    )
  }, [])

  const rememberResponseMetadata = React.useCallback((payload: Record<string, unknown>) => {
    const metadata = extractResponseMetadata(payload)
    if (!metadata?.request_id) {
      return
    }
    responseMetadataRef.current[metadata.request_id] = metadata
  }, [])

  const refreshThreadList = React.useCallback(async (query?: string) => {
    if (!isAuthenticated) {
      setThreads([])
      return
    }
    const listed = query && query.trim().length > 0
      ? await searchAiChatThreads(authenticatedFetch, query.trim())
      : await listAiChatThreads(authenticatedFetch)
    setThreads(listed.map(mapThreadSummary))
  }, [authenticatedFetch, isAuthenticated])

  const ensureThread = React.useCallback(async () => {
    if (!isAuthenticated) {
      return null
    }

    if (threadId) {
      const existing = await getAiChatThread(authenticatedFetch, threadId)
      syncThread(existing)
      return existing
    }

    const listed = await listAiChatThreads(authenticatedFetch)
    setThreads(listed.map(mapThreadSummary))
    const selected = listed[0]

    if (selected) {
      const existing = await getAiChatThread(authenticatedFetch, selected.thread_id)
      syncThread(existing)
      return existing
    }

    const created = await createAiChatThread(authenticatedFetch, {
      current_route: pageContext?.route,
      current_page_type: pageContext?.page_type,
      active_context_revision: pageContext?.context_revision,
    })
    syncThread(created)
    await refreshThreadList()
    return created
  }, [
    authenticatedFetch,
    isAuthenticated,
    pageContext?.context_revision,
    pageContext?.page_type,
    pageContext?.route,
    refreshThreadList,
    syncThread,
    threadId,
  ])

  React.useEffect(() => {
    if (!isHydrated || isLoading || !isAuthenticated) {
      return
    }

    let isMounted = true

    async function restoreThread() {
      setIsRestoring(true)
      setError(null)
      try {
        const restored = await ensureThread()
        if (!isMounted || !restored) {
          return
        }
        await refreshThreadList(threadSearch)
        await updateAiChatThreadContext(authenticatedFetch, restored.thread_id, {
          current_route: pageContext?.route,
          current_page_type: pageContext?.page_type,
          active_context_revision: pageContext?.context_revision,
        })
      } catch (restoreError) {
        console.error("Failed to restore AI chat thread:", restoreError)
        if (isMounted) {
          setError("Unable to restore conversation history.")
        }
      } finally {
        if (isMounted) {
          setIsRestoring(false)
        }
      }
    }

    void restoreThread()

    return () => {
      isMounted = false
    }
  }, [
    authenticatedFetch,
    ensureThread,
    isAuthenticated,
    isHydrated,
    isLoading,
    pageContext?.context_revision,
    pageContext?.page_type,
    pageContext?.route,
    refreshThreadList,
    threadSearch,
  ])

  React.useEffect(() => {
    if (!isAuthenticated || !isHydrated) {
      return
    }
    void refreshThreadList(threadSearch)
  }, [isAuthenticated, isHydrated, refreshThreadList, threadSearch])

  const beginInitialization = React.useCallback(() => {
    if (hasOpenedOnce) {
      return
    }
    setHasOpenedOnce(true)
    setIsInitializing(true)
    window.setTimeout(() => setIsInitializing(false), 350)
  }, [hasOpenedOnce])

  const open = React.useCallback(() => {
    setIsOpen(true)
    if (typeof window !== "undefined") {
      beginInitialization()
    }
  }, [beginInitialization])

  const close = React.useCallback(() => {
    setIsOpen(false)
  }, [])

  const toggle = React.useCallback(() => {
    setIsOpen((current) => {
      const next = !current
      if (next && typeof window !== "undefined") {
        beginInitialization()
      }
      return next
    })
  }, [beginInitialization])

  const setDraft = React.useCallback((value: string) => {
    setDraftState(value)
  }, [])

  const setThreadSearch = React.useCallback((value: string) => {
    setThreadSearchState(value)
  }, [])

  const cancelStream = React.useCallback(() => {
    abortControllerRef.current?.abort()
    abortControllerRef.current = null
    setIsStreaming(false)
    setActiveResponseStatus(null)
  }, [])

  const createNewThread = React.useCallback(async () => {
    if (!isAuthenticated || isStreaming) {
      return
    }
    setIsManagingThreads(true)
    setError(null)
    try {
      const created = await createAiChatThread(authenticatedFetch, {
        current_route: pageContext?.route,
        current_page_type: pageContext?.page_type,
        active_context_revision: pageContext?.context_revision,
      })
      syncThread(created)
      setMessages([])
      setDraftState("")
      await refreshThreadList(threadSearch)
    } catch (threadError) {
      console.error("Failed to create AI chat thread:", threadError)
      setError("Unable to create a new conversation.")
    } finally {
      setIsManagingThreads(false)
    }
  }, [
    authenticatedFetch,
    isAuthenticated,
    isStreaming,
    pageContext?.context_revision,
    pageContext?.page_type,
    pageContext?.route,
    refreshThreadList,
    syncThread,
    threadSearch,
  ])

  const selectThread = React.useCallback(async (value: string) => {
    if (!isAuthenticated || isStreaming) {
      return
    }
    setIsManagingThreads(true)
    setError(null)
    try {
      const selected = await getAiChatThread(authenticatedFetch, value)
      syncThread(selected)
      await updateAiChatThreadContext(authenticatedFetch, value, {
        current_route: pageContext?.route,
        current_page_type: pageContext?.page_type,
        active_context_revision: pageContext?.context_revision,
      })
    } catch (threadError) {
      console.error("Failed to select AI chat thread:", threadError)
      setError("Unable to load the selected conversation.")
    } finally {
      setIsManagingThreads(false)
    }
  }, [
    authenticatedFetch,
    isAuthenticated,
    isStreaming,
    pageContext?.context_revision,
    pageContext?.page_type,
    pageContext?.route,
    syncThread,
  ])

  const renameThread = React.useCallback(async (value: string) => {
    if (!threadId || !isAuthenticated) {
      return
    }
    setIsManagingThreads(true)
    setError(null)
    try {
      const renamed = await renameAiChatThread(authenticatedFetch, threadId, { title: value })
      syncThread(renamed)
      await refreshThreadList(threadSearch)
    } catch (threadError) {
      console.error("Failed to rename AI chat thread:", threadError)
      setError("Unable to rename the conversation.")
    } finally {
      setIsManagingThreads(false)
    }
  }, [authenticatedFetch, isAuthenticated, refreshThreadList, syncThread, threadId, threadSearch])

  const deleteThread = React.useCallback(async () => {
    if (!threadId || !isAuthenticated || isStreaming) {
      return
    }
    setIsManagingThreads(true)
    setError(null)
    try {
      await deleteAiChatThread(authenticatedFetch, threadId)
      setThreadId(null)
      setThreadTitle(DEFAULT_THREAD_TITLE)
      setMessages([])
      await refreshThreadList(threadSearch)
      const listed = threadSearch.trim().length > 0
        ? await searchAiChatThreads(authenticatedFetch, threadSearch.trim())
        : await listAiChatThreads(authenticatedFetch)
      const fallback = listed[0]
      if (fallback) {
        const selected = await getAiChatThread(authenticatedFetch, fallback.thread_id)
        syncThread(selected)
      }
    } catch (threadError) {
      console.error("Failed to delete AI chat thread:", threadError)
      setError("Unable to delete the conversation.")
    } finally {
      setIsManagingThreads(false)
    }
  }, [
    authenticatedFetch,
    isAuthenticated,
    isStreaming,
    refreshThreadList,
    syncThread,
    threadId,
    threadSearch,
  ])

  const exportThread = React.useCallback(async () => {
    if (!threadId || !isAuthenticated) {
      return
    }
    setError(null)
    try {
      const exported = await exportAiChatThread(authenticatedFetch, threadId, "markdown")
      if (typeof window !== "undefined" && navigator.clipboard) {
        await navigator.clipboard.writeText(exported)
      }
      setActiveResponseStatus("Conversation export copied to clipboard.")
    } catch (threadError) {
      console.error("Failed to export AI chat thread:", threadError)
      setError("Unable to export the conversation.")
    }
  }, [authenticatedFetch, isAuthenticated, threadId])

  const submitDraft = React.useCallback(async () => {
    const trimmed = draft.trim()
    if (!trimmed || !isOnline || !isAuthenticated || isStreaming) {
      return
    }

    setError(null)
    const pendingAssistant = makePendingAssistant()
    setMessages((current) => [
      ...current,
      {
        id: `user_local_${Date.now()}`,
        role: "user",
        content: trimmed,
        createdAt: new Date().toISOString(),
        status: "ready",
      },
      pendingAssistant,
    ])
    setDraftState("")
    setIsStreaming(true)
    setActiveResponseStatus("Streaming response...")
    const controller = new AbortController()
    abortControllerRef.current = controller

    try {
      const activeThread = await ensureThread()
      if (!activeThread) {
        throw new Error("No active thread available")
      }

      await streamAiChatResponse(
        authenticatedFetch,
        activeThread.thread_id,
        {
          prompt: trimmed,
        },
        {
          onMeta: (payload) => {
            rememberResponseMetadata(payload)
            const metadata = extractResponseMetadata(payload)
            setMessages((current) =>
              current.map((message) =>
                message.id === pendingAssistant.id
                  ? {
                      ...message,
                      responseStyle: metadata?.response_style,
                      taskClass: metadata?.task_class,
                      domainFocus: metadata?.domain_focus,
                    }
                  : message,
              ),
            )
            const responseStyle = metadata?.response_style ?? "summary"
            setActiveResponseStatus(`Assistant is grounded on current HaruQuant state (${responseStyle}).`)
          },
          onToken: (delta) => {
            setMessages((current) =>
              current.map((message) =>
                message.id === pendingAssistant.id
                  ? {
                      ...message,
                      content: `${message.content}${delta}`,
                    }
                  : message,
              ),
            )
          },
          onDone: async () => {
            const refreshed = await getAiChatThread(authenticatedFetch, activeThread.thread_id)
            syncThread(refreshed)
            await refreshThreadList(threadSearch)
            setActiveResponseStatus("Response complete.")
          },
          onError: (message) => {
            setError(message)
            setActiveResponseStatus(null)
          },
        },
        controller.signal,
      )
    } catch (submitError) {
      if (submitError instanceof DOMException && submitError.name === "AbortError") {
        setError("Response stopped.")
      } else {
        console.error("Failed to stream AI chat response:", submitError)
        setError("AI response failed. Draft was restored.")
      }
      setDraftState(trimmed)
      setMessages((current) => current.filter((message) => message.id !== pendingAssistant.id))
      return
    } finally {
      abortControllerRef.current = null
      setIsStreaming(false)
    }
  }, [
    authenticatedFetch,
    draft,
    ensureThread,
    isAuthenticated,
    isOnline,
    isStreaming,
    refreshThreadList,
    rememberResponseMetadata,
    syncThread,
    threadSearch,
  ])

  const regenerateLastResponse = React.useCallback(async () => {
    if (!threadId || !isAuthenticated || !isOnline || isStreaming) {
      return
    }

    setError(null)
    const pendingAssistant = makePendingAssistant()
    setMessages((current) => [...current, pendingAssistant])
    setIsStreaming(true)
    setActiveResponseStatus("Regenerating last response...")
    const controller = new AbortController()
    abortControllerRef.current = controller

    try {
      await regenerateAiChatResponse(
        authenticatedFetch,
        threadId,
        {},
        {
          onMeta: (payload) => {
            rememberResponseMetadata(payload)
            const metadata = extractResponseMetadata(payload)
            setMessages((current) =>
              current.map((message) =>
                message.id === pendingAssistant.id
                  ? {
                      ...message,
                      responseStyle: metadata?.response_style,
                      taskClass: metadata?.task_class,
                      domainFocus: metadata?.domain_focus,
                    }
                  : message,
              ),
            )
            const responseStyle = metadata?.response_style ?? "summary"
            setActiveResponseStatus(`Regenerated ${responseStyle} response in progress.`)
          },
          onToken: (delta) => {
            setMessages((current) =>
              current.map((message) =>
                message.id === pendingAssistant.id
                  ? {
                      ...message,
                      content: `${message.content}${delta}`,
                    }
                  : message,
              ),
            )
          },
          onDone: async () => {
            const refreshed = await getAiChatThread(authenticatedFetch, threadId)
            syncThread(refreshed)
            await refreshThreadList(threadSearch)
            setActiveResponseStatus("Regenerated response complete.")
          },
          onError: (message) => {
            setError(message)
            setActiveResponseStatus(null)
          },
        },
        controller.signal,
      )
    } catch (submitError) {
      if (!(submitError instanceof DOMException && submitError.name === "AbortError")) {
        console.error("Failed to regenerate AI chat response:", submitError)
        setError("Unable to regenerate the last response.")
      }
      setMessages((current) => current.filter((message) => message.id !== pendingAssistant.id))
    } finally {
      abortControllerRef.current = null
      setIsStreaming(false)
    }
  }, [
    authenticatedFetch,
    isAuthenticated,
    isOnline,
    isStreaming,
    refreshThreadList,
    rememberResponseMetadata,
    syncThread,
    threadId,
    threadSearch,
  ])

  React.useEffect(() => () => {
    abortControllerRef.current?.abort()
  }, [])

  const value = React.useMemo<ChatWidgetStoreValue>(
    () => ({
      isOpen,
      isHydrated,
      isInitializing,
      isOnline,
      isRestoring,
      isStreaming,
      isManagingThreads,
      draft,
      messages,
      threads,
      threadSearch,
      threadId,
      threadTitle,
      activeResponseStatus,
      error,
      open,
      close,
      toggle,
      setDraft,
      setThreadSearch,
      createNewThread,
      selectThread,
      renameThread,
      deleteThread,
      exportThread,
      submitDraft,
      regenerateLastResponse,
      cancelStream,
    }),
    [
      activeResponseStatus,
      cancelStream,
      close,
      createNewThread,
      deleteThread,
      draft,
      error,
      exportThread,
      isHydrated,
      isInitializing,
      isManagingThreads,
      isOnline,
      isOpen,
      isRestoring,
      isStreaming,
      messages,
      open,
      regenerateLastResponse,
      renameThread,
      setDraft,
      setThreadSearch,
      selectThread,
      submitDraft,
      threadId,
      threadSearch,
      threadTitle,
      threads,
      toggle,
    ],
  )

  return (
    <ChatWidgetStoreContext.Provider value={value}>
      {children}
    </ChatWidgetStoreContext.Provider>
  )
}

export function useChatWidgetStore() {
  const context = React.useContext(ChatWidgetStoreContext)
  if (!context) {
    throw new Error("useChatWidgetStore must be used within ChatWidgetStoreProvider")
  }
  return context
}
