"use client"

import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { ChevronDown, Table, LineChart as LineChartIcon, Settings } from "lucide-react"
import type { LucideIcon } from "lucide-react"
import { cn } from "@/lib/utils"
import { useSelectedBacktest } from "@/contexts/selected-backtest-context"
import { strategyApi } from "@/lib/api/strategies"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Button } from "@/components/ui/button"

interface NavItem {
  label: string
  href: string
  icon?: LucideIcon
  isTradesChart?: boolean
  replay?: boolean
}

interface NavSection {
  label: string
  href: string
  items: NavItem[]
  icon?: LucideIcon
}

const performanceNavItems: NavSection[] = [
  {
    label: "Overview",
    href: "/performance/overview",
    items: [],
    icon: Table
  },
  {
    label: "Trades Calendar",
    href: "/performance/trades-calender",
    items: [
      { label: "Trades Calendar", href: "/performance/trades-calender", icon: LineChartIcon },
      { label: "Trades Chart", href: "/data", icon: LineChartIcon, isTradesChart: true },
      { label: "Trades Chart Replay", href: "/data", icon: LineChartIcon, isTradesChart: true, replay: true },
    ],
    icon: LineChartIcon
  },
  {
    label: "Strategy Analysis",
    href: "/performance/strategy-analysis",
    items: [
      { label: "Total Trade Analysis", href: "/performance/strategy-analysis/total-analysis", icon: Table },
      { label: "Returns", href: "/performance/strategy-analysis/returns", icon: Table },
      { label: "Performance Ratios", href: "/performance/strategy-analysis/performance-ratios", icon: Table },
      { label: "Risk", href: "/performance/strategy-analysis/risk", icon: Table },
      { label: "Drawdown", href: "/performance/strategy-analysis/drawdown", icon: Table },
      { label: "Efficiency Analysis", href: "/performance/strategy-analysis/efficiency", icon: Table },
      { label: "Distributions", href: "/performance/strategy-analysis/distributions", icon: Table },
      { label: "Benchmark Comparison", href: "/performance/strategy-analysis/benchmarks", icon: Table },
      { label: "Buy & Hold Return", href: "/performance/strategy-analysis/buy-hold-return", icon: LineChartIcon },
      { label: "Value Added Monthly Index", href: "/performance/strategy-analysis/vami", icon: LineChartIcon },
    ]
  },
  {
    label: "Trade Analysis",
    href: "/performance/trade-analysis",
    items: [
      { label: "List of Trades", href: "/performance/trade-analysis/list", icon: Table },
      { label: "Outliers", href: "/performance/trade-analysis/outliers", icon: Table },
      { label: "Run-up/Drawdown", href: "/performance/trade-analysis/runup-drawdown", icon: Table },
      { label: "Trade Series Analysis", href: "/performance/trade-analysis/series-analysis", icon: Table },
      { label: "Trade Series Statistics", href: "/performance/trade-analysis/series-stats", icon: Table },
      { label: "Total Trades", href: "/performance/trade-analysis/total-trades", icon: LineChartIcon },
      { label: "Winning Trades", href: "/performance/trade-analysis/winning-trades", icon: LineChartIcon },
      { label: "Losing Trades", href: "/performance/trade-analysis/losing-trades", icon: LineChartIcon },
      { label: "Maximum Adverse Excursion", href: "/performance/trade-analysis/mae", icon: LineChartIcon },
      { label: "Maximum Adverse Excursion (%)", href: "/performance/trade-analysis/mae-percent", icon: LineChartIcon },
      { label: "Run-up", href: "/performance/trade-analysis/runup", icon: LineChartIcon },
      { label: "Run-up P/L", href: "/performance/trade-analysis/runup-pl", icon: LineChartIcon },
      { label: "Maximum Favorable Excursion", href: "/performance/trade-analysis/mfe", icon: LineChartIcon },
      { label: "Maximum Favorable Excursion (%)", href: "/performance/trade-analysis/mfe-percent", icon: LineChartIcon },
    ]
  },
  {
    label: "Periodical Analysis",
    href: "/performance/periodical-analysis",
    items: [
      { label: "Hourly Period Analysis", href: "/performance/periodical-analysis/hourly", icon: Table },
      { label: "Hourly Rolling Period Analysis", href: "/performance/periodical-analysis/hourly-rolling", icon: Table },
      { label: "Daily Period Analysis", href: "/performance/periodical-analysis/daily", icon: Table },
      { label: "Daily Rolling Period Analysis", href: "/performance/periodical-analysis/daily-rolling", icon: Table },
      { label: "Weekly Period Analysis", href: "/performance/periodical-analysis/weekly", icon: Table },
      { label: "Weekly Rolling Period Analysis", href: "/performance/periodical-analysis/weekly-rolling", icon: Table },
      { label: "Monthly Analysis", href: "/performance/periodical-analysis/monthly", icon: Table },
      { label: "Monthly Period Analysis", href: "/performance/periodical-analysis/monthly-period", icon: Table },
      { label: "Monthly Rolling Period Analysis", href: "/performance/periodical-analysis/monthly-rolling", icon: Table },
      { label: "Annual Period Analysis", href: "/performance/periodical-analysis/annual", icon: Table },
      { label: "Annual Rolling Period Analysis", href: "/performance/periodical-analysis/annual-rolling", icon: Table },
      { label: "Hourly Returns & Drawdowns", href: "/performance/periodical-analysis/hourly-returns", icon: LineChartIcon },
      { label: "Hourly Returns & Drawdowns (%)", href: "/performance/periodical-analysis/hourly-returns-percent", icon: LineChartIcon },
      { label: "Hourly Accumulative Net Profit", href: "/performance/periodical-analysis/hourly-accumulative", icon: LineChartIcon },
      { label: "Daily Returns & Drawdowns", href: "/performance/periodical-analysis/daily-returns", icon: LineChartIcon },
      { label: "Daily Returns & Drawdowns (%)", href: "/performance/periodical-analysis/daily-returns-percent", icon: LineChartIcon },
      { label: "Daily Accumulative Net Profit", href: "/performance/periodical-analysis/daily-accumulative", icon: LineChartIcon },
      { label: "Weekly Returns & Drawdowns", href: "/performance/periodical-analysis/weekly-returns", icon: LineChartIcon },
      { label: "Weekly Returns & Drawdowns (%)", href: "/performance/periodical-analysis/weekly-returns-percent", icon: LineChartIcon },
      { label: "Weekly Accumulative Net Profit", href: "/performance/periodical-analysis/weekly-accumulative", icon: LineChartIcon },
      { label: "Monthly Returns & Drawdowns", href: "/performance/periodical-analysis/monthly-returns", icon: LineChartIcon },
      { label: "Monthly Returns & Drawdowns (%)", href: "/performance/periodical-analysis/monthly-returns-percent", icon: LineChartIcon },
      { label: "Monthly Accumulative Net Profit", href: "/performance/periodical-analysis/monthly-accumulative", icon: LineChartIcon },
      { label: "Average Profit By Month", href: "/performance/periodical-analysis/monthly-avg-profit", icon: LineChartIcon },
      { label: "Annual Returns & Drawdowns", href: "/performance/periodical-analysis/annual-returns", icon: LineChartIcon },
      { label: "Annual Returns & Drawdowns (%)", href: "/performance/periodical-analysis/annual-returns-percent", icon: LineChartIcon },
      { label: "Annual Accumulative Net Profit", href: "/performance/periodical-analysis/annual-accumulative", icon: LineChartIcon },
    ]
  },
  {
    label: "Chart Analysis",
    href: "/performance/chart-analysis",
    items: [
      { label: "Equity Performance", href: "/performance/chart-analysis/equity-performance", icon: LineChartIcon },
      { label: "Consecutive Winners/Losers", href: "/performance/chart-analysis/consecutive-winners-losers", icon: LineChartIcon },

      { label: "Drawdown", href: "/performance/chart-analysis/drawdown", icon: LineChartIcon },
      { label: "Efficiency", href: "/performance/chart-analysis/efficiency", icon: LineChartIcon },
      { label: "Exit Analysis", href: "/performance/chart-analysis/exit-analysis", icon: LineChartIcon },
      { label: "Holding Time", href: "/performance/chart-analysis/holding-time", icon: LineChartIcon },
      { label: "Performance by Instrument", href: "/performance/chart-analysis/performance-by-instrument", icon: LineChartIcon },
      { label: "Performance by Setup", href: "/performance/chart-analysis/performance-by-setup", icon: LineChartIcon },
      { label: "Performance by Time", href: "/performance/chart-analysis/performance-by-time", icon: LineChartIcon },
      { label: "Performance by Day", href: "/performance/chart-analysis/performance-by-day", icon: LineChartIcon },
      { label: "Performance Ratio", href: "/performance/chart-analysis/performance-ratio", icon: LineChartIcon },
      { label: "Risk Distribution", href: "/performance/chart-analysis/risk-distribution", icon: LineChartIcon },
      { label: "Trades Calendar", href: "/performance/chart-analysis/trades-calendar", icon: LineChartIcon },
      { label: "Simulator", href: "/performance/chart-analysis/simulator", icon: LineChartIcon },
    ]
  },
  {
    label: "MetaParams",
    href: "/performance/metaparams",
    items: [],
    icon: Settings
  }
]

