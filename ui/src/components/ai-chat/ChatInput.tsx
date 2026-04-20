"use client"

import * as React from "react"
import { SendHorizontal, Square } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"

interface ChatInputProps {
  draft: string
  disabled?: boolean
  isStreaming?: boolean
  textareaRef?: React.RefObject<HTMLTextAreaElement | null>
  onCancel: () => void
  onDraftChange: (value: string) => void
  onSubmit: () => void
}

export function ChatInput({
  draft,
  disabled = false,
  isStreaming = false,
  textareaRef,
  onCancel,
  onDraftChange,
  onSubmit,
}: ChatInputProps) {
  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (isStreaming) {
      return
    }
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault()
      onSubmit()
    }
  }

  return (
    <div className="border-t px-4 py-3">
      <div className="flex gap-2">
        <Textarea
          ref={textareaRef}
          value={draft}
          onChange={(event) => onDraftChange(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about the current page, strategy, or workflow..."
          aria-label="Chat input"
          disabled={disabled || isStreaming}
          className="min-h-20 resize-none rounded-md"
        />
        <Button
          type="button"
          size="icon"
          className="h-20 shrink-0 rounded-md"
          onClick={isStreaming ? onCancel : onSubmit}
          disabled={isStreaming ? false : disabled || draft.trim().length === 0}
          aria-label={isStreaming ? "Stop response" : "Send message"}
        >
          {isStreaming ? <Square className="h-4 w-4" /> : <SendHorizontal className="h-4 w-4" />}
        </Button>
      </div>
      <p className="mt-2 text-[11px] text-muted-foreground">
        {isStreaming ? "Streaming response. Use stop to cancel." : "Enter sends. Shift+Enter inserts a new line."}
      </p>
    </div>
  )
}
