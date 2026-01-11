"use client"

import * as React from "react"
import {
  format,
  startOfMonth,
  endOfMonth,
  startOfWeek,
  endOfWeek,
  eachDayOfInterval,
  isSameMonth,
  isSameDay,
  addMonths,
  subMonths,
  isToday,
  parseISO
} from "date-fns"
import { useRouter } from "next/navigation"
import { useSelectedBacktest } from "@/contexts/selected-backtest-context"
import { strategyApi } from "@/lib/api/strategies"
import { cn } from "@/lib/utils"
import {
  ChevronLeft,
  ChevronRight,
  Calendar as CalendarIcon,
  Info,
  Settings,
  Camera,
  Loader2,
  ChevronUp,
  ChevronDown
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Checkbox } from "@/components/ui/checkbox"
import { Label } from "@/components/ui/label"
import { toPng } from "html-to-image"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogTrigger,
  DialogClose
} from "@/components/ui/dialog"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  CartesianGrid
} from "recharts"

interface DailyData {
  period: string
  period_start: string
  num_trades: number
  net_profit: number
  gross_profit: number
  gross_loss: number
  profit_factor: number
  win_rate: number
  return_pct: number
}

interface WeekStats {
  id: number
  netProfit: number
  tradeCount: number
  daysTraded: number
}

