"use client"

import { useState, useEffect } from "react"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Button } from "@/components/ui/button"
import { GitCommit, History, RotateCcw, FileDiff, Loader2 } from "lucide-react"
import { format } from "date-fns"
import { DiffViewer } from "./diff-viewer"
import { toast } from "sonner"
import { useStrategyVersions } from "@/lib/use-strategies"
import { strategyApi } from "@/lib/api/strategies"

interface VersionHistoryProps {
    strategyId: number
    currentCode: string
    onRestore: (code: string) => void
}

export function VersionHistory({ strategyId, currentCode, onRestore }: VersionHistoryProps) {
    const { versions, loading, error } = useStrategyVersions(strategyId)
    const [selectedVersion, setSelectedVersion] = useState<any>(null)
    const [selectedVersionCode, setSelectedVersionCode] = useState<string>("")
    const [showDiff, setShowDiff] = useState(false)
    const [loadingCode, setLoadingCode] = useState(false)

    const handleVersionClick = async (version: any) => {
        setSelectedVersion(version)
        setShowDiff(false)

        // Fetch the code for this version
        try {
            setLoadingCode(true)
            const codeData = await strategyApi.getVersionCode(strategyId, version.id)
            setSelectedVersionCode(codeData.code)
        } catch (err) {
            toast.error("Failed to load version code")
        } finally {
            setLoadingCode(false)
        }
    }

    const handleRestore = async (version: any) => {
        try {
            setLoadingCode(true)
            const codeData = await strategyApi.getVersionCode(strategyId, version.id)
            onRestore(codeData.code)
            toast.success(`Restored version ${version.version}`)
        } catch (err) {
            toast.error("Failed to restore version")
        } finally {
            setLoadingCode(false)
        }
    }

    const handleRollback = async (version: any) => {
        try {
            await strategyApi.rollbackVersion(strategyId, version.id)
            toast.success(`Rolled back to version ${version.version}`)
            window.location.reload()
        } catch (err) {
            toast.error("Failed to rollback version")
        }
    }

    if (loading) {
        return (
            <div className="flex items-center justify-center h-full">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
        )
    }

    if (error) {
        return (
            <div className="p-4 text-sm text-muted-foreground text-center">
                Error loading versions: {error}
            </div>
        )
    }

    if (versions.length === 0) {
        return (
            <div className="p-4 text-sm text-muted-foreground text-center">
                No version history available
            </div>
        )
    }

    return (
        <div className="h-full flex flex-col">
            <div className="px-4 py-2 border-b bg-muted/20">
                <h3 className="font-semibold text-sm flex items-center">
                    <History className="mr-2 h-4 w-4" />
                    Commits & Saves
                </h3>
            </div>
            <ScrollArea className="flex-1">
                <div className="p-4 space-y-4">
                    {versions.map((version, index) => (
                        <div key={version.id} className="flex flex-col gap-2 p-3 border rounded-lg bg-card hover:bg-muted/50 transition-colors">
                            <div className="flex items-start justify-between">
                                <div className="space-y-1 flex-1">
                                    <div className="flex items-center gap-2">
                                         <GitCommit className="h-4 w-4 text-muted-foreground" />
                                         <span className="font-medium text-sm">
                                            Version {version.version}
                                         </span>
                                    </div>
                                    <div className="text-xs text-muted-foreground ml-6">
                                        {format(new Date(version.created_at), "MMM d, yyyy HH:mm")}
                                    </div>
                                    {version.changelog && (
                                        <div className="text-xs text-muted-foreground ml-6">
                                            {version.changelog}
                                        </div>
                                    )}
                                </div>
                            </div>
                            <div className="flex gap-2 ml-6 mt-1">
                                <Button
                                    variant="outline"
                                    size="sm"
                                    className="h-7 text-xs"
                                    onClick={async () => {
                                        await handleVersionClick(version)
                                        setShowDiff(true)
                                    }}
                                    disabled={loadingCode}
                                >
                                    <FileDiff className="mr-1 h-3 w-3" />
                                    Compare
                                </Button>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    className="h-7 text-xs hover:bg-destructive/10 hover:text-destructive hover:border-destructive/30"
                                    onClick={() => handleRestore(version)}
                                    disabled={loadingCode}
                                >
                                    <RotateCcw className="mr-1 h-3 w-3" />
                                    Restore
                                </Button>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    className="h-7 text-xs"
                                    onClick={() => handleRollback(version)}
                                    disabled={loadingCode}
                                >
                                    Rollback
                                </Button>
                            </div>
                        </div>
                    ))}
                </div>
            </ScrollArea>

            {selectedVersion && selectedVersionCode && (
                <DiffViewer
                    open={showDiff}
                    onOpenChange={setShowDiff}
                    original={selectedVersionCode}
                    modified={currentCode}
                    title={`Comparing: Current vs Version ${selectedVersion.version}`}
                />
            )}
        </div>
    )
}
