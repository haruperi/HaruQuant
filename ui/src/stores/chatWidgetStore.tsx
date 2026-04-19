"use client"

import * as React from "react"

type ChatRole = "user" | "assistant"

export interface ChatMessage {
  id: string
  role: ChatRole
  content: string
  createdAt: string
  status?: "ready" | "pending"
}

interface ChatWidgetStoreValue {
  isOpen: boolean
  isHydrated: boolean
  isInitializing: boolean
  isOnline: boolean
  draft: string
  messages: ChatMessage[]
  open: () => void
  close: () => void
  toggle: () => void
  setDraft: (value: string) => void
  submitDraft: () => void
}

const STORAGE_KEYS = {
  open: "haruquant.ai_chat.open",
  draft: "haruquant.ai_chat.draft",
} as const

const ChatWidgetStoreContext = React.createContext<ChatWidgetStoreValue | null>(null)

function buildAssistantReply(userMessage: string): string {
  return [
    "Phase 1 widget shell is active.",
    "Persistent UI state, route-aware mounting, and local draft recovery are ready.",
    `Captured prompt: "${userMessage.trim()}".`,
    "Backend conversations, context injection, and streaming connect in later phases.",
  ].join(" ")
}

function createMessage(role: ChatRole, content: string, status: "ready" | "pending" = "ready"): ChatMessage {
  const now = new Date().toISOString()
  const idSuffix = typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}_${Math.random().toString(16).slice(2)}`

  return {
    id: `${role}_${idSuffix}`,
    role,
    content,
    createdAt: now,
    status,
  }
}

export function ChatWidgetStoreProvider({ children }: { children: React.ReactNode }) {
  const [isOpen, setIsOpen] = React.useState(false)
  const [draft, setDraftState] = React.useState("")
  const [messages, setMessages] = React.useState<ChatMessage[]>([])
  const [isHydrated, setIsHydrated] = React.useState(false)
  const [isInitializing, setIsInitializing] = React.useState(false)
  const [hasOpenedOnce, setHasOpenedOnce] = React.useState(false)
  const [isOnline, setIsOnline] = React.useState(true)

  React.useEffect(() => {
    if (typeof window === "undefined") {
      return
    }

    const persistedOpen = window.localStorage.getItem(STORAGE_KEYS.open)
    const persistedDraft = window.localStorage.getItem(STORAGE_KEYS.draft)

    setIsOpen(persistedOpen === "true")
    setDraftState(persistedDraft ?? "")
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

  const submitDraft = React.useCallback(() => {
    const trimmed = draft.trim()
    if (!trimmed || !isOnline) {
      return
    }

    const userMessage = createMessage("user", trimmed)
    const pendingAssistant = createMessage("assistant", "Thinking...", "pending")

    setMessages((current) => [...current, userMessage, pendingAssistant])
    setDraftState("")

    window.setTimeout(() => {
      setMessages((current) =>
        current.map((message) =>
          message.id === pendingAssistant.id
            ? {
                ...message,
                content: buildAssistantReply(trimmed),
                status: "ready",
              }
            : message,
        ),
      )
    }, 550)
  }, [draft, isOnline])

  const value = React.useMemo<ChatWidgetStoreValue>(
    () => ({
      isOpen,
      isHydrated,
      isInitializing,
      isOnline,
      draft,
      messages,
      open,
      close,
      toggle,
      setDraft,
      submitDraft,
    }),
    [
      close,
      draft,
      isHydrated,
      isInitializing,
      isOnline,
      isOpen,
      messages,
      open,
      setDraft,
      submitDraft,
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
