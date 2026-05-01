"use client"

import * as React from "react"
import { Plus, SendHorizontal, Square, Wrench, X } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Textarea } from "@/components/ui/textarea"
import type { AiChatToolDefinition } from "@/lib/ai-chat/contracts"

interface ChatInputProps {
  draft: string
  disabled?: boolean
  isStreaming?: boolean
  textareaRef?: React.RefObject<HTMLTextAreaElement | null>
  availableTools?: AiChatToolDefinition[]
  selectedToolIds?: string[]
  onCancel: () => void
  onDraftChange: (value: string) => void
  onToggleTool?: (toolId: string) => void
  onSubmit: () => void
}

export function ChatInput({
  draft,
  disabled = false,
  isStreaming = false,
  textareaRef,
  availableTools = [],
  selectedToolIds = [],
  onCancel,
  onDraftChange,
  onToggleTool,
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
  const selectedTools = availableTools.filter((tool) => selectedToolIds.includes(tool.tool_id))

  return (
    <div className="border-t px-4 py-3">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={disabled || isStreaming || availableTools.length === 0}
              className="h-8 gap-2 rounded-md"
            >
              <Plus className="h-4 w-4" />
              Tools
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="w-72">
            {availableTools.map((tool) => {
              const selected = selectedToolIds.includes(tool.tool_id)
              return (
                <DropdownMenuItem
                  key={tool.tool_id}
                  onClick={() => onToggleTool?.(tool.tool_id)}
                  className="flex flex-col items-start gap-1"
                >
                  <span className="flex w-full items-center justify-between gap-3">
                    <span className="font-medium">{tool.display_name}</span>
                    {selected ? <span className="text-xs text-primary">Attached</span> : null}
                  </span>
                  <span className="text-xs text-muted-foreground">{tool.description}</span>
                </DropdownMenuItem>
              )
            })}
          </DropdownMenuContent>
        </DropdownMenu>
        {selectedTools.map((tool) => (
          <button
            key={tool.tool_id}
            type="button"
            onClick={() => onToggleTool?.(tool.tool_id)}
            disabled={disabled || isStreaming}
            className="inline-flex h-8 items-center gap-2 rounded-md border bg-muted/40 px-2.5 text-xs text-foreground hover:bg-muted disabled:opacity-50"
          >
            <Wrench className="h-3.5 w-3.5" />
            {tool.display_name}
            <X className="h-3.5 w-3.5 text-muted-foreground" />
          </button>
        ))}
      </div>
      <div className="flex gap-2">
        <Textarea
          ref={textareaRef}
          value={draft}
          onChange={(event) => onDraftChange(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={isStreaming ? "Assistant is responding..." : "Ask about the current page, strategy, or workflow..."}
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
        {isStreaming ? "Streaming response. Stop interrupts the current turn." : "Enter sends. Shift+Enter inserts a new line."}
      </p>
    </div>
  )
}
