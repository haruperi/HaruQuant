"use client"

import { useState } from "react"
import { format } from "date-fns"
import { CalendarIcon, Database, Loader2, Trash2 } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Calendar } from "@/components/ui/calendar"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { cn } from "@/lib/utils"
import { useEdgeLabData } from "@/contexts/edge-lab-data-context"

export default function EdgeLabDataPage() {
  const { dataset, loading, error, loadDataset, clearDataset } = useEdgeLabData()
  const today = new Date()
  const earliestSelectableMonth = new Date(today.getFullYear() - 30, 0, 1)
  const latestSelectableMonth = new Date(today.getFullYear() + 1, 11, 31)
  const [symbol, setSymbol] = useState("EURUSD")
  const [timeframe, setTimeframe] = useState("H1")
  const [dataSource, setDataSource] = useState<"mt5" | "dukascopy">("mt5")
  const [rangeBy, setRangeBy] = useState<"dates" | "bars">("dates")
  const [startDate, setStartDate] = useState<Date | undefined>(
    new Date(new Date().setFullYear(new Date().getFullYear() - 1))
  )
  const [endDate, setEndDate] = useState<Date | undefined>(new Date())
  const [numberOfBars, setNumberOfBars] = useState("5000")

  const handlePrepare = async () => {
    await loadDataset({
      symbol: symbol.trim().toUpperCase(),
      timeframe,
      data_source: dataSource,
      range_by: rangeBy,
      start_date: rangeBy === "dates" && startDate ? format(startDate, "yyyy-MM-dd") : undefined,
      end_date: rangeBy === "dates" && endDate ? format(endDate, "yyyy-MM-dd") : undefined,
      number_of_bars: rangeBy === "bars" ? Number(numberOfBars) || 5000 : undefined,
      session_basis: "dataset_index",
    })
  }

  const previewColumns = dataset?.preview_rows[0] ? Object.keys(dataset.preview_rows[0]) : []

  return (
    <div className="flex flex-col gap-6 p-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="h-5 w-5 text-primary" />
            Data
          </CardTitle>
          <CardDescription>
            Load, validate, clean, and cache one Edge Lab dataset for reuse across tabs in this session.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <Label htmlFor="symbol">Symbol</Label>
              <Input id="symbol" value={symbol} onChange={(e) => setSymbol(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Timeframe</Label>
              <Select value={timeframe} onValueChange={setTimeframe}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="M1">M1</SelectItem>
                  <SelectItem value="M5">M5</SelectItem>
                  <SelectItem value="M15">M15</SelectItem>
                  <SelectItem value="M30">M30</SelectItem>
                  <SelectItem value="H1">H1</SelectItem>
                  <SelectItem value="H4">H4</SelectItem>
                  <SelectItem value="D1">D1</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Data Source</Label>
              <Select value={dataSource} onValueChange={(val) => setDataSource(val as "mt5" | "dukascopy")}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="mt5">MetaTrader 5</SelectItem>
                  <SelectItem value="dukascopy">Dukascopy</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-1">
            <div className="text-sm text-muted-foreground">
              Session classification uses dataset index time as-is. Fixed session windows:
              {" "}Sydney 00:00-06:59, Tokyo 02:00-08:59, London 10:00-16:59, NY 15:00-21:59.
              Overlaps and gaps are derived automatically.
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <Label>Range By</Label>
              <Select value={rangeBy} onValueChange={(val) => setRangeBy(val as "dates" | "bars")}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="dates">Dates</SelectItem>
                  <SelectItem value="bars">Bars</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {rangeBy === "dates" ? (
              <>
                <div className="space-y-2 flex flex-col">
                  <Label>Start Date</Label>
                  <Popover>
                    <PopoverTrigger asChild>
                      <Button
                        variant="outline"
                        className={cn("w-full justify-start text-left font-normal", !startDate && "text-muted-foreground")}
                      >
                        <CalendarIcon className="mr-2 h-4 w-4" />
                        {startDate ? format(startDate, "PPP") : <span>Pick a date</span>}
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-auto p-0" align="start">
                      <Calendar
                        mode="single"
                        selected={startDate}
                        onSelect={setStartDate}
                        captionLayout="dropdown"
                        startMonth={earliestSelectableMonth}
                        endMonth={latestSelectableMonth}
                        initialFocus
                      />
                    </PopoverContent>
                  </Popover>
                </div>
                <div className="space-y-2 flex flex-col">
                  <Label>End Date</Label>
                  <Popover>
                    <PopoverTrigger asChild>
                      <Button
                        variant="outline"
                        className={cn("w-full justify-start text-left font-normal", !endDate && "text-muted-foreground")}
                      >
                        <CalendarIcon className="mr-2 h-4 w-4" />
                        {endDate ? format(endDate, "PPP") : <span>Pick a date</span>}
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-auto p-0" align="start">
                      <Calendar
                        mode="single"
                        selected={endDate}
                        onSelect={setEndDate}
                        captionLayout="dropdown"
                        startMonth={earliestSelectableMonth}
                        endMonth={latestSelectableMonth}
                        initialFocus
                      />
                    </PopoverContent>
                  </Popover>
                </div>
              </>
            ) : (
              <div className="space-y-2 md:col-span-2">
                <Label htmlFor="numberOfBars">Number of Bars</Label>
                <Input
                  id="numberOfBars"
                  type="number"
                  value={numberOfBars}
                  onChange={(e) => setNumberOfBars(e.target.value)}
                />
              </div>
            )}
          </div>

          <div className="flex items-center gap-3">
            <Button onClick={handlePrepare} disabled={loading || !symbol.trim()}>
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Prepare Dataset
            </Button>
            <Button variant="outline" onClick={clearDataset} disabled={!dataset}>
              <Trash2 className="mr-2 h-4 w-4" />
              Clear Session Dataset
            </Button>
            {error && <p className="text-sm text-destructive">{error}</p>}
          </div>
        </CardContent>
      </Card>

      {dataset && (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>{dataset.request.symbol} {dataset.request.timeframe}</span>
                <Badge className={dataset.report.is_valid ? "bg-emerald-500/15 text-emerald-600" : "bg-rose-500/15 text-rose-600"}>
                  {dataset.report.is_valid ? "READY" : "HAS_FATAL_ERRORS"}
                </Badge>
              </CardTitle>
              <CardDescription>{dataset.meta.n_rows} rows cached for this browser session.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-5 text-sm">
                <div><div className="text-muted-foreground">Source</div><div>{dataset.request.data_source}</div></div>
                <div><div className="text-muted-foreground">Range</div><div>{dataset.request.range_by}</div></div>
                <div><div className="text-muted-foreground">Session Basis</div><div>{dataset.meta.session_basis ?? dataset.request.session_basis ?? "dataset_index"}</div></div>
                <div><div className="text-muted-foreground">Warnings</div><div>{dataset.report.warnings.length}</div></div>
                <div><div className="text-muted-foreground">Fatal Errors</div><div>{dataset.report.fatal_errors.length}</div></div>
                <div><div className="text-muted-foreground">Checks</div><div>{dataset.report.checks_performed.length}</div></div>
              </div>
              <div className="mt-4 text-sm text-muted-foreground">
                Session hours:
                {" "}
                {dataset.meta.session_hours
                  ? `Sydney ${dataset.meta.session_hours.sydney?.[0] ?? 0}-${(dataset.meta.session_hours.sydney?.slice(-1)[0] ?? 0)} / Tokyo ${dataset.meta.session_hours.tokyo?.[0] ?? 0}-${(dataset.meta.session_hours.tokyo?.slice(-1)[0] ?? 0)} / London ${dataset.meta.session_hours.london?.[0] ?? 0}-${(dataset.meta.session_hours.london?.slice(-1)[0] ?? 0)} / NY ${dataset.meta.session_hours.ny?.[0] ?? 0}-${(dataset.meta.session_hours.ny?.slice(-1)[0] ?? 0)}`
                  : "default"}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Preview</CardTitle>
              <CardDescription>First 200 serialized rows from the prepared dataset.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="border rounded-lg overflow-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      {previewColumns.map((column) => (
                        <TableHead key={column}>{column}</TableHead>
                      ))}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {dataset.preview_rows.map((row, index) => (
                      <TableRow key={index}>
                        {previewColumns.map((column) => (
                          <TableCell key={`${index}-${column}`} className="font-mono text-xs">
                            {String(row[column] ?? "—")}
                          </TableCell>
                        ))}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
