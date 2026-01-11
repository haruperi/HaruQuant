"use client"

import { useState } from "react"
import { MarkdownRenderer } from "@/components/documentation/markdown-renderer"
import { TableOfContents } from "@/components/documentation/toc"
import { DocEditor } from "@/components/documentation/doc-editor"
import { Button } from "@/components/ui/button"
import { Edit } from "lucide-react"
import { useRouter } from "next/navigation"

interface TOCItem {
  id: string
  text: string
  level: number
}

interface DocPageWrapperProps {
  initialContent: string
  filePath: string  // Relative path like 'fundamentals/key-concepts.md'
  headings: TOCItem[]
}

export function DocPageWrapper({ initialContent, filePath, headings }: DocPageWrapperProps) {
  const [isEditing, setIsEditing] = useState(false)
  const router = useRouter()

  if (isEditing) {
    return (
      <div className="flex-1 p-6 h-full">
        <DocEditor
          path={filePath}
          onClose={() => setIsEditing(false)}
          onSave={() => {
             // Refresh the page to show updated content
             router.refresh()
          }}
        />
      </div>
    )
  }

  return (
    <div className="flex-1 p-6 relative group">
        <div className="absolute top-6 right-6 z-10 opacity-0 group-hover:opacity-100 transition-opacity">
            <Button variant="secondary" size="sm" onClick={() => setIsEditing(true)}>
                <Edit className="mr-2 h-4 w-4" /> Edit Page
            </Button>
        </div>

        <div className="flex gap-10 max-w-7xl mx-auto">
            {/* Main Content */}
            <div className="flex-1 w-full min-w-0">
                <MarkdownRenderer content={initialContent} />
            </div>

            {/* Right Sidebar TOC */}
            <div className="hidden xl:block w-64 shrink-0">
                <div className="sticky top-6">
                    <TableOfContents items={headings} />
                </div>
            </div>
        </div>
    </div>
  )
}
