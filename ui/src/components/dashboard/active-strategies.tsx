"use client"

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { useDashboardSummary } from "@/components/dashboard/use-dashboard-summary"

export function ActiveStrategies() {
  const { data, loading } = useDashboardSummary()

  return (
    <Card className="col-span-3">
      <CardHeader>
        <CardTitle>Active Strategies</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Market</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Timeframe</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={4} className="text-center text-muted-foreground">
                  Loading active strategies...
                </TableCell>
              </TableRow>
            ) : data.active_strategies.length === 0 ? (
              <TableRow>
                <TableCell colSpan={4} className="text-center text-muted-foreground">
                  No active strategy configurations found.
                </TableCell>
              </TableRow>
            ) : (
              data.active_strategies.map((strategy, index) => (
                <TableRow key={`${strategy.session_name}-${strategy.name}-${index}`}>
                  <TableCell className="font-medium">
                    <div>{strategy.name}</div>
                    <div className="text-xs text-muted-foreground">{strategy.session_name}</div>
                  </TableCell>
                  <TableCell>{strategy.market}</TableCell>
                  <TableCell>
                    <Badge variant={strategy.status === "Running" ? "default" : "secondary"}>
                      {strategy.status}
                    </Badge>
                  </TableCell>
                  <TableCell>{strategy.timeframe}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
