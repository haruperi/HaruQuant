import { SimulationPage } from "@/components/historical-run/simulation-page"

interface SimulationReplayBacktestPageProps {
  params: Promise<{
    backtestId: string
  }>
}

export default async function SimulationReplayBacktestPage({
  params,
}: SimulationReplayBacktestPageProps) {
  const { backtestId } = await params

  return (
    <SimulationPage
      initialTab="replay"
      replayBacktestId={backtestId}
      autoStartReplay
    />
  )
}