export function TradesCalendar() {
  const { selectedBacktest } = useSelectedBacktest()
  const router = useRouter()
  const [currentMonth, setCurrentMonth] = React.useState(new Date())
  const [dailyData, setDailyData] = React.useState<DailyData[]>([])
  const [loading, setLoading] = React.useState(false)

  // Snapshot state
  const [snapshotUrl, setSnapshotUrl] = React.useState<string | null>(null)
  const [isSnapshotOpen, setIsSnapshotOpen] = React.useState(false)
  const calendarRef = React.useRef<HTMLDivElement>(null)

  // Picker state
  const [isPickerOpen, setIsPickerOpen] = React.useState(false)
  const [pickerView, setPickerView] = React.useState<"months" | "years">("months")
  const [pickerYear, setPickerYear] = React.useState(new Date().getFullYear())

  // Details Dialog State
  const [rawTrades, setRawTrades] = React.useState<any[]>([])
  const [selectedDate, setSelectedDate] = React.useState<Date | null>(null)
  const [isDetailsOpen, setIsDetailsOpen] = React.useState(false)

  // Display Settings
  // Display Settings
  const [visibleMetrics, setVisibleMetrics] = React.useState({
    rMultiple: false,
    dailyPnL: true,
    ticks: false,
    pips: false,
    points: false,
    numTrades: true,
    dayWinRate: true
  })

  // Sync picker year with current month when opening
  React.useEffect(() => {
    if (isPickerOpen) {
      setPickerYear(currentMonth.getFullYear())
      setPickerView("months")
    }
  }, [isPickerOpen, currentMonth])

  // Fetch data
  React.useEffect(() => {
    const fetchData = async () => {
      if (!selectedBacktest) return

      try {
        setLoading(true)

        let trades = selectedBacktest.trades || []
        let initialBalance = selectedBacktest.initial_balance || 10000

        // If trades are missing, fetch full backtest details
        if (trades.length === 0) {
           try {
              const fullBacktest = await strategyApi.getBacktestById(selectedBacktest.backtest_id)
              if (fullBacktest && fullBacktest.trades) {
                  trades = fullBacktest.trades
                  initialBalance = fullBacktest.initial_balance || initialBalance
              }
           } catch (err) {
              console.error("Failed to fetch full backtest details", err)
           }
        }

        setRawTrades(trades)

        // Check again if we have trades
        if (trades.length > 0) {
           const data = await strategyApi.getPeriodAnalysis('daily', trades, initialBalance)
           setDailyData(data)

           // Set current month to the last month with trades if we have data
           // We do this if the current month has no data? Or just once on load?
           // A simple heuristic: if the current view has NO trades, jump to the last trade.
           if (data.length > 0) {
             const lastTradeDate = parseISO(data[data.length - 1].period_start)
             // Only if current view is seemingly empty/far off?
             // Or just always jump on initial data load if we assume user wants to see results
             // We can check if `currentMonth` is default (Today).
             if (isSameMonth(currentMonth, new Date())) {
                 setCurrentMonth(lastTradeDate)
             }
           }
        } else {
            console.log("No trades found for backtest", selectedBacktest.backtest_id)
            setDailyData([])
        }
      } catch (error) {
        console.error("Failed to fetch calendar data", error)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [selectedBacktest]) // Remove currentMonth from dependency to avoid loop when setting it

  const nextMonth = () => setCurrentMonth(addMonths(currentMonth, 1))
  const prevMonth = () => setCurrentMonth(subMonths(currentMonth, 1))
  const goToToday = () => setCurrentMonth(new Date())

  const handleSnapshot = async () => {
      if (!calendarRef.current) return
      try {
          const url = await toPng(calendarRef.current, {
              backgroundColor: '#020617', // Match current theme bg
              pixelRatio: 2
          })
          setSnapshotUrl(url)
          setIsSnapshotOpen(true)
      } catch (err) {
          console.error("Snapshot failed", err)
      }
  }

  const handleDownload = () => {
      if (!snapshotUrl) return
      const link = document.createElement('a')
      link.href = snapshotUrl
      link.download = `trades-calendar-${format(currentMonth, 'yyyy-MM')}.png`
      link.click()
      setIsSnapshotOpen(false)
  }

  const handleCopy = async () => {
      if (!snapshotUrl) return
      try {
          const res = await fetch(snapshotUrl)
          const blob = await res.blob()
          await navigator.clipboard.write([
              new ClipboardItem({ [blob.type]: blob })
          ])
          setIsSnapshotOpen(false)
      } catch (err) {
          console.error("Failed to copy", err)
      }
  }

  // Generate calendar grid
  const monthStart = startOfMonth(currentMonth)
  const monthEnd = endOfMonth(monthStart)
  const startDate = startOfWeek(monthStart)
  const endDate = endOfWeek(monthEnd)

  const calendarDays = eachDayOfInterval({
    start: startDate,
    end: endDate,
  })

  // Group days into weeks
  const weeks: Date[][] = []
  let currentWeek: Date[] = []

  calendarDays.forEach((day) => {
    currentWeek.push(day)
    if (currentWeek.length === 7) {
      weeks.push(currentWeek)
      currentWeek = []
    }
  })

  // Helpers to get data for a day
  const getDataForDay = (date: Date) => {
    return dailyData.find(d => isSameDay(parseISO(d.period_start), date))
  }

  const safeParseDate = (dateStr: string | undefined | null) => {
      if (!dateStr) return new Date() // Fallback to now or invalid?
      try {
          return parseISO(dateStr)
      } catch (e) {
          return new Date()
      }
  }

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 1,
    }).format(val)
  }

  // Calculate monthly stats
  const monthlyStats = React.useMemo(() => {
    let profit = 0
    let tradeCount = 0
    let daysTraded = 0

    // Filter data for current month
    const monthData = dailyData.filter(d => isSameMonth(parseISO(d.period_start), currentMonth))

    monthData.forEach(d => {
      profit += d.net_profit
      tradeCount += d.num_trades
      if (d.num_trades > 0) daysTraded++
    })

    return { profit, tradeCount, daysTraded }
  }, [dailyData, currentMonth])



  // Get data for selected date
  const selectedDayData = React.useMemo(() => {
    if (!selectedDate || !rawTrades.length) {
      return null
    }



    const dayTrades = rawTrades.filter(t => {
      // Prioritize close_time for filtering since we're grouping by close date
      const timeStr = t.close_time || t.exit_time || t.time || t.entry_time
      if (!timeStr) return false

      try {
        const tradeDate = parseISO(timeStr)
        return isSameDay(tradeDate, selectedDate)
      } catch (e) {
        console.error('Failed to parse trade date:', timeStr, e)
        return false
      }
    }).sort((a, b) => {
        const tA = a.close_time || a.exit_time || a.time || a.entry_time
        const tB = b.close_time || b.exit_time || b.time || b.entry_time
        return new Date(tA).getTime() - new Date(tB).getTime()
    })



    if (dayTrades.length === 0) {
      return null
    }

    let totalPnL = 0
    let grossProfit = 0
    let grossLoss = 0
    let winners = 0
    let losers = 0
    let volume = 0
    let commissions = 0

    // Chart Data (Cumulative PnL for the day)
    const chartData = dayTrades.map((t, i) => {
      let pnl = t.profit_loss !== undefined ? t.profit_loss : (t.profit || t.net_profit || t.pnl || 0)
      if (typeof pnl === 'string') pnl = parseFloat(pnl)
      if (isNaN(pnl)) pnl = 0

      totalPnL += pnl

      let comm = t.commission || t.commissions || 0
      if (typeof comm === 'string') comm = parseFloat(comm)

      let swap = t.swap || 0
      if (typeof swap === 'string') swap = parseFloat(swap)

      commissions += Math.abs(comm + swap)

      let vol = t.volume || t.size || 0
      if (typeof vol === 'string') vol = parseFloat(vol)
      volume += vol

      if (pnl > 0) {
        grossProfit += pnl
        winners++
      } else if (pnl < 0) {
        grossLoss += Math.abs(pnl)
        losers++
      }

      return {
        time: format(safeParseDate(t.close_time || t.exit_time || t.time), "HH:mm:ss"),
        pnl: totalPnL,
        tradeAcc: i + 1
      }
    })

    // Add start point for chart
    if (chartData.length > 0) {
        chartData.unshift({ time: "Start", pnl: 0, tradeAcc: 0 })
    }

    const winRate = dayTrades.length > 0 ? (winners / dayTrades.length) * 100 : 0
    const profitFactor = grossLoss > 0 ? grossProfit / grossLoss : grossProfit > 0 ? 100 : 0

    return {
      trades: dayTrades,
      stats: {
        totalPnL,
        grossProfit,
        grossLoss,
        winners,
        losers,
        winRate,
        profitFactor,
        commissions,
        volume
      },
      chartData
    }
  }, [selectedDate, rawTrades])

  return (
    <div className="flex flex-col h-full bg-background text-foreground p-4 gap-4">
      {/* Header */}
      <header className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1">
             <Button variant="ghost" size="icon" onClick={prevMonth}>
               <ChevronLeft className="h-4 w-4" />
             </Button>

             <Popover open={isPickerOpen} onOpenChange={setIsPickerOpen}>
               <PopoverTrigger asChild>
                 <Button variant="ghost" className="text-xl font-bold h-auto py-1 px-2 hover:bg-muted">
                   {format(currentMonth, "MMMM yyyy")}
                 </Button>
               </PopoverTrigger>
               <PopoverContent className="w-[280px] p-3" align="start">
                 {/* Picker Header */}
                 <div className="flex items-center justify-between mb-4">
                    <div
                      className="font-semibold text-sm cursor-pointer hover:bg-muted px-2 py-1 rounded-md flex items-center gap-1"
                      onClick={() => setPickerView(pickerView === "months" ? "years" : "months")}
                    >
                      {pickerView === "months" ? `${pickerYear}` : "Select Year"}
                      {pickerView === "months" ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                    </div>
                 </div>

                 {/* Months View */}
                 {pickerView === "months" && (
                   <div className="grid grid-cols-3 gap-2">
                     {Array.from({ length: 12 }).map((_, i) => {
                       const date = new Date(pickerYear, i, 1)
                       const isSelected = isSameMonth(date, currentMonth)
                       return (
                         <Button
                           key={i}
                           variant={isSelected ? "default" : "ghost"}
                           onClick={() => {
                             setCurrentMonth(date)
                             setIsPickerOpen(false)
                           }}
                           className={cn(
                             "h-8 text-sm",
                             isSelected && "bg-primary text-primary-foreground"
                           )}
                         >
                           {format(date, "MMM")}
                         </Button>
                       )
                     })}
                   </div>
                 )}

                 {/* Years View - Scrollable */}
                 {pickerView === "years" && (
                   <ScrollArea className="h-[240px]">
                     <div className="grid grid-cols-3 gap-2 pr-4">
                       {Array.from({ length: 60 }).map((_, i) => {
                         // Range: Current Year - 40 to Current Year + 19 (Total 60 years)
                         // Centered somewhat around recent times, adjustable as needed.
                         // Or better: 1990 to 2030+
                         const startYear = 1990
                         const year = startYear + i
                         const isSelected = year === currentMonth.getFullYear()
                         return (
                           <Button
                             key={year}
                             variant={isSelected ? "default" : "ghost"}
                             onClick={() => {
                               setPickerYear(year)
                               setPickerView("months")
                               // Also update current month's year immediately?
                               // Typically year picker picks year, then you pick month.
                               // But user might just want to change year keeping same month.
                               // Let's stick to updating pickerYear which drives month view.
                             }}
                             className={cn(
                               "h-8 text-sm",
                               isSelected && "bg-primary text-primary-foreground"
                             )}
                           >
                             {year}
                           </Button>
                         )
                       })}
                     </div>
                   </ScrollArea>
                 )}
               </PopoverContent>
             </Popover>

             <Button variant="ghost" size="icon" onClick={nextMonth}>
               <ChevronRight className="h-4 w-4" />
             </Button>
          </div>
          <Button variant="outline" className="h-8" onClick={goToToday}>
            This month
          </Button>

          <span className="text-lg font-semibold ml-4">
            Trades Calendar - <span className="text-muted-foreground">{selectedBacktest?.alias || selectedBacktest?.strategy_name || "No Backtest Selected"}</span>
          </span>
        </div>

        <div className="flex items-center gap-6">
           <div className="flex items-center gap-2 text-sm">
             <span className="text-muted-foreground font-medium">Monthly stats:</span>
             <Badge variant={monthlyStats.profit >= 0 ? "default" : "destructive"}
                    className={cn(
                      "text-base px-2 py-0.5",
                      monthlyStats.profit >= 0 ? "bg-emerald-500 hover:bg-emerald-600" : "bg-red-500 hover:bg-red-600"
                    )}>
               {formatCurrency(monthlyStats.profit)}
             </Badge>
             <span className="text-muted-foreground">{monthlyStats.daysTraded} days</span>
           </div>

           <div className="flex items-center gap-1">
             <Popover>
               <PopoverTrigger asChild>
                 <Button variant="ghost" size="icon" className="h-8 w-8">
                   <Settings className="h-4 w-4" />
                 </Button>
               </PopoverTrigger>
               <PopoverContent className="w-56" align="end">
                 <div className="grid gap-4">
                   <div className="space-y-2">
                     <h4 className="font-medium leading-none">Display stats</h4>
                     <p className="text-xs text-muted-foreground">
                       Select metrics to show on calendar days.
                     </p>
                   </div>
                   <div className="grid gap-2">
                     <div className="flex items-center space-x-2">
                       <Checkbox
                         id="show-r-multiple"
                         checked={visibleMetrics.rMultiple}
                         onCheckedChange={(c) => setVisibleMetrics(m => ({ ...m, rMultiple: !!c }))}
                       />
                       <Label htmlFor="show-r-multiple">R Multiple</Label>
                     </div>
                     <div className="flex items-center space-x-2">
                       <Checkbox
                         id="show-pnl"
                         checked={visibleMetrics.dailyPnL}
                         onCheckedChange={(c) => setVisibleMetrics(m => ({ ...m, dailyPnL: !!c }))}
                       />
                       <Label htmlFor="show-pnl">Daily P/L</Label>
                     </div>
                     <div className="flex items-center space-x-2">
                       <Checkbox
                         id="show-ticks"
                         checked={visibleMetrics.ticks}
                         onCheckedChange={(c) => setVisibleMetrics(m => ({ ...m, ticks: !!c }))}
                       />
                       <Label htmlFor="show-ticks">Ticks</Label>
                     </div>
                     <div className="flex items-center space-x-2">
                       <Checkbox
                         id="show-pips"
                         checked={visibleMetrics.pips}
                         onCheckedChange={(c) => setVisibleMetrics(m => ({ ...m, pips: !!c }))}
                       />
                       <Label htmlFor="show-pips">Pips</Label>
                     </div>
                     <div className="flex items-center space-x-2">
                       <Checkbox
                         id="show-points"
                         checked={visibleMetrics.points}
                         onCheckedChange={(c) => setVisibleMetrics(m => ({ ...m, points: !!c }))}
                       />
                       <Label htmlFor="show-points">Points</Label>
                     </div>
                     <div className="flex items-center space-x-2">
                       <Checkbox
                         id="show-trades"
                         checked={visibleMetrics.numTrades}
                         onCheckedChange={(c) => setVisibleMetrics(m => ({ ...m, numTrades: !!c }))}
                       />
                       <Label htmlFor="show-trades">Number of trades</Label>
                     </div>
                     <div className="flex items-center space-x-2">
                       <Checkbox
                         id="show-winrate"
                         checked={visibleMetrics.dayWinRate}
                         onCheckedChange={(c) => setVisibleMetrics(m => ({ ...m, dayWinRate: !!c }))}
                       />
                       <Label htmlFor="show-winrate">Day winrate</Label>
                     </div>
                   </div>
                 </div>
               </PopoverContent>
             </Popover>
             <Button variant="ghost" size="icon" className="h-8 w-8" onClick={handleSnapshot}>
               <Camera className="h-4 w-4" />
             </Button>
             <Button variant="ghost" size="icon" className="h-8 w-8">
               <Info className="h-4 w-4" />
             </Button>
           </div>
        </div>
      </header>

      {/* Main Content */}
      <div ref={calendarRef} className="flex flex-1 gap-4 min-h-0 bg-background">
        {/* Calendar Grid */}
        <div className="flex-1 flex flex-col min-h-0 bg-card rounded-lg border shadow-sm">
           {/* Weekday Headers */}
           <div className="grid grid-cols-7 border-b">
             {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map(day => (
               <div key={day} className="py-2 text-center text-sm font-semibold text-muted-foreground border-r last:border-r-0">
                 {day}
               </div>
             ))}
           </div>

           {/* Days Grid */}
           <div className="flex-1 grid grid-cols-7 grid-rows-5 md:grid-rows-6">
             {weeks.map((week, weekIndex) => (
                <React.Fragment key={weekIndex}>
                  {week.map((day, dayIndex) => {
                    const data = getDataForDay(day)
                    const isOutside = !isSameMonth(day, currentMonth)
                    const profit = data?.net_profit || 0
                    const isPositive = profit >= 0
                    const hasTrades = (data?.num_trades || 0) > 0

                      return (
                       <div
                         key={day.toISOString()}
                         onClick={() => {
                           if (hasTrades) {
                             setSelectedDate(day)
                             setIsDetailsOpen(true)
                           }
                         }}
                         className={cn(
                           "relative p-2 border-b border-r last:border-r-0 flex flex-col justify-between transition-all min-h-[100px]",
                           isOutside && "bg-muted/10 text-muted-foreground/50",
                           // Background tint for significant days
                           !isOutside && hasTrades && isPositive && "bg-emerald-950/30 hover:bg-emerald-950/50 border-emerald-900/30 cursor-pointer",
                           !isOutside && hasTrades && !isPositive && "bg-red-950/30 hover:bg-red-950/50 border-red-900/30 cursor-pointer",
                           (!hasTrades || isOutside) && "hover:bg-accent/50 cursor-default"
                         )}
                       >
                          {/* Header: Icon + Date */}
                          <div className="flex justify-between items-start">
                              {/* Left Icon for days with trades */}
                              {!isOutside && hasTrades && (
                                <CalendarIcon className={cn(
                                  "h-4 w-4 opacity-70",
                                  isPositive ? "text-emerald-500" : "text-red-500"
                                )} />
                              )}
                              {!hasTrades && <span />} {/* Spacer */}

                              {/* Date Number */}
                              <div className={cn(
                                "text-sm font-medium",
                                isSameDay(day, new Date())
                                  ? "bg-primary text-primary-foreground rounded-full w-6 h-6 flex items-center justify-center"
                                  : "text-muted-foreground"
                              )}>
                                {format(day, "d")}
                              </div>
                          </div>

                          {/* Day Stats */}
                          {!isOutside && hasTrades && (
                            <div className="flex flex-col items-end gap-0.5 mt-auto">
                             {/* Icon for very good days? Screenshot shows calendar icon for some days */}

                             {visibleMetrics.rMultiple && (
                               <span className="text-xs text-muted-foreground">0R</span>
                             )}

                              {visibleMetrics.dailyPnL && (
                                <span className={cn(
                                  "text-lg font-bold leading-none tracking-tight my-1",
                                  isPositive ? "text-emerald-400" : "text-red-400"
                                )}>
                                  {formatCurrency(profit)}
                                </span>
                              )}

                              {visibleMetrics.numTrades && (
                                <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">
                                  {data?.num_trades} {data?.num_trades === 1 ? 'trade' : 'trades'}
                                </span>
                              )}

                              {visibleMetrics.dayWinRate && data?.win_rate !== undefined && (
                                <span className={cn(
                                  "text-[10px] font-medium",
                                  data.win_rate >= 50 ? "text-emerald-500" : "text-red-500"
                                )}>
                                  {data.win_rate.toFixed(1)}%
                                </span>
                              )}

                              {/* Others (Placeholders/Extras) */}
                              {visibleMetrics.rMultiple && <span className="text-[10px] text-muted-foreground">0R</span>}
                              {visibleMetrics.ticks && <span className="text-[10px] text-muted-foreground">0 ticks</span>}
                              {visibleMetrics.pips && <span className="text-[10px] text-muted-foreground">0 pips</span>}
                              {visibleMetrics.points && <span className="text-[10px] text-muted-foreground">0 pts</span>}

                            </div>
                          )}
                      </div>
                    )
                  })}
                </React.Fragment>
             ))}
             {/* Fill remaining space if fewer weeks? grid-rows handling sorts this mostly */}
           </div>
        </div>

        {/* Weekly Sidebar */}
        <div className="w-[180px] flex flex-col min-h-0 bg-card rounded-lg border shadow-sm">
          {/* Header to align with calendar day headers */}
          <div className="py-2 text-center text-sm font-semibold text-muted-foreground border-b h-[37px] flex items-center justify-center">
            Weekly Stats
          </div>

          <div className="flex-1 grid grid-cols-1 grid-rows-5 md:grid-rows-6">
            {weeks.map((week, index) => {
               // Calculate stats for this week row
               let weekProfit = 0
               let daysWithTrades = 0
               let tradeCount = 0

               const weekHasCurrentMonthDays = week.some(d => isSameMonth(d, currentMonth))

               // Even if we don't show stats, we render the cell to maintain alignment
               // Only calculate if relevant
               if (weekHasCurrentMonthDays || index === 0) {
                 week.forEach(day => {
                   if (!isSameMonth(day, currentMonth)) return
                   const d = getDataForDay(day)
                   if (d) {
                     weekProfit += d.net_profit
                     tradeCount += d.num_trades
                     if (d.num_trades > 0) daysWithTrades++
                   }
                 })
               }

               const showStats = (weekHasCurrentMonthDays || index === 0) && (daysWithTrades > 0 || tradeCount > 0 || weekProfit !== 0 || index < weeks.length);
               // Actually we generally want to show "Week X" even if empty?
               // Or leave blank? The screenshot shows "Week 3 $0".
               // So we always render content, just maybe $0.

               return (
                 <div key={index} className="border-b p-3 flex flex-col justify-center gap-1 transition-colors hover:bg-accent/50">
                   {weekHasCurrentMonthDays && (
                     <>
                        <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Week {index + 1}</h3>
                        <div className={cn(
                          "text-lg font-bold leading-none",
                          weekProfit > 0 ? "text-emerald-400" : weekProfit < 0 ? "text-red-400" : "text-foreground"
                        )}>
                          {formatCurrency(weekProfit)}
                        </div>
                        <div className="flex items-center gap-2 mt-1">
                             <Badge variant="secondary" className="text-[10px] px-1.5 h-5 font-normal text-muted-foreground">
                                {daysWithTrades} {daysWithTrades === 1 ? 'day' : 'days'}
                             </Badge>
                             {tradeCount > 0 && (
                                <span className="text-[10px] text-muted-foreground">
                                    {tradeCount} trades
                                </span>
                             )}
                        </div>
                     </>
                   )}
                 </div>
               )
            })}
             {/* Fill remaining space if weeks < 6?
                 The grid-rows-6 will force the used rows to be 1/6 height?
                 If we map 'weeks', we get N items. If N < 6, the last rows are empty.
                 We need to ensure we fill the grid if we want borders?
                 Actually, just letting the grid handle it is usually fine, but borders might be missing for empty slots.
                 To perfectly match the calendar which fills 6 rows, we should probably ensure 6 items if we want lines.
                 But visually, empty space at bottom is fine.
             */}
          </div>
        </div>
      </div>
      {/* Snapshot Dialog */}
      <Dialog open={isSnapshotOpen} onOpenChange={setIsSnapshotOpen}>
        <DialogContent className="bg-slate-900 border-slate-800 text-white max-w-3xl">
            <DialogHeader>
                <DialogTitle>Calendar Snapshot</DialogTitle>
            </DialogHeader>
            <div className="flex items-center justify-center p-4 bg-slate-950 rounded-lg overflow-auto max-h-[60vh]">
                {snapshotUrl && (
                    <img src={snapshotUrl} alt="Calendar Snapshot" className="max-w-full h-auto" />
                )}
            </div>
            <DialogFooter className="gap-2 sm:gap-0">
                <Button variant="outline" onClick={() => setIsSnapshotOpen(false)} className="border-slate-700 hover:bg-slate-800 text-white">
                    Cancel
                </Button>
                <Button variant="outline" onClick={handleCopy} className="border-slate-700 hover:bg-slate-800 text-white">
                    Copy to Clipboard
                </Button>
                <Button onClick={handleDownload} className="bg-emerald-600 hover:bg-emerald-700 text-white">
                    Download
                </Button>
            </DialogFooter>
        </DialogContent>
      </Dialog>
      <Dialog open={isDetailsOpen} onOpenChange={setIsDetailsOpen}>
         <DialogContent showCloseButton={false} className="max-w-[80vw] w-[80vw] sm:max-w-[80vw] bg-background text-foreground border-border max-h-[90vh] overflow-y-auto">
            {selectedDayData && (
              <div className="space-y-6">
                 {/* Header */}
                 <div className="flex items-center justify-between border-b pb-4">
                    <div className="flex items-center gap-4">
                       <DialogTitle className="text-xl font-bold flex items-center gap-2">
                         {format(selectedDate!, "EEE, MMM dd, yyyy")}
                         <span className="text-muted-foreground mx-2">•</span>
                         <span className={selectedDayData.stats.totalPnL >= 0 ? "text-emerald-500" : "text-red-500"}>
                            Net P&L {formatCurrency(selectedDayData.stats.totalPnL)}
                         </span>
                       </DialogTitle>
                    </div>
                    <div className="flex items-center gap-2">
                       <Button variant="outline" size="sm" className="gap-2 h-8">
                          <div className="w-0 h-0 border-t-[4px] border-t-transparent border-l-[6px] border-l-current border-b-[4px] border-b-transparent ml-0.5" /> Replay
                       </Button>
                       <DialogClose className="h-8 w-8 rounded-full hover:bg-muted flex items-center justify-center transition-colors">
                            <span className="sr-only">Close</span>
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="opacity-70"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
                       </DialogClose>
                    </div>
                 </div>

                 {/* Chart & Stats Section */}
                 <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Chart (2 cols) */}
                    <div className="lg:col-span-2 h-[300px] border rounded-lg p-4 bg-card/50 relative">
                       <ResponsiveContainer width="100%" height="100%">
                          <AreaChart data={selectedDayData.chartData}>
                             <defs>
                                <linearGradient id="colorPnl" x1="0" y1="0" x2="0" y2="1">
                                  <stop offset="5%" stopColor={selectedDayData.stats.totalPnL >= 0 ? "#10b981" : "#ef4444"} stopOpacity={0.3}/>
                                  <stop offset="95%" stopColor={selectedDayData.stats.totalPnL >= 0 ? "#10b981" : "#ef4444"} stopOpacity={0}/>
                                </linearGradient>
                             </defs>
                             <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--muted-foreground))" opacity={0.15} />
                             <XAxis dataKey="tradeAcc" hide />
                              <YAxis
                                orientation="left"
                                tickFormatter={(val) => `$${val}`}
                                stroke="#9ca3af"
                                tick={{ fill: '#9ca3af' }}
                                fontSize={11}
                                width={50}
                                tickLine={false}
                                axisLine={false}
                              />
                             <RechartsTooltip
                               contentStyle={{ backgroundColor: 'hsl(var(--popover))', borderColor: 'hsl(var(--border))' }}
                               formatter={(value: number) => [formatCurrency(value), "Net P&L"]}
                               labelFormatter={() => ""}
                             />
                             <Area
                               type="monotone"
                               dataKey="pnl"
                               stroke={selectedDayData.stats.totalPnL >= 0 ? "#10b981" : "#ef4444"}
                               strokeWidth={2}
                               fillOpacity={1}
                               fill="url(#colorPnl)"
                               activeDot={{ r: 4, strokeWidth: 0, fill: "white" }}
                             />
                          </AreaChart>
                       </ResponsiveContainer>
                    </div>

                    {/* Stats Grid (1 col) */}
                    <div className="lg:col-span-1 grid grid-cols-2 gap-4 auto-rows-min">
                        <div className="space-y-1">
                           <div className="text-xs text-muted-foreground">Total trades</div>
                           <div className="text-xl font-bold">{selectedDayData.stats.winners + selectedDayData.stats.losers}</div>
                        </div>
                        <div className="space-y-1">
                           <div className="text-xs text-muted-foreground">Winners</div>
                           <div className="text-xl font-bold">{selectedDayData.stats.winners}</div>
                        </div>
                        <div className="space-y-1">
                           <div className="text-xs text-muted-foreground">Winrate</div>
                           <div className="text-xl font-bold">{selectedDayData.stats.winRate.toFixed(0)}%</div>
                        </div>
                        <div className="space-y-1">
                           <div className="text-xs text-muted-foreground">Losers</div>
                           <div className="text-xl font-bold">{selectedDayData.stats.losers}</div>
                        </div>
                        <div className="space-y-1">
                           <div className="text-xs text-muted-foreground">Gross P&L</div>
                           <div className="text-xl font-bold">{formatCurrency(selectedDayData.stats.grossProfit - selectedDayData.stats.grossLoss)}</div>
                        </div>
                        <div className="space-y-1">
                           <div className="text-xs text-muted-foreground">Volume</div>
                           <div className="text-xl font-bold">{selectedDayData.stats.volume.toFixed(2)}</div>
                        </div>
                         <div className="space-y-1">
                           <div className="text-xs text-muted-foreground">Profit Factor</div>
                           <div className="text-xl font-bold">{selectedDayData.stats.profitFactor.toFixed(2)}</div>
                        </div>
                        <div className="space-y-1">
                           <div className="text-xs text-muted-foreground">Commissions</div>
                           <div className="text-xl font-bold">{formatCurrency(selectedDayData.stats.commissions)}</div>
                        </div>
                    </div>
                 </div>

                 {/* Trades Table */}
                 <div className="rounded-md border">
                    <Table>
                       <TableHeader>
                          <TableRow>
                             <TableHead>Open time</TableHead>
                             <TableHead>Close time</TableHead>
                             <TableHead>Ticker</TableHead>
                             <TableHead>Side</TableHead>
                             {/* <TableHead>Instrument</TableHead> */}
                             <TableHead className="text-right">Net P&L</TableHead>
                              <TableHead className="text-right">P&L Pips</TableHead>
                             {/* <TableHead className="text-right">Net ROI</TableHead> */}
                             {/* <TableHead className="text-right">Realized R-Multiple</TableHead> */}
                          </TableRow>
                       </TableHeader>
                       <TableBody>
                          {selectedDayData.trades.map((trade, idx) => (
                             <TableRow
                               key={idx}
                               className="cursor-pointer hover:bg-accent/50 transition-colors"
                               onClick={() => {
                                 if (trade.trade_id) {
                                   router.push(`/performance/trades-chart/${trade.trade_id}`)
                                   setIsDetailsOpen(false)
                                 }
                               }}
                             >
                                 <TableCell className="text-muted-foreground text-xs">
                                    {format(safeParseDate(trade.open_time || trade.time || trade.entry_time), "MM/dd/yyyy HH:mm:ss")}
                                 </TableCell>
                                 <TableCell className="text-muted-foreground text-xs">
                                    {format(safeParseDate(trade.close_time || trade.exit_time), "MM/dd/yyyy HH:mm:ss")}
                                 </TableCell>
                                <TableCell>
                                   <Badge variant="outline">{trade.symbol}</Badge>
                                </TableCell>
                                 <TableCell>
                                    <span className={cn("font-bold text-xs uppercase", (trade.type === 'buy' || trade.side === 1 || ['buy', 'long'].includes(String(trade.side).toLowerCase())) ? "text-emerald-400" : "text-red-400")}>
                                       {(trade.type === 'buy' || trade.side === 1 || ['buy', 'long'].includes(String(trade.side).toLowerCase())) ? "LONG" : "SHORT"}
                                    </span>
                                 </TableCell>
                                <TableCell className={cn("text-right font-medium", (Number(trade.pnl ?? trade.profit_loss ?? trade.profit ?? trade.net_profit ?? 0)) >= 0 ? "text-emerald-500" : "text-red-500")}>
                                   {formatCurrency(Number(trade.pnl ?? trade.profit_loss ?? trade.profit ?? trade.net_profit ?? 0))}
                                </TableCell>
                                 <TableCell className="text-right text-foreground">
                                    {trade.pnl_pips !== undefined ? trade.pnl_pips.toFixed(1) : (trade.pips !== undefined ? trade.pips.toFixed(1) : "-")}
                                 </TableCell>
                             </TableRow>
                          ))}
                       </TableBody>
                    </Table>
                 </div>

                 <div className="flex justify-end gap-2 pt-2 pb-2">
                    <Button variant="outline" onClick={() => setIsDetailsOpen(false)}>
                        Cancel
                    </Button>
                    <Button className="bg-indigo-600 hover:bg-indigo-700 text-white">
                        View Details
                    </Button>
                 </div>
              </div>
            )}
         </DialogContent>
      </Dialog>
    </div>
  )
}
