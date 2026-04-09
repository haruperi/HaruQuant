import { Activity, AlertTriangle, ShieldCheck, Workflow } from "lucide-react"

import { OperatorLiveEvents } from "@/components/operator/operator-live-events"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"


const statusCards = [
  {
    title: "Workflow Bus",
    value: "Scaffolded",
    description: "Creation, transition logging, and step recording are wired for migration-era workflows.",
    icon: Workflow,
  },
  {
    title: "Risk Gate",
    value: "Deterministic",
    description: "Policy resolution and approval skeletons are in place ahead of live execution work.",
    icon: ShieldCheck,
  },
  {
    title: "Incident State",
    value: "Ready",
    description: "Incident state transitions are available for the next control-plane slices.",
    icon: AlertTriangle,
  },
  {
    title: "Operator API",
    value: "Online",
    description: "The migration-era FastAPI shell is running with auth and health endpoint scaffolding.",
    icon: Activity,
  },
]


export default function OperatorOverviewPage() {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 xl:grid-cols-4">
        {statusCards.map((card) => (
          <Card key={card.title} className="border-slate-200/70 shadow-sm">
            <CardHeader className="flex flex-row items-start justify-between space-y-0">
              <div className="space-y-1">
                <CardTitle className="text-base">{card.title}</CardTitle>
                <CardDescription>{card.description}</CardDescription>
              </div>
              <card.icon className="h-5 w-5 text-slate-500" />
            </CardHeader>
            <CardContent>
              <Badge variant="outline" className="border-slate-300 text-slate-700">
                {card.value}
              </Badge>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="border-dashed">
        <CardHeader>
          <CardTitle>Live Status Layout</CardTitle>
          <CardDescription>
            This operator workspace is intentionally read-only for now. The next slices will hang workflows, proposals,
            risk, approvals, incidents, replay, and strategy lifecycle views off this layout.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-3">
          <div className="rounded-lg border bg-muted/20 p-4">
            <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Operating Mode</p>
            <p className="mt-2 text-xl font-semibold">Paper</p>
            <p className="mt-1 text-sm text-muted-foreground">No live execution is exposed through this workspace.</p>
          </div>
          <div className="rounded-lg border bg-muted/20 p-4">
            <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Approval Path</p>
            <p className="mt-2 text-xl font-semibold">Distinct Reviewers</p>
            <p className="mt-1 text-sm text-muted-foreground">Approval state machine and voting rules are already in place.</p>
          </div>
          <div className="rounded-lg border bg-muted/20 p-4">
            <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Audit Basis</p>
            <p className="mt-2 text-xl font-semibold">Replay-Ready</p>
            <p className="mt-1 text-sm text-muted-foreground">Contracts, repositories, and workflow history now have a common home.</p>
          </div>
        </CardContent>
      </Card>

      <OperatorLiveEvents />
    </div>
  )
}
