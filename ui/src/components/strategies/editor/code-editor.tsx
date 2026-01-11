"use client"

import Editor from "@monaco-editor/react"
import { useTheme } from "next-themes"

interface CodeEditorProps {
    code: string
    onChange: (value: string | undefined) => void
}

export function CodeEditor({ code, onChange }: CodeEditorProps) {
    const { resolvedTheme } = useTheme()

    // Sanitize code to remove common indentation issues
    const handleCodeChange = (value: string | undefined) => {
        if (!value) {
            onChange(value)
            return
        }

        // Fix common indentation issues:
        // 1. Remove leading whitespace from the first line if it exists
        // 2. Ensure consistent indentation throughout
        const lines = value.split('\n')

        // Find the minimum indentation (excluding empty lines)
        let minIndent = Infinity
        for (const line of lines) {
            if (line.trim().length > 0) {
                const leadingSpaces = line.match(/^\s*/)?.[0].length || 0
                minIndent = Math.min(minIndent, leadingSpaces)
            }
        }

        // If there's extra indentation at the start, remove it
        if (minIndent > 0 && minIndent !== Infinity) {
            const correctedLines = lines.map(line => {
                if (line.trim().length === 0) return line
                return line.substring(minIndent)
            })
            onChange(correctedLines.join('\n'))
        } else {
            onChange(value)
        }
    }

    return (
        <div className="h-full w-full border rounded-md overflow-hidden">
            <Editor
                height="100%"
                defaultLanguage="python"
                value={code}
                theme={resolvedTheme === "dark" ? "vs-dark" : "light"}
                onChange={handleCodeChange}
                options={{
                    minimap: { enabled: false },
                    fontSize: 14,
                    scrollBeyondLastLine: false,
                    automaticLayout: true,
                    tabSize: 4,
                    insertSpaces: true,
                    detectIndentation: true,
                    trimAutoWhitespace: true,
                    formatOnPaste: true,
                    formatOnType: true,
                    // Autocomplete & IntelliSense settings
                    suggest: {
                        showWords: true,
                        showSnippets: true,
                        showClasses: true,
                        showFunctions: true,
                        showVariables: true,
                        showMethods: true,
                        showKeywords: true,
                        preview: true,
                        previewMode: "prefix"
                    },
                    quickSuggestions: {
                        other: true,
                        comments: false,
                        strings: false
                    },
                    suggestOnTriggerCharacters: true,
                    parameterHints: { enabled: true },
                    wordBasedSuggestions: "allDocuments",
                }}
            />
        </div>
    )
}
