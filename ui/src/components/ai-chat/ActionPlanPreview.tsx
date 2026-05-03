"use client"

import * as React from "react"
import { Check, Info, ShieldAlert, ShieldCheck, Terminal, X } from "lucide-react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import type { AiChatPageActionPlan } from "@/lib/ai-chat/contracts"

interface ActionPlanPreviewProps {
  plan: AiChatPageActionPlan
  onApprove?: (plan: AiChatPageActionPlan) => void
  onApproveAll?: (plan: AiChatPageActionPlan) => void
  onReject?: () => void
  status?: "pending" | "approved" | "rejected"
  autoApproveEnabled?: boolean
}

export function ActionPlanPreview({
  plan,
  onApprove,
  onApproveAll,
  onReject,
  status = "pending",
  autoApproveEnabled = false,
}: ActionPlanPreviewProps) {
  const isPending = status === "pending"

  const riskConfig = {
    view_only: {
      icon: Info,
      color: "text-sky-500",
      bg: "bg-sky-500/10",
      border: "border-sky-500/20",
      label: "Safe: View Only",
    },
    local_ui: {
      icon: ShieldCheck,
      color: "text-emerald-500",
      bg: "bg-emerald-500/10",
      border: "border-emerald-500/20",
      label: "Safe: Local UI Navigation",
    },
    backend_non_trading: {
      icon: ShieldCheck,
      color: "text-amber-500",
      bg: "bg-amber-500/10",
      border: "border-amber-500/20",
      label: "Governed: Backend Action",
    },
    trading_adjacent: {
      icon: ShieldAlert,
      color: "text-rose-500",
      bg: "bg-rose-500/10",
      border: "border-rose-500/20",
      label: "Critical: Trading Adjacent",
    },
    prohibited: {
      icon: ShieldAlert,
      color: "text-rose-600",
      bg: "bg-rose-600/10",
      border: "border-rose-600/20",
      label: "Prohibited",
    },
  }[plan.risk_level] || {
    icon: ShieldAlert,
    color: "text-muted-foreground",
    bg: "bg-muted",
    border: "border-border",
    label: "Unknown Risk",
  }

  const RiskIcon = riskConfig.icon

  return (
    <div className={cn(
      "mt-3 overflow-hidden rounded-lg border bg-card text-card-foreground shadow-sm transition-all",
      riskConfig.border
    )}>
      {/* Header */}
      <div className={cn("flex items-center justify-between px-3 py-2 border-b", riskConfig.bg, riskConfig.border)}>
        <div className="flex items-center gap-2">
          <RiskIcon className={cn("h-4 w-4", riskConfig.color)} />
          <span className={cn("text-[11px] font-semibold uppercase tracking-wider", riskConfig.color)}>
            {riskConfig.label}
          </span>
        </div>
        <Terminal className="h-3.5 w-3.5 text-muted-foreground/50" />
      </div>

      {/* Body */}
      <div className="p-3 space-y-3">
        <div>
          <h4 className="text-sm font-medium leading-none">{plan.action_id}</h4>
          <p className="mt-1.5 text-xs text-muted-foreground leading-relaxed">
            {plan.reasoning}
          </p>
        </div>

        {/* Parameters */}
        {Object.keys(plan.parameters).length > 0 && (
          <div className="rounded-md bg-muted/50 p-2 font-mono text-[10px]">
            <p className="mb-1 font-semibold text-muted-foreground uppercase tracking-tight">Parameters</p>
            <div className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
              {Object.entries(plan.parameters).map(([key, value]) => (
                <React.Fragment key={key}>
                  <span className="text-foreground/70">{key}:</span>
                  <span className="text-foreground truncate">{JSON.stringify(value)}</span>
                </React.Fragment>
              ))}
            </div>
          </div>
        )}

        {/* Governance Footer */}
        <div className="flex items-center justify-between pt-1">
          <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
            <ShieldCheck className="h-3 w-3 text-emerald-500" />
            {autoApproveEnabled ? "AI Proposal - Auto-approved in this chat" : "AI Proposal - Requires User Approval"}
          </div>
          
          {isPending ? (
            <div className="flex flex-wrap justify-end gap-2">
              <Button 
                variant="ghost" 
                size="sm" 
                className="h-7 px-2 text-[11px] hover:bg-rose-500/10 hover:text-rose-600"
                onClick={onReject}
              >
                <X className="mr-1 h-3 w-3" />
                Reject
              </Button>
              {!autoApproveEnabled ? (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2 text-[11px] hover:bg-sky-500/10 hover:text-sky-600"
                  onClick={() => onApproveAll?.(plan)}
                >
                  <ShieldCheck className="mr-1 h-3 w-3" />
                  Approve all in this chat
                </Button>
              ) : null}
              <Button 
                variant="outline" 
                size="sm" 
                className="h-7 px-2 text-[11px] border-emerald-500/50 text-emerald-600 hover:bg-emerald-500/10"
                onClick={() => onApprove?.(plan)}
              >
                <Check className="mr-1 h-3 w-3" />
                Execute
              </Button>
            </div>
          ) : (
            <div className={cn(
              "flex items-center gap-1 text-[11px] font-medium",
              status === "approved" ? "text-emerald-600" : "text-rose-600"
            )}>
              {status === "approved" ? (
                <>
                  <Check className="h-3 w-3" />
                  Executed
                </>
              ) : (
                <>
                  <X className="h-3 w-3" />
                  Rejected
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
