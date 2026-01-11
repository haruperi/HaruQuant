import { PerformancePageHeader } from "@/components/performance/performance-page-header"

export default function PeriodicAnalysisPage() {
    return (
        <div className="flex flex-col h-full w-full">
            <PerformancePageHeader title="Periodic Analysis" />
            <div className="flex-1 flex items-center justify-center p-6 bg-muted/10">
                <div className="text-center">
                    <h3 className="text-lg font-medium text-muted-foreground">Detailed Periodic Analysis Coming Soon</h3>
                </div>
            </div>
        </div>
    )
}
