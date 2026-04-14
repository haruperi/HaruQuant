"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { Activity, BrainCircuit, ShieldCheck, Workflow, GitPullRequest, AlertTriangle, Search, LineChart, FolderArchive } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"


const operatorRoutes = [
  { href: "/operator", label: "Overview", icon: Activity },
  { href: "/operator/workflows", label: "Workflows", icon: Workflow },
  { href: "/operator/agents", label: "Agent Runs", icon: BrainCircuit },
  { href: "/operator/proposals", label: "Proposals", icon: GitPullRequest },
  { href: "/operator/risk", label: "Risk", icon: ShieldCheck },
  { href: "/operator/approvals", label: "Approvals", icon: ShieldCheck },
  { href: "/operator/incidents", label: "Incidents", icon: AlertTriangle },
  { href: "/operator/replay", label: "Replay", icon: Search },
  { href: "/operator/evidence", label: "Evidence", icon: FolderArchive },
  { href: "/operator/strategies", label: "Strategies", icon: LineChart },
]


export function OperatorShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()

  return (
    <div className="space-y-6">
      <Card className="border-stone-300 bg-[linear-gradient(135deg,rgba(28,25,23,0.98),rgba(39,39,42,0.94))] text-white shadow-xl">
        <CardContent className="space-y-5 px-6 py-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Badge variant="secondary" className="bg-emerald-500/15 text-emerald-200">
                  Operator Workspace
                </Badge>
                <Badge variant="outline" className="border-amber-300/40 text-amber-100">
                  Readiness: Drafting
                </Badge>
              </div>
              <div>
                <h1 className="text-3xl font-semibold tracking-tight">Agentic Control Plane</h1>
                <p className="max-w-3xl text-sm text-stone-300">
                  Supervise agent workflows, deterministic risk gates, approvals, execution receipts, evidence, and replay from one control surface.
                </p>
              </div>
            </div>

            <div className="grid min-w-[280px] gap-3 sm:grid-cols-3">
              <div className="rounded-lg border border-white/10 bg-white/5 p-3">
                <p className="text-xs uppercase tracking-[0.18em] text-stone-400">Mode</p>
                <p className="mt-2 text-sm font-medium text-white">Paper / Advisory</p>
              </div>
              <div className="rounded-lg border border-white/10 bg-white/5 p-3">
                <p className="text-xs uppercase tracking-[0.18em] text-stone-400">Risk Gate</p>
                <p className="mt-2 text-sm font-medium text-emerald-300">Deterministic</p>
              </div>
              <div className="rounded-lg border border-white/10 bg-white/5 p-3">
                <p className="text-xs uppercase tracking-[0.18em] text-stone-400">Event Spine</p>
                <p className="mt-2 text-sm font-medium text-amber-200">Redis Planned</p>
              </div>
            </div>
          </div>

          <nav className="flex flex-wrap gap-2">
            {operatorRoutes.map((route) => {
              const active = pathname === route.href || (route.href !== "/operator" && pathname.startsWith(route.href))
              return (
                <Link
                  key={route.href}
                  href={route.href}
                  className={cn(
                    "inline-flex items-center gap-2 rounded-lg border px-4 py-2 text-sm transition-colors",
                    active
                      ? "border-white/30 bg-white/15 text-white"
                      : "border-white/10 bg-white/5 text-stone-300 hover:bg-white/10 hover:text-white"
                  )}
                >
                  <route.icon className="h-4 w-4" />
                  <span>{route.label}</span>
                </Link>
              )
            })}
          </nav>
        </CardContent>
      </Card>

      {children}
    </div>
  )
}
