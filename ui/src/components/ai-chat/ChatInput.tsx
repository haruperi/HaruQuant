"use client"

import * as React from "react"
import { SendHorizontal } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"

interface ChatInputProps {
  draft: string
  disabled?: boolean
  textareaRef?: React.RefObject<HTMLTextAreaElement | null>
  onDraftChange: (value: string) => void
  onSubmit: () => void
}

export function ChatInput({
  draft,
  disabled = false,
  textareaRef,
  onDraftChange,
  onSubmit,
}: ChatInputProps) {
  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
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
          placeholder="Ask about the current page, strategy, or workflow…"
          aria-label="Chat input"
          disabled={disabled}
          className="min-h-20 resize-none rounded-md"
        />
        <Button
          type="button"
          size="icon"
          className="h-20 shrink-0 rounded-md"
          onClick={onSubmit}
          disabled={disabled || draft.trim().length === 0}
          aria-label="Send message"
        >
          <SendHorizontal className="h-4 w-4" />
        </Button>
      </div>
      <p className="mt-2 text-[11px] text-muted-foreground">
        Enter sends. Shift+Enter inserts a new line.
      </p>
    </div>
  )
}
