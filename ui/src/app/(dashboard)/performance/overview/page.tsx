"use client"

import React from "react"
import { format } from "date-fns"
import { usePerformanceData } from "@/components/performance/use-performance-data"
import { PerformancePageLayout, PageConfig } from "@/components/performance/shared/performance-page-layout"
import { Loader2, CheckCircle2, AlertTriangle, ShieldCheck, TrendingUp, Activity, BarChart3 } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { MetricGrid3Way, MetricConfig } from "@/components/performance/shared/metric-grid-3way"
import { PerformanceActions } from "@/components/performance/shared/performance-actions"
import { SeriesChart3Way } from "@/components/performance/shared/series-chart-3way"

const formatDateTime = (value: string | null | undefined) => {
  if (!value) return "-"
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return String(value)
  return format(parsed, "yyyy-MM-dd HH:mm:ss")
}

const dashboardConfig: Record<string, MetricConfig[]> = {
  profitability: [
    { label: "Net Profit", accessor: "net_profit", format: (v: any) => v != null ? `$${v.toFixed(2)}` : "-", unit: "USD", description: "Total monetary gain or loss after all trades and costs." },
    { label: "Total Return", accessor: "total_return", format: (v: any) => v != null ? `${v.toFixed(2)}%` : "-", unit: "%", description: "Percentage change in account balance relative to initial capital." },
    { label: "CAGR", accessor: "cagr", format: (v: any) => v != null ? `${v.toFixed(2)}%` : "-", unit: "%", description: "Compound Annual Growth Rate – the geometric mean return per year." },
    { label: "Profit Factor", accessor: "profit_factor", format: (v: any) => v != null ? v.toFixed(2) : "-", description: "Ratio of gross profit to gross loss. A value > 1.0 indicates profitability." },
    { label: "Expectancy (R)", accessor: "expectancy_r", format: (v: any) => v != null ? `${v.toFixed(2)}R` : "-", description: "The average amount you expect to win or lose per trade, measured in units of risk (R)." },
  ],
  risk: [
    { label: "Max Drawdown", accessor: "max_drawdown_pct", format: (v: any) => v != null ? `${v.toFixed(2)}%` : "-", unit: "%", description: "The largest peak-to-trough decline in account equity, expressed as a percentage." },
    { label: "MDD Duration", accessor: "max_drawdown_duration", description: "The maximum time spent recovering from a drawdown (peak to new peak)." },
    { label: "VaR (95%)", accessor: "value_at_risk_95", format: (v: any) => v != null ? `${v.toFixed(2)}%` : "-", unit: "%", description: "Value at Risk – the maximum expected loss with 95% confidence over a given period." },
    { label: "Exp. Shortfall", accessor: "expected_shortfall_95", format: (v: any) => v != null ? `${v.toFixed(2)}%` : "-", unit: "%", description: "Expected Shortfall (Conditional VaR) – the average loss in the worst 5% of cases." },
    { label: "Ulcer Index", accessor: "ulcer_index", format: (v: any) => v != null ? v.toFixed(2) : "-", description: "A measure of downside risk that penalizes both the depth and duration of drawdowns." },
    { label: "Risk of Ruin", accessor: "risk_of_ruin", format: (v: any) => v != null ? `${(v * 100).toFixed(2)}%` : "-", unit: "%", description: "The statistical probability that the account will hit a 50% loss threshold (ruin), based on a 1% risk-per-trade simulation." },
  ],
  quality: [
    { label: "Sharpe Ratio", accessor: "sharpe_ratio", format: (v: any) => v != null ? v.toFixed(2) : "-", description: "Risk-adjusted return, calculated as excess return over volatility. Higher is better." },
    { label: "Sortino Ratio", accessor: "sortino_ratio", format: (v: any) => v != null ? v.toFixed(2) : "-", description: "Similar to Sharpe, but only considers downside volatility (harmful risk)." },
    { label: "Calmar Ratio", accessor: "calmar_ratio", format: (v: any) => v != null ? v.toFixed(2) : "-", description: "Ratio of annualized return to maximum drawdown. Measures return relative to tail risk." },
    { label: "SQN", accessor: "sqn", format: (v: any) => v != null ? v.toFixed(2) : "-", description: "System Quality Number – a Van Tharp metric scoring the system's ability to achieve its objectives." },
    { label: "Win Rate", accessor: "win_rate", format: (v: any) => v != null ? `${v.toFixed(2)}%` : "-", unit: "%", description: "The percentage of trades that resulted in a profit." },
  ],
  robustness: [
    { label: "Deflated Sharpe", accessor: "deflated_sharpe_ratio", format: (v: any) => v != null ? v.toFixed(2) : "-", description: "A Sharpe ratio adjusted for selection bias and the number of strategies tested." },
    { label: "DSR P-Value", accessor: "dsr_p_value", format: (v: any) => v != null ? v.toFixed(4) : "-", description: "The probability that the strategy's performance is due to luck. Lower is better (< 0.05)." },
    { label: "Prob. Sharpe > 0", accessor: "prob_sharpe_gt_0", format: (v: any) => v != null ? `${(v * 100).toFixed(1)}%` : "-", unit: "%", description: "The estimated probability that the strategy has a positive edge (Sharpe > 0)." },
  ]
}

