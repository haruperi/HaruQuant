import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

import { operatorAgentMesh, operatorAgentRuns } from "./operator-mock-data"


export function OperatorAgentRunsView() {
  return (
    <div className="grid gap-6 xl:grid-cols-[1.2fr_0.9fr]">
      <Card className="border-stone-200/80 shadow-sm">
        <CardHeader>
          <CardTitle>Agent run ledger</CardTitle>
          <CardDescription>
            Runtime executions with prompt provenance, output schema validation, latency, and linked artifacts.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Run</TableHead>
                <TableHead>Agent</TableHead>
                <TableHead>Phase</TableHead>
                <TableHead>Schema</TableHead>
                <TableHead>Validation</TableHead>
                <TableHead>Latency</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {operatorAgentRuns.map((run) => (
                <TableRow key={run.runId}>
                  <TableCell>
                    <div className="space-y-1">
                      <p className="font-medium text-stone-950">{run.runId}</p>
                      <p className="text-xs text-muted-foreground">{run.workflowId}</p>
                    </div>
                  </TableCell>
                  <TableCell>{run.agent}</TableCell>
                  <TableCell>{run.phase}</TableCell>
                  <TableCell>
                    <div className="space-y-1">
                      <p className="font-mono text-xs">{run.outputSchema}</p>
                      <p className="text-xs text-muted-foreground">{run.promptVersion}</p>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className="border-stone-300 text-stone-700">
                      {run.validation}
                    </Badge>
                  </TableCell>
                  <TableCell>{run.latencyMs} ms</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card className="border-stone-200/80 shadow-sm">
        <CardHeader>
          <CardTitle>Runtime guardrails</CardTitle>
          <CardDescription>Operators need to see what each agent can do before trusting its output.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {operatorAgentMesh.map((agent) => (
            <div key={agent.agent} className="rounded-lg border p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="font-medium text-stone-950">{agent.agent}</p>
                <Badge variant="secondary">{agent.authority}</Badge>
              </div>
              <p className="mt-2 text-sm text-stone-700">{agent.role}</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {agent.tools.map((tool) => (
                  <Badge key={tool} variant="outline" className="border-stone-300 text-stone-700">
                    {tool}
                  </Badge>
                ))}
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card className="border-stone-200/80 shadow-sm xl:col-span-2">
        <CardHeader>
          <CardTitle>Artifact trace</CardTitle>
          <CardDescription>
            Agent output is useful to the UI only when it is linked to a contract artifact that backend services can validate.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-3">
          {operatorAgentRuns.map((run) => (
            <div key={run.artifactRef} className="rounded-lg border bg-stone-50 p-4">
              <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Artifact</p>
              <p className="mt-2 break-words font-mono text-xs text-stone-800">{run.artifactRef}</p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Badge variant="secondary">{run.costState}</Badge>
                <Badge variant="outline" className="border-stone-300 text-stone-700">
                  {run.outputSchema}
                </Badge>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}
