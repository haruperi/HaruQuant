"use client"

import { usePathname } from "next/navigation"
import { Wifi, WifiOff, X } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { getRouteAwareChatLabel } from "@/components/ai-chat/route-label"

interface ChatHeaderProps {
  isOnline: boolean
  isRestoring: boolean
  threadTitle: string
  runtimeMeta?: string | null
  onClose: () => void
}

export function ChatHeader({ isOnline, isRestoring, threadTitle, runtimeMeta, onClose }: ChatHeaderProps) {
  const pathname = usePathname()
  const label = getRouteAwareChatLabel(pathname)

  return (
    <div className="flex items-start justify-between gap-3 border-b px-4 py-3">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <h2 className="truncate text-sm font-semibold">{label}</h2>
          <Badge variant={isOnline ? "secondary" : "destructive"} className="rounded-sm px-2 py-0 text-[11px]">
            {isOnline ? (
              <>
                <Wifi className="h-3 w-3" />
                Online
              </>
            ) : (
              <>
                <WifiOff className="h-3 w-3" />
                Offline
              </>
            )}
          </Badge>
        </div>
        <p className="mt-1 text-xs text-muted-foreground">
          {isRestoring ? "Restoring durable thread state..." : `${threadTitle} | durable thread memory active.`}
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
