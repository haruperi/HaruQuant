"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { BacktestConfigForm } from "@/components/backtest/config-form"
import { BacktestExecutionView } from "@/components/backtest/execution-view"
import { BacktestImportForm } from "@/components/backtest/import-form"
import { Button } from "@/components/ui/button"
import { UploadCloud } from "lucide-react"
import { toast } from "sonner"

export default function BacktestPage() {
    const [view, setView] = useState<"config" | "execution" | "results" | "import">("config")
    const [backtestId, setBacktestId] = useState<number | null>(null)
    const [strategyId, setStrategyId] = useState<number | null>(null)

    const handleStart = (btId: number, stId: number) => {
        setBacktestId(btId)
        setStrategyId(stId)
        setView("execution")
    }

    const handleCancel = () => {
        setView("config")
        setBacktestId(null)
        setStrategyId(null)
        toast.info("Backtest aborted.")
    }

    const router = useRouter()

    const handleComplete = () => {
        if (backtestId) {
            toast.success("Backtest execution finished.")
            router.push(`/performance?selected=${backtestId}`)
        }
    }

    const handleBackToConfig = () => {
        setView("config")
        setBacktestId(null)
        setStrategyId(null)
    }

    return (
        <div className="flex flex-col gap-6 p-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Backtest</h1>
                    <p className="text-muted-foreground">
                        Configure and run historical simulations for your strategies.
                    </p>
                </div>
                {view === "config" && (
                    <Button variant="outline" onClick={() => setView("import")}>
                        <UploadCloud className="mr-2 h-4 w-4" />
                        Import Trades
                    </Button>
                )}
                 {view === "import" && (
                    <Button variant="outline" onClick={() => setView("config")}>
                        Back to Config
                    </Button>
                )}
            </div>

            <div className="w-full">
                {view === "config" && (
                    <BacktestConfigForm onSubmit={handleStart} />
                )}

                {view === "import" && (
                    <BacktestImportForm onCancel={() => setView("config")} />
                )}

                {view === "execution" && backtestId && strategyId && (
                    <BacktestExecutionView
                        backtestId={backtestId}
                        strategyId={strategyId}
                        onCancel={handleCancel}
                        onComplete={handleComplete}
                    />
                )}
            </div>
        </div>
    )
}
