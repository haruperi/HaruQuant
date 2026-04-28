"use client"

import React from "react"
import { usePerformanceData } from "@/components/performance/use-performance-data"
import { PerformancePageLayout, PageConfig } from "@/components/performance/shared/performance-page-layout"
import { Loader2, Download } from "lucide-react"
import { Button } from "@/components/ui/button"

const formatFriendlyDuration = (value: number | null | undefined, unit: 'seconds' | 'hours' | 'days' = 'seconds') => {
  if (value == null || isNaN(value)) return "-"
  
  let totalSeconds = value
  if (unit === 'hours') totalSeconds = value * 3600
  if (unit === 'days') totalSeconds = value * 86400
  
  const days = Math.floor(totalSeconds / 86400)
  const remainingSeconds = totalSeconds % 86400
  const hours = parseFloat((remainingSeconds / 3600).toFixed(1))
  
  if (days > 0) {
    if (hours > 0) return `${days} day${days > 1 ? 's' : ''} and ${hours}h`
    return `${days} day${days > 1 ? 's' : ''}`
  }
  return `${hours}h`
}

const totalAnalysisConfig: PageConfig = {
  title: "Total Trade Analysis",
  description: "Comprehensive breakdown of trade statistics, win/loss ratios, sequences, and system quality.",
  metrics: [
    // --- Core Trade Counts & Costs ---
    { label: "Core Trade Counts & Costs", accessor: "", type: "group" as const },
    { label: "Total Trades", accessor: "total_trades", description: "Total number of trades." },
    { label: "Open Trades", accessor: "open_trades", description: "Number of trades still open." },
    { label: "Long Trades", accessor: "long_trades", description: "Count of buy trades." },
    { label: "Short Trades", accessor: "short_trades", description: "Count of sell trades." },
    { label: "Winning Trades", accessor: "winning_trades", description: "Count of trades with profit > 1." },
    { label: "Losing Trades", accessor: "losing_trades", description: "Count of trades with loss < -1." },
    { label: "Breakeven Trades", accessor: "breakeven_trades", description: "Count of trades between -1 and 1." },
    { label: "Slippage Paid", accessor: "slippage_paid", format: (v: any) => (v != null) ? `$${v.toFixed(2)}` : "-", unit: "USD", description: "Total slippage costs paid." },
    { label: "Commission Paid", accessor: "commission_paid", format: (v: any) => (v != null) ? `$${v.toFixed(2)}` : "-", unit: "USD", description: "Total commissions paid." },
    { label: "Swap Paid", accessor: "swap_paid", format: (v: any) => (v != null) ? `$${v.toFixed(2)}` : "-", unit: "USD", description: "Total swap/rollover costs paid." },
    { label: "Max Size Held", accessor: "max_size_held", description: "Maximum contracts/units held at any one time." },
    { label: "Max Net Size", accessor: "max_net_size_held", description: "Maximum absolute net directional size held." },
    { label: "Max Long Size", accessor: "max_long_size_held", description: "Maximum long contracts held at once." },
    { label: "Max Short Size", accessor: "max_short_size_held", description: "Maximum short contracts held at once." },
    { label: "Open PnL", accessor: "open_pnl", format: (v: any) => (v != null) ? `$${v.toFixed(2)}` : "-", unit: "USD", description: "Unrealized profit/loss of open trades." },

    // --- Trade P&L Statistics ---
    { label: "Trade P&L Statistics", accessor: "", type: "group" as const },
    { label: "Win Rate", accessor: "win_rate", format: (v: any) => (v != null) ? `${v.toFixed(2)}%` : "-", unit: "%", description: "Percentage of winning trades." },
    { label: "Loss Rate", accessor: "loss_rate", format: (v: any) => (v != null) ? `${v.toFixed(2)}%` : "-", unit: "%", description: "Percentage of losing trades." },
    { label: "Avg Win", accessor: "avg_win", format: (v: any) => (v != null) ? `$${v.toFixed(2)}` : "-", unit: "USD", description: "Average P&L of winning trades." },
    { label: "Avg Loss", accessor: "avg_loss", format: (v: any) => (v != null) ? `$${v.toFixed(2)}` : "-", unit: "USD", description: "Average P&L of losing trades." },
    { label: "Largest Win", accessor: "largest_win", format: (v: any) => (v != null) ? `$${v.toFixed(2)}` : "-", unit: "USD", description: "Maximum P&L of a single winning trade." },
    { label: "Largest Loss", accessor: "largest_loss", format: (v: any) => (v != null) ? `$${v.toFixed(2)}` : "-", unit: "USD", description: "Maximum P&L of a single losing trade." },
    { label: "Median Win", accessor: "median_win", format: (v: any) => (v != null) ? `$${v.toFixed(2)}` : "-", unit: "USD", description: "Median P&L of winning trades." },
    { label: "Median Loss", accessor: "median_loss", format: (v: any) => (v != null) ? `$${v.toFixed(2)}` : "-", unit: "USD", description: "Median P&L of losing trades." },

    // --- R-Multiple Analytics ---
    { label: "R-Multiple Analytics", accessor: "", type: "group" as const },
    { label: "Avg R-Multiple", accessor: "avg_r_multiple", format: (v: any) => (v != null) ? v.toFixed(2) : "-", description: "Average R-multiple across all trades." },
    { label: "Median R-Multiple", accessor: "median_r_multiple", format: (v: any) => (v != null) ? v.toFixed(2) : "-", description: "Median R-multiple." },
    { label: "Max R-Multiple", accessor: "max_r_multiple", format: (v: any) => (v != null) ? v.toFixed(2) : "-", description: "Maximum R-multiple achieved." },
    { label: "Min R-Multiple", accessor: "min_r_multiple", format: (v: any) => (v != null) ? v.toFixed(2) : "-", description: "Minimum R-multiple achieved." },
    { label: "Expectancy ($)", accessor: "expectancy", format: (v: any) => (v != null) ? `$${v.toFixed(2)}` : "-", description: "Expected value per trade in USD terms." },
    { label: "R-Expectancy", accessor: "expectancy_r", format: (v: any) => (v != null) ? v.toFixed(2) : "-", description: "Expected value per trade in R-terms." },

    // --- Trade Sequence Quality ---
    { label: "Trade Sequence Quality", accessor: "", type: "group" as const },
    { label: "Max Consecutive Wins", accessor: "max_consecutive_wins", description: "Longest winning streak." },
    { label: "Max Consecutive Losses", accessor: "max_consecutive_losses", description: "Longest losing streak." },
    { label: "Avg Consecutive Wins", accessor: "avg_consecutive_wins", format: (v: any) => (v != null) ? v.toFixed(2) : "-", description: "Average length of winning streaks." },
    { label: "Avg Consecutive Losses", accessor: "avg_consecutive_losses", format: (v: any) => (v != null) ? v.toFixed(2) : "-", description: "Average length of losing streaks." },
    { label: "Runs Test Z-Score", accessor: "runs_test_zscore", format: (v: any) => (v != null) ? v.toFixed(2) : "-", description: "Wald-Wolfowitz Runs Test for randomness (Positive: Clustering, Negative: Mean Reversion)." },
    { label: "Win Follow-on Prob.", accessor: "win_after_win_probability", format: (v: any) => (v != null) ? `${(v * 100).toFixed(2)}%` : "-", description: "Probability that a win is followed by another win." },
    { label: "Max Cons. DD Trades", accessor: "max_consecutive_drawdown_trades", description: "Worst sequence of losing trades." },

    // --- Time-in-Trade ---
    { label: "Time-in-Trade", accessor: "", type: "group" as const },
    { label: "Avg Time in Trade", accessor: "avg_time_in_trade", format: (v: any) => formatFriendlyDuration(v as number, 'seconds'), description: "Average time in trade." },
    { label: "Median Time in Trade", accessor: "median_time_in_trade", format: (v: any) => formatFriendlyDuration(v as number, 'seconds'), description: "Median time in trade." },
    { label: "Max Time in Trade", accessor: "max_time_in_trade", format: (v: any) => formatFriendlyDuration(v as number, 'seconds'), description: "Maximum time in trade." },
    { label: "Min Time in Trade", accessor: "min_time_in_trade", format: (v: any) => formatFriendlyDuration(v as number, 'seconds'), description: "Minimum time in trade." },

    // --- System Quality Metrics ---
    { label: "System Quality Metrics", accessor: "", type: "group" as const },
    { label: "System Quality Number (SQN)", accessor: "sqn", format: (v: any) => (v != null) ? v.toFixed(2) : "-", description: "Van Tharp's SQN score." },
    { label: "Kelly Criterion", accessor: "kelly_criterion", format: (v: any) => (v != null) ? v.toFixed(4) : "-", description: "Optimal fraction of capital to risk." },

    // --- Advanced Performance & Information ---
    { label: "Advanced Performance & Information", accessor: "", type: "group" as const },
    { label: "Trade Efficiency", accessor: "trade_efficiency", format: (v: any) => (v != null) ? v.toFixed(3) : "-", description: "Realized R captured relative to available MFE." },
    { label: "Trade SNR", accessor: "r_signal_to_noise", format: (v: any) => (v != null) ? v.toFixed(2) : "-", description: "Signal-to-Noise Ratio (Mean R / Std R). Also known as unannualized Trade Sharpe." },
    { label: "Rolling Expectancy Stability", accessor: "rolling_expectancy_stability", format: (v: any) => (v != null) ? v.toFixed(2) : "-", description: "Consistency of expectancy over time (Mean of rolling mean R / Std of rolling mean R)." },
    { label: "Outcome Entropy", accessor: "trade_outcome_entropy", format: (v: any) => (v != null) ? v.toFixed(3) : "-", description: "Shannon entropy of trade outcomes (predictability)." },
    { label: "T-Statistic", accessor: "t_statistic", format: (v: any) => (v != null) ? v.toFixed(2) : "-", description: "T-statistic for mean outcome." },
    { label: "Median MAE (R)", accessor: "median_mae", format: (v: any) => (v != null) ? v.toFixed(3) : "-", description: "Median Maximum Adverse Excursion in R-terms." },
    { label: "Median MFE (R)", accessor: "median_mfe", format: (v: any) => (v != null) ? v.toFixed(3) : "-", description: "Median Maximum Favorable Excursion in R-terms." },

    // --- Statistical Validation ---
    { label: "Statistical Validation", accessor: "", type: "group" as const },
    { label: "Deflated Sharpe Ratio (DSR)", accessor: "deflated_sharpe_ratio", format: (v: any) => (v != null) ? v.toFixed(2) : "-", description: "Adjusted Sharpe ratio accounting for selection bias and non-normality." },
    { label: "DSR p-value", accessor: "dsr_p_value", format: (v: any) => (v != null) ? v.toFixed(4) : "-", description: "Probability that the observed performance is due to luck. < 0.05 is significant." },
    { label: "Permutation p-value", accessor: "permutation_p_value", format: (v: any) => (v != null) ? v.toFixed(4) : "-", description: "p-value from sign-flip permutation testing." },
    { label: "Is Robust?", accessor: "is_significant", format: (v: any) => (v === true) ? "Yes" : "No", description: "Whether the strategy passes significance tests." },
    { label: "P(Sharpe > 0)", accessor: "prob_sharpe_gt_0", format: (v: any) => (v != null) ? `${(v * 100).toFixed(2)}%` : "-", description: "Bootstrap probability that the true Sharpe ratio is positive." },

    // --- Time-Based Period Metrics ---
    { label: "Time-Based Period Metrics", accessor: "", type: "group" as const },
    { label: "Trading Period Duration", accessor: "trading_period_duration_days", format: (v: any) => formatFriendlyDuration(v as number, 'days'), description: "Total duration of the test period." },
    { label: "Time in Market", accessor: "time_in_market_hours", format: (v: any) => formatFriendlyDuration(v as number, 'hours'), description: "Total duration with at least one open position." },
    { label: "Percent Time in Market", accessor: "percent_time_in_market", format: (v: any) => (v != null) ? `${v.toFixed(2)}%` : "-", unit: "%", description: "Percentage of time spent in the market." },
    { label: "Longest Flat Period", accessor: "longest_flat_period_hours", format: (v: any) => formatFriendlyDuration(v as number, 'hours'), description: "Maximum time between trades." },

    // --- Equity Curve Metrics ---
    { label: "Equity Curve Metrics", accessor: "", type: "group" as const },
    { label: "Max Run-up", accessor: "max_runup", format: (v: any) => (v != null) ? `$${v.toFixed(2)}` : "-", unit: "USD", description: "Maximum peak-to-valley gain." },
  ],
  charts: []
}

