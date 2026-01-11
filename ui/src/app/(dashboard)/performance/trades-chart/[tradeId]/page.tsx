import { TradeDetailView } from "@/components/performance/trade-detail-view"
import { TradeDetailErrorBoundary } from "@/components/performance/trade-detail-error-boundary"
import { use } from "react"

export default function TradeDetailPage({
  params,
}: {
  params: Promise<{ tradeId: string }>
}) {
  const { tradeId } = use(params)
  return (
    <TradeDetailErrorBoundary>
      <TradeDetailView tradeId={Number(tradeId)} />
    </TradeDetailErrorBoundary>
  )
}
