"use client"

import EdgeLabDataPage from "../edge-lab/page"
import { EdgeLabDataProvider } from "@/contexts/edge-lab-data-context"

export default function DataPage() {
  return (
    <EdgeLabDataProvider>
      <EdgeLabDataPage />
    </EdgeLabDataProvider>
  )
}
