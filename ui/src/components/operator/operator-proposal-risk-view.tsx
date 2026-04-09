import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

import { operatorProposals } from "./operator-mock-data"


export function OperatorProposalRiskView() {
  return (
    <div className="grid gap-6 xl:grid-cols-[1.2fr_1fr]">
      <Card className="border-slate-200/70 shadow-sm">
        <CardHeader>
          <CardTitle>Proposal queue</CardTitle>
          <CardDescription>
            Pending and recently decided proposals with readiness, queue order, and linked risk outcomes.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Proposal</TableHead>
                <TableHead>Direction</TableHead>
                <TableHead>Readiness</TableHead>
                <TableHead>Risk Decision</TableHead>
                <TableHead>Expiry</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {operatorProposals.map((proposal) => (
                <TableRow key={proposal.proposalId}>
                  <TableCell>
                    <div className="space-y-1">
                      <p className="font-medium text-slate-900">{proposal.proposalId}</p>
                      <p className="text-xs text-muted-foreground">{proposal.symbol}</p>
                    </div>
                  </TableCell>
                  <TableCell>{proposal.direction}</TableCell>
                  <TableCell>
                    <Badge variant="outline" className="border-slate-300 text-slate-700">
                      {proposal.readiness}
                    </Badge>
                  </TableCell>
                  <TableCell>{proposal.riskDecision}</TableCell>
                  <TableCell>{proposal.expiryAt}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card className="border-slate-200/70 shadow-sm">
        <CardHeader>
          <CardTitle>Constraint snapshot</CardTitle>
          <CardDescription>Decision-linked constraints that operators must respect before execution.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {operatorProposals.map((proposal) => (
            <div key={proposal.proposalId} className="rounded-lg border p-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="font-medium text-slate-900">{proposal.proposalId}</p>
                  <p className="text-sm text-muted-foreground">{proposal.state}</p>
                </div>
                <Badge variant="secondary">Queue #{proposal.queuePosition}</Badge>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {proposal.constraints.map((constraint) => (
                  <Badge key={constraint} variant="outline" className="border-slate-300 text-slate-700">
                    {constraint}
                  </Badge>
                ))}
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}
