import { BrainCircuit, DatabaseZap, GitBranch, ShieldCheck } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

import { operatorAgentMesh, operatorApiBacklog, operatorControlLoop } from "./operator-mock-data"


export function OperatorAgenticBlueprint() {
  return (
    <div className="space-y-6">
      <Card className="border-stone-200/80 shadow-sm">
        <CardHeader className="flex flex-row items-start justify-between space-y-0">
          <div>
            <CardTitle>Agentic operating loop</CardTitle>
            <CardDescription>
              The UI should follow the backend artifact chain from intent through replay instead of separating work
              by legacy feature page.
            </CardDescription>
          </div>
          <GitBranch className="h-5 w-5 text-stone-500" />
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 lg:grid-cols-7">
            {operatorControlLoop.map((stage) => (
              <div key={stage.stage} className="rounded-lg border bg-stone-50 p-3">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-semibold text-stone-950">{stage.stage}</p>
                  <Badge variant="outline" className="border-stone-300 text-stone-700">
                    {stage.status}
                  </Badge>
                </div>
                <p className="mt-2 text-xs text-stone-600">{stage.owner}</p>
                <p className="mt-3 font-mono text-xs text-stone-800">{stage.contract}</p>
                <p className="mt-2 text-xs text-stone-500">{stage.backend}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <Card className="border-stone-200/80 shadow-sm">
          <CardHeader className="flex flex-row items-start justify-between space-y-0">
            <div>
              <CardTitle>Agent mesh</CardTitle>
              <CardDescription>Specialists visible to operators with their policy-bounded responsibilities.</CardDescription>
            </div>
            <BrainCircuit className="h-5 w-5 text-stone-500" />
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Agent</TableHead>
                  <TableHead>Runtime Pattern</TableHead>
                  <TableHead>Authority</TableHead>
                  <TableHead>Tools</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {operatorAgentMesh.map((agent) => (
                  <TableRow key={agent.agent}>
                    <TableCell>
                      <div className="space-y-1">
                        <p className="font-medium text-stone-950">{agent.agent}</p>
                        <p className="text-xs text-muted-foreground">{agent.role}</p>
                      </div>
                    </TableCell>
                    <TableCell>{agent.pattern}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className="border-stone-300 text-stone-700">
                        {agent.authority}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-2">
                        {agent.tools.map((tool) => (
                          <Badge key={tool} variant="secondary">
                            {tool}
                          </Badge>
                        ))}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card className="border-stone-200/80 shadow-sm">
          <CardHeader className="flex flex-row items-start justify-between space-y-0">
            <div>
              <CardTitle>Connection backlog</CardTitle>
              <CardDescription>Read endpoints needed to replace operator mock data with backend read models.</CardDescription>
            </div>
            <DatabaseZap className="h-5 w-5 text-stone-500" />
          </CardHeader>
          <CardContent className="space-y-4">
            {operatorApiBacklog.map((endpoint) => (
              <div key={endpoint.route} className="rounded-lg border p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="font-mono text-sm font-medium text-stone-950">{endpoint.route}</p>
                  <ShieldCheck className="h-4 w-4 text-emerald-600" />
                </div>
                <p className="mt-2 text-sm text-stone-700">{endpoint.purpose}</p>
                <p className="mt-2 text-xs text-muted-foreground">{endpoint.source}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
