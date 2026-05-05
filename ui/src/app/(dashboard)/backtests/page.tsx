import { AgenticFirmPage } from "@/components/agentic-firm/agentic-firm-page"

export default function BacktestsPage() {
  return (
    <AgenticFirmPage
      title="Backtest Center"
      subtitle="Historical runs, metrics, equity behavior, drawdown, trades, long-short split, and period analysis."
      status="Simulation evidence"
      sections={[
        { title: "Runs", items: ["Backtest runs", "Metrics", "Equity curve", "Drawdown"] },
        { title: "Diagnostics", items: ["Trades", "Long/short split", "Period analysis"] },
      ]}
    />
  )
}