export function PerformanceNav() {
  const pathname = usePathname()
  const router = useRouter()
  const { selectedBacktest } = useSelectedBacktest()

  const formatDateSegment = (value?: string | null) => {
    if (!value) return "null"
    const parsed = new Date(value)
    if (Number.isNaN(parsed.getTime())) return value.slice(0, 10)
    return parsed.toISOString().slice(0, 10)
  }

  const buildTradesChartHref = (replay = false) => {
    if (!selectedBacktest?.symbol) return "/data"
    const timeframe = selectedBacktest.timeframe || selectedBacktest.data_resolution || "H1"
    const start = formatDateSegment(selectedBacktest.start_date)
    const end = formatDateSegment(selectedBacktest.end_date)
    return `/data/${selectedBacktest.symbol}/${timeframe}/dates/${start}/${end}/trades-charts${replay ? "/replay" : ""}`
  }

  const openTradesChart = async (event: React.MouseEvent<HTMLAnchorElement>, href: string) => {
    if (!selectedBacktest) return
    event.preventDefault()

    let backtest = selectedBacktest
    if (!backtest.trades?.length) {
      backtest = await strategyApi.getBacktestById(backtest.backtest_id)
    }

    if (typeof window === "undefined") return
    window.sessionStorage.setItem(
      "haruquant:trades-chart-overlay",
      JSON.stringify({
        backtest_id: backtest.backtest_id,
        symbol: backtest.symbol,
        timeframe: backtest.timeframe || backtest.data_resolution || "H1",
        start_date: backtest.start_date,
        end_date: backtest.end_date,
        trades: backtest.trades || [],
      })
    )
    router.push(href)
  }

  return (
    <nav className="flex items-center gap-1 px-6 pb-4 overflow-x-auto">
      {performanceNavItems.map((section) => {
        const isActive = pathname.startsWith(section.href)
        const hasItems = section.items.length > 0

        if (!hasItems) {
          // Simple link without dropdown (MetaParams, Trades Chart)
          const Icon = section.icon || Settings
          return (
            <Link key={section.href} href={section.href}>
              <Button
                variant={isActive ? "secondary" : "ghost"}
                size="sm"
                className={cn(
                  "h-9 px-4 font-medium",
                  isActive && "bg-primary/10 text-primary"
                )}
              >
                <Icon className="h-4 w-4 mr-2" />
                {section.label}
              </Button>
            </Link>
          )
        }

        return (
          <DropdownMenu key={section.href}>
            <DropdownMenuTrigger asChild>
              <Button
                variant={isActive ? "secondary" : "ghost"}
                size="sm"
                className={cn(
                  "h-9 px-4 font-medium",
                  isActive && "bg-primary/10 text-primary"
                )}
              >
                {section.label}
                <ChevronDown className="ml-2 h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              align="start"
              className="w-72 max-h-[70vh] overflow-y-auto"
            >
              {section.items.map((item) => {
                const ItemIcon = item.icon
                const href = item.isTradesChart ? buildTradesChartHref(item.replay) : item.href
                const isItemActive = item.isTradesChart
                  ? pathname.startsWith("/data") && href.includes("/trades-charts")
                  : pathname === item.href
                const isDisabled = item.isTradesChart && !selectedBacktest?.symbol

                return (
                  <DropdownMenuItem key={`${section.href}:${item.label}`} asChild disabled={isDisabled}>
                    <Link
                      href={href}
                      onClick={item.isTradesChart ? (event) => void openTradesChart(event, href) : undefined}
                      className={cn(
                        "flex items-center gap-2 cursor-pointer",
                        isDisabled && "pointer-events-none opacity-50",
                        isItemActive && "bg-accent"
                      )}
                    >
                      {ItemIcon && <ItemIcon className="h-4 w-4 text-muted-foreground" />}
                      <span className="truncate">{item.label}</span>
                    </Link>
                  </DropdownMenuItem>
                )
              })}
            </DropdownMenuContent>
          </DropdownMenu>
        )
      })}
    </nav>
  )
}
