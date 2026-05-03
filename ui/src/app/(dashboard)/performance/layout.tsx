"use client"
import { PerformanceNav } from "@/components/performance/performance-nav"
import { SelectedBacktestProvider } from "@/contexts/selected-backtest-context"
import { useRegisterPageActions } from "@/hooks/useRegisterPageActions"
import { useRouter } from "next/navigation"

export default function PerformanceLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const router = useRouter()

  useRegisterPageActions(
    [
      {
        id: "navigate_performance_page",
        label: "Navigate Performance Page",
        description: "Switch between different performance analysis views (Overview, Trades Calendar, Strategy Analysis, etc.)",
        riskLevel: "view_only",
        parameters: [
          {
            name: "path",
            type: "string",
            description: "The sub-path or absolute app path to navigate to (e.g., 'overview', 'trades-calender', 'strategy-analysis', '/simulation', '/optimization')",
            required: true,
          }
        ]
      }
    ],
    {
      navigate_performance_page: ({ path }) => {
        if (typeof path !== "string") {
          return
        }
        router.push(path.startsWith("/") ? path : `/performance/${path}`)
      }
    }
  )

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
