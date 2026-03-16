"use client"

import { Loader2 } from "lucide-react"

export function EdgeLabCollectionState({
  loading,
  hasItems,
  emptyMessage,
  children,
}: {
  loading: boolean
  hasItems: boolean
  emptyMessage: string
  children: React.ReactNode
}) {
  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading...
      </div>
    )
  }

  if (!hasItems) {
    return <div className="text-sm text-muted-foreground">{emptyMessage}</div>
  }

  return <>{children}</>
}
