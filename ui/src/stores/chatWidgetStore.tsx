"use client"

import * as React from "react"

import {
  createAiChatThread,
  getAiChatThread,
  listAiChatThreads,
  streamAiChatResponse,
  updateAiChatThreadContext,
} from "@/lib/api/ai-chat"
import type { AiChatMessage, AiChatThreadDetail } from "@/lib/ai-chat/contracts"
import { useAuth } from "@/lib/auth-context"
import { usePageContext } from "@/hooks/usePageContext"

type ChatRole = "user" | "assistant"

export interface ChatMessage {
  id: string
  role: ChatRole
  content: string
  createdAt: string
  toolCalls?: string[]
  status?: "ready" | "pending"
}

interface ChatWidgetStoreValue {
  isOpen: boolean
  isHydrated: boolean
  isInitializing: boolean
  isOnline: boolean
  isRestoring: boolean
  isStreaming: boolean
  draft: string
  messages: ChatMessage[]
  threadId: string | null
  threadTitle: string
  error: string | null
  open: () => void
  close: () => void
  toggle: () => void
  setDraft: (value: string) => void
  submitDraft: () => Promise<void>
  cancelStream: () => void
}

const STORAGE_KEYS = {
  open: "haruquant.ai_chat.open",
  draft: "haruquant.ai_chat.draft",
  activeThreadId: "haruquant.ai_chat.active_thread_id",
} as const

const DEFAULT_THREAD_TITLE = "New conversation"
const ChatWidgetStoreContext = React.createContext<ChatWidgetStoreValue | null>(null)

function mapApiMessage(message: AiChatMessage): ChatMessage {
  return {
    id: message.message_id,
    role: message.role === "assistant" ? "assistant" : "user",
    content: message.content,
    createdAt: message.created_at,
    toolCalls: message.tool_calls,
    status: "ready",
  }
}

function makePendingAssistant(): ChatMessage {
  const idSuffix = typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}_${Math.random().toString(16).slice(2)}`
  return {
    id: `assistant_pending_${idSuffix}`,
    role: "assistant",
    content: "Thinking...",
    createdAt: new Date().toISOString(),
    status: "pending",
  }
}

export function ChatWidgetStoreProvider({ children }: { children: React.ReactNode }) {
  const { authenticatedFetch, isAuthenticated, isLoading } = useAuth()
  const { pageContext } = usePageContext()
  const [isOpen, setIsOpen] = React.useState(false)
  const [draft, setDraftState] = React.useState("")
  const [messages, setMessages] = React.useState<ChatMessage[]>([])
  const [isHydrated, setIsHydrated] = React.useState(false)
  const [isInitializing, setIsInitializing] = React.useState(false)
  const [hasOpenedOnce, setHasOpenedOnce] = React.useState(false)
  const [isOnline, setIsOnline] = React.useState(true)
  const [isRestoring, setIsRestoring] = React.useState(false)
  const [isStreaming, setIsStreaming] = React.useState(false)
  const [threadId, setThreadId] = React.useState<string | null>(null)
  const [threadTitle, setThreadTitle] = React.useState(DEFAULT_THREAD_TITLE)
  const [error, setError] = React.useState<string | null>(null)
  const abortControllerRef = React.useRef<AbortController | null>(null)

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
        .map(mapApiMessage),
    )
  }, [])

  const ensureThread = React.useCallback(async () => {
    if (!isAuthenticated) {
      return null
    }

    if (threadId) {
      const existing = await getAiChatThread(authenticatedFetch, threadId)
      syncThread(existing)
      return existing
    }

    const threads = await listAiChatThreads(authenticatedFetch)
    const selected = threads[0]

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
    return created
  }, [authenticatedFetch, isAuthenticated, pageContext?.context_revision, pageContext?.page_type, pageContext?.route, syncThread, threadId])

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
  ])

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

  const cancelStream = React.useCallback(() => {
    abortControllerRef.current?.abort()
    abortControllerRef.current = null
    setIsStreaming(false)
  }, [])

  const submitDraft = React.useCallback(async () => {
    const trimmed = draft.trim()
    if (!trimmed || !isOnline || !isAuthenticated || isStreaming) {
      return
    }

    setError(null)
    const pendingAssistantId = makePendingAssistant().id
    setMessages((current) => [
      ...current,
      {
        id: `user_local_${Date.now()}`,
        role: "user",
        content: trimmed,
        createdAt: new Date().toISOString(),
        status: "ready",
      },
      {
        id: pendingAssistantId,
        role: "assistant",
        content: "",
        createdAt: new Date().toISOString(),
        status: "pending",
      },
    ])
    setDraftState("")
    setIsStreaming(true)
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
          onToken: (delta) => {
            setMessages((current) =>
              current.map((message) =>
                message.id === pendingAssistantId
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
          },
          onError: (message) => {
            setError(message)
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
      setMessages((current) => current.filter((message) => message.id !== pendingAssistantId))
      return
    } finally {
      abortControllerRef.current = null
      setIsStreaming(false)
    }
  }, [authenticatedFetch, draft, ensureThread, isAuthenticated, isOnline, isStreaming, syncThread])

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
      draft,
      messages,
      threadId,
      threadTitle,
      error,
      open,
      close,
      toggle,
      setDraft,
      submitDraft,
      cancelStream,
    }),
    [
      cancelStream,
      close,
      draft,
      error,
      isHydrated,
      isInitializing,
      isOnline,
      isOpen,
      isRestoring,
      isStreaming,
      messages,
      open,
      setDraft,
      submitDraft,
      threadId,
      threadTitle,
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
