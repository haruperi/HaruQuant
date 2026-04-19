"use client"

import * as React from "react"

import { ChatHeader } from "@/components/ai-chat/ChatHeader"
import { ChatInput } from "@/components/ai-chat/ChatInput"
import { MessageList } from "@/components/ai-chat/MessageList"
import { cn } from "@/lib/utils"

interface ChatPanelProps {
  isOpen: boolean
  isHydrated: boolean
  isInitializing: boolean
  isOnline: boolean
  isRestoring: boolean
  threadTitle: string
  error: string | null
  draft: string
  messages: {
    id: string
    role: "user" | "assistant"
    content: string
    createdAt: string
    status?: "ready" | "pending"
  }[]
  onClose: () => void
  onDraftChange: (value: string) => void
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

export function ChatPanel({
  isOpen,
  isHydrated,
  isInitializing,
  isOnline,
  isRestoring,
  threadTitle,
  error,
  draft,
  messages,
  onClose,
  onDraftChange,
  onSubmit,
}: ChatPanelProps) {
  const panelRef = React.useRef<HTMLDivElement | null>(null)
  const textareaRef = React.useRef<HTMLTextAreaElement | null>(null)

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

  return (
    <aside
      aria-hidden={!isOpen}
      aria-label="HaruQuant AI chat panel"
      role="dialog"
      ref={panelRef}
      className={cn(
        "fixed inset-x-0 bottom-0 z-40 flex h-[70vh] max-h-[70vh] flex-col border bg-background shadow-xl transition-all duration-200 md:inset-x-auto md:bottom-6 md:right-6 md:h-[36rem] md:max-h-[calc(100vh-5rem)] md:w-[24rem] md:rounded-md",
        isOpen
          ? "translate-y-0 opacity-100"
          : "pointer-events-none translate-y-4 opacity-0 md:translate-y-2",
      )}
    >
      <ChatHeader
        isOnline={isOnline}
        isRestoring={isRestoring}
        threadTitle={threadTitle}
        onClose={onClose}
      />
      <div className="min-h-0 flex-1">
        <MessageList
          messages={messages}
          isInitializing={!isHydrated || isInitializing || isRestoring}
          isOnline={isOnline}
          error={error}
        />
      </div>
      <ChatInput
        draft={draft}
        disabled={!isOnline || !isHydrated}
        textareaRef={textareaRef}
        onDraftChange={onDraftChange}
        onSubmit={onSubmit}
      />
    </aside>
  )
}
