"use client"

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { TrendingUp, TrendingDown } from "lucide-react"
import type { CurrencyPairSignal } from "@/types/live"

interface CurrencyPairStrengthTableProps {
  pairs: CurrencyPairSignal[]
  title: string
  type: "strong" | "weak"
  maxRows?: number
  tf1Label: string
  tf2Label: string
  tf3Label: string
}

export function CurrencyPairStrengthTable({
  pairs,
  title,
  type,
  maxRows = 10,
  tf1Label,
  tf2Label,
  tf3Label,
}: CurrencyPairStrengthTableProps) {
  const isStrong = type === "strong"
  const displayPairs = pairs.slice(0, maxRows)

  const getStrengthColor = (strength: number) => {
    const absStrength = Math.abs(strength)
    if (absStrength > 1.0) return isStrong ? "text-emerald-600" : "text-red-600"
    if (absStrength > 0.5) return isStrong ? "text-emerald-500" : "text-red-500"
    return isStrong ? "text-emerald-400" : "text-red-400"
  }

  const getChangeColor = (change: number) => {
    if (change > 0) return "text-emerald-500"
    if (change < 0) return "text-red-500"
    return "text-muted-foreground"
  }

  if (displayPairs.length === 0) {
    return (
      <div className="rounded-lg border bg-card text-card-foreground shadow-sm">
        <div className="p-6">
          <h3 className="text-lg font-semibold mb-4">{title}</h3>
          <p className="text-sm text-muted-foreground text-center py-8">
            No pairs available
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="rounded-lg border bg-card text-card-foreground shadow-sm">
      <div className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">{title}</h3>
          <Badge variant="outline" className="font-semibold">
            {displayPairs.length} pair{displayPairs.length !== 1 ? "s" : ""}
          </Badge>
        </div>

        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[80px]">Pair</TableHead>
                <TableHead className="w-[60px]">Base</TableHead>
                <TableHead className="w-[60px]">Quote</TableHead>
                <TableHead className="text-right w-[70px]">{tf1Label}</TableHead>
                <TableHead className="text-right w-[70px]">{tf2Label}</TableHead>
                <TableHead className="text-right w-[70px]">{tf3Label}</TableHead>
                <TableHead className="text-right w-[90px]">Strength</TableHead>
                <TableHead className="text-right w-[100px]">Signal</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {displayPairs.map((pair, index) => (
                <TableRow
                  key={pair.pair}
                  className={index % 2 === 0 ? "bg-muted/20" : ""}
                >
                  <TableCell className="font-mono font-semibold">
                    {pair.pair}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {pair.base}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {pair.quote}
                  </TableCell>
                  <TableCell
                    className={`text-right font-mono text-sm ${
                      pair.tf1_change != null
                        ? getChangeColor(pair.tf1_change)
                        : "text-muted-foreground"
                    }`}
                  >
                    {pair.tf1_change != null
                      ? `${pair.tf1_change > 0 ? "+" : ""}${pair.tf1_change.toFixed(
                          2
                        )}%`
                      : "-"}
                  </TableCell>
                  <TableCell
                    className={`text-right font-mono text-sm ${
                      pair.tf2_change != null
                        ? getChangeColor(pair.tf2_change)
                        : "text-muted-foreground"
                    }`}
                  >
                    {pair.tf2_change != null
                      ? `${pair.tf2_change > 0 ? "+" : ""}${pair.tf2_change.toFixed(
                          2
                        )}%`
                      : "-"}
                  </TableCell>
                  <TableCell
                    className={`text-right font-mono text-sm ${
                      pair.tf3_change != null
                        ? getChangeColor(pair.tf3_change)
                        : "text-muted-foreground"
                    }`}
                  >
                    {pair.tf3_change != null
                      ? `${pair.tf3_change > 0 ? "+" : ""}${pair.tf3_change.toFixed(
                          2
                        )}%`
                      : "-"}
                  </TableCell>
                  <TableCell
                    className={`text-right font-mono font-bold ${getStrengthColor(
                      pair.pair_strength
                    )}`}
                  >
                    {pair.pair_strength > 0 ? "+" : ""}
                    {pair.pair_strength.toFixed(2)}%
                  </TableCell>
                  <TableCell className="text-right">
                    <Badge
                      className={`font-semibold ${
                        isStrong
                          ? "bg-emerald-500/20 text-emerald-500 hover:bg-emerald-500/30"
                          : "bg-red-500/20 text-red-500 hover:bg-red-500/30"
                      }`}
                    >
                      {isStrong ? (
                        <TrendingUp className="h-3 w-3 mr-1" />
                      ) : (
                        <TrendingDown className="h-3 w-3 mr-1" />
                      )}
                      {pair.recommendation}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>
    </div>
  )
}
