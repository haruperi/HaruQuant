"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { Save, Play, RotateCcw, Loader2 } from "lucide-react"
import { MetadataForm } from "./metadata-form"
import { CodeEditor } from "./code-editor"
import { ConfigPreview } from "./config-preview"
import { VersionHistory } from "./version-history"
import { toast } from "sonner"
import { useStrategy, useStrategyMutations } from "@/lib/use-strategies"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { AlertCircle } from "lucide-react"

interface EditorLayoutProps {
    strategyId: string
}

interface StrategyEditorMetadata {
    name: string
    description: string
    status: "inactive" | "active" | "testing"
    category: string
    parameters: Record<string, unknown>
    parameterTypes: Record<string, string>
    symbol: string
    timeframe: string
    type: string
    moneyManagement: Record<string, unknown>
    variables: Record<string, unknown>
    variableTypes: Record<string, string>
}

const defaultMoneyManagement = {
    method: "Fixed lot size",
    positionSize: 0.1,
}

export function EditorLayout({ strategyId }: EditorLayoutProps) {
    const router = useRouter()
    const strategyIdNum = parseInt(strategyId)
    const { strategy, strategyCode, loading, error, refetch } = useStrategy(strategyIdNum)
    const { updateStrategy, updating } = useStrategyMutations()

    const [code, setCode] = React.useState("")
    const [metadata, setMetadata] = React.useState<StrategyEditorMetadata>({
        name: "",
        description: "",
        status: "inactive" as "inactive" | "active" | "testing",
        category: "",
        parameters: {},
        parameterTypes: {} as Record<string, string>,
        symbol: "",
        timeframe: "H1",
        type: "MetaTrader5 (hedged)",
        moneyManagement: defaultMoneyManagement,
        variables: {},
        variableTypes: {} as Record<string, string>
    })
    const [hasChanges, setHasChanges] = React.useState(false)

    // Store original values for comparison
    const [originalCode, setOriginalCode] = React.useState("")
    const [originalMetadata, setOriginalMetadata] = React.useState<StrategyEditorMetadata>({
        name: "",
        description: "",
        status: "inactive" as "inactive" | "active" | "testing",
        category: "",
        parameters: {},
        parameterTypes: {} as Record<string, string>,
        symbol: "",
        timeframe: "H1",
        type: "MetaTrader5 (hedged)",
        moneyManagement: defaultMoneyManagement,
        variables: {},
        variableTypes: {} as Record<string, string>
    })

    // Load strategy data when it's fetched
    React.useEffect(() => {
        if (strategyCode) {
            const codeStr = strategyCode.code || ""
            setCode(codeStr)
            setOriginalCode(codeStr)
        }
        if (strategy) {
            const meta = {
                name: strategy.name,
                description: strategy.description || "",
                status: strategy.status,
                category: strategy.category || "",
                parameters: strategyCode?.parameters || {},
                parameterTypes: strategyCode?.parameterTypes || {},
                symbol: strategyCode?.symbol || "EURUSD",
                timeframe: strategyCode?.timeframe || "H1",
                type: strategyCode?.type || "MetaTrader5 (hedged)",
                moneyManagement: strategyCode?.moneyManagement || defaultMoneyManagement,
                variables: strategyCode?.variables || {},
                variableTypes: strategyCode?.variableTypes || {}
            }
            setMetadata(meta)
            setOriginalMetadata(meta)
        }
    }, [strategy, strategyCode])

    // Track changes - compare both code and metadata
    React.useEffect(() => {
        const codeChanged = code !== originalCode
        const metadataChanged = JSON.stringify(metadata) !== JSON.stringify(originalMetadata)
        setHasChanges(codeChanged || metadataChanged)
    }, [code, metadata, originalCode, originalMetadata])

    const handleSave = async () => {
        try {
            // Sanitize code before saving to remove any global indentation issues
            const sanitizeCode = (code: string): string => {
                const lines = code.split('\n')

                // Find minimum indentation (excluding empty lines)
                let minIndent = Infinity
                for (const line of lines) {
                    if (line.trim().length > 0) {
                        const leadingSpaces = line.match(/^\s*/)?.[0].length || 0
                        minIndent = Math.min(minIndent, leadingSpaces)
                    }
                }

                // Remove the minimum indentation from all lines
                if (minIndent > 0 && minIndent !== Infinity) {
                    return lines.map(line => {
                        if (line.trim().length === 0) return ''
                        return line.substring(minIndent)
                    }).join('\n')
                }

                return code
            }

            // Update the strategy
            await updateStrategy(strategyIdNum, {
                name: metadata.name,
                description: metadata.description,
                status: metadata.status,
                category: metadata.category,
                code: sanitizeCode(code),
                parameters: metadata.parameters,
                symbol: metadata.symbol,
                timeframe: metadata.timeframe,
                type: metadata.type,
                parameterTypes: metadata.parameterTypes,
                moneyManagement: metadata.moneyManagement,
                variables: metadata.variables,
                variableTypes: metadata.variableTypes,
                changelog: "Updated via editor"
            })

            toast.success("Strategy saved successfully! New version created.")

            // Refetch the strategy to get the new version
            await refetch()

            // Reset the hasChanges flag
            setHasChanges(false)
        } catch (error: unknown) {
            toast.error(error instanceof Error ? error.message : "Failed to save strategy")
            console.error("Save error:", error)
        }
    }

    const handleDiscard = () => {
        // Revert both code and metadata to original values
        setCode(originalCode)
        setMetadata(originalMetadata)
        setHasChanges(false)
        toast.info("Changes discarded")
    }

    if (loading) {
        return (
            <div className="flex items-center justify-center h-[calc(100vh-6rem)]">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        )
    }

    if (error || !strategy) {
        return (
            <div className="p-8">
                <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>
                        {error || "Strategy not found"}
                    </AlertDescription>
                </Alert>
            </div>
        )
    }

    return (
        <div className="flex flex-col h-[calc(100vh-6rem)] gap-4">
             <div className="flex items-center justify-between border-b pb-4">
                <div>
                    <h2 className="text-2xl font-bold tracking-tight">{strategy.name}</h2>
                    <p className="text-sm text-muted-foreground">
                        Version {strategy.active_version} • Updated {new Date(strategy.updated_at).toLocaleString()}
                    </p>
                </div>
                <div className="flex items-center space-x-2">
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={handleDiscard}
                        disabled={!hasChanges}
                    >
                        <RotateCcw className="mr-2 h-4 w-4" />
                        Discard
                    </Button>
                    <Button
                        size="sm"
                        onClick={handleSave}
                        disabled={!hasChanges || updating}
                    >
                        {updating ? (
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        ) : (
                            <Save className="mr-2 h-4 w-4" />
                        )}
                        Save Changes
                    </Button>
                    <Button
                        size="sm"
                        variant="secondary"
                        onClick={() =>
                            router.push(
                                `/simulation/batch-auto?strategyId=${strategyId}`
                            )
                        }
                    >
                         <Play className="mr-2 h-4 w-4" />
                         Run Batch
                    </Button>
                </div>
            </div>

            <ResizablePanelGroup direction="horizontal" className="rounded-lg border">
                <ResizablePanel defaultSize={30} minSize={20}>
                    <div className="h-full p-4 bg-muted/10">
                        <Tabs defaultValue="metadata" className="h-full flex flex-col">
                            <TabsList className="w-full">
                                <TabsTrigger value="metadata" className="flex-1">Settings</TabsTrigger>
                                <TabsTrigger value="preview" className="flex-1">JSON</TabsTrigger>
                                <TabsTrigger value="history" className="flex-1">History</TabsTrigger>
                            </TabsList>
                            <TabsContent value="metadata" className="flex-1 overflow-hidden mt-4">
                                <MetadataForm
                                    metadata={metadata}
                                    onChange={setMetadata}
                                />
                            </TabsContent>
                             <TabsContent value="preview" className="flex-1 overflow-hidden mt-4">
                                <ConfigPreview
                                    metadata={metadata}
                                    version={strategy.active_version || undefined}
                                />
                            </TabsContent>
                            <TabsContent value="history" className="flex-1 overflow-hidden mt-0">
                                <VersionHistory
                                    strategyId={strategyIdNum}
                                    currentCode={code}
                                    onRestore={setCode}
                                />
                            </TabsContent>
                        </Tabs>
                    </div>
                </ResizablePanel>
                <ResizableHandle withHandle />
                <ResizablePanel defaultSize={70}>
                    <div className="h-full flex flex-col">
                         <div className="border-b px-4 py-2 bg-muted/30 text-xs font-mono text-muted-foreground flex justify-between items-center">
                            <span>strategy.py</span>
                            <span>Python 3.10</span>
                         </div>
                         <div className="flex-1">
                             <CodeEditor code={code} onChange={(val) => setCode(val || "")} />
                         </div>
                    </div>
                </ResizablePanel>
            </ResizablePanelGroup>
        </div>
    )
}
