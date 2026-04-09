import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

import { operatorApprovals } from "./operator-mock-data"


export function OperatorApprovalView() {
  return (
    <div className="grid gap-6 xl:grid-cols-[1.15fr_0.95fr]">
      <Card className="border-slate-200/70 shadow-sm">
        <CardHeader>
          <CardTitle>Approval queue</CardTitle>
          <CardDescription>Pending approvals that gate live execution, policy changes, and override flows.</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Approval</TableHead>
                <TableHead>Action</TableHead>
                <TableHead>Progress</TableHead>
                <TableHead>Created By</TableHead>
                <TableHead>Expiry</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {operatorApprovals.map((approval) => (
                <TableRow key={approval.approvalId}>
                  <TableCell className="font-medium text-slate-900">{approval.approvalId}</TableCell>
                  <TableCell>{approval.actionType}</TableCell>
                  <TableCell>
                    {approval.collectedVotes}/{approval.requiredCount}
                  </TableCell>
                  <TableCell>{approval.createdBy}</TableCell>
                  <TableCell>{approval.expiresAt}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card className="border-slate-200/70 shadow-sm">
        <CardHeader>
          <CardTitle>Pending reviewer mix</CardTitle>
          <CardDescription>Outstanding reviewer roles before the approval can transition out of `PENDING`.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {operatorApprovals.map((approval) => (
            <div key={approval.approvalId} className="rounded-lg border p-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="font-medium text-slate-900">{approval.targetRefId}</p>
                  <p className="text-sm text-muted-foreground">{approval.state}</p>
                </div>
                <Badge variant="outline" className="border-slate-300 text-slate-700">
                  {approval.actionType}
                </Badge>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {approval.pendingRoles.map((role) => (
                  <Badge key={role} variant="secondary">
                    {role}
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
