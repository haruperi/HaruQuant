"use client"

import { Loader2, Sparkles, User2, WifiOff } from "lucide-react"

import { ScrollArea } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"
import type { ChatMessage } from "@/stores/chatWidgetStore"

interface MessageListProps {
  messages: ChatMessage[]
  isInitializing: boolean
  isOnline: boolean
  error: string | null
}

export function MessageList({ messages, isInitializing, isOnline, error }: MessageListProps) {
  return (
    <ScrollArea className="h-full">
      <div className="flex min-h-full flex-col gap-3 p-4">
        {isInitializing ? (
          <>
            <div className="space-y-2">
              <Skeleton className="h-4 w-24 rounded-sm" />
              <Skeleton className="h-16 w-full rounded-sm" />
            </div>
            <div className="space-y-2 self-end">
              <Skeleton className="ml-auto h-4 w-20 rounded-sm" />
              <Skeleton className="ml-auto h-12 w-48 rounded-sm" />
            </div>
          </>
        ) : messages.length === 0 ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-3 text-center">
            <div className="rounded-md border bg-muted/30 p-3">
              {isOnline ? <Sparkles className="h-5 w-5" /> : <WifiOff className="h-5 w-5" />}
            </div>
            <div className="space-y-1">
              <p className="text-sm font-medium">
                {isOnline ? "Start a conversation" : "You are offline"}
              </p>
              <p className="max-w-xs text-xs text-muted-foreground">
                {isOnline
                  ? "This Phase 2 widget restores durable threads and keeps the active conversation available across navigation."
                  : "Draft text is still preserved locally, but replies are disabled until connectivity returns."}
              </p>
              {error ? (
                <p className="max-w-xs text-xs text-destructive">
                  {error}
                </p>
              ) : null}
            </div>
          </div>
        ) : (
          <div aria-live="polite" className="space-y-3">
            {messages.map((message) => (
              <div
                key={message.id}
                className={cn(
                  "flex gap-2",
                  message.role === "user" ? "justify-end" : "justify-start",
                )}
              >
                {message.role === "assistant" && (
                  <div className="mt-1 rounded-sm border bg-muted/40 p-1.5">
                    <Sparkles className="h-3.5 w-3.5" />
                  </div>
                )}
                <div
                  className={cn(
                    "max-w-[85%] rounded-md border px-3 py-2 text-sm shadow-xs",
                    message.role === "user"
                      ? "bg-primary text-primary-foreground"
                      : "bg-background",
                  )}
                >
                  <div className="mb-1 flex items-center gap-2 text-[11px] opacity-75">
                    {message.role === "user" ? (
                      <>
                        <User2 className="h-3 w-3" />
                        You
                      </>
                    ) : (
                      <>
                        <Sparkles className="h-3 w-3" />
                        HaruQuant AI
                      </>
                    )}
                    {message.status === "pending" && (
                      <>
                        <Loader2 className="h-3 w-3 animate-spin" />
                        Thinking
                      </>
                    )}
                  </div>
                  <p className="whitespace-pre-wrap break-words">{message.content}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </ScrollArea>
  )
}