export default function TotalAnalysisPage() {
  const { analytics, loading, error, selectedBacktest } = usePerformanceData()

  if (!selectedBacktest) {
    return <div className="p-8 text-center text-muted-foreground">Select a backtest to view trade analysis.</div>
  }

  if (loading) {
    return (
      <div className="flex h-[400px] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (error) {
    return <div className="p-8 text-red-500">Error: {error}</div>
  }

  // Merge ALL analytics categories for comprehensive availability in the total analysis page
  const metricsData = {
    all: { 
      ...(analytics?.metrics?.all || {}), 
      ...(analytics?.returns?.all || {}),
      ...(analytics?.ratios?.all || {}),
      ...(analytics?.risks?.all || {}),
      ...(analytics?.drawdowns?.all || {}),
      ...(analytics?.efficiency?.all || {}),
      ...(analytics?.validation?.all || {}) 
    },
    long: { 
      ...(analytics?.metrics?.long || {}), 
      ...(analytics?.returns?.long || {}),
      ...(analytics?.ratios?.long || {}),
      ...(analytics?.risks?.long || {}),
      ...(analytics?.drawdowns?.long || {}),
      ...(analytics?.efficiency?.long || {}),
      ...(analytics?.validation?.long || {}) 
    },
    short: { 
      ...(analytics?.metrics?.short || {}), 
      ...(analytics?.returns?.short || {}),
      ...(analytics?.ratios?.short || {}),
      ...(analytics?.risks?.short || {}),
      ...(analytics?.drawdowns?.short || {}),
      ...(analytics?.efficiency?.short || {}),
      ...(analytics?.validation?.short || {}) 
    },
  };

  return (
    <div className="space-y-6">
      <PerformancePageLayout 
        config={totalAnalysisConfig} 
        data={{ metrics: metricsData as any }}
      />
    </div>
  )
}
