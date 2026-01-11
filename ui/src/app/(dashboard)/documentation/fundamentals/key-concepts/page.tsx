import fs from "fs"
import path from "path"
import matter from "gray-matter"
import { DocPageWrapper } from "@/components/documentation/doc-page-wrapper"

export default async function KeyConceptsPage() {
    const docsDirectory = path.join(process.cwd(), "..", "docs", "fundamentals")
    const relativePath = "fundamentals/key-concepts.md"
    const filePath = path.join(process.cwd(), "..", "docs", relativePath)

    // Read markdown file
    if (!fs.existsSync(filePath)) {
        return (
            <div className="flex-1 p-6">
                <div className="alert alert-error">Documentation file not found: {filePath}</div>
            </div>
        )
    }

    const fileContent = fs.readFileSync(filePath, "utf8")
    const { content } = matter(fileContent)

    // Extract headings for TOC
    const headings = content.match(/^#{2,3}\s.+/gm)?.map((heading) => {
        const level = heading.match(/^#+/)?.[0].length || 2
        const text = heading.replace(/^#+\s/, "")
        const id = text
            .toLowerCase()
            .replace(/[^a-z0-9]+/g, "-")
            .replace(/(^-|-$)+/g, "")
        return { id, text, level }
    }) || []

    return (
        <DocPageWrapper
            initialContent={content}
            filePath={relativePath}
            headings={headings}
        />
    )
}