function StrategyScorecard({ scorecard }: { scorecard: any }) {
  if (!scorecard?.all) return null
  const data = scorecard.all

  const decisionColors: Record<string, string> = {
    PASS: "bg-green-500/10 text-green-500 border-green-500/20",
    WATCHLIST: "bg-yellow-500/10 text-yellow-500 border-yellow-500/20",
    REJECT: "bg-red-500/10 text-red-500 border-red-500/20",
  }

  const scoreColor = data.score >= 75 ? "text-green-500" : data.score >= 50 ? "text-yellow-500" : "text-red-500"

  return (
    <Card className="overflow-hidden border-2 shadow-md">
      <div className={`h-2 ${data.decision === 'PASS' ? 'bg-green-500' : data.decision === 'WATCHLIST' ? 'bg-yellow-500' : 'bg-red-500'}`} />
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
        <div className="space-y-1">
          <CardTitle className="text-2xl font-bold flex items-center gap-2">
            <ShieldCheck className="h-6 w-6 text-primary" />
            Strategy Decision Scorecard
          </CardTitle>
          <CardDescription>Institutional-grade evaluation based on risk, return, and robustness</CardDescription>
        </div>
        <div className="flex flex-col items-end gap-2">
           <Badge variant="outline" className={`text-xl px-6 py-1.5 font-black tracking-widest ${decisionColors[data.decision]}`}>
             {data.decision}
           </Badge>
           <div className="text-sm font-semibold text-muted-foreground uppercase tracking-tighter">
             Quality Score: <span className={scoreColor}>{data.score}</span> / 100
           </div>
        </div>
      </CardHeader>
      <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-8 pt-2">
        <div className="space-y-4">
            <div className="rounded-lg bg-green-50/50 dark:bg-green-900/10 p-4 border border-green-100 dark:border-green-900/20">
               <h4 className="text-sm font-bold mb-3 flex items-center gap-2 text-green-700 dark:text-green-400">
                 <CheckCircle2 className="h-4 w-4" />
                 STRENGTHS
               </h4>
               <ul className="text-sm space-y-2">
                 {data.strengths.map((s: string, i: number) => (
                   <li key={i} className="flex items-start gap-2 text-muted-foreground">
                     <span className="text-green-500 mt-1">•</span>
                     <span>{s}</span>
                   </li>
                 ))}
                 {data.strengths.length === 0 && <li className="text-muted-foreground italic">No major strengths identified.</li>}
               </ul>
            </div>
        </div>
        <div className="space-y-4">
            <div className="rounded-lg bg-orange-50/50 dark:bg-orange-900/10 p-4 border border-orange-100 dark:border-orange-900/20">
               <h4 className="text-sm font-bold mb-3 flex items-center gap-2 text-orange-700 dark:text-orange-400">
                 <AlertTriangle className="h-4 w-4" />
                 WARNINGS & FAILURES
               </h4>
               <ul className="text-sm space-y-2">
                 {data.fail_reasons.map((f: string, i: number) => (
                   <li key={`f-${i}`} className="flex items-start gap-2 text-red-600 dark:text-red-400 font-semibold">
                     <span className="mt-1">⚠</span>
                     <span>{f}</span>
                   </li>
                 ))}
                 {data.warnings.map((w: string, i: number) => (
                   <li key={`w-${i}`} className="flex items-start gap-2 text-muted-foreground">
                     <span className="text-orange-500 mt-1">•</span>
                     <span>{w}</span>
                   </li>
                 ))}
                 {data.fail_reasons.length === 0 && data.warnings.length === 0 && <li className="text-muted-foreground italic">No risk warnings found.</li>}
               </ul>
            </div>
        </div>
      </CardContent>
    </Card>
  )
}

function DashboardGrid({ title, icon: Icon, metrics, data }: { title: string, icon: any, metrics: MetricConfig[], data: any }) {
  if (!data) return null;
  
  // Support both new 3-way backend structure and legacy flat structure
  const transformedData = (data.all && data.long && data.short) ? data : {
    all: data,
    long: {},
    short: {}
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 px-1">
        <Icon className="h-5 w-5 text-primary" />
        <h3 className="text-lg font-bold tracking-tight uppercase text-muted-foreground/80">{title}</h3>
      </div>
      <MetricGrid3Way 
        metrics={metrics} 
        data={transformedData} 
        className="border shadow-sm bg-card/50" 
      />
    </div>
  )
}

