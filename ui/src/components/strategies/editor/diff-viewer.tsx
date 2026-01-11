"use client"

import { DiffEditor } from "@monaco-editor/react"
import { useTheme } from "next-themes"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"

interface DiffViewerProps {
    open: boolean
    onOpenChange: (open: boolean) => void
    original: string
    modified: string
    title?: string
}

export function DiffViewer({ open, onOpenChange, original, modified, title = "Version Comparison" }: DiffViewerProps) {
    const { resolvedTheme } = useTheme()

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-[90vw] w-[90vw] h-[90vh] flex flex-col p-6">
                <DialogHeader className="mb-4">
                    <DialogTitle>{title}</DialogTitle>
                </DialogHeader>
                <div className="flex-1 border rounded-md overflow-hidden">
                    <DiffEditor
                        height="100%"
                        original={original}
                        modified={modified}
                        language="python"
                        theme={resolvedTheme === "dark" ? "vs-dark" : "light"}
                        options={{
                            renderSideBySide: true,
                            minimap: { enabled: false },
                            scrollBeyondLastLine: false,
                            originalEditable: false,
                            readOnly: true
                        }}
                    />
                </div>
            </DialogContent>
        </Dialog>
    )
}
