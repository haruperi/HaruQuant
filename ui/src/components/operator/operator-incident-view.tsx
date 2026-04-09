import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

import { operatorIncidents } from "./operator-mock-data"


export function OperatorIncidentView() {
  return (
    <div className="grid gap-6 xl:grid-cols-[1.2fr_1fr]">
      <Card className="border-slate-200/70 shadow-sm">
        <CardHeader>
          <CardTitle>Incident console</CardTitle>
          <CardDescription>Operational incidents, current lifecycle state, and recommended containment actions.</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Incident</TableHead>
                <TableHead>Severity</TableHead>
                <TableHead>State</TableHead>
                <TableHead>Source</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {operatorIncidents.map((incident) => (
                <TableRow key={incident.incidentId}>
                  <TableCell>
                    <div className="space-y-1">
                      <p className="font-medium text-slate-900">{incident.incidentId}</p>
                      <p className="text-xs text-muted-foreground">{incident.summary}</p>
                    </div>
                  </TableCell>
                  <TableCell>{incident.severity}</TableCell>
                  <TableCell>
                    <Badge variant="outline" className="border-slate-300 text-slate-700">
                      {incident.state}
                    </Badge>
                  </TableCell>
                  <TableCell>{incident.source}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card className="border-slate-200/70 shadow-sm">
        <CardHeader>
          <CardTitle>Containment guidance</CardTitle>
          <CardDescription>Recommended actions produced by monitoring and reconciliation services.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {operatorIncidents.map((incident) => (
            <div key={incident.incidentId} className="rounded-lg border p-4">
              <div className="flex items-center justify-between gap-3">
                <p className="font-medium text-slate-900">{incident.alertType}</p>
                <Badge variant="secondary">{incident.severity}</Badge>
              </div>
              <p className="mt-3 text-sm text-slate-700">{incident.recommendedAction}</p>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}
