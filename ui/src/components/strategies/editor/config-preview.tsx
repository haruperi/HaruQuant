"use client"

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"

interface ConfigPreviewProps {
    metadata: {
        name: string
        description: string
        status: "active" | "inactive" | "testing"
        category: string
        parameters: Record<string, unknown>
        symbol?: string
        timeframe?: string
        type?: string
        moneyManagement?: Record<string, unknown>
        variables?: Record<string, unknown>
    }
    version?: string
}

export function ConfigPreview({ metadata, version }: ConfigPreviewProps) {
    const config = {
        name: metadata.name,
        description: metadata.description,
        category: metadata.category,
        status: metadata.status,
        active: metadata.status === "active",
        symbol: metadata.symbol,
        timeframe: metadata.timeframe,
        type: metadata.type,
        moneyManagement: metadata.moneyManagement,
        parameters: metadata.parameters,
        variables: metadata.variables,
        version: version || "current"
    }

    return (
        <Card className="h-full flex flex-col">
            <CardHeader>
                <CardTitle>Configuration JSON</CardTitle>
                <CardDescription>
                    Read-only preview of strategy configuration
                </CardDescription>
            </CardHeader>
            <CardContent className="flex-1 p-0">
                <ScrollArea className="h-full">
                    <div className="bg-zinc-950 text-zinc-50 font-mono text-sm p-4 rounded-b-lg">
                        <pre>{JSON.stringify(config, null, 2)}</pre>
                    </div>
                </ScrollArea>
            </CardContent>
        </Card>
    )
}