export default function OverviewPage() {
  const {
    analytics,
    charts,
    quickLoading,
    detailedLoading,
    error,
    selectedBacktest,
    hasQuickData,
  } = usePerformanceData()

  if (!selectedBacktest) {
    return <div className="p-12 text-center text-muted-foreground">Select a backtest to view performance summary.</div>
  }

  if (quickLoading && !hasQuickData) {
    return (
      <div className="flex h-[600px] flex-col items-center justify-center gap-4">
        <Loader2 className="h-10 w-10 animate-spin text-primary/60" />
        <span className="text-lg font-medium text-muted-foreground animate-pulse">Orchestrating performance analytics...</span>
      </div>
    )
  }

  if (error && !analytics) {
    return <div className="p-12 text-center text-red-500 bg-red-50 dark:bg-red-950/20 rounded-xl border border-red-200 dark:border-red-900">
      <AlertTriangle className="h-12 w-12 mx-auto mb-4 opacity-50" />
      <h3 className="text-xl font-bold mb-2">Analysis Failed</h3>
      <p>{error}</p>
    </div>
  }

  if (!analytics) return null;

  return (
    <div className="container mx-auto p-6 max-w-[1600px] pb-20">
      <div id="performance-overview-report" className="space-y-10">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div>
            <h1 className="text-4xl font-black tracking-tighter uppercase">Performance Overview</h1>
            <p className="text-muted-foreground mt-2 text-lg">Executive summary for <span className="font-mono text-primary">{selectedBacktest.strategy_name}</span></p>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-4 text-sm font-medium border rounded-full px-4 py-1.5 bg-muted/30">
               <div className="flex items-center gap-2">
                 <span className="text-muted-foreground">START:</span>
                 <span className="font-mono">{formatDateTime(analytics.summary.all.start).split(' ')[0]}</span>
               </div>
               <Separator orientation="vertical" className="h-4" />
               <div className="flex items-center gap-2">
                 <span className="text-muted-foreground">END:</span>
                 <span className="font-mono">{formatDateTime(analytics.summary.all.end).split(' ')[0]}</span>
               </div>
            </div>
            
            <PerformanceActions 
              data={analytics} 
              filename={`overview-${selectedBacktest.strategy_name}`}
              containerId="performance-overview-report"
            />
          </div>
        </div>

        <Separator />

        {/* Background loading indicator */}
        {detailedLoading && (
          <div className="fixed top-4 right-4 z-50 flex items-center gap-2 bg-background/80 backdrop-blur border px-3 py-1.5 rounded-full shadow-lg text-xs font-medium">
            <Loader2 className="h-3 w-3 animate-spin text-primary" />
            Refining metrics...
          </div>
        )}

        {/* 1. Scorecard */}
        {analytics.scorecard && (
          <section>
            <StrategyScorecard scorecard={analytics.scorecard} />
          </section>
        )}

        {/* 2. Dashboard KPIs */}
        {analytics.dashboard && (
          <div className="grid grid-cols-1 gap-12">
             <DashboardGrid 
               title="Profitability & Growth" 
               icon={TrendingUp} 
               metrics={dashboardConfig.profitability as any} 
               data={analytics.dashboard.profitability as any} 
             />
             
             <DashboardGrid 
               title="Risk & Preservation" 
               icon={ShieldCheck} 
               metrics={dashboardConfig.risk as any} 
               data={analytics.dashboard.risk as any} 
             />

             <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
               <DashboardGrid 
                 title="Strategy Quality" 
                 icon={Activity} 
                 metrics={dashboardConfig.quality as any} 
                 data={analytics.dashboard.quality as any} 
               />
               <DashboardGrid 
                 title="Statistical Robustness" 
                 icon={BarChart3} 
                 metrics={dashboardConfig.robustness as any} 
                 data={analytics.dashboard.robustness as any} 
               />
             </div>
          </div>
        )}

        {/* 3. Primary Charts */}
        {charts && (
          <div className="grid grid-cols-1 gap-10">
            {charts.equity_curve && (
              <SeriesChart3Way 
                title="Cumulative Equity" 
                data={charts.equity_curve as any} 
                valueFormatter={(v) => `$${v.toLocaleString()}`}
              />
            )}
            {charts.drawdown_curve && (
              <SeriesChart3Way 
                title="Strategy Drawdown" 
                data={charts.drawdown_curve as any} 
                valueFormatter={(v) => `${v.toFixed(2)}%`}
              />
            )}
          </div>
        )}

        {/* Metadata / Details */}
        <div className="flex justify-between items-center text-[10px] text-muted-foreground/50 pt-8 border-t">
           <div>SIMULATION ID: {selectedBacktest.backtest_id}</div>
           <div className="flex gap-4">
             <div>DURATION: {analytics.summary.all.duration_days?.toFixed(1)} DAYS</div>
             <div>TICKS: {analytics.summary.all.processed_ticks?.toLocaleString()}</div>
           </div>
        </div>
      </div>
    </div>
  )
}
