import { Skeleton } from "@/components/ui/skeleton"
import { Card, CardContent, CardHeader } from "@/components/ui/card"

export function TradeStatsSkeleton() {
  return (
    <div className="space-y-6 p-6">
      {/* Tabs skeleton */}
      <div className="flex space-x-2 border-b">
        <Skeleton className="h-10 w-24" />
        <Skeleton className="h-10 w-24" />
        <Skeleton className="h-10 w-24" />
        <Skeleton className="h-10 w-24" />
        <Skeleton className="h-10 w-24" />
      </div>

      {/* Tab content skeleton */}
      <div className="space-y-4">
        {/* Section 1 */}
        <div className="space-y-3">
          <Skeleton className="h-5 w-32" />
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-6 w-24" />
            </div>
            <div className="space-y-2">
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-6 w-24" />
            </div>
            <div className="space-y-2">
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-6 w-24" />
            </div>
            <div className="space-y-2">
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-6 w-24" />
            </div>
          </div>
        </div>

        {/* Section 2 */}
        <div className="space-y-3">
          <Skeleton className="h-5 w-32" />
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-6 w-24" />
            </div>
            <div className="space-y-2">
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-6 w-24" />
            </div>
            <div className="space-y-2">
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-6 w-24" />
            </div>
            <div className="space-y-2">
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-6 w-24" />
            </div>
          </div>
        </div>

        {/* Section 3 */}
        <div className="space-y-3">
          <Skeleton className="h-5 w-32" />
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-6 w-24" />
            </div>
            <div className="space-y-2">
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-6 w-24" />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export function TradeChartSkeleton() {
  return (
    <div className="flex h-full w-full items-center justify-center p-6">
      <div className="w-full space-y-4">
        {/* Chart header skeleton */}
        <div className="flex items-center justify-between">
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-6 w-32" />
        </div>

        {/* Chart area skeleton */}
        <Skeleton className="h-[600px] w-full rounded-lg" />

        {/* Chart controls skeleton */}
        <div className="flex justify-between">
          <Skeleton className="h-8 w-24" />
          <Skeleton className="h-8 w-24" />
        </div>
      </div>
    </div>
  )
}

export function TradeDetailSkeleton() {
  return (
    <div className="flex h-full w-full flex-col overflow-hidden">
      {/* Header skeleton */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between border-b bg-background px-4 sm:px-6 py-3 sm:py-4 gap-3 sm:gap-0">
        <div className="flex items-center gap-2 sm:gap-4 w-full sm:w-auto">
          <Skeleton className="h-9 w-16 sm:w-20" />
          <Skeleton className="h-6 sm:h-7 w-48 sm:w-64" />
        </div>
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <Skeleton className="h-9 w-20 sm:w-28" />
          <Skeleton className="h-6 w-12 sm:w-16" />
          <Skeleton className="h-9 w-16 sm:w-20" />
        </div>
      </div>

      {/* Main content skeleton */}
      <div className="flex flex-1 overflow-hidden flex-col lg:flex-row">
        {/* Left sidebar skeleton */}
        <div className="w-full lg:w-[30%] xl:w-[25%] overflow-y-auto border-b lg:border-b-0 lg:border-r bg-background max-h-[50vh] lg:max-h-none">
          <TradeStatsSkeleton />
        </div>

        {/* Right content skeleton */}
        <div className="flex-1 overflow-hidden bg-background">
          <TradeChartSkeleton />
        </div>
      </div>
    </div>
  )
}
