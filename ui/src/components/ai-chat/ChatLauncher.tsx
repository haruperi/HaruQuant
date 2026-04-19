"use client"

import { MessageSquareText } from "lucide-react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

interface ChatLauncherProps {
  onOpen: () => void
  hidden?: boolean
}

export function ChatLauncher({ onOpen, hidden = false }: ChatLauncherProps) {
  return (
    <Button
      type="button"
      aria-label="Open HaruQuant AI chat"
      onClick={onOpen}
      size="lg"
      className={cn(
        "fixed bottom-4 right-4 z-40 h-12 rounded-md px-4 shadow-lg md:bottom-6 md:right-6",
        hidden && "pointer-events-none opacity-0",
      )}
    >
      <MessageSquareText className="h-4 w-4" />
      <span className="text-sm">AI Chat</span>
    </Button>
  )
}
