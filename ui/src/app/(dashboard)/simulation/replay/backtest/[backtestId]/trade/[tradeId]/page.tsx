import { SimulationPage } from "@/components/historical-run/simulation-page"

interface SimulationReplayTradePageProps {
  params: Promise<{
    backtestId: string
    tradeId: string
  }>
}

export default async function SimulationReplayTradePage({
  params,
}: SimulationReplayTradePageProps) {
  const { backtestId, tradeId } = await params

  return (
    <SimulationPage
      initialTab="replay"
      replayBacktestId={backtestId}
      replayTradeId={tradeId}
      autoStartReplay
    />
  )
}
