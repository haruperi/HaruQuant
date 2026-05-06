"use client"

import { usePathname } from "next/navigation"
import { X } from "lucide-react"

import { CEOStatusBadge } from "@/components/ai-chat/CEOStatusBadge"
import { Button } from "@/components/ui/button"
import { getRouteAwareChatLabel } from "@/components/ai-chat/route-label"

interface ChatHeaderProps {
  isOnline: boolean
  isRestoring: boolean
  threadTitle: string
  activeResponseStatus?: string | null
  runtimeMeta?: string | null
  onClose: () => void
}

export function ChatHeader({ isOnline, isRestoring, threadTitle, activeResponseStatus, runtimeMeta, onClose }: ChatHeaderProps) {
  const pathname = usePathname()
  const label = getRouteAwareChatLabel(pathname)

  return (
    <div className="flex items-start justify-between gap-3 border-b px-4 py-3">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <h2 className="truncate text-sm font-semibold">HaruQuant AI</h2>
          <CEOStatusBadge
            isOnline={isOnline}
            isRestoring={isRestoring}
            activeResponseStatus={activeResponseStatus}
          />
        </div>
        <p className="mt-1 text-xs text-muted-foreground">
          {isRestoring ? "Restoring durable thread state..." : `${label} | ${threadTitle}`}
        </p>
        {runtimeMeta ? (
          <p className="mt-1 text-[11px] text-muted-foreground">
            {runtimeMeta}
          </p>
        ) : null}
      </div>
      <Button
        type="button"
        variant="ghost"
        size="icon-sm"
        aria-label="Close chat"
        onClick={onClose}
        className="shrink-0"
      >
        <X className="h-4 w-4" />
      </Button>
    </div>
  )
}
