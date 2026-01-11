import { PerformanceNav } from "@/components/performance/performance-nav"
import { SelectedBacktestProvider } from "@/contexts/selected-backtest-context"

export default function PerformanceLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <SelectedBacktestProvider>
      <div className="flex flex-col h-full w-full">
        {/* Header with title and navigation */}
        <div className="border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
          <div className="px-6 pt-6 pb-2">
            <h1 className="text-2xl font-semibold tracking-tight">Performance Report</h1>
          </div>
          <PerformanceNav />
        </div>

        {/* Content area for child pages */}
        <div className="flex-1 overflow-auto">
          {children}
        </div>
      </div>
    </SelectedBacktestProvider>
  )
}
