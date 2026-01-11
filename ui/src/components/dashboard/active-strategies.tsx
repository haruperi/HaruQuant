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

const strategies = [
  {
    name: "BTC Trend Follow",
    market: "BTCUSD",
    status: "Running",
    pnl: "+$1,240",
    roi: "+12.5%",
  },
  {
    name: "EURUSD Scalper",
    market: "EURUSD",
    status: "Running",
    pnl: "-$120",
    roi: "-0.8%",
  },
  {
    name: "Gold Mean Rev",
    market: "XAUUSD",
    status: "Paused",
    pnl: "+$450",
    roi: "+4.2%",
  },
]

export function ActiveStrategies() {
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
              <TableHead className="text-right">PnL</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {strategies.map((strategy) => (
              <TableRow key={strategy.name}>
                <TableCell className="font-medium">{strategy.name}</TableCell>
                <TableCell>{strategy.market}</TableCell>
                <TableCell>
                  <Badge variant={strategy.status === "Running" ? "default" : "secondary"}>
                    {strategy.status}
                  </Badge>
                </TableCell>
                <TableCell className={`text-right ${strategy.pnl.startsWith('+') ? 'text-emerald-500' : 'text-red-500'}`}>
                    {strategy.pnl}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
