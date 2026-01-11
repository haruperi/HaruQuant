import { PerformancePageHeader } from "@/components/performance/performance-page-header"

export default function TradeAnalysisPage() {
    return (
        <div className="flex flex-col h-full w-full">
            <PerformancePageHeader title="Trade Analysis" />
            <div className="flex-1 flex items-center justify-center p-6 bg-muted/10">
                <div className="text-center">
                    <h3 className="text-lg font-medium text-muted-foreground">Detailed Trade Analysis Coming Soon</h3>
                </div>
            </div>
        </div>
    )
}
