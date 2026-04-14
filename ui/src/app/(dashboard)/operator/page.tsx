import { Activity, AlertTriangle, ShieldCheck, Workflow } from "lucide-react"

import { OperatorAgenticBlueprint } from "@/components/operator/operator-agentic-blueprint"
import { OperatorLiveEvents } from "@/components/operator/operator-live-events"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"


const statusCards = [
  {
    title: "Workflow Bus",
    value: "Agentic",
    description: "Workflow intents, plans, phase steps, transitions, and trajectory logs are now first-class backend artifacts.",
    icon: Workflow,
  },
  {
    title: "Risk Gate",
    value: "Deterministic",
    description: "Agents can explain risk posture, but backend services own policy, freshness, and execution decisions.",
    icon: ShieldCheck,
  },
  {
    title: "Incident State",
    value: "Governed",
    description: "Monitoring, stale-state detection, reconciliation, and kill-switch recovery belong in the operator plane.",
    icon: AlertTriangle,
  },
  {
    title: "Operator API",
    value: "Partially Wired",
    description: "Health, approvals, and SSE exist; read-model endpoints are the next connection layer for the UI.",
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
          <CardTitle>Frontend migration target</CardTitle>
          <CardDescription>
            The frontend should pivot from legacy feature pages to one governed artifact chain:
            intent, plan, proposal, risk decision, approval, execution, reconciliation, evidence, and replay.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-3">
          <div className="rounded-lg border bg-muted/20 p-4">
            <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Primary Surface</p>
            <p className="mt-2 text-xl font-semibold">Command Center</p>
            <p className="mt-1 text-sm text-muted-foreground">Operators start from live workflow state and pending human work.</p>
          </div>
          <div className="rounded-lg border bg-muted/20 p-4">
            <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Safety Model</p>
            <p className="mt-2 text-xl font-semibold">Backend-owned Gates</p>
            <p className="mt-1 text-sm text-muted-foreground">The client renders allowed actions; it does not infer execution permission.</p>
          </div>
          <div className="rounded-lg border bg-muted/20 p-4">
            <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Audit Basis</p>
            <p className="mt-2 text-xl font-semibold">Every Row Has Provenance</p>
            <p className="mt-1 text-sm text-muted-foreground">Contract refs, authority state, freshness, and replay coverage stay visible.</p>
          </div>
        </CardContent>
      </Card>

      <OperatorAgenticBlueprint />

      <OperatorLiveEvents />
    </div>
  )
}
