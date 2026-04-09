import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

import { operatorWorkflows, selectedWorkflow } from "./operator-mock-data"

export function OperatorWorkflowView() {
  return (
    <div className="grid gap-6 xl:grid-cols-[1.35fr_0.95fr]">
      <Card className="border-slate-200/70 shadow-sm">
        <CardHeader>
          <CardTitle>Workflow supervision</CardTitle>
          <CardDescription>
            Active migration-era workflows with their current step, owning runtime, and latest supervision state.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Workflow</TableHead>
                <TableHead>State</TableHead>
                <TableHead>Owner</TableHead>
                <TableHead>Current Step</TableHead>
                <TableHead>Updated</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {operatorWorkflows.map((workflow) => (
                <TableRow key={workflow.workflowId}>
                  <TableCell>
                    <div className="space-y-1">
                      <p className="font-medium text-slate-900">{workflow.workflowId}</p>
                      <p className="text-xs text-muted-foreground">{workflow.objective}</p>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className="border-slate-300 text-slate-700">
                      {workflow.state}
                    </Badge>
                  </TableCell>
                  <TableCell>{workflow.owner}</TableCell>
                  <TableCell>{workflow.currentStep}</TableCell>
                  <TableCell>{workflow.updatedAt}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card className="border-slate-200/70 shadow-sm">
        <CardHeader>
          <CardTitle>Selected workflow</CardTitle>
          <CardDescription>Read view for the workflow currently under operator supervision.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-lg border bg-muted/20 p-4">
            <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Objective</p>
            <p className="mt-2 text-sm text-slate-800">{selectedWorkflow.objective}</p>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <div className="rounded-lg border p-4">
              <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">State</p>
              <p className="mt-2 font-medium">{selectedWorkflow.state}</p>
            </div>
            <div className="rounded-lg border p-4">
              <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Transitions</p>
              <p className="mt-2 font-medium">{selectedWorkflow.transitionCount}</p>
            </div>
          </div>
          <div className="rounded-lg border p-4">
            <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Supervisor Notes</p>
            <ul className="mt-3 space-y-2 text-sm text-slate-700">
              {selectedWorkflow.notes.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
