"use client"

import type { ReactNode } from "react"

import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"

export function EdgeLabControlToggle({
  label,
  description,
  checked,
  onCheckedChange,
  className,
}: {
  label: ReactNode
  description: ReactNode
  checked: boolean
  onCheckedChange: (checked: boolean) => void
  className?: string
}) {
  return (
    <div className={["flex items-center justify-between rounded-lg border p-3", className].filter(Boolean).join(" ")}>
      <div>
        <Label>{label}</Label>
        <p className="text-xs text-muted-foreground">{description}</p>
      </div>
      <Switch checked={checked} onCheckedChange={onCheckedChange} />
    </div>
  )
}
