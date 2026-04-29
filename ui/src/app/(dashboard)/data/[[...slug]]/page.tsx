"use client"

import DataPageContent from "@/components/data/data-page-content"
import { MarketDataProvider } from "@/contexts/market-data-context"

export default function DataPage() {
  return (
    <MarketDataProvider>
      <DataPageContent />
    </MarketDataProvider>
  )
}
