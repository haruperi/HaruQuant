"use client"

import { CircleDot, ShieldAlert, WifiOff } from "lucide-react"

import { Badge } from "@/components/ui/badge"

interface CEOStatusBadgeProps {
  isOnline: boolean
  isRestoring: boolean
  activeResponseStatus?: string | null
}

function statusLabel({ isOnline, isRestoring, activeResponseStatus }: CEOStatusBadgeProps): string {
  if (!isOnline) {
    return "Offline"
  }
  if (isRestoring) {
    return "Restoring"
  }
  if (activeResponseStatus) {
    if (activeResponseStatus.includes("approval")) {
      return "Waiting for approval"
    }
    if (activeResponseStatus.includes("tool")) {
      return "Using tools"
    }
    if (activeResponseStatus.includes("plan")) {
      return "Planning"
    }
    if (activeResponseStatus.includes("block")) {
      return "Blocked"
    }
    return "Thinking"
  }
  return "Ready"
}

export function CEOStatusBadge(props: CEOStatusBadgeProps) {
  const label = statusLabel(props)
  const Icon = props.isOnline ? (label === "Blocked" ? ShieldAlert : CircleDot) : WifiOff

  return (
    <Badge
      variant={props.isOnline ? (label === "Blocked" ? "destructive" : "secondary") : "destructive"}
      className="rounded-sm px-2 py-0 text-[11px]"
    >
      <Icon className="h-3 w-3" />
      {label}
    </Badge>
  )
}

